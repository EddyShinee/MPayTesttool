import streamlit as st
import json
import datetime
import uuid
import pyperclip
from typing import Dict, List, Any
import jwt
import base64

# Constants
KEY_PREFIX = str(uuid.uuid4())[:8]


class WebhookReceiver:
    def __init__(self):
        self.session_state = st.session_state

    def initialize_session_state(self):
        """Initialize session state for webhook data"""
        if "webhook_data" not in self.session_state:
            self.session_state["webhook_data"] = []
        if "webhook_filters" not in self.session_state:
            self.session_state["webhook_filters"] = {
                "show_all": True,
                "filter_by_type": "",
                "filter_by_status": "",
                "max_records": 100
            }

    @staticmethod
    def decode_jwt_payload(jwt_token):
        """Decode JWT payload"""
        try:
            payload_part = jwt_token.split('.')[1]
            padding = '=' * (-len(payload_part) % 4)
            decoded_bytes = base64.urlsafe_b64decode(payload_part + padding)
            return json.loads(decoded_bytes)
        except Exception as e:
            return {"error": str(e)}

    def parse_webhook_data(self, raw_data: str) -> Dict[str, Any]:
        """Parse incoming webhook data"""
        try:
            # Try to parse as JSON
            data = json.loads(raw_data)

            # Add metadata
            parsed_data = {
                "id": str(uuid.uuid4())[:8],
                "timestamp": datetime.datetime.now(),
                "raw_data": raw_data,
                "parsed_data": data,
                "type": self.detect_webhook_type(data),
                "status": self.extract_status(data)
            }

            # Try to decode JWT if present
            if isinstance(data, dict) and 'payload' in data:
                try:
                    decoded_payload = self.decode_jwt_payload(data['payload'])
                    parsed_data["decoded_payload"] = decoded_payload
                except:
                    parsed_data["decoded_payload"] = None

            return parsed_data

        except json.JSONDecodeError:
            # If not JSON, treat as plain text
            return {
                "id": str(uuid.uuid4())[:8],
                "timestamp": datetime.datetime.now(),
                "raw_data": raw_data,
                "parsed_data": {"message": raw_data, "type": "plain_text"},
                "type": "plain_text",
                "status": "unknown"
            }

    def detect_webhook_type(self, data: Dict[str, Any]) -> str:
        """Detect the type of webhook based on data structure"""
        if isinstance(data, dict):
            if "paymentToken" in data or "merchantID" in data:
                return "payment"
            elif "transactionID" in data:
                return "transaction"
            elif "inquiryType" in data:
                return "inquiry"
            elif "respCode" in data:
                return "response"
            elif "error" in data:
                return "error"
        return "unknown"

    def extract_status(self, data: Dict[str, Any]) -> str:
        """Extract status from webhook data"""
        if isinstance(data, dict):
            if "respCode" in data:
                return "success" if data["respCode"] == "0000" else "failed"
            elif "status" in data:
                return str(data["status"]).lower()
            elif "respDesc" in data:
                return "success" if "success" in str(data["respDesc"]).lower() else "failed"
        return "unknown"

    def add_webhook_data(self, raw_data: str):
        """Add new webhook data to session state"""
        parsed_data = self.parse_webhook_data(raw_data)

        # Add to beginning of list (newest first)
        self.session_state["webhook_data"].insert(0, parsed_data)

        # Keep only max_records
        max_records = self.session_state["webhook_filters"]["max_records"]
        if len(self.session_state["webhook_data"]) > max_records:
            self.session_state["webhook_data"] = self.session_state["webhook_data"][:max_records]

    def render_webhook_input(self):
        """Render webhook data input section"""
        st.subheader("📥 Webhook Data Input")

        # Input methods
        input_method = st.radio(
            "Choose input method:",
            ["Manual Input", "File Upload", "URL Simulation"],
            key=f"{KEY_PREFIX}_input_method",
            horizontal=True
        )

        if input_method == "Manual Input":
            webhook_data = st.text_area(
                "Enter webhook data (JSON or plain text):",
                height=150,
                placeholder='{"respCode": "0000", "paymentToken": "abc123", "merchantID": "704704000000000"}',
                key=f"{KEY_PREFIX}_manual_input"
            )

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("📨 Add Webhook Data", type="primary", key=f"{KEY_PREFIX}_add_manual"):
                    if webhook_data.strip():
                        self.add_webhook_data(webhook_data.strip())
                        st.success("✅ Webhook data added!")
                        st.rerun()
                    else:
                        st.error("❌ Please enter some data")

            with col2:
                if st.button("🧪 Add Sample Payment Webhook", key=f"{KEY_PREFIX}_add_sample"):
                    sample_data = {
                        "respCode": "0000",
                        "respDesc": "Success",
                        "paymentToken": "KSAops9ZwhosShSTq",
                        "merchantID": "704704000000000",
                        "invoiceNo": f"INV{datetime.datetime.now().strftime('%y%m%d%H%M%S')}",
                        "amount": 5000,
                        "currencyCode": "VND",
                        "transactionID": f"TXN{datetime.datetime.now().strftime('%y%m%d%H%M%S')}",
                        "paymentStatus": "completed",
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    self.add_webhook_data(json.dumps(sample_data, indent=2))
                    st.success("✅ Sample webhook data added!")
                    st.rerun()

        elif input_method == "File Upload":
            uploaded_file = st.file_uploader(
                "Upload webhook data file (JSON/TXT):",
                type=['json', 'txt'],
                key=f"{KEY_PREFIX}_file_upload"
            )

            if uploaded_file is not None:
                file_content = uploaded_file.read().decode('utf-8')
                st.code(file_content, language="json")

                if st.button("📁 Process Uploaded File", type="primary", key=f"{KEY_PREFIX}_process_file"):
                    self.add_webhook_data(file_content)
                    st.success("✅ File data processed!")
                    st.rerun()

        else:  # URL Simulation
            st.info("🔗 **URL Simulation Mode**")
            st.code(f"POST https://your-webhook-endpoint.com/webhook", language="bash")

            simulated_data = st.text_area(
                "Simulate webhook POST data:",
                value='{"respCode": "0000", "message": "Payment completed"}',
                height=100,
                key=f"{KEY_PREFIX}_url_sim"
            )

            if st.button("🌐 Simulate Webhook Request", type="primary", key=f"{KEY_PREFIX}_simulate"):
                self.add_webhook_data(simulated_data)
                st.success("✅ Webhook simulation added!")
                st.rerun()

    def render_filters(self):
        """Render filtering options"""
        st.subheader("🔍 Filters & Settings")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            show_all = st.checkbox(
                "Show All",
                value=self.session_state["webhook_filters"]["show_all"],
                key=f"{KEY_PREFIX}_show_all"
            )
            self.session_state["webhook_filters"]["show_all"] = show_all

        with col2:
            filter_by_type = st.selectbox(
                "Filter by Type:",
                ["", "payment", "transaction", "inquiry", "response", "error", "unknown"],
                key=f"{KEY_PREFIX}_filter_type"
            )
            self.session_state["webhook_filters"]["filter_by_type"] = filter_by_type

        with col3:
            filter_by_status = st.selectbox(
                "Filter by Status:",
                ["", "success", "failed", "unknown"],
                key=f"{KEY_PREFIX}_filter_status"
            )
            self.session_state["webhook_filters"]["filter_by_status"] = filter_by_status

        with col4:
            max_records = st.number_input(
                "Max Records:",
                min_value=10,
                max_value=500,
                value=self.session_state["webhook_filters"]["max_records"],
                key=f"{KEY_PREFIX}_max_records"
            )
            self.session_state["webhook_filters"]["max_records"] = max_records

    def filter_webhook_data(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply filters to webhook data"""
        filters = self.session_state["webhook_filters"]

        if filters["show_all"]:
            filtered_data = data_list
        else:
            filtered_data = data_list

            if filters["filter_by_type"]:
                filtered_data = [d for d in filtered_data if d["type"] == filters["filter_by_type"]]

            if filters["filter_by_status"]:
                filtered_data = [d for d in filtered_data if d["status"] == filters["filter_by_status"]]

        return filtered_data

    def render_webhook_data_display(self):
        """Render webhook data display section"""
        webhook_data = self.session_state.get("webhook_data", [])

        if not webhook_data:
            st.info("📭 No webhook data received yet. Add some data using the input section above.")
            return

        # Apply filters
        filtered_data = self.filter_webhook_data(webhook_data)

        st.subheader(f"📊 Webhook Data ({len(filtered_data)} records)")

        # Summary metrics
        if filtered_data:
            col1, col2, col3, col4 = st.columns(4)

            success_count = len([d for d in filtered_data if d["status"] == "success"])
            failed_count = len([d for d in filtered_data if d["status"] == "failed"])

            with col1:
                st.metric("📈 Total Records", len(filtered_data))
            with col2:
                st.metric("✅ Success", success_count)
            with col3:
                st.metric("❌ Failed", failed_count)
            with col4:
                st.metric("📅 Latest", filtered_data[0]["timestamp"].strftime("%H:%M:%S") if filtered_data else "N/A")

        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🗑️ Clear All Data", key=f"{KEY_PREFIX}_clear_all"):
                self.session_state["webhook_data"] = []
                st.success("✅ All data cleared!")
                st.rerun()

        with col2:
            if st.button("📋 Export Data", key=f"{KEY_PREFIX}_export"):
                export_data = json.dumps(filtered_data, indent=2, default=str)
                try:
                    pyperclip.copy(export_data)
                    st.success("✅ Data copied to clipboard!")
                except:
                    st.code(export_data)
                    st.info("📋 Copy the data above manually")

        with col3:
            if st.button("🔄 Refresh", key=f"{KEY_PREFIX}_refresh"):
                st.rerun()

        # Display webhook data
        for i, data in enumerate(filtered_data):
            with st.expander(
                    f"🔔 {data['type'].upper()} - {data['status'].upper()} - {data['timestamp'].strftime('%H:%M:%S')}",
                    expanded=i == 0  # Expand first (newest) record
            ):
                # Header info
                info_col1, info_col2, info_col3 = st.columns(3)
                with info_col1:
                    st.write(f"**ID:** `{data['id']}`")
                with info_col2:
                    st.write(f"**Type:** `{data['type']}`")
                with info_col3:
                    st.write(f"**Status:** `{data['status']}`")

                st.write(f"**Timestamp:** {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

                # Tabs for different views
                tab1, tab2, tab3 = st.tabs(["📋 Parsed Data", "🔍 Raw Data", "🧩 JWT Decoded"])

                with tab1:
                    st.json(data["parsed_data"])

                    # Copy button for parsed data
                    if st.button(f"📋 Copy Parsed Data", key=f"{KEY_PREFIX}_copy_parsed_{data['id']}"):
                        try:
                            pyperclip.copy(json.dumps(data["parsed_data"], indent=2))
                            st.success("✅ Parsed data copied!")
                        except:
                            st.warning("⚠️ Cannot copy to clipboard")

                with tab2:
                    st.code(data["raw_data"], language="json")

                    # Copy button for raw data
                    if st.button(f"📋 Copy Raw Data", key=f"{KEY_PREFIX}_copy_raw_{data['id']}"):
                        try:
                            pyperclip.copy(data["raw_data"])
                            st.success("✅ Raw data copied!")
                        except:
                            st.warning("⚠️ Cannot copy to clipboard")

                with tab3:
                    if data.get("decoded_payload"):
                        st.json(data["decoded_payload"])

                        # Copy button for decoded JWT
                        if st.button(f"📋 Copy JWT Decoded", key=f"{KEY_PREFIX}_copy_jwt_{data['id']}"):
                            try:
                                pyperclip.copy(json.dumps(data["decoded_payload"], indent=2))
                                st.success("✅ JWT decoded data copied!")
                            except:
                                st.warning("⚠️ Cannot copy to clipboard")
                    else:
                        st.info("💡 No JWT payload found in this webhook")

    def render_webhook_stats(self):
        """Render webhook statistics"""
        webhook_data = self.session_state.get("webhook_data", [])

        if not webhook_data:
            return

        st.subheader("📈 Webhook Statistics")

        # Type distribution
        type_counts = {}
        status_counts = {}

        for data in webhook_data:
            data_type = data["type"]
            data_status = data["status"]

            type_counts[data_type] = type_counts.get(data_type, 0) + 1
            status_counts[data_status] = status_counts.get(data_status, 0) + 1

        col1, col2 = st.columns(2)

        with col1:
            st.write("**📊 By Type:**")
            for webhook_type, count in type_counts.items():
                st.write(f"• {webhook_type}: {count}")

        with col2:
            st.write("**📊 By Status:**")
            for status, count in status_counts.items():
                st.write(f"• {status}: {count}")


def render_webhook_receiver():
    """Main function to render webhook receiver page"""
    st.title("📡 Webhook Receiver")
    st.markdown("Monitor and analyze incoming webhook data from payment APIs")

    # Initialize receiver
    receiver = WebhookReceiver()
    receiver.initialize_session_state()

    # Layout
    col1, col2 = st.columns([1, 1])

    with col1:
        # Input section
        receiver.render_webhook_input()

        # Filters
        receiver.render_filters()

        # Statistics
        receiver.render_webhook_stats()

    with col2:
        # Data display
        receiver.render_webhook_data_display()


if __name__ == "__main__":
    render_webhook_receiver()