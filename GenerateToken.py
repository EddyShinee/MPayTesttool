#!/usr/bin/env python3
"""
Quick JWT Token Generator
Tạo JWT token nhanh cho webhook server
"""

import jwt
from datetime import datetime, timedelta
import os

# Cấu hình JWT (giống webhook server)
JWT_SECRET = os.getenv("WEBHOOK_AUTH_TOKEN_SECRET", "")
EXPECTED_PAYLOAD = {
    "name": "Eddy",
    "admin": True,
    "phone": 909700980,
    "random_number": 1993
}

def generate_token():
    """Tạo JWT token hợp lệ"""
    if not JWT_SECRET:
        raise ValueError("Missing WEBHOOK_AUTH_TOKEN_SECRET environment variable")
    # Thêm thời gian hết hạn (24 giờ)
    payload = EXPECTED_PAYLOAD.copy()
    payload['exp'] = datetime.utcnow() + timedelta(hours=24)
    payload['iat'] = datetime.utcnow()
    
    # Tạo token
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

if __name__ == "__main__":
    try:
        # Tạo token
        token = generate_token()
        
        print("🔑 JWT TOKEN ĐƯỢC TẠO THÀNH CÔNG!")
        print("=" * 60)
        print(f"Token: {token}")
        print("=" * 60)
        print("\n🧪 SỬ DỤNG TOKEN:")
        print(f"curl -X POST 'http://localhost:8000/webhook?token={token}' \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"test\": \"data\"}'")
        print("\n🌐 Hoặc trong browser:")
        print(f"http://localhost:8000/webhook?token={token}")
        print("\n⏰ Token hết hạn sau 24 giờ")
        
    except ImportError:
        print("❌ Cần cài PyJWT: pip install PyJWT")
    except Exception as e:
        print(f"❌ Lỗi: {e}")