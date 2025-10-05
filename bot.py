import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import praw
import prawcore
import time
import re
import sys
import traceback

print("🚀 Starting bot.py...")

# -------------------------
# Tiny HTTP server (required by Render)
# -------------------------
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Reddit bot running!")

def start_http_server():
    try:
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(('0.0.0.0', port), DummyHandler)
        print(f"🟢 Dummy HTTP server running on port {port}")
        server.serve_forever()
    except Exception as e:
        print("❌ Error starting HTTP server:", e)
        traceback.print_exc()

# Start the HTTP server in a separate thread
threading.Thread(target=start_http_server, daemon=True).start()

# -------------------------
# Reddit bot setup
# -------------------------
print("🔍 Checking environment variables...")
required_vars = [
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
    "REDDIT_USERNAME", "REDDIT_PASSWORD",
    "REDDIT_USER_AGENT", "SUBREDDIT"
]
missing = [v for v in required_vars if v not in os.environ or not o_]()
