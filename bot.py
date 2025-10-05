import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import praw
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
missing = [v for v in required_vars if v not in os.environ or not os.environ[v].strip()]
if missing:
    print(f"❌ Missing environment variables: {missing}")
    sys.exit(1)
else:
    print("✅ All required environment variables found.")

try:
    print("🚀 Setting up Reddit connection...")
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
        user_agent=os.environ["REDDIT_USER_AGENT"]
    )
    subreddit_name = os.environ["SUBREDDIT"]
    subreddit = reddit.subreddit(subreddit_name)
    print(f"✅ Logged in as: {reddit.user.me()}")
    print(f"Monitoring subreddit: r/{subreddit_name}")
except Exception as e:
    print("❌ Reddit setup failed:", e)
    traceback.print_exc()
    sys.exit(1)

# -------------------------
# Function to load FAQ from wiki
# -------------------------
def load_faq():
    print("📘 Loading FAQ from subreddit wiki...")
    try:
        page = subreddit.wiki["faq"].content_md
        faq = {}
        matches = re.findall(r"(\[FAQ\d+\])\s*\n(.+?)(?=\n\[FAQ|\Z)", page, re.S)
        for code, answer in matches:
            faq[code.strip()] = answer.strip()
        print(f"✅ Loaded {len(faq)} FAQ entries.")
        return faq
    except Exception as e:
        print(f"⚠️ Error loading wiki: {e}")
        traceback.print_exc()
        return {}

faq_answers = load_faq()

# -------------------------
# Bot loop
# -------------------------
last_reload = time.time()
reload_interval = 300
replied_comments = set()

print("🤖 Bot is now watching comments...")
try:
    for comment in subreddit.stream.comments(skip_existing=True):
        # Reload FAQ periodically
        if time.time() - last_reload > reload_interval:
            faq_answers = load_faq()
            last_reload = time.time()
            print(f"🔄 Reloaded FAQ from wiki ({len(faq_answers)} entries)")

        if comment.id in replied_comments:
            continue

        for code, answer in faq_answers.items():
            if code in comment.body:
                try:
                    comment.reply(answer)
                    replied_comments.add(comment.id)
                    print(f"✅ Replied to {comment.author} with {code}")
                except Exception as e:
                    print(f"⚠️ Error replying: {e}")
                    traceback.print_exc()
                break

        time.sleep(2)
except Exception as e:
    print("❌ Fatal error in main loop:", e)
    traceback.print_exc()
