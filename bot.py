import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import praw
import prawcore
import time
import re
import traceback

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

threading.Thread(target=start_http_server, daemon=True).start()

# -------------------------
# Reddit bot setup
# -------------------------
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
print(f"📍 Target subreddit: r/{subreddit_name}")

# -------------------------
# Function to load FAQ from wiki
# -------------------------
def load_faq():
    print("📘 Loading FAQ from subreddit wiki...")
    try:
        page = subreddit.wiki["ifaq"].content_md  # Adjust your wiki page name here
        faq = {}
        matches = re.findall(r"(\[FAQ\d+\])\s*\n(.+?)(?=\n\[FAQ|\Z)", page, re.S)
        for code, answer in matches:
            # Normalize code to lowercase and strip spaces
            faq[code.strip().lower()] = answer.strip()
        print(f"✅ Loaded {len(faq)} FAQ entries.")
        return faq
    except prawcore.exceptions.NotFound:
        print("❌ Could not find the FAQ wiki page.")
        print("   • Check that the page exists.")
        print("   • Check that the bot account has permission to view it.")
        return {}
    except Exception as e:
        print("❌ Unexpected error while loading wiki:")
        print(e)
        traceback.print_exc()
        return {}

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
print("🔍 Monitoring subreddit comments...")
for comment in subreddit.stream.comments(skip_existing=True):
    # Reload FAQ periodically
    if time.time() - last_reload > reload_interval:
        faq_answers = load_faq()
        last_reload = time.time()
        print(f"🔄 Reloaded FAQ from wiki ({len(faq_answers)} entries)")

    if comment.id in replied_comments:
        continue

    body = comment.body.lower().strip()
    # Remove trailing whitespace and newlines after FAQ code
    body_clean = re.sub(r"\s+", " ", body)
    print(f"👀 Seen comment {comment.id} by {comment.author}: '{body_clean}'")  # debug

    # Check FAQ codes
    matched = False
    for code, answer in faq_answers.items():
        print(f"   🔍 Comparing against code: '{code}'")  # debug
        # Match code even if it's followed by spaces/newlines in comment
        if re.search(re.escape(code) + r"(\s|$)", body_clean):
            try:
                comment.reply(answer)
                replied_comments.add(comment.id)
                matched = True
                print(f"💬 Replied to u/{comment.author} with {code}")
            except Exception as e:
                print(f"⚠️ Error replying: {e}")
            break

    if not matched:
        print("   ❌ No matching FAQ code found.")

    time.sleep(2)
