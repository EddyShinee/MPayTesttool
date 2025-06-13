import streamlit as st
import requests
import json
import datetime
import jwt  # PyJWT
import base64
import uuid
from utils.EnvSelector import select_environment

# import Sidebar.Sidebar as Sidebar

# st.set_page_config(page_title="PaymentToken", layout="wide")
st.title("🔐 Payment Token")
# --- Sidebar options ---
# st.sidebar.title("Chọn API")
# api_selected = st.sidebar.radio("Chọn API:", Sidebar.api_list)

env, api_url = select_environment(key_suffix="payment_token", env_type="PaymentToken")

# --- Generate invoiceNo & idempotencyID ---
def generate_invoice_no():
    return datetime.datetime.now().strftime("INV%y%m%d%H%M%S")

def generate_idempotency_id():
    return f"idem-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

# --- Layout: 2 columns ---
col1, col2 = st.columns(2)
with col1:
    merchant_id = st.text_input("merchantID", "704704000000000", key="merchant_id_token")
    if "invoice_no" not in st.session_state:
        st.session_state["invoice_no"] = generate_invoice_no()
    invoice_no = st.text_input("invoiceNo", value=st.session_state["invoice_no"], key="invoice_no_token")
    if "idempotency_id" not in st.session_state:
        st.session_state["idempotency_id"] = generate_idempotency_id()
    idempotency_id = st.text_input("idempotencyID", value=st.session_state["idempotency_id"], key="idempotency_id_token")
    description = st.text_input("description", f"Eddy - Payment {invoice_no}", key="description_token")
    amount = st.number_input("amount", value=5000, key="amount_token")
    currency_code = st.text_input("currencyCode", "VND", key="currency_code_token")
    payment_channel = st.multiselect("paymentChannel", ["ALL", "CC", "IPP", "APM", "QR"], default=["ALL"], key="payment_channel_token")

    optional_fields = {}
    with st.expander("➕ Tuỳ chọn nâng cao"):
        if st.checkbox("agentChannel"):
            optional_fields['agentChannel'] = st.text_input("agentChannel", key="agent_channel_token")
        if st.checkbox("locale"):
            optional_fields['locale'] = st.text_input("locale", "vi", key="locale_token")
        if st.checkbox("request3DS"):
            optional_fields['request3DS'] = st.selectbox("request3DS", ["Y", "N"], key="request3ds_token")
        if st.checkbox("tokenize"):
            optional_fields['tokenize'] = st.selectbox("tokenize", [True, False], key="tokenize_token")
        if st.checkbox("customerToken"):
            optional_fields['customerToken'] = st.text_input("customerToken", key="customer_token_token")
        if st.checkbox("customerTokenOnly"):
            optional_fields['customerTokenOnly'] = st.selectbox("customerTokenOnly", ["Y", "N"], key="customer_token_only_token")
        if st.checkbox("tokenizeOnly"):
            optional_fields['tokenizeOnly'] = st.selectbox("tokenizeOnly", ["Y", "N"], key="tokenize_only_token")
        if st.checkbox("storeCredentials"):
            optional_fields['storeCredentials'] = st.selectbox("storeCredentials", ["Y", "N"], key="store_credentials_token")
        if st.checkbox("interestType"):
            optional_fields['interestType'] = st.selectbox("interestType", ["FULL", "PARTIAL"], key="interest_type_token")
        if st.checkbox("installmentPeriodFilter"):
            optional_fields['installmentPeriodFilter'] = st.text_input("installmentPeriodFilter", key="installment_period_filter_token")
        if st.checkbox("installmentBankFilter"):
            optional_fields['installmentBankFilter'] = st.text_input("installmentBankFilter", key="installment_bank_filter_token")
        if st.checkbox("productCode"):
            optional_fields['productCode'] = st.text_input("productCode", key="product_code_token")
        if st.checkbox("recurring"):
            optional_fields['recurring'] = st.selectbox("recurring", ["Y", "N"], key="recurring_token")
        if st.checkbox("invoicePrefix"):
            optional_fields['invoicePrefix'] = st.text_input("invoicePrefix", key="invoice_prefix_token")
        if st.checkbox("recurringAmount"):
            optional_fields['recurringAmount'] = st.number_input("recurringAmount", value=0, key="recurring_amount_token")
        if st.checkbox("allowAccumulate"):
            optional_fields['allowAccumulate'] = st.selectbox("allowAccumulate", ["Y", "N"], key="allow_accumulate_token")
        if st.checkbox("maxAccumulateAmount"):
            optional_fields['maxAccumulateAmount'] = st.number_input("maxAccumulateAmount", value=0, key="max_accumulate_amount_token")
        if st.checkbox("recurringInterval"):
            optional_fields['recurringInterval'] = st.text_input("recurringInterval", key="recurring_interval_token")
        if st.checkbox("recurringCount"):
            optional_fields['recurringCount'] = st.number_input("recurringCount", value=0, key="recurring_count_token")
        if st.checkbox("chargeNextDate"):
            optional_fields['chargeNextDate'] = st.date_input("chargeNextDate", key="charge_next_date_token")
        if st.checkbox("chargeOnDate"):
            optional_fields['chargeOnDate'] = st.date_input("chargeOnDate", key="charge_on_date_token")
        if st.checkbox("paymentExpiry"):
            optional_fields['paymentExpiry'] = st.text_input("paymentExpiry (yyyy-MM-dd HH:mm:ss)", key="payment_expiry_token")
        if st.checkbox("promotionCode"):
            optional_fields['promotionCode'] = st.text_input("promotionCode", key="promotion_code_token")
        if st.checkbox("paymentRouteID"):
            optional_fields['paymentRouteID'] = st.text_input("paymentRouteID", key="payment_route_id_token")
        if st.checkbox("fxProviderCode"):
            optional_fields['fxProviderCode'] = st.text_input("fxProviderCode", key="fx_provider_code_token")
        if st.checkbox("fxRateIdoriginalAmount"):
            optional_fields['fxRateIdoriginalAmount'] = st.text_input("fxRateIdoriginalAmount", key="fx_rate_id_original_amount_token")
        if st.checkbox("originalAmount"):
            optional_fields['originalAmount'] = st.number_input("originalAmount", value=0, key="original_amount_token")
        if st.checkbox("immediatePayment"):
            optional_fields['immediatePayment'] = st.selectbox("immediatePayment", ["Y", "N"], key="immediate_payment_token")

    secret_key = st.text_input("🔑 Merchant SHA Key", type="password", value="0A85F7ED911FD69D3316ECDF20FCA4E138E590E7EF5D93009FEF1BEC5B2FF13F", key="secret_key_token")

    if st.button("🔐 Send request Payment Token"):
        with st.spinner("🔄 Đang gửi request..."):
            start_time = datetime.datetime.now()
            payload_data = {
                "merchantID": merchant_id,
                "invoiceNo": invoice_no,
                "description": description,
                "amount": amount,
                "currencyCode": currency_code,
                "paymentChannel": payment_channel
            }
            payload_data.update(optional_fields)

            st.session_state["payload_data"] = payload_data

            jwt_token = jwt.encode(payload_data, secret_key, algorithm="HS256")

            # Save to display in right column
            st.session_state["request_payload"] = jwt_token

            try:
                res = requests.post(api_url, json={"payload": jwt_token}, headers={"Content-Type": "application/json"})
                st.session_state["response_payload"] = res.text
                st.toast("Gửi yêu cầu thành công!", icon="✅")
            except Exception as e:
                st.session_state["response_payload"] = str(e)
                st.toast("Gửi yêu cầu thất bại!", icon="⚠️")
            end_time = datetime.datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()
            st.success(f"⏱️ Request xử lý {elapsed_time:.2f} giây")

