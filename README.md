# 7075.uz Web Sayt - Telegram Login

Telegram orqali autentifikatsiya bilan web sayt. Bot bilan bir xil database'ni ishlatadi.

## 1. O'rnatish

```bash
cd 7075_taxi_web
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

## 2. Sozlash

`.env` faylini oching:
```
BOT_TOKEN=BotFather'dan olingan token
DB_PATH=../7075_taxi_bot/taxi.db  # Bot bilan shared
PORT=8000
```

## 3. Ishga tushirish (localhost)

```bash
python main.py
```

Keyin **http://localhost:8000** da oching.

## 4. Telegram Login Widget sozlash

`templates/index.html`da `data-telegram-login` qatorini o'zgartiring:

```html
data-telegram-login="YOUR_BOT_USERNAME"
```

`YOUR_BOT_USERNAME` o'rniga @BotFather bergan bot username'ingizni qo'ying.

Masalan: agar bot `@7075_uz_bot` bo'lsa:
```html
data-telegram-login="7075_uz_bot"
```

## 5. Ishchi Jarayoni

### Yo'lovchi:
1. Telegram Login Widget bilan kirish
2. "E'lonlar" bo'limida taksi e'lonlarini ko'rish
3. "Joy band qilish" tugmasi bilan joy band qilish
4. "Buyurtmalarim"da joyning holatini ko'rish

### Taksichi:
1. Bot orqali e'lon berish
2. Web saytda "Buyurtmalarim" ko'rish
3. Bot'da "✅ Qabul qilish" yoki "❌ Rad etish"

## 6. Bot bilan integration

Web sayt va bot **bir xil SQLite database'ni** ishlatadi:
- Bot `/7075_taxi_bot/taxi.db` dan e'lonlarni yozadi
- Web sayt shu bazadan o'qiydi va buyurtmalarni yozadi
- Har ikkala taraf bir-birining ma'lumotlarini ko'radi

## 7. Railway'ga deploy

Bot va web saytni alohida projectlarda deploy qiling:

### A. Bot (allaqachon deploy qilingan)
- Repository: `7075-taxi-bot`
- Environment: `BOT_TOKEN`, `DB_PATH=/tmp/taxi.db`

### B. Web sayt (yangi)
- Repository: `7075-taxi-web`
- Environment: `BOT_TOKEN`, `DB_PATH=/tmp/taxi.db`
- Port: 8000 (Railway avtomatik)

**Muhim:** Ikkala container ham `/tmp/taxi.db`'ga yozishsa, data conflict bo'lishi mumkin.
**Yechim v2.0'da:** PostgreSQL qo'shish yoki shared volume.

## 8. API Endpoints

- `POST /api/auth/telegram` — Telegram login
- `GET /api/announcements` — E'lonlarni olish
- `GET /api/announcements/my` — O'z e'lonlari (taksichi)
- `GET /api/bookings/my` — O'z buyurtmalari (yo'lovchi)
- `POST /api/bookings/create` — Joy band qilish
- `GET /api/user/me` — Profil ma'lumotlari

## 9. Xatolar va yechimlar

**Q: "db file is locked"**
- A: Bot va web sayt bir vaqtda bir xil bazaga yozmoqchi. 
- Yechim: PostgreSQL qo'shish (v2.0)

**Q: "Telegram Login ishlamaydi"**
- A: Bot username'i to'g'ri kiritildi mi? `data-telegram-login="..."`
- A: HTTPS'ga bo'lishi kerak (localhost'da test uchun ishlamaydi widget)

**Q: "Cookie'lar o'chirilmaydi"**
- A: Simple session uchun hozircha. JWT token implementatsiyasi kerak (v2.0)

## 10. v2.0 Features (Plan)

- PostgreSQL database (production)
- JWT authentication
- Payment integration (Click/Payme)
- Email/SMS notifications
- Admin dashboard
- Rating system
- Analytics
