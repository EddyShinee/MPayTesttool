from flask import Flask, request, jsonify
import json
import datetime
import os
import threading
import time

app = Flask(__name__)

# Store webhook data in memory (in production, use database)
webhook_storage = []
MAX_STORAGE = 1000


def save_webhook_data(data):
    """Save webhook data with timestamp"""
    webhook_entry = {
        "id": len(webhook_storage) + 1,
        "timestamp": datetime.datetime.now().isoformat(),
        "method": data.get("method"),
        "headers": data.get("headers"),
        "body": data.get("body"),
        "query_params": data.get("query_params"),
        "ip_address": data.get("ip_address")
    }

    # Add to beginning of list (newest first)
    webhook_storage.insert(0, webhook_entry)

    # Keep only MAX_STORAGE entries
    if len(webhook_storage) > MAX_STORAGE:
        webhook_storage = webhook_storage[:MAX_STORAGE]

    print(f"📥 Webhook received at {webhook_entry['timestamp']}")
    print(f"Method: {webhook_entry['method']}")
    print(f"Body: {webhook_entry['body']}")
    print("-" * 50)


@app.route('/webhook', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def webhook_endpoint():
    """Main webhook endpoint that accepts all HTTP methods"""
    try:
        # Get request data
        webhook_data = {
            "method": request.method,
            "headers": dict(request.headers),
            "query_params": dict(request.args),
            "ip_address": request.remote_addr
        }

        # Get body data
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                webhook_data["body"] = request.get_json()
            else:
                webhook_data["body"] = request.get_data(as_text=True)
        else:
            webhook_data["body"] = None

        # Save webhook data
        save_webhook_data(webhook_data)

        # Return success response
        response = {
            "status": "success",
            "message": "Webhook received successfully",
            "timestamp": datetime.datetime.now().isoformat(),
            "received_data": webhook_data["body"]
        }

        return jsonify(response), 200

    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }
        return jsonify(error_response), 500


@app.route('/webhook/<path:custom_path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def custom_webhook_endpoint(custom_path):
    """Custom webhook endpoint with path parameters"""
    try:
        webhook_data = {
            "method": request.method,
            "path": custom_path,
            "headers": dict(request.headers),
            "query_params": dict(request.args),
            "ip_address": request.remote_addr
        }

        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                webhook_data["body"] = request.get_json()
            else:
                webhook_data["body"] = request.get_data(as_text=True)
        else:
            webhook_data["body"] = None

        save_webhook_data(webhook_data)

        response = {
            "status": "success",
            "message": f"Webhook received at path: {custom_path}",
            "timestamp": datetime.datetime.now().isoformat(),
            "received_data": webhook_data["body"]
        }

        return jsonify(response), 200

    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }
        return jsonify(error_response), 500


@app.route('/webhooks', methods=['GET'])
def get_all_webhooks():
    """Get all received webhooks"""
    return jsonify({
        "total": len(webhook_storage),
        "webhooks": webhook_storage
    })


@app.route('/webhooks/latest', methods=['GET'])
def get_latest_webhook():
    """Get the latest webhook"""
    if webhook_storage:
        return jsonify(webhook_storage[0])
    else:
        return jsonify({"message": "No webhooks received yet"}), 404


@app.route('/webhooks/clear', methods=['DELETE'])
def clear_webhooks():
    """Clear all webhooks"""
    global webhook_storage
    webhook_storage = []
    return jsonify({"message": "All webhooks cleared"})


@app.route('/', methods=['GET'])
def home():
    """Home page with instructions"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Webhook Server</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 800px; }}
            .endpoint {{ background: #f4f4f4; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .method {{ color: #2196F3; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Webhook Server</h1>
            <p>Server is running on <strong>http://localhost:5000</strong></p>

            <h2>📡 Available Endpoints:</h2>

            <div class="endpoint">
                <span class="method">POST/GET/PUT/DELETE</span> 
                <code>/webhook</code> - Main webhook endpoint
            </div>

            <div class="endpoint">
                <span class="method">POST/GET/PUT/DELETE</span> 
                <code>/webhook/payment</code> - Payment webhooks
            </div>

            <div class="endpoint">
                <span class="method">POST/GET/PUT/DELETE</span> 
                <code>/webhook/transaction</code> - Transaction webhooks
            </div>

            <div class="endpoint">
                <span class="method">GET</span> 
                <code>/webhooks</code> - Get all received webhooks
            </div>

            <div class="endpoint">
                <span class="method">GET</span> 
                <code>/webhooks/latest</code> - Get latest webhook
            </div>

            <div class="endpoint">
                <span class="method">DELETE</span> 
                <code>/webhooks/clear</code> - Clear all webhooks
            </div>

            <h2>📝 Example Usage:</h2>
            <pre>
# Send a webhook
curl -X POST http://localhost:5000/webhook \\
  -H "Content-Type: application/json" \\
  -d '{{"respCode": "0000", "message": "Payment completed"}}'

# Get all webhooks
curl http://localhost:5000/webhooks

# Get latest webhook
curl http://localhost:5000/webhooks/latest
            </pre>

            <h2>📊 Statistics:</h2>
            <p>Total webhooks received: <strong>{len(webhook_storage)}</strong></p>
            <p>Last updated: <strong>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></p>

            <h2>🔄 Auto-refresh every 5 seconds</h2>
            <script>
                setTimeout(function(){{
                    location.reload();
                }}, 5000);
            </script>
        </div>
    </body>
    </html>
    """
    return html_content


if __name__ == '__main__':
    print("🚀 Starting Webhook Server...")
    print("📡 Server will be available at: http://localhost:5000")
    print("🔗 Main webhook endpoint: http://localhost:5000/webhook")
    print("📊 View all webhooks: http://localhost:5000/webhooks")
    print("🏠 Home page: http://localhost:5000")
    print("-" * 60)

    # Run Flask app
    app.run(
        host='0.0.0.0',  # Accept connections from any IP
        port=5000,
        debug=True,
        threaded=True
    )