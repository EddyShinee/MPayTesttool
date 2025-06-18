import streamlit as st
import requests
import json
import datetime
import jwt  # PyJWT
import base64
import uuid
import pyperclip  # Ensure this is imported at the top
from utils.EnvSelector import select_environment

# Add KEY_PREFIX after imports
KEY_PREFIX = str(uuid.uuid4())[:8]

def render_payment_token():
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
        merchant_id = st.text_input("merchantID", "704704000000000", key=f"{KEY_PREFIX}_merchant_id_token")
        if "invoice_no" not in st.session_state:
            st.session_state["invoice_no"] = generate_invoice_no()
        invoice_no = st.text_input("invoiceNo", value=st.session_state["invoice_no"], key=f"{KEY_PREFIX}_invoice_no_token")
        if "idempotency_id" not in st.session_state:
            st.session_state["idempotency_id"] = generate_idempotency_id()
        idempotency_id = st.text_input("idempotencyID", value=st.session_state["idempotency_id"], key=f"{KEY_PREFIX}_idempotency_id_token")
        description = st.text_input("description", f"Eddy - Payment {invoice_no}", key=f"{KEY_PREFIX}_description_token")
        amount = st.number_input("amount", value=5000, key=f"{KEY_PREFIX}_amount_token")
        currency_code = st.text_input("currencyCode", "VND", key=f"{KEY_PREFIX}_currency_code_token")
        payment_channel = st.multiselect("paymentChannel", ["ALL", "CC", "IPP", "APM", "QR"], default=["ALL"], key=f"{KEY_PREFIX}_payment_channel_token")

        optional_fields = {}
        with st.expander("➕ Advanced Options"):
            if st.checkbox("frontendReturnUrl", key=f"{KEY_PREFIX}_checkbox_frontendReturnUrl"):
                optional_fields['frontendReturnUrl'] = st.text_input("frontendReturnUrl", "https://webhook.site/08fd12ec-4a71-4499-968c-0dbe729b8686", key=f"{KEY_PREFIX}_frontend_return_url_token")
            if st.checkbox("backendReturnUrl", key=f"{KEY_PREFIX}_checkbox_backendReturnUrl"):
                optional_fields['backendReturnUrl'] = st.text_input("backendReturnUrl", "https://webhook.site/08fd12ec-4a71-4499-968c-0dbe729b8686", key=f"{KEY_PREFIX}_backend_return_url_token")
            if st.checkbox("locale", key=f"{KEY_PREFIX}_checkbox_locale"):
                optional_fields['locale'] = st.text_input("locale", "vi", key=f"{KEY_PREFIX}_locale_token")
            if st.checkbox("paymentExpiry", key=f"{KEY_PREFIX}_checkbox_paymentExpiry"):
                optional_fields['paymentExpiry'] = st.text_input("paymentExpiry (yyyy-MM-dd HH:mm:ss)", key=f"{KEY_PREFIX}_payment_expiry_token")
            if st.checkbox("agentChannel", key=f"{KEY_PREFIX}_checkbox_agentChannel"):
                optional_fields['agentChannel'] = st.text_input("agentChannel", key=f"{KEY_PREFIX}_agent_channel_token")
            if st.checkbox("request3DS", key=f"{KEY_PREFIX}_checkbox_request3DS"):
                optional_fields['request3DS'] = st.selectbox("request3DS", ["Y", "N"], key=f"{KEY_PREFIX}_request3ds_token")
            if st.checkbox("tokenize", key=f"{KEY_PREFIX}_checkbox_tokenize"):
                optional_fields['tokenize'] = st.selectbox("tokenize", [True, False], key=f"{KEY_PREFIX}_tokenize_token")
            if st.checkbox("customerToken", key=f"{KEY_PREFIX}_checkbox_customerToken"):
                raw_token_input = st.text_area("customerToken (comma-separated)", key=f"{KEY_PREFIX}_customer_token_token")
                optional_fields['customerToken'] = [token.strip() for token in raw_token_input.split(',') if token.strip()]
            if st.checkbox("customerTokenOnly", key=f"{KEY_PREFIX}_checkbox_customerTokenOnly"):
                optional_fields['customerTokenOnly'] = st.checkbox("Is customerTokenOnly True?", key=f"{KEY_PREFIX}_customer_token_only_token")
            if st.checkbox("tokenizeOnly", key=f"{KEY_PREFIX}_checkbox_tokenizeOnly"):
                optional_fields['tokenizeOnly'] = st.checkbox("Is tokenizeOnly True?", key=f"{KEY_PREFIX}_tokenize_only_token")
            if st.checkbox("storeCredentials", key=f"{KEY_PREFIX}_checkbox_storeCredentials"):
                optional_fields['storeCredentials'] = st.selectbox("storeCredentials", ["Y", "N"], key=f"{KEY_PREFIX}_store_credentials_token")
            if st.checkbox("interestType", key=f"{KEY_PREFIX}_checkbox_interestType"):
                optional_fields['interestType'] = st.selectbox("interestType", ["FULL", "PARTIAL"], key=f"{KEY_PREFIX}_interest_type_token")
            if st.checkbox("installmentPeriodFilter", key=f"{KEY_PREFIX}_checkbox_installmentPeriodFilter"):
                optional_fields['installmentPeriodFilter'] = st.text_input("installmentPeriodFilter", key=f"{KEY_PREFIX}_installment_period_filter_token")
            if st.checkbox("installmentBankFilter", key=f"{KEY_PREFIX}_checkbox_installmentBankFilter"):
                optional_fields['installmentBankFilter'] = st.text_input("installmentBankFilter", key=f"{KEY_PREFIX}_installment_bank_filter_token")
            if st.checkbox("productCode", key=f"{KEY_PREFIX}_checkbox_productCode"):
                optional_fields['productCode'] = st.text_input("productCode", key=f"{KEY_PREFIX}_product_code_token")
            if st.checkbox("recurring", key=f"{KEY_PREFIX}_checkbox_recurring"):
                optional_fields['recurring'] = st.selectbox("recurring", ["Y", "N"], key=f"{KEY_PREFIX}_recurring_token")
            if st.checkbox("invoicePrefix", key=f"{KEY_PREFIX}_checkbox_invoicePrefix"):
                optional_fields['invoicePrefix'] = st.text_input("invoicePrefix", key=f"{KEY_PREFIX}_invoice_prefix_token")
            if st.checkbox("recurringAmount", key=f"{KEY_PREFIX}_checkbox_recurringAmount"):
                optional_fields['recurringAmount'] = st.number_input("recurringAmount", value=0, key=f"{KEY_PREFIX}_recurring_amount_token")
            if st.checkbox("allowAccumulate", key=f"{KEY_PREFIX}_checkbox_allowAccumulate"):
                optional_fields['allowAccumulate'] = st.selectbox("allowAccumulate", ["Y", "N"], key=f"{KEY_PREFIX}_allow_accumulate_token")
            if st.checkbox("maxAccumulateAmount", key=f"{KEY_PREFIX}_checkbox_maxAccumulateAmount"):
                optional_fields['maxAccumulateAmount'] = st.number_input("maxAccumulateAmount", value=0, key=f"{KEY_PREFIX}_max_accumulate_amount_token")
            if st.checkbox("recurringInterval", key=f"{KEY_PREFIX}_checkbox_recurringInterval"):
                optional_fields['recurringInterval'] = st.text_input("recurringInterval", key=f"{KEY_PREFIX}_recurring_interval_token")
            if st.checkbox("recurringCount", key=f"{KEY_PREFIX}_checkbox_recurringCount"):
                optional_fields['recurringCount'] = st.number_input("recurringCount", value=0, key=f"{KEY_PREFIX}_recurring_count_token")
            if st.checkbox("chargeNextDate", key=f"{KEY_PREFIX}_checkbox_chargeNextDate"):
                optional_fields['chargeNextDate'] = st.date_input("chargeNextDate", key=f"{KEY_PREFIX}_charge_next_date_token")
            if st.checkbox("chargeOnDate", key=f"{KEY_PREFIX}_checkbox_chargeOnDate"):
                optional_fields['chargeOnDate'] = st.date_input("chargeOnDate", key=f"{KEY_PREFIX}_charge_on_date_token")
            if st.checkbox("promotionCode", key=f"{KEY_PREFIX}_checkbox_promotionCode"):
                optional_fields['promotionCode'] = st.text_input("promotionCode", key=f"{KEY_PREFIX}_promotion_code_token")
            if st.checkbox("paymentRouteID", key=f"{KEY_PREFIX}_checkbox_paymentRouteID"):
                optional_fields['paymentRouteID'] = st.text_input("paymentRouteID", key=f"{KEY_PREFIX}_payment_route_id_token")
            if st.checkbox("fxProviderCode", key=f"{KEY_PREFIX}_checkbox_fxProviderCode"):
                optional_fields['fxProviderCode'] = st.text_input("fxProviderCode", key=f"{KEY_PREFIX}_fx_provider_code_token")
            if st.checkbox("fxRateIdoriginalAmount", key=f"{KEY_PREFIX}_checkbox_fxRateIdoriginalAmount"):
                optional_fields['fxRateIdoriginalAmount'] = st.text_input("fxRateIdoriginalAmount", key=f"{KEY_PREFIX}_fx_rate_id_original_amount_token")
            if st.checkbox("originalAmount", key=f"{KEY_PREFIX}_checkbox_originalAmount"):
                optional_fields['originalAmount'] = st.number_input("originalAmount", value=0, key=f"{KEY_PREFIX}_original_amount_token")
            if st.checkbox("immediatePayment", key=f"{KEY_PREFIX}_checkbox_immediatePayment"):
                optional_fields['immediatePayment'] = st.selectbox("immediatePayment", ["Y", "N"], key=f"{KEY_PREFIX}_immediate_payment_token")

        secret_key = st.text_input("🔑 Merchant SHA Key", type="password", value="0A85F7ED911FD69D3316ECDF20FCA4E138E590E7EF5D93009FEF1BEC5B2FF13F", key=f"{KEY_PREFIX}_secret_key_token")

        if st.button("🔐 Send request Payment Token", key=f"{KEY_PREFIX}_send_request_button"):
            st.session_state["invoice_no"] = generate_invoice_no()
            st.session_state["idempotency_id"] = generate_idempotency_id()
            st.session_state["trigger_send_request"] = True
            st.rerun()

        if st.session_state.get("trigger_send_request", False):
            st.session_state["trigger_send_request"] = False  # Reset trigger
            with st.spinner("🔄 Sending request..."):
                start_time = datetime.datetime.now()
                invoice_no = st.session_state["invoice_no"]
                idempotency_id = st.session_state["idempotency_id"]
                description = f"Eddy - Payment {invoice_no}"
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
                st.session_state["request_payload"] = jwt_token
                try:
                    res = requests.post(api_url, json={"payload": jwt_token}, headers={"Content-Type": "application/json"})
                    st.session_state["response_payload"] = res.text
                    st.toast("Request sent successfully!", icon="✅")
                except Exception as e:
                    st.session_state["response_payload"] = str(e)
                    st.toast("Request failed!", icon="⚠️")
                end_time = datetime.datetime.now()
                elapsed_time = (end_time - start_time).total_seconds()
                st.success(f"⏱️Request successful in {elapsed_time:.2f} giây")

    # --- Right column ---
    with col2:
        st.subheader("📤 Unencrypted Payload:")
        st.code(json.dumps(st.session_state.get("payload_data", {}), indent=2))

        st.subheader("📤 Encrypted Payload (JWT):")
        st.code(st.session_state.get("request_payload", ""))

        st.subheader("📥 Response from API:")
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
                    st.subheader("🧩 Decoded JWT Response:")
                    st.json(decode_jwt_payload(decoded_response['payload']))
                    row1_col1, row1_col2 = st.columns(2)
                    with row1_col1:
                        web_url = decode_jwt_payload(decoded_response['payload']).get('webPaymentUrl')
                        if web_url:
                            st.markdown(f"[🌐 Open Web Payment URL]({web_url})", unsafe_allow_html=True)

                    with row1_col2:
                        if st.button("📋 Copy payment token", key=f"{KEY_PREFIX}_copy_token_button"):
                            payment_token = decode_jwt_payload(decoded_response['payload']).get('paymentToken', 'paymentToken not found')
                            try:
                                pyperclip.copy(payment_token)
                                st.toast("✅ Token copied to clipboard!", icon="📋")
                            except pyperclip.PyperclipException:
                                st.warning("⚠️ Unable to copy token to clipboard. Please copy it manually.")
                                st.code(payment_token)
            except:
                st.info("Unable to decode JWT response or 'payload' not found in response.")

if __name__ == "__main__":
    render_payment_token()
