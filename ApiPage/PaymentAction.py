import streamlit as st
import os
import json
import requests
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jwcrypto import jwk, jws, jwe
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives.serialization import pkcs12
import xml.dom.minidom
from utils.EnvSelector import select_environment


def render_payment_action():
    st.title("🔐 Payment Action")

    # --- Chọn môi trường ---
    env, api_url = select_environment(key_suffix="payment_action", env_type="PaymentAction")

    # --- Download Config File ---
    st.markdown("### 📥 Download Configuration")
    config_file_path = "KeyPaymentAction/Config_To_Client_Portal.txt"
    
    if os.path.exists(config_file_path):
        with open(config_file_path, 'rb') as file:
            config_content = file.read()
        
        st.download_button(
            label="📄 Download Config_To_Client_Portal.txt",
            data=config_content,
            file_name="Config_To_Client_Portal.txt",
            mime="text/plain",
            help="Download configuration file for client portal"
        )
    else:
        st.info("ℹ️ Config file not available for download")

    st.divider()

    # Pretty print XML helper
    def pretty_print_xml(xml_str: str) -> str:
        try:
            parsed = xml.dom.minidom.parseString(xml_str)
            return parsed.toprettyxml(indent="  ")
        except Exception as e:
            st.error(f"Error formatting XML: {e}")
            return xml_str

    # Enhanced file upload with error handling
    def safe_file_upload(label, file_types, key=None):
        try:
            uploaded_file = st.file_uploader(label, type=file_types, key=key)
            if uploaded_file is not None:
                # Validate file size
                if uploaded_file.size > 50 * 1024 * 1024:  # 50MB limit
                    st.error("❌ File size too large. Please upload a file smaller than 50MB.")
                    return None

                # Validate file extension
                if not uploaded_file.name.lower().endswith(tuple(f".{ext}" for ext in file_types)):
                    st.error(f"❌ Invalid file type. Please upload: {', '.join(file_types)}")
                    return None

                return uploaded_file
            return None
        except Exception as e:
            st.error(f"❌ File upload error: {e}")
            return None

    # Auto-load default keys
    default_private_key_path = "KeyPaymentAction/123.pfx"
    default_public_cert_path = "KeyPaymentAction/abc.cer"
    
    st.markdown("### 🔑 Key Management")
    
    # Check for default keys
    default_private_exists = os.path.exists(default_private_key_path)
    default_public_exists = os.path.exists(default_public_cert_path)
    
    # Show summary status
    if default_private_exists and default_public_exists:
        st.success("✅ Default keys available")
    elif default_private_exists or default_public_exists:
        st.warning("⚠️ Some default keys missing")
    else:
        st.info("ℹ️ No default keys found - upload required")

    # Option to use custom keys
    use_custom_keys = st.checkbox("🔧 Use custom keys (override defaults)", value=False)
    
    # File uploads (only show if using custom keys or defaults don't exist)
    private_key_file = None
    public_cert_file = None
    
    if use_custom_keys or not default_private_exists:
        private_key_file = safe_file_upload(
            "🔐 Upload Private Key (.pfx, .p12, .pem, .key)" + 
            (" (Optional - will use default if not provided)" if default_private_exists else " (Required)"),
            ["pfx", "p12", "pem", "key"],
            key="private_key"
        )
    
    if use_custom_keys or not default_public_exists:
        public_cert_file = safe_file_upload(
            "📄 Upload Public Certificate (.cer, .crt)" + 
            (" (Optional - will use default if not provided)" if default_public_exists else " (Required)"),
            ["cer", "crt"],
            key="public_cert"
        )

    # Load previously saved password if available
    config_path = "config.json"
    saved_password = ""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                saved_config = json.load(f)
            saved_password = saved_config.get("last_password", "")
        except Exception:
            pass  # Load silently

    private_key_password = st.text_input(
        "🔑 Private Key Password",
        type="password",
        value=saved_password,
        help="Password for the private key file"
    )

    # Process keys
    private_jwk = None
    public_jwk = None
    
    # Determine which keys to use
    use_default_private = (not use_custom_keys and default_private_exists) or (use_custom_keys and private_key_file is None and default_private_exists)
    use_default_public = (not use_custom_keys and default_public_exists) or (use_custom_keys and public_cert_file is None and default_public_exists)
    
    try:
        # Process private key
        if use_default_private:
            with open(default_private_key_path, 'rb') as f:
                private_key_data = f.read()
                key_filename = "123.pfx"
        elif private_key_file is not None:
            private_key_data = private_key_file.getvalue()
            key_filename = private_key_file.name
        else:
            private_key_data = None
            key_filename = None

        if private_key_data is not None:
            if key_filename.lower().endswith((".pfx", ".p12")):
                private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                    private_key_data,
                    password=private_key_password.encode() if private_key_password else None,
                    backend=default_backend()
                )
            elif key_filename.lower().endswith((".pem", ".key")):
                private_key = serialization.load_pem_private_key(
                    private_key_data,
                    password=private_key_password.encode() if private_key_password else None,
                    backend=default_backend()
                )
                certificate = None
            else:
                raise ValueError("Unsupported private key file type.")

            # Convert private key to PEM format for jwcrypto JWK import
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            private_jwk = jwk.JWK.from_pem(private_key_pem)

        # Process public certificate
        if use_default_public:
            with open(default_public_cert_path, 'rb') as f:
                public_cert_data = f.read()
        elif public_cert_file is not None:
            public_cert_data = public_cert_file.getvalue()
        else:
            public_cert_data = None

        if public_cert_data is not None:
            try:
                public_jwk = jwk.JWK.from_pem(public_cert_data)
            except Exception:
                from cryptography import x509
                cert = x509.load_der_x509_certificate(public_cert_data, default_backend())
                pem_cert = cert.public_bytes(serialization.Encoding.PEM)
                public_jwk = jwk.JWK.from_pem(pem_cert)

        if private_jwk is not None and public_jwk is not None:
            st.success("✅ Keys loaded successfully!")
            
            # Save current config silently
            try:
                config_to_save = {
                    "last_password": private_key_password,
                    "last_private_key_filename": key_filename if private_key_file else default_private_key_path,
                    "last_cert_filename": public_cert_file.name if public_cert_file else default_public_cert_path,
                    "use_custom_keys": use_custom_keys
                }
                with open(config_path, "w") as f:
                    json.dump(config_to_save, f)
            except Exception:
                pass  # Save silently

    except Exception as e:
        st.error(f"❌ Error processing key files: {e}")
        st.info("💡 Verify password and file integrity")
        private_jwk = None
        public_jwk = None

    st.divider()

    # Form inputs
    st.markdown("### 📝 Payment Request Parameters")
    col1, col2 = st.columns(2)

    with col1:
        version = st.text_input("Version", value="3.8")
        mid = st.text_input("Merchant ID", value="704704000000211")
        invoice_no = st.text_input("Invoice No", value="01a00a81-364c-48f4-8278-3aef4ec61399")
        amount = st.text_input("Action Amount", value="5000")
        processType = st.selectbox("Process Type", ["I", "R", "V"])
        timestamp = st.text_input("Timestamp", value=datetime.now().strftime('%y%m%d%H%M%S'))
        recurring_id = st.text_input("Recurring Unique ID", value="")

        if processType in ["R", "V"]:
            notifyURL = st.text_input("Notify URL", value="https://eddy.io.vn/callback/webhooks?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiRWRkeSIsImFkbWluIjp0cnVlLCJwaG9uZSI6OTA5NzAwOTgwLCJyYW5kb21fbnVtYmVyIjoxOTkzLCJleHAiOjE3NTU5MzA5NTksImlhdCI6MTc1NTg0NDU1OX0.UXPAQxfEWK1W3RdF9L5yGx023ZYNunnn1uGuZDjZjwo")
        else:
            notifyURL = ""

        st.divider()

        # Only show send button if keys are loaded
        if private_jwk is not None and public_jwk is not None:
            send_request = st.button("🔁 Send Request to 2C2P", type="primary")
        else:
            st.warning("⚠️ Please ensure both private key and public certificate are loaded.")
            send_request = False

    with col2:
        if not send_request:
            st.markdown("### 📊 Response")
            st.info("Response will appear here after sending request")

        if send_request:
            import time
            with st.spinner("⏳ Sending request to 2C2P..."):
                start_time = time.time()

                try:
                    # Create XML payload
                    root = ET.Element("PaymentProcessRequest")
                    ET.SubElement(root, "version").text = version
                    ET.SubElement(root, "timeStamp").text = timestamp
                    ET.SubElement(root, "merchantID").text = mid
                    ET.SubElement(root, "invoiceNo").text = invoice_no
                    ET.SubElement(root, "actionAmount").text = amount
                    ET.SubElement(root, "recurringUniqueID").text = recurring_id
                    ET.SubElement(root, "processType").text = processType
                    ET.SubElement(root, "notifyURL").text = notifyURL
                    xml_payload = ET.tostring(root, encoding="unicode")

                    st.markdown("### 📄 XML Payload:")
                    st.code(xml_payload, language="xml")

                    # Create JWE token
                    jwe_token_obj = jwe.JWE(xml_payload.encode('utf-8'),
                                            protected={"alg": "RSA-OAEP", "enc": "A256GCM", "kid": "1"})
                    jwe_token_obj.add_recipient(public_jwk)
                    jwe_token = jwe_token_obj.serialize(compact=True)

                    st.markdown("### 🔐 JWE (Encrypted XML):")
                    st.code(jwe_token, language="text")

                    # Create JWS token
                    jws_token_obj = jws.JWS(jwe_token.encode('utf-8'))
                    jws_token_obj.add_signature(private_jwk, protected={"alg": "PS256", "kid": "1"})
                    final_token = jws_token_obj.serialize(compact=True)

                    st.markdown("### 🖋️ Final JWS over JWE:")
                    st.code(final_token)

                    # Send request
                    headers = {'content-type': 'text/plain'}
                    response = requests.post(api_url, data=final_token, headers=headers, timeout=60)

                    end_time = time.time()
                    duration = round(end_time - start_time, 2)

                    st.markdown("### 📤 Sent JWS Token:")
                    st.code(final_token)

                    if response.status_code == 200:
                        st.success(f"✅ Request successful! ⏱ Took {duration} seconds.")
                    else:
                        st.warning(f"⚠️ Request failed. Status code: {response.status_code} ⏱ Took {duration} seconds.")

                    st.markdown("### 📦 Raw Encrypted Response:")
                    st.code(response.text)

                    # Decrypt response
                    def is_jwe_compact_format(text):
                        return len(text.split(".")) == 5

                    def is_jws_compact_format(text):
                        return len(text.split(".")) == 3

                    xml_result = None
                    try:
                        if is_jws_compact_format(response.text):
                            incoming_jws = jws.JWS()
                            incoming_jws.deserialize(response.text.strip())
                            incoming_jws.verify(public_jwk)
                            jwe_payload = incoming_jws.payload.decode("utf-8")

                            incoming_jwe = jwe.JWE()
                            incoming_jwe.deserialize(jwe_payload.strip())
                            incoming_jwe.decrypt(private_jwk)
                            xml_result = incoming_jwe.payload.decode("utf-8")

                        elif is_jwe_compact_format(response.text):
                            incoming_jwe = jwe.JWE()
                            incoming_jwe.deserialize(response.text.strip())
                            incoming_jwe.decrypt(private_jwk)
                            xml_result = incoming_jwe.payload.decode("utf-8")

                        else:
                            raise ValueError("Response is not in compact JWS or JWE format.")

                    except Exception as e:
                        import traceback
                        st.error(f"❌ Error decoding response:\n{traceback.format_exc()}")
                        st.markdown("### ❌ Raw Response:")
                        st.code(response.text)

                    if xml_result:
                        st.markdown("### ✅ Final Decrypted 2C2P Response:")
                        try:
                            formatted_xml = ET.tostring(ET.fromstring(xml_result), encoding='unicode', method='xml')
                            pretty = pretty_print_xml(formatted_xml)
                            st.code(pretty, language="xml")
                        except Exception:
                            pretty = pretty_print_xml(xml_result)
                            st.code(pretty, language="xml")

                except Exception as e:
                    st.error(f"❌ Error during request processing: {e}")
                    import traceback
                    st.code(traceback.format_exc())


if __name__ == "__main__":
    render_payment_action()