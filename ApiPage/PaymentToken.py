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
from ApiPage.common.response_view import (
    save_request_trace,
    render_request_response,
    notify_request_toast_failed,
)
from ApiPage.common.ui import apply_submit_button_style
from ApiPage.common.payload_utils import omit_empty_fields

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

    # ------------------------------------------------------------------
    # Request parameters (derived from PaymentToken_RequestParameter.docx)
    # Phan loai theo nhom de de tim. Chi field co gia tri moi vao request.
    # ------------------------------------------------------------------
    def _param_categories(self):
        sca_options = [
            "authentication_outage", "delegated_authentication", "low_value",
            "low_risk", "secure_corporate_payment", "trusted_merchant",
            "recurring_payment", "out_of_sca_scope", "transaction_risk_assessment",
            "other", "none",
        ]
        return {
            "\U0001F517 URLs": [
                ("frontendReturnUrl", "Frontend Return URL", "text",
                 {"default": "https://eddy.io.vn/callback/webhook/callback-frontend"}),
                ("backendReturnUrl", "Backend Return URL", "text",
                 {"default": "https://eddy.io.vn/callback/webhook/payment"}),
                ("schemeReturnUrl", "Scheme Return URL", "text", {}),
                ("appBundleID", "App Bundle ID", "text", {}),
                ("nonceStr", "Nonce Str", "text", {}),
            ],
            "\U0001F4B3 Payment": [
                ("locale", "Locale", "select", {"options": ["vi", "en"]}),
                ("request3DS", "Request 3DS", "select", {"options": ["Y", "F", "N"]}),
                ("paymentExpiry", "Payment Expiry (yyyy-MM-dd HH:mm:ss)", "text", {}),
                ("immediatePayment", "Immediate Payment", "bool", {}),
                ("iframeMode", "Iframe Mode", "bool", {}),
                ("paymentRouteID", "Payment Route ID", "text", {}),
                ("promotionCode", "Promotion Code", "text", {}),
                ("transactionInitiator", "Transaction Initiator", "select", {"options": ["C", "M"]}),
                ("transactionMode", "Transaction Mode", "text", {}),
                ("agentChannel", "Agent Channel (CSV)", "list_csv", {}),
                ("allowCustomerNote", "Allow Customer Note", "bool", {}),
            ],
            "\U0001F3AB Tokenization": [
                ("tokenize", "Tokenize", "bool", {}),
                ("tokenizeOnly", "Tokenize Only", "bool", {}),
                ("customerTokenOnly", "Customer Token Only", "bool", {}),
                ("customerToken", "Customer Token (CSV)", "list_csv", {}),
                ("storeCredentials", "Store Credentials", "select", {"options": ["F", "S", "N"]}),
                ("externalToken", "External Token", "text", {}),
            ],
            "\U0001F4B0 Installment": [
                ("interestType", "Interest Type", "select", {"options": ["A", "C", "M"]}),
                ("installmentPeriodFilter", "Installment Period Filter (CSV int)", "list_int_csv", {}),
                ("installmentBankFilter", "Installment Bank Filter (CSV)", "list_csv", {}),
                ("productCode", "Product Code", "text", {}),
            ],
            "\U0001F501 Recurring": [
                ("recurring", "Recurring", "bool", {}),
                ("invoicePrefix", "Invoice Prefix", "text", {}),
                ("recurringAmount", "Recurring Amount", "float", {}),
                ("allowAccumulate", "Allow Accumulate", "bool", {}),
                ("maxAccumulateAmount", "Max Accumulate Amount", "float", {}),
                ("recurringInterval", "Recurring Interval (days)", "int", {}),
                ("recurringCount", "Recurring Count", "int", {}),
                ("chargeNextDate", "Charge Next Date (ddMMyyyy)", "text", {}),
                ("chargeOnDate", "Charge On Date (ddMM)", "text", {}),
            ],
            "\U0001F510 3DS / Auth": [
                ("protocolVersion", "Protocol Version", "text", {"help": "Default: 2.1.0"}),
                ("eci", "ECI", "select",
                 {"options": ["00", "01", "02", "05", "06", "07", "80", "81", "82", "83"]}),
                ("cavv", "CAVV", "text", {}),
                ("dsTransactionId", "DS Transaction ID", "text", {}),
                ("scaExemptionIndicator", "SCA Exemption Indicator", "select", {"options": sca_options}),
                ("previousPaymentID", "Previous Payment ID", "text", {}),
                ("allow3DSUpgrade", "Allow 3DS Upgrade", "select", {"options": ["Y", "N"]}),
                ("requestReauthentication", "Request Reauthentication", "bool", {}),
            ],
            "\U0001F4B1 Forex": [
                ("fxProviderCode", "FX Provider Code", "text", {}),
                ("fxRateId", "FX Rate ID", "text", {}),
                ("originalAmount", "Original Amount", "float", {}),
            ],
            "\U0001F3EC Merchant": [
                ("externalSubMerchantID", "External Sub Merchant ID", "text", {}),
                ("childMerchantID", "Child Merchant ID", "text", {}),
                ("defaultSettlementCurrencyMerchantID", "Default Settlement Currency Merchant ID", "text", {}),
                ("settlementCurrencyMerchantID", "Settlement Currency Merchant ID", "text", {}),
                ("statementDescriptor", "Statement Descriptor", "text", {}),
                ("newRedisCacheOptimizationSwitchTag", "Redis Cache Optimization", "bool", {}),
                ("subMerchants", "Sub Merchants", "submerchants", {}),
            ],
            "\U0001F4DD User Defined": [
                ("userDefined1", "User Defined 1", "text", {}),
                ("userDefined2", "User Defined 2", "text", {}),
                ("userDefined3", "User Defined 3", "text", {}),
                ("userDefined4", "User Defined 4", "text", {}),
                ("userDefined5", "User Defined 5", "text", {}),
            ],
            "\U0001F9FE Client": [
                ("clientIP", "Client IP", "text", {}),
                ("clientAppID", "Client App ID", "text", {}),
                ("userAgent", "User Agent", "text", {}),
            ],
            "\U0001F4E6 Complex (JSON)": [
                ("paymentItems", "Payment Items", "json", {}),
                ("uiParams", "UI Params", "json", {}),
                ("customerAddress", "Customer Address", "json", {}),
                ("airlinePassengers", "Airline Passengers", "json", {}),
                ("3DSecure2Params", "3DSecure2 Params", "json", {}),
                ("loyaltyPoints", "Loyalty Points", "json", {}),
                ("browserDetails", "Browser Details", "json", {}),
                ("accountFunding", "Account Funding", "json", {}),
            ],
        }

    def _collect_param(self, optional_fields, name, label, kind, opts):
        """Render one input and add it to optional_fields only when it has a value."""
        wkey = f"{KEY_PREFIX}_opt_{name}"
        help_text = opts.get("help")

        if kind == "text":
            val = st.text_input(label, value=opts.get("default", ""), key=wkey, help=help_text)
            if val and val.strip():
                optional_fields[name] = val.strip()

        elif kind == "select":
            choices = [""] + list(opts["options"])
            val = st.selectbox(label, choices, key=wkey, help=help_text)
            if val:
                optional_fields[name] = val

        elif kind == "bool":
            val = st.selectbox(label, ["(not set)", "true", "false"], key=wkey, help=help_text)
            if val == "true":
                optional_fields[name] = True
            elif val == "false":
                optional_fields[name] = False

        elif kind == "int":
            val = st.text_input(label, value="", key=wkey, help=help_text)
            if val and val.strip():
                try:
                    optional_fields[name] = int(val.strip())
                except ValueError:
                    st.warning(f"\u26a0\ufe0f {label}: phai la so nguyen")

        elif kind == "float":
            val = st.text_input(label, value="", key=wkey, help=help_text)
            if val and val.strip():
                try:
                    optional_fields[name] = float(val.strip())
                except ValueError:
                    st.warning(f"\u26a0\ufe0f {label}: phai la so")

        elif kind == "list_csv":
            val = st.text_input(label, value="", key=wkey, help=help_text or "Ngan cach bang dau phay")
            items = [v.strip() for v in val.split(",") if v.strip()]
            if items:
                optional_fields[name] = items

        elif kind == "list_int_csv":
            val = st.text_input(label, value="", key=wkey, help=help_text or "Vi du: 3,6,12")
            items, ok = [], True
            for v in val.split(","):
                v = v.strip()
                if not v:
                    continue
                try:
                    items.append(int(v))
                except ValueError:
                    ok = False
            if not ok:
                st.warning(f"\u26a0\ufe0f {label}: phai la danh sach so nguyen")
            if items:
                optional_fields[name] = items

        elif kind == "json":
            raw = st.text_area(label, value="", key=wkey, height=120,
                               help=help_text or "Nhap JSON hop le")
            if raw and raw.strip():
                try:
                    parsed = json.loads(raw)
                    if parsed not in (None, "", [], {}):
                        optional_fields[name] = parsed
                except json.JSONDecodeError as exc:
                    st.warning(f"\u26a0\ufe0f {label}: JSON khong hop le ({exc})")

        elif kind == "submerchants":
            self._collect_submerchants(optional_fields, name, label, wkey)

    def _collect_submerchants(self, optional_fields, name, label, wkey):
        """Chon so luong sub merchant -> tu dong sinh bo input cho tung sub merchant."""
        st.markdown(f"**{label}**")
        count = st.number_input(
            "Number of Sub Merchants",
            min_value=0,
            max_value=20,
            value=0,
            step=1,
            key=f"{wkey}_count",
            help="Chon so luong de tu dong sinh form nhap cho tung sub merchant",
        )

        sub_list = []
        for i in range(int(count)):
            with st.expander(f"Sub Merchant #{i + 1}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    m_id = st.text_input("merchantID *", key=f"{wkey}_{i}_merchantID")
                    invoice_no = st.text_input("invoiceNo *", key=f"{wkey}_{i}_invoiceNo")
                    description = st.text_input("description *", key=f"{wkey}_{i}_description")
                with c2:
                    amount_raw = st.text_input("amount *", key=f"{wkey}_{i}_amount")
                    original_amount_raw = st.text_input("originalAmount", key=f"{wkey}_{i}_originalAmount")

                sub = {}
                if m_id.strip():
                    sub["merchantID"] = m_id.strip()
                if invoice_no.strip():
                    sub["invoiceNo"] = invoice_no.strip()
                if description.strip():
                    sub["description"] = description.strip()
                for fld, raw in (("amount", amount_raw), ("originalAmount", original_amount_raw)):
                    raw = (raw or "").strip()
                    if not raw:
                        continue
                    try:
                        sub[fld] = float(raw)
                    except ValueError:
                        st.warning(f"\u26a0\ufe0f Sub Merchant #{i + 1} - {fld}: phai la so")

                if sub:
                    sub_list.append(sub)

        if sub_list:
            optional_fields[name] = sub_list

    def render_advanced_options(self):
        """Render advanced/optional fields grouped by category (tabs)."""
        optional_fields = {}
        categories = self._param_categories()
        wide_kinds = {"json", "submerchants"}

        with st.expander("\u2795 Advanced Options", expanded=False):
            tab_labels = list(categories.keys())
            tabs = st.tabs(tab_labels)
            for tab, label in zip(tabs, tab_labels):
                with tab:
                    specs = categories[label]
                    normal_specs = [s for s in specs if s[2] not in wide_kinds]
                    wide_specs = [s for s in specs if s[2] in wide_kinds]

                    if normal_specs:
                        cols = st.columns(2)
                        for idx, (fname, flabel, kind, opts) in enumerate(normal_specs):
                            with cols[idx % 2]:
                                self._collect_param(optional_fields, fname, flabel, kind, opts)

                    for fname, flabel, kind, opts in wide_specs:
                        self._collect_param(optional_fields, fname, flabel, kind, opts)

        return optional_fields

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
            description = (basic_fields.get("description") or "").strip()
            payload_data = omit_empty_fields({
                "merchantID": basic_fields["merchant_id"],
                "invoiceNo": st.session_state["invoice_no"],
                "idempotencyID": basic_fields.get("idempotency_id"),
                "description": description or f"Eddy - Payment {st.session_state['invoice_no']}",
                "amount": basic_fields["amount"],
                "currencyCode": basic_fields["currency_code"],
                "paymentChannel": basic_fields["payment_channel"],
                **optional_fields,
            })

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
            elif not result.get("success"):
                notify_request_toast_failed(
                    "PaymentToken",
                    result.get("error", "Unknown error"),
                    result.get("duration"),
                )

    with col2_main:
        st.subheader("📊 Results")
        generator.render_response_section(generator)


if __name__ == "__main__":
    render_payment_token()