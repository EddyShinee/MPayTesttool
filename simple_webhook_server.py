#!/usr/bin/env python3
"""
Simple Webhook Server - No Flask Required
Uses Python's built-in HTTP server
"""

import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import sys

# Global storage for webhooks
webhook_storage = []
MAX_STORAGE = 1000


class WebhookHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/':
            self.send_home_page()
        elif path == '/webhooks':
            self.send_all_webhooks()
        elif path == '/webhooks/latest':
            self.send_latest_webhook()
        elif path == '/webhooks/clear':
            self.clear_webhooks()
        else:
            self.handle_webhook('GET')

    def do_POST(self):
        """Handle POST requests"""
        self.handle_webhook('POST')

    def do_PUT(self):
        """Handle PUT requests"""
        self.handle_webhook('PUT')

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/webhooks/clear':
            self.clear_webhooks()
        else:
            self.handle_webhook('DELETE')

    def handle_webhook(self, method):
        """Process webhook requests"""
        try:
            # Get request info
            content_length = int(self.headers.get('Content-Length', 0))

            # Read body
            body_data = None
            if content_length > 0:
                body_raw = self.rfile.read(content_length)
                try:
                    body_data = json.loads(body_raw.decode('utf-8'))
                except json.JSONDecodeError:
                    body_data = body_raw.decode('utf-8')

            # Create webhook entry
            webhook_entry = {
                "id": len(webhook_storage) + 1,
                "timestamp": datetime.datetime.now().isoformat(),
                "method": method,
                "path": self.path,
                "headers": dict(self.headers),
                "body": body_data,
                "client_address": self.client_address[0]
            }

            # Store webhook
            webhook_storage.insert(0, webhook_entry)
            if len(webhook_storage) > MAX_STORAGE:
                webhook_storage.pop()

            # Print to console
            print(f"\n📥 Webhook received at {webhook_entry['timestamp']}")
            print(f"Method: {method}")
            print(f"Path: {self.path}")
            print(f"Body: {body_data}")
            print("-" * 60)

            # Send success response
            response_data = {
                "status": "success",
                "message": "Webhook received successfully",
                "timestamp": datetime.datetime.now().isoformat(),
                "received_data": body_data
            }

            self.send_json_response(200, response_data)

        except Exception as e:
            print(f"❌ Error processing webhook: {str(e)}")
            error_response = {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
            self.send_json_response(500, error_response)

    def send_home_page(self):
        """Send HTML home page"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🚀 Simple Webhook Server</title>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="10">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    margin: 40px; 
                    background: #f5f5f5;
                }}
                .container {{ 
                    background: white; 
                    padding: 30px; 
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    padding: 20px; 
                    border-radius: 10px; 
                    margin-bottom: 30px;
                }}
                .endpoint {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    margin: 15px 0; 
                    border-radius: 8px; 
                    border-left: 4px solid #007bff;
                }}
                .method {{ 
                    background: #007bff; 
                    color: white; 
                    padding: 4px 8px; 
                    border-radius: 4px; 
                    font-size: 12px;
                    font-weight: bold;
                }}
                .stats {{ 
                    background: #e8f5e8; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0;
                }}
                .example {{ 
                    background: #2d3748; 
                    color: #e2e8f0; 
                    padding: 20px; 
                    border-radius: 8px; 
                    overflow-x: auto;
                }}
                .recent {{ 
                    background: #fff3cd; 
                    padding: 15px; 
                    border-radius: 8px; 
                    margin: 15px 0;
                    max-height: 200px;
                    overflow-y: auto;
                }}
            </style>
        </head>
        <body>
            <div class="">
                <h2>📝 Recent Webhooks</h2>
                <div class="recent">
                    {self._get_recent_webhooks_html()}
                </div>
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def _get_recent_webhooks_html(self):
        """Get HTML for recent webhooks"""
        if not webhook_storage:
            return "<p>No webhooks received yet</p>"

        html = ""
        for webhook in webhook_storage[:5]:  # Show last 5
            body_preview = str(webhook.get('body', 'No body'))
            html += f"""
            <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 5px;">
                <strong>{webhook['method']}</strong> {webhook['path']} 
                <small>({webhook['timestamp']})</small><br>
                <code>{body_preview}</code>
            </div>
            """
        return html

    def send_all_webhooks(self):
        """Send all webhooks as JSON"""
        response_data = {
            "total": len(webhook_storage),
            "webhooks": webhook_storage
        }
        self.send_json_response(200, response_data)

    def send_latest_webhook(self):
        """Send latest webhook as JSON"""
        if webhook_storage:
            self.send_json_response(200, webhook_storage[0])
        else:
            self.send_json_response(404, {"message": "No webhooks received yet"})

    def clear_webhooks(self):
        """Clear all webhooks"""
        global webhook_storage
        webhook_storage = []
        self.send_json_response(200, {"message": "All webhooks cleared"})

    def send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode('utf-8'))

    def log_message(self, format, *args):
        """Suppress default log messages"""
        pass


def run_server(port=8000):
    """Run the webhook server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, WebhookHandler)

    print("🚀 Simple Webhook Server Starting...")
    print(f"📡 Server running on: http://localhost:{port}")
    print(f"🏠 Home page: http://localhost:{port}")
    print(f"🔗 Main webhook: http://localhost:{port}/webhook")
    print(f"💳 Payment webhook: http://localhost:{port}/webhook/payment")
    print(f"📊 All webhooks: http://localhost:{port}/webhooks")
    print("-" * 60)
    print("Press Ctrl+C to stop the server")
    print("-" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        httpd.server_close()


if __name__ == '__main__':
    # Get port from command line argument or use default
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number, using default 8000")

    run_server(port)