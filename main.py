import streamlit as st
st.set_page_config(page_title="2C2P API Simulator", layout="wide")

import Sidebar.Sidebar as Sidebar
import requests
import json
import datetime
import jwt  # PyJWT
import base64
import importlib
from ApiPage import PaymentToken
import os

# st.title("🔗 2C2P API Simulator")

st.sidebar.title("Payment API List")
api_selected = st.sidebar.radio("Choose API", Sidebar.api_list)

# Biến tên thành tên file
module_file = f"ApiPage/{api_selected.replace(' ', '')}.py"

# Kiểm tra và thực thi
if os.path.exists(module_file):
    with open(module_file, 'r', encoding='utf-8') as f:
        exec(f.read(), globals())
else:
    st.warning(f"🚧 File '{module_file}' chưa được tạo.")
