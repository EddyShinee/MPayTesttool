import streamlit as st
from utils.EnvSelector import select_environment
from streamlit_ace import st_ace
import json
import uuid
import pyperclip
import requests
import time

def render_do_payment():
    st.title("💳 Do Payment")
    env, api_url = select_environment(key_suffix="do_payment", env_type="DoPayment")
    col1, col2 = st.columns([1, 1])
    with col1:
        # PaymentToken and ClientID
        # --- Set session state for payment_token if not present ---
        if 'payment_token' not in st.session_state:
            clipboard_token = pyperclip.paste()
            if clipboard_token.startswith("kSA"):
                st.session_state.payment_token = clipboard_token
            else:
                st.session_state.payment_token = ""
        payment_token = st.text_input("🔑 Payment Token", value=st.session_state.payment_token, key="payment_token")
        client_id = st.text_input("🧾 Client ID", value=str(uuid.uuid4()).replace("-", "").upper())
        client_ip = st.text_input("📡 Client IP", "47.89.102.11")

        # Locale and Return URL
        locale = st.text_input("🌐 Locale", "en")
        return_url = st.text_input("🔁 Response Return URL", "https://webhook.site/08fd12ec-4a71-4499-968c-0dbe729b8686")

        st.markdown("## 💰 Channel Code")
        default_code_json = {
            "channelCode": "CC",
            "agentCode": "",
            "agentChannelCode": ""
        }
        code_json_raw = st_ace(
            value=json.dumps(default_code_json, indent=2),
            language="json",
            theme="chrome",
            key="payment_code_editor",
            height=200
        )

        st.markdown("## 👤 Payment Information")
        default_data_json = {
            "name": "NGUYEN VAN A",
            "isIppChosen": False,
            "cardDetails": {
                "email": "eddy.vu@2c2p.com"
            },
            "loyaltyPoints": [],
            "email": "eddy.vu@2c2p.com"
        }
        data_json_raw = st_ace(
            value=json.dumps(default_data_json, indent=2),
            language="json",
            theme="chrome",
            key="payment_data_editor",
            height=200
        )

        # --- Encrypted Card Info Response Input ---
        encrypted_response = st.text_area(
            "🔐 Encrypted Card Info Response",
            "",
            help="Paste full query string here (e.g., encryptedCardInfo=...&...)"
        )

        from urllib.parse import parse_qs
        if encrypted_response:
            parsed_qs = parse_qs(encrypted_response)
            if 'encryptedCardInfo' in parsed_qs:
                secure_token = parsed_qs['encryptedCardInfo'][0]
                st.session_state.secure_token_input = secure_token
                st.success("✅ securePayToken auto-filled from Encrypted Card Info.")

        secure_token_input = st.text_input("🔐 securePayToken", key="secure_token_input")

        # --- Card Details Inputs for securePayToken ---
        st.markdown("---")
        st.markdown("### 🔐 Card Details (for securePayToken)")

        card_number = st.text_input("💳 Card Number", max_chars=16, value="4111 1111 1111 1111")
        expiry_month = st.text_input("📅 Expiry Month (MM)", max_chars=2, value="12")
        expiry_year = st.text_input("📅 Expiry Year (YYYY)", max_chars=4, value="2029")
        cvv = st.text_input("🔒 CVV / CVC", type="password", max_chars=4, value="123")

        if all([card_number, expiry_month, expiry_year, cvv]):
            st.markdown("### 🧾 2C2P Card Encryption Form")
            button_html = f'''
            <form id="2c2p-payment-form" action="https://webhook.site/08fd12ec-4a71-4499-968c-0dbe729b8686" method="POST">
                <input type="hidden" data-encrypt="cardnumber" value="{card_number.replace(" ", "")}">
                <input type="hidden" data-encrypt="month" value="{expiry_month}">
                <input type="hidden" data-encrypt="year" value="{expiry_year}">
                <input type="hidden" data-encrypt="cvv" value="{cvv}">
                <input type="submit" value="🔒 Submit to Encrypt Card" style="background-color:#0099ff; color:white; font-size:16px; padding:10px 20px; border:none; border-radius:5px;">
            </form>
            <script src="https://demo2.2c2p.com/2C2PFrontEnd/SecurePayment/api/my2c2p.1.7.6.min.js"></script>
            <script>
                My2c2p.onSubmitForm("2c2p-payment-form", function(errCode, errDesc){{
                    if(errCode!=0){{
                        alert(errDesc+" ("+errCode+")");
                    }}
                }});
            </script>
            '''
            import streamlit.components.v1 as components
            components.html(button_html, height=100)
        else:
            st.info("ℹ️ Enter all card details to see form preview.")

        if st.button("🚀 Send Request"):
            if not payment_token:
                st.warning("⚠️ Payment Token is required.")
            elif not client_id:
                st.warning("⚠️ Client ID is required.")
            else:
                try:
                    data_dict = json.loads(data_json_raw)
                    data_dict['securePayToken'] = secure_token_input
                    if not secure_token_input:
                        data_dict['cardNo'] = card_number.replace(" ", "")
                        data_dict['expiryMonth'] = expiry_month
                        data_dict['expiryYear'] = expiry_year
                        data_dict['securityCode'] = cvv
                    payload = {
                        "paymentToken": payment_token,
                        "clientID": client_id,
                        "clientIP": client_ip,
                        "locale": locale,
                        "responseReturnUrl": return_url,
                        "payment": {
                            "code": json.loads(code_json_raw),
                            "data": data_dict
                        }
                    }
                    headers = {"Content-Type": "application/json"}
                    start_time = time.time()
                    response = requests.post(api_url, headers=headers, json=payload)
                    duration = round(time.time() - start_time, 2)

                    st.session_state['response_text'] = f"HTTP {response.status_code} | {duration}s\n\n{response.text}"
                    if response.status_code == 200:
                        st.session_state['response_summary'] = f"✅ Request successful in {duration} seconds"
                    else:
                        st.session_state['response_summary'] = f"❌ Request failed with HTTP {response.status_code} in {duration}s"
                except Exception as e:
                    st.session_state['response_text'] = f"❌ Error sending request: {str(e)}"
                    st.session_state['response_summary'] = f"❌ Exception occurred during request"
                st.session_state['submitted'] = True

    import re
    with col2:
        st.markdown("### 📨 Request")
        if st.session_state.get('submitted'):
            try:
                st.json(payload)
            except:
                st.code("⚠️ Payload could not be displayed.")

        st.markdown("### 📬 Response")
        if st.session_state.get('submitted'):
            st.info(st.session_state.get('response_summary', ''))
            response_text = st.session_state.get('response_text', 'No response')
            # Attempt to extract JSON body
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                try:
                    parsed_json = json.loads(match.group())
                    st.json(parsed_json)
                    # If 'data' field contains redirect URL, create a button to navigate
                    redirect_url = parsed_json.get("data", "")
                    if isinstance(redirect_url, str) and redirect_url.startswith("http"):
                        st.markdown(f"[➡️ Click here to proceed ACS page]({redirect_url})", unsafe_allow_html=True)
                except Exception:
                    st.code(response_text)
            else:
                st.code(response_text)


if __name__ == "__main__":
    render_do_payment()