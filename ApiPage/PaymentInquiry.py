def render_payment_inquiry():
    import pyperclip
    import time
    import requests
    import json
    import streamlit as st
    from streamlit_ace import st_ace
    import uuid

    KEY_PREFIX = str(uuid.uuid4())[:8]

    st.title("🧾 Payment Inquiry")
    from utils.EnvSelector import select_environment
    env, api_url = select_environment(key_suffix="payment_inquiry", env_type="PaymentInquiry")

    col1, col2 = st.columns([1, 1])

    with col1:
        merchant_id = st.text_input("🏢 Merchant ID", "704704000000000")
        # --- Invoice No session state initialization from clipboard ---
        if 'invoice_no' not in st.session_state:
            try:
                clipboard_text = pyperclip.paste()
                if clipboard_text.startswith("INV"):
                    st.session_state.invoice_no = clipboard_text
                else:
                    st.session_state.invoice_no = "254b77aabc"
            except Exception:
                st.session_state.invoice_no = "254b77aabc"
        invoice_no = st.text_input("🧾 Invoice No", value=st.session_state.invoice_no, key="invoice_no")
        locale = st.text_input("🌍 Locale", "en")
        # Initialize secret_key in session state with default value
        if f"{KEY_PREFIX}_secret_key_token" not in st.session_state:
            st.session_state[f"{KEY_PREFIX}_secret_key_token"] = "0A85F7ED911FD69D3316ECDF20FCA4E138E590E7EF5D93009FEF1BEC5B2FF13F"
        
        secret_key = st.text_input("🔑 Merchant SHA Key", type="password", value=st.session_state[f"{KEY_PREFIX}_secret_key_token"], key=f"{KEY_PREFIX}_secret_key_token")

        if st.button("🚀 Send Request"):
            payload = {
                "merchantID": merchant_id,
                "invoiceNo": invoice_no,
                "locale": locale
            }
            try:
                st.session_state['req_payload'] = payload

                import jwt
                encoded_payload = jwt.encode(payload, secret_key, algorithm="HS256")
                final_payload = {"payload": encoded_payload}
                st.session_state['final_payload'] = final_payload
                start = time.time()
                res = requests.post(api_url, json=final_payload, headers={"Content-Type": "application/json"})
                elapsed = round(time.time() - start, 2)
                st.session_state['res_payload'] = f"⏱ {elapsed}s | HTTP {res.status_code}\n\n{res.text}"
                if res.status_code == 200:
                    st.toast(f"✅ Request successful in {elapsed} seconds", icon="⏱")
                    st.success(f"✅ Request successful in ({elapsed} seconds)")
                else:
                    st.toast(f"❌ Request failed in {elapsed}s", icon="⏱")
                    st.error(f"❌ Failed with HTTP {res.status_code}")
            except Exception as e:
                st.session_state['res_payload'] = f"❌ Exception: {e}"
                st.error("❌ Exception occurred")

    with col2:
        st.markdown("### 🧾 Raw Payload (Before Encryption)")
        st.json(st.session_state.get('req_payload', {}))

        st.markdown("### 📨 Request")
        st.json(st.session_state.get('final_payload', {}))

        # st.markdown("### 🔓 Decrypted Payload (JWT Claims)")
        # try:
        #     import jwt
        #     decoded = jwt.decode(
        #         st.session_state.get('final_payload', {}).get("payload", ""),
        #         secret_key,
        #         algorithms=["HS256"]
        #     )
        #     st.json(decoded)
        # except Exception as e:
        #     st.warning(f"Could not decode JWT: {e}")

        st.markdown("### 📬 Response")
        try:
            parsed_response = json.loads(st.session_state.get('res_payload', '{}').split('\n\n', 1)[-1])
            st.json(parsed_response)
        except Exception:
            st.code(st.session_state.get('res_payload', 'No response'))

        st.markdown("### 🔓 Decrypted Response Payload (JWT Claims)")
        try:
            jwt_payload = parsed_response.get("payload")
            if jwt_payload:
                decoded_res = jwt.decode(jwt_payload, secret_key, algorithms=["HS256"])
                st.json(decoded_res)
            else:
                st.info("No payload to decode in response.")
        except Exception as e:
            st.warning(f"Could not decode response JWT: {e}")

if __name__ == "__main__":
    render_payment_inquiry()
