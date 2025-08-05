#!/usr/bin/env python3
"""
Beautiful Webhook Server - Modern UI Design
Uses Python's built-in HTTP server with enhanced styling
"""

import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import sys
import html

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
        """Send beautiful HTML home page"""
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>🚀 Webhook Monitor</title>
            <meta http-equiv="refresh" content="30">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}

                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #2d3748;
                }}

                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}

                .header {{
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 30px;
                    margin-bottom: 30px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                    text-align: center;
                }}

                .header h1 {{
                    font-size: 2.5em;
                    font-weight: 700;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 10px;
                }}

                .stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}

                .stat-card {{
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 15px;
                    padding: 25px;
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                    transition: transform 0.3s ease;
                }}

                .stat-card:hover {{
                    transform: translateY(-5px);
                }}

                .stat-number {{
                    font-size: 2.5em;
                    font-weight: 700;
                    color: #667eea;
                    margin-bottom: 5px;
                }}

                .stat-label {{
                    color: #718096;
                    font-weight: 500;
                    text-transform: uppercase;
                    font-size: 0.9em;
                    letter-spacing: 1px;
                }}

                .webhooks-container {{
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 30px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                }}

                .section-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 25px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #e2e8f0;
                }}

                .section-title {{
                    font-size: 1.8em;
                    font-weight: 600;
                    color: #2d3748;
                }}

                .action-buttons {{
                    display: flex;
                    gap: 10px;
                }}

                .btn {{
                    padding: 10px 20px;
                    border: none;
                    border-radius: 10px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                }}

                .btn-primary {{
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                }}

                .btn-danger {{
                    background: linear-gradient(135deg, #fc8181, #f56565);
                    color: white;
                }}

                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
                }}

                .webhook-item {{
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 15px;
                    padding: 20px;
                    margin-bottom: 20px;
                    transition: all 0.3s ease;
                }}

                .webhook-item:hover {{
                    box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
                    transform: translateY(-2px);
                }}

                .webhook-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }}

                .method-badge {{
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.8em;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}

                .method-POST {{
                    background: #48bb78;
                    color: white;
                }}

                .method-GET {{
                    background: #4299e1;
                    color: white;
                }}

                .method-PUT {{
                    background: #ed8936;
                    color: white;
                }}

                .method-DELETE {{
                    background: #f56565;
                    color: white;
                }}

                .webhook-path {{
                    font-family: 'Monaco', 'Menlo', monospace;
                    background: #2d3748;
                    color: #e2e8f0;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 0.9em;
                }}

                .webhook-time {{
                    color: #718096;
                    font-size: 0.9em;
                }}

                .webhook-body {{
                    background: #2d3748;
                    color: #e2e8f0;
                    padding: 15px;
                    border-radius: 10px;
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-size: 0.85em;
                    white-space: pre-wrap;
                    word-break: break-all;
                    max-height: 200px;
                    overflow-y: auto;
                    line-height: 1.4;
                }}

                .no-webhooks {{
                    text-align: center;
                    padding: 60px 20px;
                    color: #718096;
                }}

                .no-webhooks i {{
                    font-size: 4em;
                    margin-bottom: 20px;
                    opacity: 0.5;
                }}

                .endpoints {{
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 30px;
                    margin-bottom: 30px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                }}

                .endpoint-list {{
                    display: grid;
                    gap: 15px;
                }}

                .endpoint-item {{
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    padding: 15px;
                    background: #f8fafc;
                    border-radius: 10px;
                    border-left: 4px solid #667eea;
                }}

                .endpoint-url {{
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-weight: 600;
                    color: #2d3748;
                }}

                @media (max-width: 768px) {{
                    .container {{
                        padding: 15px;
                    }}

                    .header h1 {{
                        font-size: 2em;
                    }}

                    .stats {{
                        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                        gap: 15px;
                    }}

                    .webhook-header {{
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 10px;
                    }}

                    .action-buttons {{
                        flex-direction: column;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1><i class="fas fa-satellite-dish"></i> Webhook Monitor</h1>
                    <p>Real-time webhook monitoring and debugging tool</p>
                </div>

                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{len(webhook_storage)}</div>
                        <div class="stat-label">Total Webhooks</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{self._get_recent_count()}</div>
                        <div class="stat-label">Last Hour</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{len(set(w.get('client_address', 'unknown') for w in webhook_storage))}</div>
                        <div class="stat-label">Unique IPs</div>
                    </div>
                </div>

                <div class="endpoints">
                    <div class="section-header">
                        <h2 class="section-title"><i class="fas fa-link"></i> Available Endpoints</h2>
                    </div>
                    <div class="endpoint-list">
                        <div class="endpoint-item">
                            <i class="fas fa-globe"></i>
                            <span class="endpoint-url">http://localhost:8000/webhook</span>
                            <span>Main webhook endpoint</span>
                        </div>
                        <div class="endpoint-item">
                            <i class="fas fa-credit-card"></i>
                            <span class="endpoint-url">http://localhost:8000/webhook/payment</span>
                            <span>Payment webhook endpoint</span>
                        </div>
                        <div class="endpoint-item">
                            <i class="fas fa-database"></i>
                            <span class="endpoint-url">http://localhost:8000/webhooks</span>
                            <span>JSON API - All webhooks</span>
                        </div>
                    </div>
                </div>

                <div class="webhooks-container">
                    <div class="section-header">
                        <h2 class="section-title"><i class="fas fa-history"></i> Recent Webhooks</h2>
                        <div class="action-buttons">
                            <a href="/webhooks" class="btn btn-primary">
                                <i class="fas fa-download"></i> Export JSON
                            </a>
                            <a href="/webhooks/clear" class="btn btn-danger">
                                <i class="fas fa-trash"></i> Clear All
                            </a>
                        </div>
                    </div>

                    {self._get_beautiful_webhooks_html()}
                </div>
            </div>

            <script>
                // Auto-refresh every 30 seconds
                setTimeout(() => {{
                    location.reload();
                }}, 30000);

                // Add click to copy functionality
                document.querySelectorAll('.webhook-body').forEach(el => {{
                    el.addEventListener('click', () => {{
                        navigator.clipboard.writeText(el.textContent);
                        el.style.background = '#48bb78';
                        setTimeout(() => {{
                            el.style.background = '#2d3748';
                        }}, 500);
                    }});
                }});
            </script>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def _get_recent_count(self):
        """Get count of webhooks from last hour"""
        now = datetime.datetime.now()
        one_hour_ago = now - datetime.timedelta(hours=1)
        count = 0
        for webhook in webhook_storage:
            try:
                webhook_time = datetime.datetime.fromisoformat(webhook['timestamp'])
                if webhook_time > one_hour_ago:
                    count += 1
            except:
                continue
        return count

    def _get_beautiful_webhooks_html(self):
        """Get beautiful HTML for webhooks"""
        if not webhook_storage:
            return """
            <div class="no-webhooks">
                <i class="fas fa-inbox"></i>
                <h3>No webhooks received yet</h3>
                <p>Send a POST request to any endpoint to see webhooks appear here</p>
            </div>
            """

        html = ""
        for webhook in webhook_storage[:20]:  # Show last 20
            method = webhook.get('method', 'UNKNOWN')
            path = html.escape(webhook.get('path', ''))
            timestamp = webhook.get('timestamp', '')
            body = webhook.get('body', '')
            client_ip = webhook.get('client_address', 'unknown')

            # Format timestamp
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime('%H:%M:%S - %d/%m/%Y')
            except:
                formatted_time = timestamp

            # Format body for display
            if isinstance(body, dict):
                body_display = json.dumps(body, indent=2, ensure_ascii=False)
            elif isinstance(body, str) and body:
                try:
                    # Try to parse as JSON for pretty printing
                    parsed = json.loads(body)
                    body_display = json.dumps(parsed, indent=2, ensure_ascii=False)
                except:
                    body_display = body
            else:
                body_display = str(body) if body else "No body data"

            html += f"""
            <div class="webhook-item">
                <div class="webhook-header">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span class="method-badge method-{method}">{method}</span>
                        <span class="webhook-path">{path}</span>
                    </div>
                    <div style="text-align: right;">
                        <div class="webhook-time">
                            <i class="fas fa-clock"></i> {formatted_time}
                        </div>
                        <div class="webhook-time">
                            <i class="fas fa-map-marker-alt"></i> {client_ip}
                        </div>
                    </div>
                </div>
                <div class="webhook-body" title="Click to copy">{html.escape(body_display)}</div>
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
        # Redirect back to home page after clearing
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

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

    print("🚀 Beautiful Webhook Server Starting...")
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