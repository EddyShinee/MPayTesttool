import streamlit as st
from utils.EnvSelector import select_environment
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

        # Replace st_ace with expandable form for Channel Code
        with st.expander("📝 Edit Channel Code", expanded=True):
            col_cc1, col_cc2, col_cc3 = st.columns(3)
            with col_cc1:
                channel_code = st.text_input("Channel Code", value="CC", key="channel_code")
            with col_cc2:
                agent_code = st.text_input("Agent Code", value="", key="agent_code")
            with col_cc3:
                agent_channel_code = st.text_input("Agent Channel Code", value="", key="agent_channel_code")

        # Show formatted JSON preview
        code_json = {
            "channelCode": channel_code,
            "agentCode": agent_code,
            "agentChannelCode": agent_channel_code
        }
        st.code(json.dumps(code_json, indent=2), language="json")

        st.markdown("## 👤 Payment Information")

        # Replace st_ace with form inputs for Payment Information
        with st.expander("📝 Edit Payment Information", expanded=True):
            col_pi1, col_pi2 = st.columns(2)
            with col_pi1:
                customer_name = st.text_input("Customer Name", value="NGUYEN VAN A", key="customer_name")
                customer_email = st.text_input("Customer Email", value="eddy.vu@2c2p.com", key="customer_email")
            with col_pi2:
                is_ipp_chosen = st.checkbox("IPP Chosen", value=False, key="is_ipp_chosen")
                card_email = st.text_input("Card Email", value="eddy.vu@2c2p.com", key="card_email")

        # Build payment information JSON
        payment_data = {
            "name": customer_name,
            "isIppChosen": is_ipp_chosen,
            "cardDetails": {
                "email": card_email
            },
            "loyaltyPoints": [],
            "email": customer_email
        }

        st.code(json.dumps(payment_data, indent=2), language="json")

        # --- Encrypted Card Info Response Input ---
        encrypted_response = st.text_area(
            "🔐 Encrypted Card Info Response",
            "",
            help="Paste full query string here (e.g., encryptedCardInfo=...&...)",
            height=100
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

        col_card1, col_card2 = st.columns(2)
        with col_card1:
            card_number = st.text_input("💳 Card Number", max_chars=19, value="4111 1111 1111 1111")
            expiry_month = st.text_input("📅 Expiry Month (MM)", max_chars=2, value="12")
        with col_card2:
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
                <input type="submit" value="🔒 Submit to Encrypt Card" style="background-color:#0099ff; color:white; font-size:16px; padding:10px 20px; border:none; border-radius:5px; cursor:pointer;">
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

        # Send Request Button
        st.markdown("---")
        if st.button("🚀 Send Request", type="primary", use_container_width=True):
            if not payment_token:
                st.warning("⚠️ Payment Token is required.")
            elif not client_id:
                st.warning("⚠️ Client ID is required.")
            else:
                try:
                    # Prepare payment data
                    payment_data['securePayToken'] = secure_token_input
                    if not secure_token_input:
                        payment_data['cardNo'] = card_number.replace(" ", "")
                        payment_data['expiryMonth'] = expiry_month
                        payment_data['expiryYear'] = expiry_year
                        payment_data['securityCode'] = cvv

                    payload = {
                        "paymentToken": payment_token,
                        "clientID": client_id,
                        "clientIP": client_ip,
                        "locale": locale,
                        "responseReturnUrl": return_url,
                        "payment": {
                            "code": code_json,
                            "data": payment_data
                        }
                    }

                    headers = {"Content-Type": "application/json"}

                    with st.spinner("🔄 Sending request..."):
                        start_time = time.time()
                        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
                        duration = round(time.time() - start_time, 2)

                    st.session_state['response_text'] = f"HTTP {response.status_code} | {duration}s\n\n{response.text}"
                    st.session_state['payload'] = payload

                    if response.status_code == 200:
                        st.session_state['response_summary'] = f"✅ Request successful in {duration} seconds"
                    else:
                        st.session_state[
                            'response_summary'] = f"❌ Request failed with HTTP {response.status_code} in {duration}s"

                except requests.exceptions.Timeout:
                    st.session_state['response_text'] = "❌ Request timeout (30s)"
                    st.session_state['response_summary'] = "❌ Request timed out"
                except requests.exceptions.ConnectionError:
                    st.session_state['response_text'] = "❌ Connection error - Check network/VPS settings"
                    st.session_state['response_summary'] = "❌ Connection failed"
                except Exception as e:
                    st.session_state['response_text'] = f"❌ Error sending request: {str(e)}"
                    st.session_state['response_summary'] = f"❌ Exception occurred during request"

                st.session_state['submitted'] = True
                st.rerun()

    # Response Column
    import re
    with col2:
        st.markdown("### 📨 Request Payload")
        if st.session_state.get('submitted') and 'payload' in st.session_state:
            st.json(st.session_state['payload'])
        else:
            st.info("👆 Click 'Send Request' to see the payload")

        st.markdown("### 📬 API Response")
        if st.session_state.get('submitted'):
            # Show response summary
            summary = st.session_state.get('response_summary', '')
            if "successful" in summary:
                st.success(summary)
            else:
                st.error(summary)

            # Show response details
            response_text = st.session_state.get('response_text', 'No response')

            # Try to extract and display JSON
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if match:
                try:
                    parsed_json = json.loads(match.group())
                    st.json(parsed_json)

                    # Handle redirect URL if present
                    redirect_url = parsed_json.get("data", "")
                    if isinstance(redirect_url, str) and redirect_url.startswith("http"):
                        st.markdown("---")
                        st.markdown("### 🔗 Next Step")
                        st.link_button("➡️ Proceed to ACS Page", redirect_url, type="primary")

                except json.JSONDecodeError:
                    st.code(response_text, language="text")
            else:
                st.code(response_text, language="text")
        else:
            st.info("👆 Submit a request to see the response")

        # Clear response button
        if st.session_state.get('submitted'):
            if st.button("🗑️ Clear Response"):
                for key in ['submitted', 'response_text', 'response_summary', 'payload']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()


if __name__ == "__main__":
    render_do_payment()