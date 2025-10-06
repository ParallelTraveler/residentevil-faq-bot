import os
import threading
import time
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import praw
import prawcore
import traceback

# -------------------------
# Dummy HTTP server (required by Render)
# -------------------------
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Reddit FAQ bot is running!")

def start_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"🟢 Dummy HTTP server running on port {port}")
    server.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

# -------------------------
# Reddit API setup
# -------------------------
print("🚀 Starting bot.py...")
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

# -------------------------
# Load FAQ from wiki (old Reddit)
# -------------------------
def load_faq():
    print("📘 Loading FAQ from subreddit wiki...")
    try:
        page = subreddit.wiki["ifaq"].content_md  # ← use your working page here
        faq = {}
        matches = re.findall(r"(\[FAQ\d+\])\s*\n(.+?)(?=\n\[FAQ|\Z)", page, re.S)
        for code, answer in matches:
            faq[code.strip()] = answer.strip()
        print(f"✅ Loaded {len(faq)} FAQ entries.")
        return faq
    except prawcore.exceptions.NotFound:
        print("❌ Could not find the wiki page '/ifaq'. Make sure it exists on OLD Reddit.")
    except Exception as e:
        print("⚠️ Error loading wiki:", e)
        traceback.print_exc()
    return {}

faq_answers = load_faq()

# -------------------------
# Bot loop setup
# -------------------------
last_reload = time.time()
reload_interval = 300  # 5 minutes
replied_comments = set()

# -------------------------
# Main bot loop
# -------------------------
print("🤖 Bot is now watching comments...")

for comment in subreddit.stream.comments(skip_existing=True):
    try:
        # Periodically reload FAQ
        if time.time() - last_reload > reload_interval:
            faq_answers = load_faq()
            last_reload = time.time()

        # Skip already replied comments
        if comment.id in replied_comments:
            continue

        # Look for FAQ codes
        for code, answer in faq_answers.items():
            if code in comment.body:
                try:
                    comment.reply(answer)
                    replied_comments.add(comment.id)
                    print(f"✅ Replied to u/{comment.author} with {code}")
                except Exception as e:
                    print(f"⚠️ Error replying: {e}")
                break

        time.sleep(2)
    except Exception as e:
        print("⚠️ Stream error:", e)
        time.sleep(10)
