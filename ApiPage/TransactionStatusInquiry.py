def render_transaction_status_inquiry():
    import pyperclip
    import time
    import requests
    import json
    import streamlit as st
    from streamlit_ace import st_ace

    st.title("🔍 Transaction Status Inquiry")
    from utils.EnvSelector import select_environment
    env, api_url = select_environment(key_suffix="transaction_status_inquiry", env_type="TransactionStatusInquiry")

    col1, col2 = st.columns([1, 1])

    with col1:
        if 'txn_status_payment_token' not in st.session_state:
            clip = pyperclip.paste()
            st.session_state.txn_status_payment_token = clip if clip.startswith("kSA") else ""

        payment_token = st.text_input("🔑 Payment Token", key="txn_status_payment_token")

        import uuid
        if 'client_id_option' not in st.session_state:
            st.session_state.client_id_option = str(uuid.uuid4()).replace("-", "").upper()
        client_id = st.text_input("🧾 Client ID", value=st.session_state.client_id_option, key="client_id_option")

        locale = st.text_input("🌍 Locale", "en")
        # category_code and group_code are no longer used in the payload
        # category_code = st.text_input("📂 Category Code", "GCARD")
        # group_code = st.text_input("👥 Group Code", "CC")

        additional_info = st.radio("Include Additional Info?", options=["Yes", "No"], index=0)
        additional_info_bool = additional_info == "Yes"

        if st.button("🚀 Send Request"):
            if not payment_token:
                st.warning("⚠️ Payment Token is required.")
            else:
                payload = {
                    "paymentToken": payment_token,
                    "clientID": client_id,
                    "locale": locale,
                    "additionalInfo": additional_info_bool
                }
                try:
                    st.session_state['req_payload'] = payload
                    start = time.time()
                    res = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"})
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
        st.markdown("### 📤 Transaction Inquiry Request")
        st.json(st.session_state.get('req_payload', {}))

        st.markdown("### 📥 Transaction Inquiry Response")
        try:
            parsed_response = json.loads(st.session_state.get('res_payload', '{}').split('\n\n', 1)[-1])
            st.json(parsed_response)
        except Exception:
            st.code(st.session_state.get('res_payload', 'No response'))

if __name__ == "__main__":
    render_transaction_status_inquiry()
