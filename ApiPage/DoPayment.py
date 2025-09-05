import streamlit as st
from utils.EnvSelector import select_environment
import json
import uuid
import pyperclip
import requests
import time
import re
import streamlit.components.v1 as components

KEY_PREFIX = str(uuid.uuid4())[:8]


def initialize_payment_token():
    """Initialize payment token from clipboard if available"""
    if 'payment_token' not in st.session_state:
        clipboard_token = pyperclip.paste()
        if clipboard_token.startswith("kSA"):
            st.session_state.payment_token = clipboard_token
        else:
            st.session_state.payment_token = ""


def render_basic_info():
    """Render basic payment information inputs"""
    initialize_payment_token()
    
    payment_token = st.text_input("🔑 Payment Token", value=st.session_state.payment_token, key="payment_token")
    client_id = st.text_input("🧾 Client ID", value=str(uuid.uuid4()).replace("-", "").upper())
    client_ip = st.text_input("📡 Client IP", "47.89.102.11")
    locale = st.text_input("🌐 Locale", "en")
    
    return payment_token, client_id, client_ip, locale


def render_channel_code():
    """Render channel code configuration"""
    st.markdown("## 💰 Channel Code")
    
    with st.expander("📝 Edit Channel Code", expanded=True):
        col_cc1, col_cc2, col_cc3 = st.columns(3)
        with col_cc1:
            channel_code = st.text_input("Channel Code", value="CC", key="channel_code")
        with col_cc2:
            agent_code = st.text_input("Agent Code", value="", key="agent_code")
        with col_cc3:
            agent_channel_code = st.text_input("Agent Channel Code", value="", key="agent_channel_code")

    code_json = {
        "channelCode": channel_code,
        "agentCode": agent_code,
        "agentChannelCode": agent_channel_code
    }
    st.code(json.dumps(code_json, indent=2), language="json")
    
    return code_json


def render_payment_information():
    """Render payment information and optional fields"""
    st.markdown("## 👤 Payment Information")
    
    with st.expander("📝 Edit Payment Information", expanded=True):
        col_pi1, col_pi2 = st.columns(2)
        with col_pi1:
            customer_name = st.text_input("Customer Name", value="NGUYEN VAN A", key="customer_name")
            customer_email = st.text_input("Customer Email", value="eddy.vu@2c2p.com", key="customer_email")
        with col_pi2:
            optional_fields = {}
            st.markdown("IPP Payment")
            if st.checkbox("IPP Payment", key=f"{KEY_PREFIX}_checkbox_ippPayment"):
                optional_fields['interestType'] = "Y"
                optional_fields['installmentPeriod'] = st.text_input(
                    "Installment Period",
                    key=f"{KEY_PREFIX}_installment_period"
                )
            card_email = st.text_input("Card Email", value="eddy.vu@2c2p.com", key="card_email")
            qr_type = st.selectbox(
                "QR Type",
                options=["", "RAW", "BASE64", "URL"],
                index=0,
                key=f"{KEY_PREFIX}_qrType"
            )
            optional_fields['qrType'] = qr_type
    # Build payment information JSON
    payment_data = {
        "name": customer_name,
        "cardDetails": {"email": card_email},
        "loyaltyPoints": [],
        "email": customer_email
    }
    
    # Add optional fields if they exist
    for key, value in optional_fields.items():
        if value:
            payment_data[key] = value

    st.code(json.dumps(payment_data, indent=2), language="json")
    return payment_data


