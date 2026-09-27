FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bot'ning bazasini ulash uchun (agar bot containerida bo'lsa)
# Bu yerda bot DB'si shared service orqali ulanadi (v2.0'da)

CMD ["python", "main.py"]
