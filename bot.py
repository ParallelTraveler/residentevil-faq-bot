print("🔍 Checking environment variables...")

import os
print("✅ os imported")

import threading
print("✅ threading imported")

from http.server import HTTPServer, BaseHTTPRequestHandler
print("✅ HTTP server imported")

import praw
print("✅ praw imported")

import time, re
print("✅ time and re imported")

# -------------------------
# Tiny HTTP server (required by Render)
# -------------------------
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Reddit bot running!")

def start_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"🟢 Dummy HTTP server running on port {port}")
    server.serve_forever()

# Start the HTTP server in a separate thread
threading.Thread(target=start_http_server, daemon=True).start()

# -------------------------
# Reddit bot setup
# -------------------------
print("🚀 Setting up Reddit connection...")

try:
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
        user_agent=os.environ["REDDIT_USER_AGENT"]
    )
    print("✅ Reddit instance created")
except Exception as e:
    print(f"❌ Failed to create Reddit instance: {e}")
    raise

subreddit_name = os.environ.get("SUBREDDIT", "").strip()
if not subreddit_name:
    print("❌ SUBREDDIT environment variable is missing!")
else:
    print(f"📋 Target subreddit: r/{subreddit_name}")

subreddit = reddit.subreddit(subreddit_name)
print(f"✅ Logged in as: {reddit.user.me()}")
print(f"Monitoring subreddit: r/{subreddit_name}")

# -------------------------
# Function to load FAQ from wiki
# -------------------------
def load_faq():
    print("📖 Loading FAQ from subreddit wiki...")
    try:
        page = subreddit.wiki["faq"].content_md
    except Exception as e:
        print(f"⚠️ Error loading wiki: {e}")
        return {}
    
    faq = {}
    matches = re.findall(r"(\[FAQ\d+\])\s*\n(.+?)(?=\n\[FAQ|\Z)", page, re.S)
    for code, answer in matches:
        faq[code.strip()] = answer.strip()
    print(f"✅ Loaded {len(faq)} FAQ entries.")
    return faq

# -------------------------
# Initial FAQ load
# -------------------------
faq_answers = load_faq()

# -------------------------
# Bot loop variables
# -------------------------
last_reload = time.time()
reload_interval = 300  # seconds
replied_comments = set()

# -------------------------
# Main loop: monitor comments
# -------------------------
print("👀 Starting comment stream...")
for comment in subreddit.stream.comments(skip_existing=True):
    # Reload FAQ periodically
    if time.time() - last_reload > reload_interval:
        faq_answers = load_faq()
        last_reload = time.time()
        print(f"🔄 Reloaded FAQ from wiki ({len(faq_answers)} entries)")

    # Skip already replied comments
    if comment.id in replied_comments:
        continue

    # Check for FAQ codes
    for code, answer in faq_answers.items():
        if code in comment.body:
            try:
                comment.reply(answer)
                replied_comments.add(comment.id)
                print(f"✅ Replied to {comment.author} with {code}")
            except Exception as e:
                print(f"⚠️ Error replying: {e}")
            break

    time.sleep(2)
