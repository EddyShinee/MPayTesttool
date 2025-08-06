# env_selector.py

import streamlit as st

def select_environment(key_suffix="", default_urls=None, env_type="paymentToken"):
    import uuid
    if not key_suffix:
        key_suffix = str(uuid.uuid4())  # auto-generate unique key if not provided
    if default_urls is None:
        if env_type == "PaymentAction":
            default_urls = {
                "UAT / Sandbox": "https://demo2.2c2p.com/2C2PFrontend/PaymentAction/2.0/action",
                "Production": "https://t.2c2p.com/PaymentAction/2.0/action",
                "MPay - Production": "https://pgwcore.m-pay.vn/PaymentActionV2/2.0/action"
            }
        elif env_type == "DoPayment":
            default_urls = {
                "UAT / Sandbox": "https://sandbox-pgw.2c2p.com/payment/4.3/payment",
                "Production": "https://pgw.2c2p.com/payment/4.3/payment",
                "MPay - Production": "https://pgw.m-pay.vn/payment/4.1/payment"
            }
        elif env_type == "PaymentOption":
            default_urls = {
                "UAT / Sandbox": "https://sandbox-pgw.2c2p.com/payment/4.3/paymentOption",
                "Production": "https://pgw.2c2p.com/payment/4.3/paymentOption",
                "MPay - Production": "https://pgw.m-pay.vn/payment/4.1/paymentOption"
            }
        elif env_type == "PaymentOptionDetails":
            default_urls = {
                "UAT / Sandbox": "https://sandbox-pgw.2c2p.com/payment/4.3/paymentOptionDetails",
                "Production": "https://pgw.2c2p.com/payment/4.3/paymentOptionDetails",
                "MPay - Production": "https://pgw.m-pay.vn/payment/4.1/paymentOptionDetails"
            }
        elif env_type == "TransactionStatusInquiry":
            default_urls = {
                "UAT / Sandbox": "https://sandbox-pgw.2c2p.com/payment/4.3/transactionStatus",
                "Production": "https://pgw.2c2p.com/payment/4.3/transactionStatus",
                "MPay - Production": "https://pgw.m-pay.vn/payment/4.3/transactionStatus"
            }
        elif env_type == "PaymentInquiry":
            default_urls = {
                "UAT / Sandbox": "https://sandbox-pgw.2c2p.com/payment/4.3/paymentInquiry",
                "Production": "https://pgw.2c2p.com/payment/4.3/paymentInquiry",
                "MPay - Production": "https://pgw.m-pay.vn/payment/4.3/paymentInquiry"
            }
        elif env_type == "PaymentPOS":
            default_urls = {
                "UAT / Sandbox": "https://sandbox-pgw.2c2p.com/pos/v4.4/order/create",
                "Production": "https://posgw.2c2p.com/pos/4.4/order/create",
                "MPay - Production": "https://posgw.m-pay.vn/pos/4.4/order/create"
            }
        else:
            default_urls = {
                "UAT / Sandbox": "https://sandbox-pgw.2c2p.com/payment/4.3/paymentToken",
                "Production": "https://pgw.2c2p.com/payment/4.3/paymentToken",
                "MPay - Production": "https://pgw.m-pay.vn/payment/4.1/paymentToken"
            }

    env = st.radio(
        "🌍 Choose Environment",
        list(default_urls.keys()),
        index=0,
        horizontal=True,
        key=f"env_token_{env_type}_{key_suffix}"
    )

    api_url = st.text_input("🔗 API Endpoint", value=default_urls[env], key=f"api_url_{env_type}_{key_suffix}")
    return env, api_url