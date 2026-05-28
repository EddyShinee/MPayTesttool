import streamlit as st
import streamlit.components.v1 as components
import json
import datetime
import jwt  # PyJWT
import base64
import uuid
import pyperclip
import time
import subprocess
import platform
from utils.EnvSelector import select_environment
from ApiPage.common.config import get_secret
from ApiPage.common.http_client import post_json
from ApiPage.common.response_view import save_request_trace, render_request_response
from ApiPage.common.ui import apply_submit_button_style

# Constants
KEY_PREFIX = "payment_token"
DEFAULT_MERCHANT_ID = "704704000000000"
DEFAULT_SECRET_KEY = get_secret("MERCHANT_SHA_KEY", "")
PAYMENT_CHANNEL_OPTIONS = ["ALL", "CC", "IPP", "APM", "QR", "VNPAY", "MOMO", "ZALOPAY"]
PT_PAYLOAD_DATA_KEY = "payment_token_payload_data"
PT_REQUEST_PAYLOAD_KEY = "payment_token_request_payload"
PT_RESPONSE_PAYLOAD_KEY = "payment_token_response_payload"


class PaymentTokenGenerator:
    def __init__(self):
        self.session_state = st.session_state

    def copy_to_clipboard(self, text, label="text"):
        """Copy text to clipboard with multiple fallback methods"""
        success = False
        error_msg = ""
        
        # Method 1: Try pyperclip first
        try:
            pyperclip.copy(text)
            success = True
        except Exception as e:
            error_msg = f"pyperclip failed: {str(e)}"
            
            # Method 2: Try system clipboard commands
            try:
                if platform.system() == "Darwin":  # macOS
                    process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                    process.communicate(input=text.encode('utf-8'))
                    success = True
                elif platform.system() == "Windows":
                    process = subprocess.Popen(['clip'], stdin=subprocess.PIPE)
                    process.communicate(input=text.encode('utf-8'))
                    success = True
                elif platform.system() == "Linux":
                    process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                    process.communicate(input=text.encode('utf-8'))
                    success = True
            except Exception as e2:
                error_msg = f"pyperclip failed: {str(e)}, system command failed: {str(e2)}"
        
        return success, error_msg

    @staticmethod
    def generate_invoice_no():
        return datetime.datetime.now().strftime("INV%y%m%d%H%M%S")

    @staticmethod
    def generate_idempotency_id():
        return f"idem-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    @staticmethod
    def decode_jwt_payload(jwt_token):
        try:
            payload_part = jwt_token.split('.')[1]
            padding = '=' * (-len(payload_part) % 4)
            decoded_bytes = base64.urlsafe_b64decode(payload_part + padding)
            return json.loads(decoded_bytes)
        except Exception as e:
            return {"error": str(e)}

    def initialize_session_state(self):
        """Initialize session state variables"""
        if "invoice_no" not in self.session_state:
            self.session_state["invoice_no"] = self.generate_invoice_no()
        if "idempotency_id" not in self.session_state:
            self.session_state["idempotency_id"] = self.generate_idempotency_id()

    def render_payment_channel_input(self):
        """Render payment channel selection with custom input option"""
        st.write("**Payment Channel:**")

        # Radio button for selection method
        channel_mode = st.radio(
            "Choose input method:",
            ["Select from list", "Custom input"],
            key=f"{KEY_PREFIX}_channel_mode",
            horizontal=True
        )

        if channel_mode == "Select from list":
            payment_channel = st.multiselect(
                "Select payment channels:",
                PAYMENT_CHANNEL_OPTIONS,
                default=["ALL"],
                key=f"{KEY_PREFIX}_payment_channel_select"
            )
        else:
            custom_input = st.text_input(
                "Enter custom payment channels (comma-separated):",
                placeholder="e.g., CUSTOM1,CUSTOM2,ALL",
                key=f"{KEY_PREFIX}_payment_channel_custom"
            )
            payment_channel = [ch.strip() for ch in custom_input.split(',') if ch.strip()]

        return payment_channel

    def render_basic_fields(self):
        """Render basic payment fields"""
        col1, col2 = st.columns(2)

        with col1:
            merchant_id = st.text_input(
                "Merchant ID",
                DEFAULT_MERCHANT_ID,
                key=f"{KEY_PREFIX}_merchant_id"
            )

            invoice_no = st.text_input(
                "Invoice No",
                value=self.session_state["invoice_no"],
                key=f"{KEY_PREFIX}_invoice_no"
            )

            idempotency_id = st.text_input(
                "Idempotency ID",
                value=self.session_state["idempotency_id"],
                key=f"{KEY_PREFIX}_idempotency_id"
            )

        with col2:
            description = st.text_input(
                "Description",
                f"Eddy - Payment {invoice_no}",
                key=f"{KEY_PREFIX}_description"
            )

            amount = st.number_input(
                "Amount",
                value=5000,
                min_value=1,
                key=f"{KEY_PREFIX}_amount"
            )

            currency_code = st.text_input(
                "Currency Code",
                "VND",
                key=f"{KEY_PREFIX}_currency_code"
            )

        # Payment channel section
        payment_channel = self.render_payment_channel_input()

        return {
            'merchant_id': merchant_id,
            'invoice_no': invoice_no,
            'idempotency_id': idempotency_id,
            'description': description,
            'amount': amount,
            'currency_code': currency_code,
            'payment_channel': payment_channel
        }

    def render_advanced_options(self):
        """Render advanced/optional fields"""
        optional_fields = {}

        with st.expander("➕ Advanced Options"):
            # URL Options
            st.subheader("🔗 URL Configuration")
            col1, col2 = st.columns(2)

            with col1:
                if st.checkbox("Frontend Return URL", key=f"{KEY_PREFIX}_checkbox_frontendReturnUrl", value=True):
                    optional_fields['frontendReturnUrl'] = st.text_input(
                        "Frontend Return URL",
                        "https://eddy.io.vn/callback/webhook/callback-frontend",
                        key=f"{KEY_PREFIX}_frontend_return_url"
                    )

            with col2:
                if st.checkbox("Backend Return URL", key=f"{KEY_PREFIX}_checkbox_backendReturnUrl", value=True):
                    optional_fields['backendReturnUrl'] = st.text_input(
                        "Backend Return URL",
                        "https://eddy.io.vn/callback/webhook/payment",
                        key=f"{KEY_PREFIX}_backend_return_url"
                    )

            # Payment Options
            st.subheader("💳 Payment Configuration")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.checkbox("Locale", key=f"{KEY_PREFIX}_checkbox_locale"):
                    optional_fields['locale'] = st.selectbox(
                        "Locale", ["vi", "en"],
                        key=f"{KEY_PREFIX}_locale"
                    )

                if st.checkbox("Request 3DS", key=f"{KEY_PREFIX}_checkbox_request3DS"):
                    optional_fields['request3DS'] = st.selectbox(
                        "Request 3DS", ["Y", "N", "F"],
                        key=f"{KEY_PREFIX}_request3ds"
                    )

            with col2:
                if st.checkbox("Payment Expiry", key=f"{KEY_PREFIX}_checkbox_paymentExpiry"):
                    optional_fields['paymentExpiry'] = st.text_input(
                        "Payment Expiry (yyyy-MM-dd HH:mm:ss)",
                        key=f"{KEY_PREFIX}_payment_expiry"
                    )

                if st.checkbox("Agent Channel", key=f"{KEY_PREFIX}_checkbox_agentChannel"):
                    optional_fields['agentChannel'] = st.text_input(
                        "Agent Channel",
                        key=f"{KEY_PREFIX}_agent_channel"
                    )

            with col3:
                if st.checkbox("Immediate Payment", key=f"{KEY_PREFIX}_checkbox_immediatePayment"):
                    optional_fields['immediatePayment'] = st.selectbox(
                        "Immediate Payment", ["Y", "N"],
                        key=f"{KEY_PREFIX}_immediate_payment"
                    )

            # Token Options
            st.subheader("🎫 Token Configuration")
            col1, col2 = st.columns(2)

            with col1:
                if st.checkbox("Tokenize", key=f"{KEY_PREFIX}_checkbox_tokenize"):
                    optional_fields['tokenize'] = st.selectbox(
                        "Tokenize", [True, False],
                        key=f"{KEY_PREFIX}_tokenize"
                    )

                if st.checkbox("Customer Token Only", key=f"{KEY_PREFIX}_checkbox_customerTokenOnly"):
                    optional_fields['customerTokenOnly'] = st.checkbox(
                        "Customer Token Only",
                        key=f"{KEY_PREFIX}_customer_token_only"
                    )

            with col2:
                if st.checkbox("Customer Token", key=f"{KEY_PREFIX}_checkbox_customerToken"):
                    raw_token_input = st.text_area(
                        "Customer Token (comma-separated)",
                        key=f"{KEY_PREFIX}_customer_token"
                    )
                    optional_fields['customerToken'] = [
                        token.strip() for token in raw_token_input.split(',') if token.strip()
                    ]

                if st.checkbox("Tokenize Only", key=f"{KEY_PREFIX}_checkbox_tokenizeOnly"):
                    optional_fields['tokenizeOnly'] = st.checkbox(
                        "Tokenize Only",
                        key=f"{KEY_PREFIX}_tokenize_only"
                    )

            # 3DS Configuration Block
            st.subheader("🎫 3DS Configuration")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.checkbox("Protocol Version", key=f"{KEY_PREFIX}_checkbox_protocol_version"):
                    optional_fields['protocolVersion'] = st.text_input(
                        "Protocol Version",
                        value="2.1.0",
                        help="Default: 2.1.0",
                        key=f"{KEY_PREFIX}_protocol_version"
                    )
                    
                if st.checkbox("ECI", key=f"{KEY_PREFIX}_checkbox_eci"):
                    optional_fields['eci'] = st.selectbox(
                        "ECI",
                        options=["", "00", "01", "02", "05", "06", "07", "80", "81", "82", "83"],
                        help="Length: 2 characters",
                        key=f"{KEY_PREFIX}_eci"
                    )
            
            with col2:
                if st.checkbox("CAVV", key=f"{KEY_PREFIX}_checkbox_cavv"):
                    optional_fields['cavv'] = st.text_input(
                        "CAVV",
                        help="Length: 40 characters",
                        key=f"{KEY_PREFIX}_cavv"
                    )
                    
                if st.checkbox("DS Transaction ID", key=f"{KEY_PREFIX}_checkbox_ds_transaction_id"):
                    optional_fields['dsTransactionId'] = st.text_input(
                        "DS Transaction ID",
                        help="Length: 36 characters (GUID)",
                        key=f"{KEY_PREFIX}_ds_transaction_id"
                    )

            # Installment & Recurring fields (moved from nested expander)
            st.subheader("💰 Installment & Recurring")
            self._render_installment_fields(optional_fields)
            self._render_recurring_fields(optional_fields)

            # Other fields (moved from nested expander)
            st.subheader("🔧 Other Options")
            self._render_other_fields(optional_fields)

        return optional_fields

    def _render_installment_fields(self, optional_fields):
        """Render installment related fields"""
        col1, col2 = st.columns(2)

        with col1:
            if st.checkbox("Interest Type", key=f"{KEY_PREFIX}_checkbox_interestType"):
                optional_fields['interestType'] = st.selectbox(
                    "Interest Type", ["FULL", "PARTIAL"],
                    key=f"{KEY_PREFIX}_interest_type"
                )

            if st.checkbox("Installment Period Filter", key=f"{KEY_PREFIX}_checkbox_installmentPeriodFilter"):
                optional_fields['installmentPeriodFilter'] = st.text_input(
                    "Installment Period Filter",
                    key=f"{KEY_PREFIX}_installment_period_filter"
                )

        with col2:
            if st.checkbox("Installment Bank Filter", key=f"{KEY_PREFIX}_checkbox_installmentBankFilter"):
                optional_fields['installmentBankFilter'] = st.text_input(
                    "Installment Bank Filter",
                    key=f"{KEY_PREFIX}_installment_bank_filter"
                )

    def _render_recurring_fields(self, optional_fields):
        """Render recurring payment fields"""
        col1, col2 = st.columns(2)

        with col1:
            if st.checkbox("Recurring", key=f"{KEY_PREFIX}_checkbox_recurring"):
                optional_fields['recurring'] = st.selectbox(
                    "Recurring", ["Y", "N"],
                    key=f"{KEY_PREFIX}_recurring"
                )

            if st.checkbox("Recurring Amount", key=f"{KEY_PREFIX}_checkbox_recurringAmount"):
                optional_fields['recurringAmount'] = st.number_input(
                    "Recurring Amount", value=0,
                    key=f"{KEY_PREFIX}_recurring_amount"
                )

            if st.checkbox("Recurring Interval", key=f"{KEY_PREFIX}_checkbox_recurringInterval"):
                optional_fields['recurringInterval'] = st.text_input(
                    "Recurring Interval",
                    key=f"{KEY_PREFIX}_recurring_interval"
                )

        with col2:
            if st.checkbox("Recurring Count", key=f"{KEY_PREFIX}_checkbox_recurringCount"):
                optional_fields['recurringCount'] = st.number_input(
                    "Recurring Count", value=0,
                    key=f"{KEY_PREFIX}_recurring_count"
                )

            if st.checkbox("Charge Next Date", key=f"{KEY_PREFIX}_checkbox_chargeNextDate"):
                optional_fields['chargeNextDate'] = st.date_input(
                    "Charge Next Date",
                    key=f"{KEY_PREFIX}_charge_next_date"
                )

            if st.checkbox("Charge On Date", key=f"{KEY_PREFIX}_checkbox_chargeOnDate"):
                optional_fields['chargeOnDate'] = st.date_input(
                    "Charge On Date",
                    key=f"{KEY_PREFIX}_charge_on_date"
                )

    def _render_other_fields(self, optional_fields):
        """Render other miscellaneous fields"""
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.checkbox("Product Code", key=f"{KEY_PREFIX}_checkbox_productCode"):
                optional_fields['productCode'] = st.text_input(
                    "Product Code",
                    key=f"{KEY_PREFIX}_product_code"
                )

            if st.checkbox("Store Credentials", key=f"{KEY_PREFIX}_checkbox_storeCredentials"):
                optional_fields['storeCredentials'] = st.selectbox(
                    "Store Credentials", ["F", "S", "N"],
                    key=f"{KEY_PREFIX}_store_credentials"
                )
            if st.checkbox("Customer Address", key=f"{KEY_PREFIX}_checkbox_customerAddress"):
                customer_address = {
                    "billing": {
                        "address1": "123 placeholder address",
                        "city": "Ipoh",
                        "countryCode": "MY",
                        "postalCode": "50000"
                            }
                        }
                # customer_address_json_raw = st_ace(
                #     value=json.dumps(customer_address, indent=2),
                #     language="json",
                #     theme="chrome",
                #     key="browser_json_editor",
                #     height=200
                # )

                optional_fields['customerAddress'] = customer_address

        with col2:
            if st.checkbox("Promotion Code", key=f"{KEY_PREFIX}_checkbox_promotionCode"):
                optional_fields['promotionCode'] = st.text_input(
                    "Promotion Code",
                    key=f"{KEY_PREFIX}_promotion_code"
                )

            if st.checkbox("Payment Route ID", key=f"{KEY_PREFIX}_checkbox_paymentRouteID"):
                optional_fields['paymentRouteID'] = st.text_input(
                    "Payment Route ID",
                    key=f"{KEY_PREFIX}_payment_route_id"
                )
            if st.checkbox("Transaction Initiator", key=f"{KEY_PREFIX}_checkbox_transactionInitiator"):
                optional_fields['transactionInitiator'] = st.selectbox(
                    "Transaction Initiator", ["C", "M"],
                    key=f"{KEY_PREFIX}_transaction_initiator"
                )

        with col3:
            if st.checkbox("Allow Accumulate", key=f"{KEY_PREFIX}_checkbox_allowAccumulate"):
                optional_fields['allowAccumulate'] = st.selectbox(
                    "Allow Accumulate", ["Y", "N"],
                    key=f"{KEY_PREFIX}_allow_accumulate"
                )

            if st.checkbox("Max Accumulate Amount", key=f"{KEY_PREFIX}_checkbox_maxAccumulateAmount"):
                optional_fields['maxAccumulateAmount'] = st.number_input(
                    "Max Accumulate Amount", value=0,
                    key=f"{KEY_PREFIX}_max_accumulate_amount"
                )

    def send_payment_request(self, payload_data, secret_key, api_url):
        """Send payment token request and return normalized result."""
        try:
            start_time = datetime.datetime.now()
            jwt_token = jwt.encode(payload_data, secret_key, algorithm="HS256")

            result = post_json(
                api_url,
                {"payload": jwt_token},
                api_name="PaymentToken",
                headers={"Content-Type": "application/json"},
                timeout=(10, 300),
                retries=2,
            )

            end_time = datetime.datetime.now()
            total_elapsed = (end_time - start_time).total_seconds()

            return {
                'success': True,
                'jwt_token': jwt_token,
                'response': result.text if not result.error else f"ERROR: {result.error}",
                'status_code': result.status_code,
                'start_time': start_time,
                'end_time': end_time,
                'duration': total_elapsed,
                'trace': result,
            }

        except Exception as e:
            end_time = datetime.datetime.now()
            total_elapsed = (end_time - start_time).total_seconds()

            return {
                'success': False,
                'error': str(e),
                'jwt_token': None,
                'response': None,
                'start_time': start_time,
                'end_time': end_time,
                'duration': total_elapsed
            }

    @st.dialog("💳 2C2P Payment Gateway", width="large")
    def show_payment_dialog(self, web_url):
        """Show payment dialog with iframe"""
        
        # Add warning about potential iframe issues
        st.warning("⚠️ **Note:** Some payment pages may not load in iframe due to security restrictions. If you see an error, use the 'Open in New Tab' button below.")
        
        # Create iframe with error handling
        iframe_html = f"""
        <div style="border: 2px solid #e0e0e0; border-radius: 8px; padding: 10px; background-color: #f9f9f9;">
            <div id="iframeContainer">
                <iframe 
                    id="paymentIframe" 
                    src="{web_url}" 
                    width="100%" 
                    height="600" 
                    frameborder="0"
                    style="border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"
                    onerror="handleIframeError()"
                    onload="handleIframeLoad()">
                </iframe>
            </div>
            <div id="iframeError" style="display: none; padding: 20px; text-align: center; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; margin-top: 10px;">
                <h4 style="color: #721c24; margin: 0 0 10px 0;">❌ Iframe Loading Error</h4>
                <p style="color: #721c24; margin: 0 0 15px 0;">The payment page cannot be displayed in iframe due to security restrictions (X-Frame-Options).</p>
                <button onclick="openInNewTab()" style="background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-right: 10px;">🌐 Open in New Tab</button>
                <button onclick="retryIframe()" style="background: #6c757d; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">🔄 Retry</button>
            </div>
        </div>
        
        <script>
            let iframeLoadTimeout;
            
            // Handle iframe load success
            function handleIframeLoad() {{
                console.log('Iframe loaded successfully');
                clearTimeout(iframeLoadTimeout);
                document.getElementById('iframeError').style.display = 'none';
            }}
            
            // Handle iframe load error
            function handleIframeError() {{
                console.log('Iframe failed to load');
                showIframeError();
            }}
            
            // Show iframe error message
            function showIframeError() {{
                document.getElementById('iframeError').style.display = 'block';
                document.getElementById('iframeContainer').style.display = 'none';
            }}
            
            // Open payment URL in new tab
            function openInNewTab() {{
                window.open('{web_url}', '_blank');
            }}
            
            // Retry loading iframe
            function retryIframe() {{
                const iframe = document.getElementById('paymentIframe');
                const container = document.getElementById('iframeContainer');
                const error = document.getElementById('iframeError');
                
                container.style.display = 'block';
                error.style.display = 'none';
                
                // Reload iframe
                iframe.src = iframe.src;
                
                // Set timeout to show error if still fails
                iframeLoadTimeout = setTimeout(() => {{
                    showIframeError();
                }}, 5000);
            }}
            
            // Set timeout to detect iframe loading issues
            iframeLoadTimeout = setTimeout(() => {{
                // Check if iframe is still loading or has errors
                const iframe = document.getElementById('paymentIframe');
                try {{
                    // Try to access iframe content (will fail if X-Frame-Options blocks it)
                    if (iframe.contentDocument || iframe.contentWindow) {{
                        // Iframe loaded successfully
                        return;
                    }}
                }} catch (e) {{
                    // X-Frame-Options or other security error
                    console.log('Iframe blocked by security policy:', e);
                    showIframeError();
                }}
            }}, 3000);
            
            // Handle payment result messages from iframe
            const handlePaymentPostMessages = (event) => {{
                const {{ data }} = event;
                if (data && data.paymentResult) {{
                    const {{ respCode, respDesc, respData }} = data.paymentResult;
                    
                    // Display payment result
                    const resultDiv = document.getElementById('paymentResult');
                    if (resultDiv) {{
                        resultDiv.innerHTML = `
                            <div style="margin-top: 10px; padding: 10px; border-radius: 4px; background-color: ${{respCode === '2000' ? '#d4edda' : '#f8d7da'}}; border: 1px solid ${{respCode === '2000' ? '#c3e6cb' : '#f5c6cb'}};">
                                <strong>Payment Result:</strong><br/>
                                <strong>Code:</strong> ${{respCode}}<br/>
                                <strong>Description:</strong> ${{respDesc}}<br/>
                                ${{respData ? `<strong>Data:</strong> ${{respData}}<br/>` : ''}}
                            </div>
                        `;
                    }}
                    
                    // Handle specific response codes
                    if (respCode === '2000') {{
                        //alert("🎉 Payment completed successfully!");
                    }} else if (respCode === '1001') {{
                        // alert("🔄 Redirect to continue payment: " + respData);
                    }} else {{
                        // alert("⚠️ Payment result: " + respCode + " - " + respDesc);
                    }}
                }}
            }};
            
            // Subscribe to post messages
            window.addEventListener('message', handlePaymentPostMessages);
            
            // Function to trigger payment submission from parent page
            function triggerSubmitPayment() {{
                const iframe = document.getElementById('paymentIframe');
                if (iframe && iframe.contentWindow) {{
                    iframe.contentWindow.postMessage('submit_gcard', '*');
                }}
            }}
        </script>
        
        <div id="paymentResult"></div>
        """
        
        st.components.v1.html(iframe_html, height=700)
        
        # Add fallback buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🌐 Open in New Tab", key=f"{KEY_PREFIX}_open_new_tab"):
                st.markdown(f"[Click here to open payment page]({web_url})")
        with col2:
            if st.button("💳 Submit Payment", key=f"{KEY_PREFIX}_submit_payment"):
                st.info("💡 Use the 'Submit Payment' button inside the iframe above")
        with col3:
            if st.button("🔄 Refresh Dialog", key=f"{KEY_PREFIX}_refresh_dialog"):
                st.rerun()

    def render_response_section(self, generator_instance=None):
        """Render strict Request/Response views without mixing."""
        def _render_response_extras(parsed, raw):
            decoded_response = parsed
            if not isinstance(decoded_response, dict):
                if isinstance(raw, str):
                    try:
                        decoded_response = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        return
                else:
                    return

            jwt_payload = decoded_response.get("payload")
            if not jwt_payload:
                return

            st.subheader("🧩 Decoded JWT Response")
            decoded_payload = self.decode_jwt_payload(jwt_payload)
            st.json(decoded_payload)

            web_url = decoded_payload.get("webPaymentUrl")
            if web_url:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"[🌐 Open Payment URL]({web_url})")
                with col2:
                    if st.button("🖼️ Open Payment Dialog", key=f"{KEY_PREFIX}_open_dialog"):
                        self.show_payment_dialog(web_url)

            if st.button("📋 Copy Payment Token", key=f"{KEY_PREFIX}_copy_token"):
                payment_token = decoded_payload.get("paymentToken", "Token not found")
                success, error_msg = (
                    generator_instance.copy_to_clipboard(payment_token, "Payment Token")
                    if generator_instance
                    else (False, "Generator instance not available")
                )
                if success:
                    st.toast("Payment token copied to clipboard!", icon="✅")
                else:
                    st.error(f"❌ Failed to copy to clipboard: {error_msg}")
                    st.code(payment_token, language="text")

        render_request_response(
            "payment_token",
            request_title="### 📨 Request Trace",
            response_title="### 📬 Response Trace",
            on_response_tab=_render_response_extras,
        )