def render_card_encryption_form(card_number, expiry_month, expiry_year, cvv):
    """Render the card encryption form with JavaScript"""
    st.markdown("### 🧾 2C2P Card Encryption Form")
    
    button_html = f'''
    <div id="encryption-container">
        <form id="2c2p-payment-form" style="display: none;">
            <input type="hidden" data-encrypt="cardnumber" value="{card_number.replace(" ", "")}">
            <input type="hidden" data-encrypt="month" value="{expiry_month}">
            <input type="hidden" data-encrypt="year" value="{expiry_year}">
            <input type="hidden" data-encrypt="cvv" value="{cvv}">
        </form>

        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button id="encrypt-button" onclick="encryptCard()" 
                    style="background: linear-gradient(135deg, #667eea, #764ba2); color:white; font-size:14px; padding:10px 20px; border:none; border-radius:8px; cursor:pointer; font-weight: 600; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); transition: all 0.3s ease;">
                🔒 Encrypt Card Data
            </button>

            <button id="manual-copy-button" onclick="copyToClipboard()" style="display: none;
                    background: linear-gradient(135deg, #48bb78, #38a169); color:white; font-size:14px; padding:10px 20px; border:none; border-radius:8px; cursor:pointer; font-weight: 600; box-shadow: 0 4px 12px rgba(72, 187, 120, 0.3); transition: all 0.3s ease;">
                📋 Copy Encrypted Token
            </button>
        </div>

        <div id="encryption-status" style="margin-top: 15px; padding: 10px; border-radius: 6px; display: none;"></div>
        <div id="encryption-result" style="margin-top: 15px; padding: 15px; background: #f8fafc; border-radius: 6px; display: none; font-family: Monaco, monospace; font-size: 12px; word-break: break-all;"></div>
    </div>

    <script src="https://demo2.2c2p.com/2C2PFrontEnd/SecurePayment/api/my2c2p.1.7.6.min.js"></script>
    <script>
        let encryptedToken = null;

        // Style the buttons on hover
        ['encrypt-button', 'manual-copy-button'].forEach(id => {{
            const btn = document.getElementById(id);
            if (btn) {{
                btn.addEventListener('mouseenter', function() {{
                    this.style.transform = 'translateY(-2px)';
                    this.style.boxShadow = this.style.boxShadow.replace('0 4px 12px', '0 6px 20px');
                }});

                btn.addEventListener('mouseleave', function() {{
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = this.style.boxShadow.replace('0 6px 20px', '0 4px 12px');
                }});
            }}
        }});

        function showStatus(message, type) {{
            const statusEl = document.getElementById('encryption-status');
            statusEl.style.display = 'block';
            statusEl.innerHTML = message;

            const styles = {{
                'loading': {{ background: '#e6f3ff', color: '#0066cc', border: '1px solid #b3d9ff' }},
                'success': {{ background: '#e8f5e8', color: '#2d7a2d', border: '1px solid #a3d9a3' }},
                'error': {{ background: '#ffe6e6', color: '#cc0000', border: '1px solid #ffb3b3' }}
            }};

            Object.assign(statusEl.style, styles[type] || styles['loading']);
        }}

        function showResult(data) {{
            const resultEl = document.getElementById('encryption-result');
            resultEl.style.display = 'block';
            resultEl.innerHTML = '<strong>🔐 Encrypted Data:</strong><br>' + JSON.stringify(data, null, 2);

            const copyBtn = document.getElementById('manual-copy-button');
            if (copyBtn) copyBtn.style.display = 'inline-block';
        }}

        function copyToClipboard() {{
            if (encryptedToken) {{
                navigator.clipboard.writeText(encryptedToken).then(() => {{
                    showStatus('✅ Encrypted token copied to clipboard!', 'success');
                    setTimeout(() => {{
                        const tempInput = document.createElement('input');
                        tempInput.value = encryptedToken;
                        tempInput.style.position = 'absolute';
                        tempInput.style.left = '-9999px';
                        document.body.appendChild(tempInput);
                        tempInput.select();
                        document.execCommand('copy');
                        document.body.removeChild(tempInput);
                        showStatus('✅ Token copied! Paste it into the securePayToken field above.', 'success');
                    }}, 100);
                }}).catch(err => {{
                    showStatus('❌ Failed to copy to clipboard', 'error');
                    console.error('Copy failed:', err);
                }});
            }}
        }}

        async function sendToWebhook(formData) {{
            try {{
                showStatus('📤 Sending encrypted data to webhook...', 'loading');

                const endpoints = [
                    'https://eddy.io.vn/callback/webhook/encrypt-card?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiRWRkeSIsImFkbWluIjp0cnVlLCJwaG9uZSI6OTA5NzAwOTgwLCJyYW5kb21fbnVtYmVyIjoxOTkzLCJleHAiOjE3NTU5MzA5NTksImlhdCI6MTc1NTg0NDU1OX0.UXPAQxfEWK1W3RdF9L5yGx023ZYNunnn1uGuZDjZjwo',
                    'http://localhost:8000/webhook/encrypt-card?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiRWRkeSIsImFkbWluIjp0cnVlLCJwaG9uZSI6OTA5NzAwOTgwLCJyYW5kb21fbnVtYmVyIjoxOTkzLCJleHAiOjE3NTU5MzA5NTksImlhdCI6MTc1NTg0NDU1OX0.UXPAQxfEWK1W3RdF9L5yGx023ZYNunnn1uGuZDjZjwo'
                ];

                for (const endpoint of endpoints) {{
                    try {{
                        const response = await fetch(endpoint, {{
                            method: 'POST',
                            mode: 'cors',
                            headers: {{
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Accept': 'application/json, text/html, */*'
                            }},
                            body: new URLSearchParams(formData).toString()
                        }});

                        if (response.ok) {{
                            showStatus('✅ Successfully sent to webhook server!', 'success');
                            if (formData.get('encryptedCardInfo')) {{
                                showResult({{
                                    encryptedCardInfo: formData.get('encryptedCardInfo'),
                                    timestamp: new Date().toISOString(),
                                    webhook: endpoint
                                }});
                                navigator.clipboard.writeText(formData.get('encryptedCardInfo'));
                                showStatus('✅ Encrypted token copied to clipboard!', 'success');
                            }}
                            return;
                        }}
                    }} catch (error) {{
                        console.log(`Failed to reach ${{endpoint}}:`, error);
                        continue;
                    }}
                }}
                throw new Error('All webhook endpoints failed');
            }} catch (error) {{
                console.error('Webhook error:', error);
                showStatus('⚠️ Webhook call failed, but encryption succeeded!', 'error');
                if (formData.get('encryptedCardInfo')) {{
                    showResult({{
                        encryptedCardInfo: formData.get('encryptedCardInfo'),
                        timestamp: new Date().toISOString(),
                        note: 'Encryption successful, webhook failed'
                    }});
                    navigator.clipboard.writeText(formData.get('encryptedCardInfo'));
                    showStatus('✅ Encrypted token copied to clipboard! (Webhook failed but data is ready)', 'success');
                }}
            }}
        }}

        function encryptCard() {{
            const button = document.getElementById('encrypt-button');
            button.disabled = true;
            button.innerHTML = '🔄 Encrypting...';
            button.style.opacity = '0.7';

            showStatus('🔐 Encrypting card data...', 'loading');

            My2c2p.onSubmitForm("2c2p-payment-form", async function(errCode, errDesc) {{
                button.disabled = false;
                button.innerHTML = '🔒 Encrypt Card Data';
                button.style.opacity = '1';

                if (errCode != 0) {{
                    showStatus('❌ Encryption failed: ' + errDesc + ' (Code: ' + errCode + ')', 'error');
                    return;
                }}

                showStatus('✅ Card data encrypted successfully!', 'success');

                const form = document.getElementById('2c2p-payment-form');
                const formData = new FormData();

                const inputs = form.querySelectorAll('input');
                inputs.forEach(input => {{
                    if (input.value) {{
                        const name = input.name || input.getAttribute('data-encrypt') || 'encryptedCardInfo';
                        formData.append(name, input.value);

                        if (name === 'encryptedCardInfo' || input.value.length > 50) {{
                            encryptedToken = input.value;
                        }}
                    }}
                }});

                if (encryptedToken) {{
                    showResult({{
                        encryptedCardInfo: encryptedToken,
                        timestamp: new Date().toISOString()
                    }});
                }}

                try {{
                    await sendToWebhook(formData);
                }} catch (e) {{
                    console.log('Webhook failed, but encryption succeeded');
                }}
            }});

            const form = document.getElementById('2c2p-payment-form');
            if (form) {{
                form.dispatchEvent(new Event('submit'));
            }}
        }}
    </script>
    '''

    components.html(button_html, height=300)
    st.info("💡 **Instructions:** Click 'Encrypt Card Data' → Copy the encrypted token → Paste it into the 'securePayToken' field above")


