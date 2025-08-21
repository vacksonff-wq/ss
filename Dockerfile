# استفاده از تصویر پایه Python
FROM python:3.11-slim

# نصب ffmpeg و ابزارهای ضروری
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

# ایجاد دایرکتوری پروژه
WORKDIR /app

# کپی کردن فایل‌ها
COPY . .

# نصب dependencies
RUN pip install --no-cache-dir -r requirements.txt

# دستور اجرای ربات
CMD ["python", "botq.py"]
