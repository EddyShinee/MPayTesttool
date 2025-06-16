import streamlit as st
st.set_page_config(page_title="2C2P API Simulator", layout="wide")

import Sidebar.Sidebar as Sidebar
import requests
import json
import datetime
import jwt  # PyJWT
import base64
import importlib
from ApiPage import PaymentToken, PaymentAction, DoPayment, PaymentOptions, PaymentOptionDetails, TransactionStatusInquiry, PaymentInquiry, PaymentPOS
import os

# st.title("🔗 2C2P API Simulator")

st.sidebar.title("Payment API List")
api_selected = st.sidebar.radio("Choose API", Sidebar.api_list)

from ApiPage import PaymentToken  # import các trang khác nếu có thêm

api_pages = {
    "Payment Token": PaymentToken.render_payment_token,
    "Payment Action": PaymentAction.render_payment_action,
    "Do Payment": DoPayment.render_do_payment,
    "Payment Options": PaymentOptions.render_payment_options,
    "Payment Option Details": PaymentOptionDetails.render_payment_option_details,
    "Transaction Status Inquiry": TransactionStatusInquiry.render_transaction_status_inquiry,
    "Payment Inquiry": PaymentInquiry.render_payment_inquiry,
    "Payment POS": PaymentPOS.render_payment_pos
    # thêm các API khác tại đây nếu đã định nghĩa
}

if api_selected in api_pages:
    api_pages[api_selected]()
else:
    st.warning(f"🚧 Trang '{api_selected}' chưa được tạo.")