def render_payment_token():
    """Main function to render payment token page"""
    st.title("🔐 Payment Token Generator")
    apply_submit_button_style()

    # Initialize generator
    generator = PaymentTokenGenerator()
    generator.initialize_session_state()

    # Environment selection
    env, api_url = select_environment(key_suffix="payment_token", env_type="PaymentToken")

    # Layout
    col1_main, col2_main = st.columns([1, 1])

    with col1_main:
        st.subheader("⚙️ Configuration")

        # Basic fields
        basic_fields = generator.render_basic_fields()

        # Advanced options
        optional_fields = generator.render_advanced_options()

        # Secret key
        secret_key = st.text_input(
            "🔑 Merchant SHA Key",
            type="password",
            value=DEFAULT_SECRET_KEY,
            key=f"{KEY_PREFIX}_secret_key"
        )

        # Send request button
        if st.button("🚀 Generate Payment Token", key=f"{KEY_PREFIX}_send_request", type="primary"):
            # Update session state with new values
            st.session_state["invoice_no"] = generator.generate_invoice_no()
            st.session_state["idempotency_id"] = generator.generate_idempotency_id()

            # Prepare payload
            payload_data = {
                "merchantID": basic_fields['merchant_id'],
                "invoiceNo": st.session_state["invoice_no"],
                "description": f"Eddy - Payment {st.session_state['invoice_no']}",
                "amount": basic_fields['amount'],
                "currencyCode": basic_fields['currency_code'],
                "paymentChannel": basic_fields['payment_channel']
            }
            payload_data.update(optional_fields)

            # Send request (details are shown in unified request/response panel)
            result = generator.send_payment_request(
                payload_data,
                secret_key,
                api_url,
            )

            # Store results in session state
            st.session_state[PT_PAYLOAD_DATA_KEY] = payload_data
            st.session_state[PT_REQUEST_PAYLOAD_KEY] = result.get('jwt_token', '')
            st.session_state[PT_RESPONSE_PAYLOAD_KEY] = result.get('response', '')
            if result.get("trace") is not None:
                save_request_trace("payment_token", result["trace"])

            if result['success']:
                st.toast(
                    f"Payment token generated in {result.get('duration', 0):.2f}s "
                    f"(HTTP {result.get('status_code', 'N/A')})",
                    icon="✅",
                )

            else:
                st.toast(
                    f"Payment token generation failed after {result.get('duration', 0):.2f}s: "
                    f"{result.get('error', 'Unknown error')}",
                    icon="❌",
                )

    with col2_main:
        st.subheader("📊 Results")
        generator.render_response_section(generator)


if __name__ == "__main__":
    render_payment_token()