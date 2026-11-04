# ZARB BILLIARD Telegram bot

## Hozirgi funksiyalar
- 10 ta stol
- 50 000 so'm/soat
- Har boshlangan daqiqa bo'yicha hisob
- Boshlash, pauza, davom ettirish, tugatish
- Kunlik yakunlangan o'yinlar va tushum
- Birinchi `/setup` yuborgan foydalanuvchi admin bo'ladi
- Admin kassirlarni Telegram ID orqali qo'shadi

## Xavfsizlik
BotFather tokenini hech kimga yubormang va ommaviy GitHub repozitoriyasiga joylamang.
Tokenni hosting xizmatida `BOT_TOKEN` nomli maxfiy environment variable sifatida kiriting.

## Ishga tushirish
Python 3.10+ kerak.

```bash
pip install -r requirements.txt
export BOT_TOKEN="BOTFATHER_TOKENINGIZ"
python bot.py
```

Windows PowerShell:
```powershell
$env:BOT_TOKEN="BOTFATHER_TOKENINGIZ"
python bot.py
```

## Telegram'da birinchi sozlash
1. Botga `/start` yuboring.
2. Birinchi admin `/setup` yuboradi.
3. O'z Telegram ID'ingizni bilish uchun `/myid`.
4. Kassir botni ochib `/start` va `/myid` yuboradi.
5. Admin: `/addcashier KASSIR_ID`
6. Kassirni o'chirish: `/delcashier KASSIR_ID`

## Eslatma
Bu boshlang'ich versiya. Bot doim ishlashi uchun uni doimiy ishlaydigan hostingga joylash kerak.
SQLite fayli saqlanadigan persistent disk kerak; vaqtinchalik fayl tizimiga joylamang.
Tarif `bot.py` ichidagi `RATE_PER_HOUR` qiymatidan o'zgartiriladi.
