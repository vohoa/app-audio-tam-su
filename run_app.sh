#!/bin/bash
# Script để chạy app với config đúng project này

# Unset biến môi trường global (nếu có)
unset AUDIO_DOWNLOAD_PATH

# Chạy app
python3 main.py "$@"
