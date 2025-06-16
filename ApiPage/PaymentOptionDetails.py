def render_payment_option_details():
    import pyperclip
    import time
    import requests
    import json
    import streamlit as st
    from streamlit_ace import st_ace

    st.title("🧾 Payment Option Details")
    from utils.EnvSelector import select_environment
    env, api_url = select_environment(key_suffix="payment_option_details", env_type="PaymentOptionDetails")

    col1, col2 = st.columns([1, 1])

    with col1:
        if 'payment_token_option' not in st.session_state:
            clip = pyperclip.paste()
            st.session_state.payment_token_option = clip if clip.startswith("kSA") else ""

        payment_token = st.text_input("🔑 Payment Token", key="payment_token_option")

        import uuid
        if 'client_id_option' not in st.session_state:
            st.session_state.client_id_option = str(uuid.uuid4()).replace("-", "").upper()
        client_id = st.text_input("🧾 Client ID", value=st.session_state.client_id_option, key="client_id_option")

        locale = st.text_input("🌍 Locale", "en")
        category_code = st.text_input("📂 Category Code", "GCARD")
        group_code = st.text_input("👥 Group Code", "CC")

        if st.button("🚀 Send Request"):
            if not payment_token:
                st.warning("⚠️ Payment Token is required.")
            else:
                payload = {
                    "paymentToken": payment_token,
                    "clientID": client_id,
                    "locale": locale,
                    "categoryCode": category_code,
                    "groupCode": group_code
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
        st.markdown("### 📨 Request")
        st.json(st.session_state.get('req_payload', {}))

        st.markdown("### 📬 Response")
        try:
            parsed_response = json.loads(st.session_state.get('res_payload', '{}').split('\n\n', 1)[-1])
            st.json(parsed_response)
        except Exception:
            st.code(st.session_state.get('res_payload', 'No response'))

if __name__ == "__main__":
    render_payment_option_details()
