import streamlit as st
import requests
import json
import datetime
import jwt  # PyJWT
import base64
import uuid
import time
from utils.EnvSelector import select_environment

KEY_PREFIX = str(uuid.uuid4())[:8]

def render_payment_pos():
    st.title("🔐 Payment POS")

    env, api_url = select_environment(key_suffix="payment_pos", env_type="PaymentPOS")

    def generate_invoice_no():
        return datetime.datetime.now().strftime("INV-POS-%y%m%d%H%M%S")

    def generate_idempotency_id():
        return f"idem-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    col1, col2 = st.columns(2)
    with col1:
        merchant_id = st.text_input("merchantID", "704704000000211", key=f"{KEY_PREFIX}_merchant_id_token")
        if "invoice_no" not in st.session_state:
            st.session_state["invoice_no"] = generate_invoice_no()
        invoice_no = st.text_input("invoiceNo", value=st.session_state["invoice_no"], key=f"{KEY_PREFIX}_invoice_no_token")
        if "idempotency_id" not in st.session_state:
            st.session_state["idempotency_id"] = generate_idempotency_id()
        idempotency_id = st.text_input("idempotencyID", value=st.session_state["idempotency_id"], key=f"{KEY_PREFIX}_idempotency_id_token")
        description = st.text_input("description", f"Eddy - Payment {invoice_no}", key=f"{KEY_PREFIX}_description_token")
        amount = st.number_input("amount", value=5000, key=f"{KEY_PREFIX}_amount_token")
        currency_code = st.text_input("currencyCode", "VND", key=f"{KEY_PREFIX}_currency_code_token")
        payment_channel = [st.radio("paymentChannel", ["POSCC", "VNQR"], index=0, key=f"{KEY_PREFIX}_payment_channel_token")]
        user_defined_1 = st.text_input("userDefined1", "00024500937", key=f"{KEY_PREFIX}_user_defined_1_token")
        secret_key = st.text_input("🔑 Merchant SHA Key", type="password", value="3BEFEF0675BDB0333A435DB13F5C14D606C5A548E817842A1C0F7CB475EE6076", key=f"{KEY_PREFIX}_secret_key_token")
        response_return_url = st.text_input(
            "responseReturnUrl",
            value="https://webhook.site/08fd12ec-4a71-4499-968c-0dbe729b8686",
            key=f"{KEY_PREFIX}_response_return_url_token"
        )
        customer_name = st.text_input("Customer Name", "Eddy", key=f"{KEY_PREFIX}_customer_name_token")
        customer_email = st.text_input("Customer Email", "eddy.vu@2c2p.com", key=f"{KEY_PREFIX}_customer_email_token")

        # Save state for UI
        st.session_state["merchant_id"] = merchant_id
        st.session_state["invoice_no"] = invoice_no
        st.session_state["idempotency_id"] = idempotency_id
        st.session_state["description"] = description
        st.session_state["amount"] = amount
        st.session_state["currency_code"] = currency_code
        st.session_state["payment_channel"] = payment_channel
        st.session_state["user_defined_1"] = user_defined_1
        st.session_state["secret_key"] = secret_key
        st.session_state["response_return_url"] = response_return_url
        st.session_state["customer_name"] = customer_name
        st.session_state["customer_email"] = customer_email

        if st.button("🔐 Send request Payment Token", key=f"{KEY_PREFIX}_send_request_button"):
            start_time = time.perf_counter()
            start_timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            realtime_placeholder = st.empty()
            st.session_state["response_payload"] = None

            # Hiển thị ngay sau khi bấm nút
            realtime_placeholder.info(f"🕒 Elapsed Time: ...\n🔹 Started at: `{start_timestamp}`")

            # Regenerate invoice_no and idempotency_id each time the button is clicked
            invoice_no = generate_invoice_no()
            st.session_state["invoice_no"] = invoice_no
            idempotency_id = generate_idempotency_id()
            st.session_state["idempotency_id"] = idempotency_id

            # ----- Build payload & sign JWT -----
            payload_data = {
                "merchantId": merchant_id,
                "invoiceNo": invoice_no,
                "description": description,
                "amount": amount,
                "currencyCode": currency_code,
                "idempotencyID": idempotency_id,
                "userDefined1": user_defined_1
            }
            st.session_state["payload_data"] = payload_data
            jwt_token = jwt.encode(payload_data, secret_key, algorithm="HS256")
            st.session_state["request_payload"] = jwt_token

            api_payload = {
                "paymentToken": jwt_token,
                "clientID": str(uuid.uuid4()).replace("-", ""),
                "locale": "en",
                "responseReturnUrl": response_return_url,
                "payment": {
                    "code": {
                        "channelCode": payment_channel[0]
                    },
                    "data": {
                        "name": customer_name,
                        "email": customer_email
                    }
                }
            }
            st.session_state["api_payload"] = api_payload

            # ----- Send API request -----
            try:
                res = requests.post(api_url, json=api_payload, headers={"Content-Type": "application/json"})
                st.session_state["response_payload"] = res.text
                st.toast("Request sent successfully!", icon="✅")
            except Exception as e:
                st.session_state["response_payload"] = f"ERROR: {e}"
                st.toast("Request failed!", icon="⚠️")
                st.error(str(e))

            # ----- Show elapsed time (update lại placeholder) -----
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            realtime_placeholder.info(f"🕒 Elapsed Time: {elapsed_time:.2f} s\n🔹 Started at: `{start_timestamp}`")
            st.session_state["request_time"] = elapsed_time
            st.success(f"✅ Request completed in {elapsed_time:.4f} seconds")

    # ---- RIGHT COLUMN: Show request/response/debug ----
    with col2:
        st.subheader("📤 Unencrypted Payload:")
        st.code(json.dumps(st.session_state.get("payload_data", {}), indent=2))

        st.subheader("📤 Encrypted Payload (JWT):")
        st.code(st.session_state.get("request_payload", ""))

        st.subheader("🔎 Decoded JWT Payload:")
        try:
            decoded_jwt = jwt.decode(
                st.session_state.get("request_payload", ""),
                st.session_state.get("secret_key", ""),
                algorithms=["HS256"]
            )
            st.json(decoded_jwt)
        except Exception as e:
            st.warning(f"Unable to decode JWT with current secret key: {e}")

        st.subheader("📦 Final API Payload:")
        st.code(json.dumps(st.session_state.get("api_payload", {}), indent=2))

        st.subheader("📥 Response from API:")
        response_raw = st.session_state.get("response_payload", "")
        with st.expander("📩 Raw API Response", expanded=True):
            st.code(response_raw, language='json')

        if "request_time" in st.session_state:
            st.info(f"⏱️ Response Time: {st.session_state['request_time']:.4f} seconds")

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
                        if st.button("📋 Copy Invoice ID", key=f"{KEY_PREFIX}_copy_invoice_id_button"):
                            invoice_id = st.session_state.get("invoice_no", "invoice_no not found")
                            try:
                                import pyperclip
                                pyperclip.copy(invoice_id)
                                st.toast("✅ Invoice ID copied to clipboard!", icon="📋")
                            except Exception:
                                st.warning("⚠️ Unable to copy Invoice ID to clipboard. Please copy it manually.")
                                st.code(invoice_id)
            except:
                st.info("Unable to decode JWT response or 'payload' not found in response.")

if __name__ == "__main__":
    render_payment_pos()
