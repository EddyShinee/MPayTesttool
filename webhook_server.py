#!/usr/bin/env python3
"""
JWT-Secured Webhook Server - Enhanced with JWT Authentication
Uses Python's built-in HTTP server with JWT token verification
"""

import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import sys
import html as html_module
import base64
import jwt  # pip install PyJWT
import traceback

# JWT Configuration
JWT_SECRET = "85C237EC4F47FBB2C56B988924786"
EXPECTED_PAYLOAD = {
    "name": "Eddy",
    "admin": True,
    "phone": "909700980",
    "random_number": 1993
}

# Global storage for webhooks and security events
webhook_storage = []
security_events = []
MAX_STORAGE = 1000
MAX_SECURITY_EVENTS = 500


class JWTSecuredWebhookHandler(BaseHTTPRequestHandler):

    def _verify_jwt_token(self, token_param):
        """Verify JWT token and return validation result"""
        if not token_param:
            return False, "Missing token parameter"
        
        try:
            # Decode JWT token
            decoded_payload = jwt.decode(token_param, JWT_SECRET, algorithms=["HS256"])
            
            # Compare with expected payload (remove exp and iat for comparison)
            payload_to_check = {k: v for k, v in decoded_payload.items() if k not in ['exp', 'iat']}
            
            if payload_to_check == EXPECTED_PAYLOAD:
                return True, "Token valid"
            else:
                return False, f"Invalid payload: {payload_to_check}"
                
        except jwt.ExpiredSignatureError:
            return False, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, f"Invalid token: {str(e)}"
        except Exception as e:
            return False, f"Token verification error: {str(e)}"

    def _log_security_event(self, event_type, details, client_ip):
        """Log security events for monitoring"""
        security_event = {
            "id": len(security_events) + 1,
            "timestamp": datetime.datetime.now().isoformat(),
            "type": event_type,
            "client_ip": client_ip,
            "details": details,
            "path": self.path,
            "user_agent": self.headers.get('User-Agent', 'Unknown')
        }
        
        security_events.insert(0, security_event)
        if len(security_events) > MAX_SECURITY_EVENTS:
            security_events.pop()
        
        # Print to console for immediate monitoring
        print(f"\n🚨 SECURITY EVENT: {event_type}")
        print(f"IP: {client_ip}")
        print(f"Path: {self.path}")
        print(f"Details: {details}")
        print(f"Time: {security_event['timestamp']}")
        print("-" * 60)

    def _authenticate_request(self):
        """Authenticate request using JWT token"""
        client_ip = self.client_address[0]
        
        # Parse query parameters to get token
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        token_param = query_params.get('token', [None])[0]
        
        # Verify JWT token
        is_valid, message = self._verify_jwt_token(token_param)
        
        if not is_valid:
            # Log security event
            self._log_security_event(
                "AUTHENTICATION_FAILED",
                {
                    "reason": message,
                    "token_provided": bool(token_param),
                    "token_preview": token_param[:20] + "..." if token_param and len(token_param) > 20 else token_param
                },
                client_ip
            )
            return False, message
        
        # Log successful authentication
        self._log_security_event(
            "AUTHENTICATION_SUCCESS",
            {"user": EXPECTED_PAYLOAD["name"]},
            client_ip
        )
        
        return True, "Authenticated"

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # Public endpoints (no auth required)
        if path == '/':
            self.send_home_page()
            return
        elif path == '/security-events':
            self.send_security_events()
            return
            
        # Protected endpoints (require JWT auth)
        is_authenticated, auth_message = self._authenticate_request()
        if not is_authenticated:
            self.send_auth_error(auth_message)
            return

        if path == '/webhooks':
            self.send_all_webhooks()
        elif path == '/webhooks/latest':
            self.send_latest_webhook()
        elif path == '/webhooks/clear':
            self.clear_webhooks()
        elif path == '/webhook/callback-frontend':
            self.handle_callback_frontend('GET')
        elif path == '/webhook/encrypt-card':
            self.handle_encrypt_card('GET')
        else:
            self.handle_webhook('GET')

    def do_POST(self):
        """Handle POST requests"""
        # All POST endpoints require authentication
        is_authenticated, auth_message = self._authenticate_request()
        if not is_authenticated:
            self.send_auth_error(auth_message)
            return
            
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/webhook/encrypt-card':
            self.handle_encrypt_card('POST')
        elif parsed_path.path == '/webhook/callback-frontend':
            self.handle_callback_frontend('POST')
        else:
            self.handle_webhook('POST')

    def do_PUT(self):
        """Handle PUT requests"""
        is_authenticated, auth_message = self._authenticate_request()
        if not is_authenticated:
            self.send_auth_error(auth_message)
            return
        self.handle_webhook('PUT')

    def do_DELETE(self):
        """Handle DELETE requests"""
        is_authenticated, auth_message = self._authenticate_request()
        if not is_authenticated:
            self.send_auth_error(auth_message)
            return
            
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/webhooks/clear':
            self.clear_webhooks()
        else:
            self.handle_webhook('DELETE')

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization')
        self.send_header('Access-Control-Max-Age', '3600')
        self.end_headers()
        self.wfile.write(b'')

    def send_auth_error(self, message):
        """Send authentication error response"""
        error_response = {
            "status": "error",
            "code": "AUTH_FAILED",
            "message": message,
            "timestamp": datetime.datetime.now().isoformat(),
            "help": "Please provide a valid JWT token in the 'token' query parameter"
        }
        
        self.send_response(401)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(error_response, indent=2).encode('utf-8'))

    def handle_webhook(self, method):
        """Process webhook requests (authenticated)"""
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
                "client_address": self.client_address[0],
                "authenticated": True,
                "user": EXPECTED_PAYLOAD["name"]
            }

            # Store webhook
            webhook_storage.insert(0, webhook_entry)
            if len(webhook_storage) > MAX_STORAGE:
                webhook_storage.pop()

            # Print to console
            print(f"\n📥 Authenticated Webhook received at {webhook_entry['timestamp']}")
            print(f"User: {EXPECTED_PAYLOAD['name']}")
            print(f"Method: {method}")
            print(f"Path: {self.path}")
            print(f"IP: {self.client_address[0]}")
            print(f"Body: {body_data}")
            print("-" * 60)

            # Send success response
            response_data = {
                "status": "success",
                "message": "Webhook received successfully",
                "timestamp": datetime.datetime.now().isoformat(),
                "webhook_id": webhook_entry["id"],
                "user": EXPECTED_PAYLOAD["name"]
            }

            self.send_json_response(200, response_data)

        except Exception as e:
            print(f"❌ Error processing webhook: {str(e)}")
            traceback.print_exc()
            error_response = {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
            self.send_json_response(500, error_response)

    def handle_callback_frontend(self, method):
        """Handle callback-frontend GET/POST request (authenticated)"""
        try:
            payment_response = None
            
            if method == 'GET':
                # Parse query parameters for GET request
                parsed_path = urlparse(self.path)
                query_params = parse_qs(parsed_path.query)
                payment_response = query_params.get('paymentResponse', [None])[0]
                
                if not payment_response:
                    self.send_error_html("Missing paymentResponse parameter in query string")
                    return
                    
            elif method == 'POST':
                # Get request body for POST request
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    self.send_error_html("Missing request body")
                    return
                    
                body_raw = self.rfile.read(content_length)
                body_str = body_raw.decode('utf-8')
                
                # Try to parse as form data first
                if 'application/x-www-form-urlencoded' in self.headers.get('Content-Type', ''):
                    form_data = parse_qs(body_str)
                    payment_response = form_data.get('paymentResponse', [None])[0]
                else:
                    # Try to parse as JSON
                    try:
                        json_data = json.loads(body_str)
                        payment_response = json_data.get('paymentResponse')
                    except json.JSONDecodeError:
                        # If not JSON, treat the entire body as paymentResponse
                        payment_response = body_str

                if not payment_response:
                    self.send_error_html("Missing paymentResponse parameter in request body")
                    return

            # Decode base64
            try:
                decoded_bytes = base64.b64decode(payment_response)
                decoded_json = json.loads(decoded_bytes.decode('utf-8'))
            except Exception as e:
                self.send_error_html(f"Error decoding paymentResponse: {str(e)}")
                return

            # Store in webhook storage
            webhook_entry = {
                "id": len(webhook_storage) + 1,
                "timestamp": datetime.datetime.now().isoformat(),
                "method": method,
                "path": self.path,
                "headers": dict(self.headers),
                "body": decoded_json,
                "raw_payment_response": payment_response,
                "client_address": self.client_address[0],
                "type": "callback-frontend",
                "authenticated": True,
                "user": EXPECTED_PAYLOAD["name"]
            }
            webhook_storage.insert(0, webhook_entry)
            if len(webhook_storage) > MAX_STORAGE:
                webhook_storage.pop()

            # Print to console
            print(f"\n🔄 Authenticated Callback-frontend webhook received at {webhook_entry['timestamp']}")
            print(f"User: {EXPECTED_PAYLOAD['name']}")
            print(f"Method: {method}")
            print(f"IP: {self.client_address[0]}")
            print(f"Decoded Data: {decoded_json}")
            print("-" * 60)

            # Send success HTML
            self.send_callback_success_html(decoded_json)

        except Exception as e:
            print(f"❌ Error processing callback-frontend: {str(e)}")
            self.send_error_html(f"Internal server error: {str(e)}")

    def handle_encrypt_card(self, method):
        """Handle encrypt-card requests (authenticated)"""
        try:
            # Get request body if POST
            body_data = None
            if method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body_raw = self.rfile.read(content_length)
                    try:
                        body_data = json.loads(body_raw.decode('utf-8'))
                    except json.JSONDecodeError:
                        body_data = body_raw.decode('utf-8')

            # Store in webhook storage
            webhook_entry = {
                "id": len(webhook_storage) + 1,
                "timestamp": datetime.datetime.now().isoformat(),
                "method": method,
                "path": self.path,
                "headers": dict(self.headers),
                "body": body_data,
                "client_address": self.client_address[0],
                "type": "encrypt-card",
                "authenticated": True,
                "user": EXPECTED_PAYLOAD["name"]
            }
            webhook_storage.insert(0, webhook_entry)
            if len(webhook_storage) > MAX_STORAGE:
                webhook_storage.pop()

            # Print to console
            print(f"\n🔐 Authenticated Encrypt-card webhook received at {webhook_entry['timestamp']}")
            print(f"User: {EXPECTED_PAYLOAD['name']}")
            print(f"Method: {method}")
            print(f"IP: {self.client_address[0]}")
            print(f"Body: {body_data}")
            print("-" * 60)

            # Send success HTML
            self.send_encrypt_success_html(body_data)

        except Exception as e:
            print(f"❌ Error processing encrypt-card: {str(e)}")
            self.send_error_html(f"Internal server error: {str(e)}")

    def send_home_page(self):
        """Send beautiful HTML home page with security information"""
        # Get recent security events stats
        failed_auths = len([e for e in security_events if e['type'] == 'AUTHENTICATION_FAILED'])
        successful_auths = len([e for e in security_events if e['type'] == 'AUTHENTICATION_SUCCESS'])
        
        # Get unique IPs that failed authentication
        failed_ips = set([e['client_ip'] for e in security_events if e['type'] == 'AUTHENTICATION_FAILED'])
        
        endpoints_html = f"""
        <div class="endpoint-item">
            <i class="fas fa-globe"></i>
            <span class="endpoint-url">https://eddy.io.vn/callback/webhook?token=YOUR_JWT_TOKEN</span>
            <span>Main webhook endpoint (JWT Required)</span>
        </div>
        <div class="endpoint-item">
            <i class="fas fa-credit-card"></i>
            <span class="endpoint-url">https://eddy.io.vn/callback/webhook/payment?token=YOUR_JWT_TOKEN</span>
            <span>Payment webhook endpoint (JWT Required)</span>
        </div>
        <div class="endpoint-item">
            <i class="fas fa-arrow-left"></i>
            <span class="endpoint-url">https://eddy.io.vn/callback/webhook/callback-frontend?token=YOUR_JWT_TOKEN</span>
            <span>Frontend callback (JWT Required)</span>
        </div>
        <div class="endpoint-item">
            <i class="fas fa-shield-alt"></i>
            <span class="endpoint-url">https://eddy.io.vn/callback/webhook/encrypt-card?token=YOUR_JWT_TOKEN</span>
            <span>Card encryption webhook (JWT Required)</span>
        </div>
        <div class="endpoint-item">
            <i class="fas fa-database"></i>
            <span class="endpoint-url">https://eddy.io.vn/callback/webhooks?token=YOUR_JWT_TOKEN</span>
            <span>JSON API - All webhooks (JWT Required)</span>
        </div>
        """

        # Recent security events HTML
        security_events_html = self._get_security_events_html()

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>🔐 JWT-Secured Webhook Monitor</title>
            <meta http-equiv="refresh" content="30">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #2d3748; font-size: 13px; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                .header {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 20px; padding: 30px; margin-bottom: 30px; text-align: center; }}
                .header h1 {{ font-size: 2em; font-weight: 700; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; }}
                .security-badge {{ background: linear-gradient(135deg, #48bb78, #38a169); color: white; padding: 8px 16px; border-radius: 20px; font-size: 0.8em; font-weight: 600; display: inline-block; margin: 5px; }}
                .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: rgba(255, 255, 255, 0.95); border-radius: 15px; padding: 20px; text-align: center; }}
                .stat-number {{ font-size: 1.8em; font-weight: 700; color: #667eea; margin-bottom: 5px; }}
                .stat-number.danger {{ color: #e53e3e; }}
                .stat-number.success {{ color: #38a169; }}
                .stat-label {{ color: #718096; font-weight: 500; text-transform: uppercase; font-size: 0.7em; }}
                .endpoints {{ background: rgba(255, 255, 255, 0.95); border-radius: 20px; padding: 30px; margin-bottom: 30px; }}
                .section-title {{ font-size: 1.4em; font-weight: 600; color: #2d3748; margin-bottom: 25px; }}
                .endpoint-list {{ display: grid; gap: 15px; }}
                .endpoint-item {{ display: flex; align-items: center; gap: 15px; padding: 15px; background: #f8fafc; border-radius: 10px; border-left: 4px solid #667eea; }}
                .endpoint-url {{ font-family: 'Monaco', monospace; font-weight: 600; color: #2d3748; font-size: 0.85em; }}
                .webhooks-container {{ background: rgba(255, 255, 255, 0.95); border-radius: 20px; padding: 30px; margin-bottom: 30px; }}
                .security-container {{ background: rgba(255, 255, 255, 0.95); border-radius: 20px; padding: 30px; }}
                .section-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 2px solid #e2e8f0; }}
                .action-buttons {{ display: flex; gap: 10px; }}
                .btn {{ padding: 10px 20px; border: none; border-radius: 10px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; font-size: 0.85em; }}
                .btn-primary {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; }}
                .btn-danger {{ background: linear-gradient(135deg, #fc8181, #f56565); color: white; }}
                .btn-warning {{ background: linear-gradient(135deg, #ed8936, #dd6b20); color: white; }}
                .alert {{ padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
                .alert-danger {{ background: #fed7d7; border: 1px solid #fc8181; color: #742a2a; }}
                .alert-success {{ background: #c6f6d5; border: 1px solid #48bb78; color: #22543d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1><i class="fas fa-shield-alt"></i> JWT-Secured Webhook Monitor</h1>
                    <div class="security-badge">🔐 JWT Authentication Required</div>
                    <p>All endpoints require valid JWT token authentication</p>
                </div>

                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{len(webhook_storage)}</div>
                        <div class="stat-label">Total Webhooks</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number success">{successful_auths}</div>
                        <div class="stat-label">Successful Auths</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number danger">{failed_auths}</div>
                        <div class="stat-label">Failed Auths</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number danger">{len(failed_ips)}</div>
                        <div class="stat-label">Blocked IPs</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{self._get_recent_count()}</div>
                        <div class="stat-label">Last Hour</div>
                    </div>
                </div>

                <div class="endpoints">
                    <h2 class="section-title"><i class="fas fa-link"></i> Protected Endpoints (JWT Required)</h2>
                    <div class="alert alert-danger">
                        <strong>⚠️ Authentication Required:</strong> All webhook endpoints require a valid JWT token in the 'token' query parameter.
                    </div>
                    <div class="endpoint-list">
                        {endpoints_html}
                    </div>
                </div>

                <div class="webhooks-container">
                    <div class="section-header">
                        <h2 class="section-title"><i class="fas fa-history"></i> Recent Authenticated Webhooks</h2>
                        <div class="action-buttons">
                            <a href="/webhooks?token=YOUR_JWT_TOKEN" class="btn btn-primary">
                                <i class="fas fa-download"></i> Export JSON
                            </a>
                            <a href="/webhooks/clear?token=YOUR_JWT_TOKEN" class="btn btn-danger">
                                <i class="fas fa-trash"></i> Clear All
                            </a>
                        </div>
                    </div>
                    {self._get_beautiful_webhooks_html()}
                </div>

                <div class="security-container">
                    <div class="section-header">
                        <h2 class="section-title"><i class="fas fa-exclamation-triangle"></i> Security Events</h2>
                        <div class="action-buttons">
                            <a href="/security-events" class="btn btn-warning">
                                <i class="fas fa-eye"></i> View All Events
                            </a>
                        </div>
                    </div>
                    {security_events_html}
                </div>
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def _get_security_events_html(self):
        """Get HTML for recent security events"""
        if not security_events:
            return """
            <div style="text-align: center; padding: 40px 20px; color: #718096;">
                <i class="fas fa-shield-alt" style="font-size: 2em; margin-bottom: 15px; opacity: 0.5;"></i>
                <h3>No security events</h3>
                <p>All authentication attempts have been successful</p>
            </div>
            """

        html_content = ""
        for event in security_events[:10]:  # Show last 10 events
            event_type = event.get('type', 'UNKNOWN')
            timestamp = event.get('timestamp', '')
            client_ip = event.get('client_ip', 'unknown')
            details = event.get('details', {})
            
            # Format timestamp
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime('%H:%M:%S - %d/%m/%Y')
            except:
                formatted_time = timestamp

            # Set colors based on event type
            if event_type == 'AUTHENTICATION_FAILED':
                bg_color = '#fed7d7'
                border_color = '#fc8181'
                text_color = '#742a2a'
                icon = 'fas fa-times-circle'
            else:
                bg_color = '#c6f6d5'
                border_color = '#48bb78'
                text_color = '#22543d'
                icon = 'fas fa-check-circle'

            details_str = json.dumps(details, indent=2) if details else "No details"

            html_content += f"""
            <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 10px; padding: 15px; margin-bottom: 15px; color: {text_color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <i class="{icon}"></i>
                        <span style="font-weight: 600; text-transform: uppercase; font-size: 0.8em;">{event_type.replace('_', ' ')}</span>
                        <span style="background: rgba(0,0,0,0.1); padding: 4px 8px; border-radius: 5px; font-family: Monaco, monospace; font-size: 0.75em;">{client_ip}</span>
                    </div>
                    <span style="font-size: 0.85em; opacity: 0.8;">{formatted_time}</span>
                </div>
                <div style="font-family: Monaco, monospace; font-size: 0.7em; background: rgba(0,0,0,0.1); padding: 10px; border-radius: 5px; white-space: pre-wrap;">{html_module.escape(details_str)}</div>
            </div>
            """
        return html_content

    def send_security_events(self):
        """Send all security events as JSON"""
        response_data = {
            "total": len(security_events),
            "events": security_events
        }
        self.send_json_response(200, response_data)

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
            <div style="text-align: center; padding: 60px 20px; color: #718096;">
                <i class="fas fa-inbox" style="font-size: 3em; margin-bottom: 20px; opacity: 0.5;"></i>
                <h3>No authenticated webhooks received yet</h3>
                <p>Send a request with a valid JWT token to see webhooks appear here</p>
            </div>
            """

        html_content = ""
        for webhook in webhook_storage[:20]:  # Show last 20
            method = webhook.get('method', 'UNKNOWN')
            path = html_module.escape(webhook.get('path', ''))
            timestamp = webhook.get('timestamp', '')
            body = webhook.get('body', '')
            client_ip = webhook.get('client_address', 'unknown')
            user = webhook.get('user', 'Unknown')
            authenticated = webhook.get('authenticated', False)
            
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
                    parsed = json.loads(body)
                    body_display = json.dumps(parsed, indent=2, ensure_ascii=False)
                except:
                    body_display = body
            else:
                body_display = str(body) if body else "No body data"

            method_colors = {
                'POST': '#48bb78', 'GET': '#4299e1', 
                'PUT': '#ed8936', 'DELETE': '#f56565'
            }
            method_color = method_colors.get(method, '#718096')

            auth_badge = '<span style="background: #48bb78; color: white; padding: 4px 8px; border-radius: 10px; font-size: 0.6em; font-weight: 700;">✅ AUTHENTICATED</span>' if authenticated else '<span style="background: #e53e3e; color: white; padding: 4px 8px; border-radius: 10px; font-size: 0.6em; font-weight: 700;">❌ NOT AUTH</span>'

            html_content += f"""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 15px; padding: 20px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="background: {method_color}; color: white; padding: 6px 12px; border-radius: 20px; font-size: 0.7em; font-weight: 700; text-transform: uppercase;">{method}</span>
                        <span style="font-family: Monaco, monospace; background: #2d3748; color: #e2e8f0; padding: 8px 12px; border-radius: 6px; font-size: 0.75em;">{path}</span>
                        {auth_badge}
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #718096; font-size: 0.9em;">
                            <i class="fas fa-user"></i> {user}
                        </div>
                        <div style="color: #718096; font-size: 0.9em;">
                            <i class="fas fa-clock"></i> {formatted_time}
                        </div>
                        <div style="color: #718096; font-size: 0.9em;">
                            <i class="fas fa-map-marker-alt"></i> {client_ip}
                        </div>
                    </div>
                </div>
                <div style="background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 10px; font-family: Monaco, monospace; font-size: 0.7em; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto;">{html_module.escape(body_display)}</div>
            </div>
            """
        return html_content

    def send_callback_success_html(self, decoded_data):
        """Send success HTML for callback-frontend"""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>✅ Authenticated Payment Callback Success</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 20px;
                }
                .container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    max-width: 600px;
                    width: 100%;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                    text-align: center;
                }
                .auth-badge {
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    padding: 10px 20px;
                    border-radius: 25px;
                    font-weight: 600;
                    display: inline-block;
                    margin-bottom: 20px;
                }
                .success-icon {
                    font-size: 4em;
                    color: #48bb78;
                    margin-bottom: 20px;
                }
                .title {
                    font-size: 2em;
                    font-weight: 700;
                    color: #2d3748;
                    margin-bottom: 20px;
                }
                .message {
                    font-size: 1.2em;
                    color: #4a5568;
                    margin-bottom: 30px;
                }
                .data-container {
                    background: #f7fafc;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: left;
                    margin-bottom: 30px;
                }
                .data-title {
                    font-weight: 600;
                    color: #2d3748;
                    margin-bottom: 15px;
                    font-size: 1.1em;
                }
                .data-content {
                    background: #2d3748;
                    color: #e2e8f0;
                    padding: 15px;
                    border-radius: 8px;
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-size: 0.9em;
                    white-space: pre-wrap;
                    overflow-x: auto;
                }
                .back-link {
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    text-decoration: none;
                    padding: 12px 24px;
                    border-radius: 10px;
                    font-weight: 600;
                    transition: transform 0.3s ease;
                }
                .back-link:hover {
                    transform: translateY(-2px);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="auth-badge">🔐 JWT Authenticated</div>
                <div class="success-icon">
                    <i class="fas fa-check-circle"></i>
                </div>
                <h1 class="title">Payment Redirect Received!</h1>
                <p class="message">Your authenticated payment response has been successfully processed and decoded.</p>
                
                <div class="data-container">
                    <div class="data-title">📋 Decoded Payment Information:</div>
                    <div class="data-content">""" + json.dumps(decoded_data, indent=2, ensure_ascii=False) + """</div>
                </div>
                
                <a href="/" class="back-link">
                    <i class="fas fa-arrow-left"></i>
                    Back to Webhook Monitor
                </a>
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-Frame-Options', 'ALLOWALL')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def send_encrypt_success_html(self, request_data):
        """Send success HTML for encrypt-card"""
        data_section = ""
        if request_data:
            data_section = f"""
            <div class="data-container">
                <div class="data-title">📋 Request Data:</div>
                <div class="data-content">{json.dumps(request_data, indent=2, ensure_ascii=False) if request_data else "No request data"}</div>
            </div>
            """

        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>🔐 Authenticated Card Encryption Success</title>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                body {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 20px;
                }
                .container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    max-width: 600px;
                    width: 100%;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                    text-align: center;
                }
                .auth-badge {
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    padding: 10px 20px;
                    border-radius: 25px;
                    font-weight: 600;
                    display: inline-block;
                    margin-bottom: 20px;
                }
                .success-icon {
                    font-size: 4em;
                    color: #4299e1;
                    margin-bottom: 20px;
                }
                .title {
                    font-size: 2em;
                    font-weight: 700;
                    color: #2d3748;
                    margin-bottom: 20px;
                }
                .message {
                    font-size: 1.2em;
                    color: #4a5568;
                    margin-bottom: 30px;
                }
                .ok-badge {
                    background: linear-gradient(135deg, #48bb78, #38a169);
                    color: white;
                    padding: 15px 30px;
                    border-radius: 50px;
                    font-size: 1.5em;
                    font-weight: 700;
                    display: inline-block;
                    margin-bottom: 30px;
                    box-shadow: 0 5px 15px rgba(72, 187, 120, 0.3);
                }
                .data-container {
                    background: #f7fafc;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: left;
                    margin-bottom: 30px;
                }
                .data-title {
                    font-weight: 600;
                    color: #2d3748;
                    margin-bottom: 15px;
                    font-size: 1.1em;
                }
                .data-content {
                    background: #2d3748;
                    color: #e2e8f0;
                    padding: 15px;
                    border-radius: 8px;
                    font-family: 'Monaco', 'Menlo', monospace;
                    font-size: 0.9em;
                    white-space: pre-wrap;
                    overflow-x: auto;
                }
                .back-link {
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    text-decoration: none;
                    padding: 12px 24px;
                    border-radius: 10px;
                    font-weight: 600;
                    transition: transform 0.3s ease;
                }
                .back-link:hover {
                    transform: translateY(-2px);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="auth-badge">🔐 JWT Authenticated</div>
                <div class="success-icon">
                    <i class="fas fa-shield-alt"></i>
                </div>
                <h1 class="title">Card Encryption Complete!</h1>
                <div class="ok-badge">✅ OK</div>
                <p class="message">Your authenticated card encryption request has been processed successfully.</p>
                
                """ + data_section + """
                
                <a href="/" class="back-link">
                    <i class="fas fa-arrow-left"></i>
                    Back to Webhook Monitor
                </a>
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-Frame-Options', 'ALLOWALL')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def send_error_html(self, error_message):
        """Send error HTML page"""
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>❌ Error</title>
            <style>
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #f56565 0%, #e53e3e 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    max-width: 600px;
                    width: 100%;
                    text-align: center;
                }}
                .title {{
                    font-size: 2em;
                    color: #2d3748;
                    margin-bottom: 20px;
                }}
                .message {{
                    font-size: 1.1em;
                    color: #4a5568;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: #fed7d7;
                    border-radius: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="title">Request Failed</h1>
                <div class="message">{html_module.escape(error_message)}</div>
            </div>
        </body>
        </html>
        """

        self.send_response(400)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-Frame-Options', 'ALLOWALL')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

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
    """Run the JWT-secured webhook server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, JWTSecuredWebhookHandler)

    print("🔐 JWT-Secured Webhook Server Starting...")
    print(f"📡 Server running on: http://localhost:{port}")
    print(f"🏠 Home page: http://localhost:{port}")
    print("-" * 60)
    print("🔑 JWT Configuration:")
    print(f"   Secret Key: {JWT_SECRET}")
    print(f"   Expected User: {EXPECTED_PAYLOAD['name']}")
    print(f"   Admin: {EXPECTED_PAYLOAD['admin']}")
    print(f"   Phone: {EXPECTED_PAYLOAD['phone']}")
    print(f"   Random Number: {EXPECTED_PAYLOAD['random_number']}")
    print("-" * 60)
    print("📋 Protected Endpoints (require JWT token):")
    print(f"   🔗 Main webhook: http://localhost:{port}/webhook?token=YOUR_JWT_TOKEN")
    print(f"   💳 Payment webhook: http://localhost:{port}/webhook/payment?token=YOUR_JWT_TOKEN")
    print(f"   🔄 Frontend callback: http://localhost:{port}/webhook/callback-frontend?token=YOUR_JWT_TOKEN")
    print(f"   🔐 Encrypt card: http://localhost:{port}/webhook/encrypt-card?token=YOUR_JWT_TOKEN")
    print(f"   📊 All webhooks: http://localhost:{port}/webhooks?token=YOUR_JWT_TOKEN")
    print("-" * 60)
    print("⚠️  SECURITY FEATURES:")
    print("   ✅ JWT Token Authentication Required")
    print("   ✅ Payload Verification")
    print("   ✅ Security Event Logging")
    print("   ✅ Failed Authentication Tracking")
    print("   ✅ IP Address Monitoring")
    print("-" * 60)
    print("Press Ctrl+C to stop the server")
    print("-" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 JWT-Secured server stopped by user")
        httpd.server_close()


if __name__ == '__main__':
    # Check if PyJWT is installed
    try:
        import jwt
    except ImportError:
        print("❌ Error: PyJWT library is required!")
        print("Install it with: pip install PyJWT")
        sys.exit(1)
    
    # Get port from command line argument or use default
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number, using default 8000")

    run_server(port)