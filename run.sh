#!/bin/bash
# Run script for Audio Generator Desktop App

echo "🎵 Audio Generator Desktop App"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Tạo môi trường ảo..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Kích hoạt môi trường ảo..."
source venv/bin/activate

# Install requirements if needed
if [ ! -f "venv/.installed" ]; then
    echo "📥 Cài đặt dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  File .env chưa tồn tại. Tạo từ .env.example..."
    cp .env.example .env
    echo "✅ Đã tạo file .env. Vui lòng kiểm tra cấu hình trước khi chạy."
fi

# Run the application
echo "🚀 Khởi động ứng dụng..."
python main.py
