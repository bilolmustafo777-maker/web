"""
Telegram Login Widget - verificatsiya qilish
Telegram'dan kelgan data hashini tekshiradi.
"""

import hashlib
import hmac
from typing import Optional


async def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """Telegram Login Widget'dan kelgan data'ni verify qiladi.
    
    Telegram data quyidagi ustunlarni o'z ichiga oladi:
    - id, first_name, last_name (ixtiyoriy), username (ixtiyoriy), 
    - photo_url (ixtiyoriy), auth_date, hash
    
    hash = HMAC-SHA256((BOT_TOKEN), concatenated_data)
    """
    if "hash" not in data:
        return False
    
    received_hash = data.pop("hash")
    
    # Data'ni tartiblash va string qilib concatenate qilish
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )
    
    # BOT_TOKEN'dan secret key yaratish
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # HMAC-SHA256 hisoblash
    computed_hash = hmac.new(
        secret_key, 
        data_check_string.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    return computed_hash == received_hash


async def get_or_create_user_from_telegram(tg_data: dict, db_connection):
    """Telegram'dan kelgan foydalanuvchi ma'lumotlaridan
    bazada user yaratadi yoki yangilaydi."""
    import aiosqlite
    
    tg_id = int(tg_data["id"])
    
    # Agar user mavjud bo'lsa, mavjudning o'zgartirish, yo'q bo'lsa yaratish
    cur = await db_connection.execute(
        "SELECT tg_id FROM users WHERE tg_id=?", (tg_id,)
    )
    exists = await cur.fetchone()
    
    full_name = tg_data.get("first_name", "")
    if "last_name" in tg_data:
        full_name += f" {tg_data['last_name']}"
    
    username = tg_data.get("username")
    
    if not exists:
        # Foydalanuvchi yangi bo'lsa, qo'shish (roli aniqlanmagan)
        await db_connection.execute(
            """INSERT INTO users (tg_id, full_name, username)
               VALUES (?, ?, ?)""",
            (tg_id, full_name.strip(), username),
        )
    else:
        # Mavjud bo'lsa, ma'lumotlarni yangilash
        await db_connection.execute(
            """UPDATE users SET full_name=?, username=? WHERE tg_id=?""",
            (full_name.strip(), username, tg_id),
        )
    
    await db_connection.commit()
    return tg_id
