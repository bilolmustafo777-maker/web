import os
import json
from fastapi import FastAPI, Request, HTTPException, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiosqlite
from datetime import datetime, timedelta
import asyncio

from telegram_auth import verify_telegram_auth, get_or_create_user_from_telegram

# .env dan BOT_TOKEN o'qish
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "../7075_taxi_bot/taxi.db")  # Bot bilan shared DB

app = FastAPI(title="7075.uz Taksi")

# CORS middleware (Frontend bot-dan har joydan so'rov qila olsin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static fayllar (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ============== Database helpers ==============

async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


# ============== Telegram Login API ==============

@app.post("/api/auth/telegram")
async def telegram_login(request: Request):
    """Telegram Login Widget'dan kelgan data'ni verify qiladi.
    Foydalanuvchini bazaga qo'shadi yoki yangilaydi.
    Session cookie qo'yadi."""
    
    data = await request.json()
    
    # Telegram data'ni verify qilish
    is_valid = await verify_telegram_auth(data, BOT_TOKEN)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    
    # Bazada foydalanuvchi yaratish yoki yangilash
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        tg_id = await get_or_create_user_from_telegram(data, db)
        
        # Foydalanuvchi ma'lumotlarini olish (role, avatar)
        cur = await db.execute(
            "SELECT * FROM users WHERE tg_id=?", (tg_id,)
        )
        user = await cur.fetchone()
    
    # Session qo'yish (optionally, simple)
    response = JSONResponse({
        "success": True,
        "tg_id": tg_id,
        "full_name": user["full_name"],
        "username": user["username"],
        "role": user["role"],
    })
    
    # Token-like simple session (production'da JWT ishlatish kerak)
    response.set_cookie(
        "session_tg_id",
        str(tg_id),
        max_age=30*24*60*60,  # 30 kun
        httponly=True,
    )
    
    return response


# ============== E'lonlar API ==============

@app.get("/api/announcements")
async def get_announcements(from_city: str = None, to_city: str = None):
    """Faol taksi e'lonlarini olish (yo'lovchilar uchun)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = "SELECT * FROM announcements WHERE status='active' AND available_seats>0"
        params = []
        
        if from_city and from_city != "Barchasi":
            query += " AND from_city=?"
            params.append(from_city)
        if to_city and to_city != "Barchasi":
            query += " AND to_city=?"
            params.append(to_city)
        
        query += " ORDER BY created_at DESC"
        
        cur = await db.execute(query, params)
        anns = await cur.fetchall()
        
        result = []
        for ann in anns:
            # Haydovchi ma'lumotlarini qo'shish
            driver_cur = await db.execute(
                "SELECT full_name, username, phone, car_brand, plate_number, has_luggage, takes_parcel "
                "FROM users WHERE tg_id=?",
                (ann["driver_id"],)
            )
            driver = await driver_cur.fetchone()
            
            result.append({
                "id": ann["id"],
                "from_city": ann["from_city"],
                "to_city": ann["to_city"],
                "trip_date": ann["trip_date"],
                "car_type": ann["car_type"],
                "total_seats": ann["total_seats"],
                "available_seats": ann["available_seats"],
                "driver": {
                    "full_name": driver["full_name"],
                    "username": driver["username"],
                    "phone": driver["phone"],
                    "car_brand": driver["car_brand"],
                    "plate_number": driver["plate_number"],
                    "has_luggage": driver["has_luggage"],
                    "takes_parcel": driver["takes_parcel"],
                } if driver else {}
            })
        
        return result


@app.get("/api/announcements/my")
async def get_my_announcements(session_tg_id: str = Cookie(None)):
    """O'z e'lonlarini olish (haydovchilar uchun)."""
    if not session_tg_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cur = await db.execute(
            "SELECT * FROM announcements WHERE driver_id=? ORDER BY created_at DESC",
            (int(session_tg_id),)
        )
        anns = await cur.fetchall()
        
        return [dict(ann) for ann in anns]


# ============== Buyurtmalar API ==============

@app.get("/api/bookings/my")
async def get_my_bookings(session_tg_id: str = Cookie(None)):
    """O'z buyurtmalarini olish (yo'lovchilar uchun)."""
    if not session_tg_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cur = await db.execute(
            "SELECT * FROM bookings WHERE client_id=? ORDER BY created_at DESC",
            (int(session_tg_id),)
        )
        bookings = await cur.fetchall()
        
        result = []
        for b in bookings:
            ann_cur = await db.execute(
                "SELECT from_city, to_city, trip_date, car_type FROM announcements WHERE id=?",
                (b["announcement_id"],)
            )
            ann = await ann_cur.fetchone()
            
            result.append({
                "id": b["id"],
                "announcement_id": b["announcement_id"],
                "seats": b["seats"],
                "status": b["status"],
                "payment_status": b["payment_status"],
                "announcement": dict(ann) if ann else {}
            })
        
        return result


@app.post("/api/bookings/create")
async def create_booking(
    announcement_id: int,
    seats: int,
    session_tg_id: str = Cookie(None)
):
    """Joy band qilish (yo'lovchi)."""
    if not session_tg_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # E'lon tekshirish
        ann_cur = await db.execute(
            "SELECT available_seats FROM announcements WHERE id=?",
            (announcement_id,)
        )
        ann = await ann_cur.fetchone()
        
        if not ann or ann["available_seats"] < seats:
            raise HTTPException(status_code=400, detail="Not enough seats")
        
        # Booking qo'shish
        cur = await db.execute(
            "INSERT INTO bookings (announcement_id, client_id, seats) VALUES (?,?,?)",
            (announcement_id, int(session_tg_id), seats)
        )
        booking_id = cur.lastrowid
        await db.commit()
        
        return {"booking_id": booking_id, "status": "pending_payment"}


# ============== Profil API ==============

@app.get("/api/user/me")
async def get_current_user(session_tg_id: str = Cookie(None)):
    """Joriy foydalanuvchi ma'lumotlari."""
    if not session_tg_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        cur = await db.execute(
            "SELECT * FROM users WHERE tg_id=?",
            (int(session_tg_id),)
        )
        user = await cur.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return dict(user)


# ============== HTML pages ==============

@app.get("/", response_class=HTMLResponse)
async def index():
    """Bosh sahifa - Login."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard - e'lonlar / buyurtmalar."""
    with open("templates/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/announcements-page", response_class=HTMLResponse)
async def announcements_page():
    """E'lonlarni ko'rish va band qilish."""
    with open("templates/announcements.html", "r", encoding="utf-8") as f:
        return f.read()


# ============== Health check ==============

@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
