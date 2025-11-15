@echo off
REM Run script for Audio Generator Desktop App (Windows)

echo 🎵 Audio Generator Desktop App
echo ================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Tạo môi trường ảo...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Kích hoạt môi trường ảo...
call venv\Scripts\activate.bat

REM Install requirements if needed
if not exist "venv\.installed" (
    echo 📥 Cài đặt dependencies...
    pip install -r requirements.txt
    echo. > venv\.installed
)

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  File .env chưa tồn tại. Tạo từ .env.example...
    copy .env.example .env
    echo ✅ Đã tạo file .env. Vui lòng kiểm tra cấu hình trước khi chạy.
)

REM Run the application
echo 🚀 Khởi động ứng dụng...
python main.py

pause