# --- Right column ---
with col2:
    st.subheader("📤 Payload chưa mã hoá:")
    st.code(json.dumps(st.session_state.get("payload_data", {}), indent=2))

    st.subheader("📤 Payload đã mã hoá (JWT):")
    st.code(st.session_state.get("request_payload", ""))

    st.subheader("📥 Response từ API:")
    response_raw = st.session_state.get("response_payload", "")
    st.code(response_raw)

    def decode_jwt_payload(jwt_token):
        try:
            payload_part = jwt_token.split('.')[1]
            padding = '=' * (-len(payload_part) % 4)
            decoded_bytes = base64.urlsafe_b64decode(payload_part + padding)
            return json.loads(decoded_bytes)
        except Exception as e:
            return {"error": str(e)}

    if response_raw:
        try:
            decoded_response = json.loads(response_raw)
            if 'payload' in decoded_response:
                st.subheader("🧩 Response (Decode JWT):")
                st.json(decode_jwt_payload(decoded_response['payload']))
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1:
                    web_url = decode_jwt_payload(decoded_response['payload']).get('webPaymentUrl')
                    if web_url:
                        st.markdown(f"[🌐 Mở Web Payment URL]({web_url})", unsafe_allow_html=True)

                with row1_col2:
                    if st.button("📋 Copy payment token", key="copy_token_button"):
                        payment_token = decode_jwt_payload(decoded_response['payload']).get('paymentToken', 'Không tìm thấy paymentToken')
                        st.toast("✅ Token copied to clipboard!", icon="📋")
                        st.code(payment_token)
        except:
            st.info("Không thể giải mã response JWT hoặc không có 'payload' trong response.")
