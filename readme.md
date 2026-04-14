# Mood2Movie

## ติดตั้งโปรเจค

### 1. clone โค้ดจาก Git
```bash
git clone https://github.com/sirikan711/Mood2Movies.git
cd mood2movie_project
```

### 2. สร้าง virtual environment
```bash
python -m venv venv
```

### 3. เปิดใช้งาน virtual environment
- Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```
- Windows CMD:
```cmd
.venv\Scripts\activate
```
- macOS / Linux:
```mac
source venv/bin/activate
```

### 4. ติดตั้ง dependencies
```bash
pip install -r requirements.txt
```

### 5. ตั้งค่าตัวแปรแวดล้อม
คัดลอกไฟล์ `.env.example` เป็น `.env` แล้วแก้ค่าตามเครื่องของคุณ
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

### 6. ตัวอย่างไฟล์ `.env`
```dotenv
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=mood2movie_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1234
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
TMDB_API_KEY=your-tmdb-api-key-here
```

### 7. สร้างฐานข้อมูล PostgreSQL
ใช้คำสั่งใน PostgreSQL Shell:
```sql
CREATE DATABASE mood2movie_db;
```
ถ้าใช้ username หรือรหัสผ่านที่ต่างจากค่า default ให้แก้ไข `.env` ตามจริง

### 8. รัน migration
```bash
python manage.py migrate
```

### 9. สร้าง superuser
```bash
python manage.py createsuperuser
```

### 10. รันเซิร์ฟเวอร์
```bash
python manage.py runserver
```

แล้วเปิดเบราว์เซอร์ที่:
```text
http://127.0.0.1:8000/
```