def render_card_details():
    """Render card details input section"""
    st.markdown("---")
    st.markdown("### 🔐 Card Details (for securePayToken)")

    col_card1, col_card2 = st.columns(2)
    with col_card1:
        card_number = st.text_input("💳 Card Number", max_chars=19, value="4111 1111 1111 1111")
        expiry_month = st.text_input("📅 Expiry Month (MM)", max_chars=2, value="12")
    with col_card2:
        expiry_year = st.text_input("📅 Expiry Year (YYYY)", max_chars=4, value="2029")
        cvv = st.text_input("🔒 CVV / CVC", type="password", max_chars=4, value="123")

    secure_token_input = st.text_input("🔐 securePayToken", key="secure_token_input")

    if all([card_number, expiry_month, expiry_year, cvv]):
        render_card_encryption_form(card_number, expiry_month, expiry_year, cvv)
    else:
        st.info("ℹ️ Enter all card details to see encryption form.")

    return card_number, expiry_month, expiry_year, cvv, secure_token_input


def send_payment_request(api_url, payment_token, client_id, client_ip, locale, code_json, payment_data, secure_token_input, card_number, expiry_month, expiry_year, cvv):
    """Send the payment request to the API"""
    if not payment_token:
        st.warning("⚠️ Payment Token is required.")
        return False
    elif not client_id:
        st.warning("⚠️ Client ID is required.")
        return False

    try:
        # Prepare payment data
        if secure_token_input:
            payment_data['securePayToken'] = secure_token_input
        else:
            payment_data['cardNo'] = card_number.replace(" ", "")
            payment_data['expiryMonth'] = expiry_month
            payment_data['expiryYear'] = expiry_year
            payment_data['securityCode'] = cvv

        payload = {
            "paymentToken": payment_token,
            "clientID": client_id,
            "clientIP": client_ip,
            "locale": locale,
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
            st.session_state['response_summary'] = f"❌ Request failed with HTTP {response.status_code} in {duration}s"

        return True

    except requests.exceptions.Timeout:
        st.session_state['response_text'] = "❌ Request timeout (30s)"
        st.session_state['response_summary'] = "❌ Request timed out"
    except requests.exceptions.ConnectionError:
        st.session_state['response_text'] = "❌ Connection error - Check network/VPS settings"
        st.session_state['response_summary'] = "❌ Connection failed"
    except Exception as e:
        st.session_state['response_text'] = f"❌ Error sending request: {str(e)}"
        st.session_state['response_summary'] = f"❌ Exception occurred during request"

    return False


def render_response_section():
    """Render the response display section"""
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


def render_do_payment():
    """Main function to render the Do Payment page"""
    st.title("💳 Do Payment")
    env, api_url = select_environment(key_suffix="do_payment", env_type="DoPayment")
    
    col1, col2 = st.columns([1, 1])

    with col1:
        # Render all input sections
        payment_token, client_id, client_ip, locale = render_basic_info()
        code_json = render_channel_code()
        payment_data = render_payment_information()
        card_number, expiry_month, expiry_year, cvv, secure_token_input = render_card_details()

        # Send Request Button
        st.markdown("---")
        if st.button("🚀 Send Request", type="primary", use_container_width=True):
            success = send_payment_request(
                api_url, payment_token, client_id, client_ip, locale, 
                code_json, payment_data, secure_token_input, 
                card_number, expiry_month, expiry_year, cvv
            )
            if success:
                st.session_state['submitted'] = True
                st.rerun()

    # Response Column
    with col2:
        render_response_section()


if __name__ == "__main__":
    render_do_payment()