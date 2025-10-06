import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import praw
import prawcore
import traceback
import re

# -------------------------
# Tiny HTTP server (Render health check)
# -------------------------
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ResidentEvil FAQ Bot is running!")

def start_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    print(f"🌐 Web server running on port {port}")
    server.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

# -------------------------
# Environment check
# -------------------------
print("🚀 bot.py started...")
required_vars = [
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USERNAME",
    "REDDIT_PASSWORD",
    "REDDIT_USER_AGENT",
    "SUBREDDIT",
]
missing = [v for v in required_vars if v not in os.environ or not os.environ[v]]
if missing:
    raise EnvironmentError(f"❌ Missing environment variables: {', '.join(missing)}")
else:
    print("✅ All required environment variables found.")

# -------------------------
# Reddit setup
# -------------------------
reddit = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    username=os.environ["REDDIT_USERNAME"],
    password=os.environ["REDDIT_PASSWORD"],
    user_agent=os.environ["REDDIT_USER_AGENT"],
)

subreddit_name = os.environ["SUBREDDIT"]
subreddit = reddit.subreddit(subreddit_name)

print(f"✅ Logged in as: {reddit.user.me()}")
print(f"📍 Target subreddit: r/{subreddit_name}")

# -------------------------
# Load FAQ from wiki
# -------------------------
def load_faq():
    wiki_page_name = "ifaq"  # use the page you confirmed works
    print(f"📘 Checking wiki page '{wiki_page_name}'...")

    try:
        page = subreddit.wiki[wiki_page_name].content_md
        print(f"✅ Loaded '{wiki_page_name}' page successfully ({len(page)} characters).")
    except prawcore.exceptions.NotFound:
        print(f"❌ Could not find the '{wiki_page_name}' wiki page.")
        return {}

    faq = {}
    matches = re.findall(r"(\[FAQ\d+\])\s*\n(.+?)(?=\n\[FAQ|\Z)", page, re.S)
    for code, answer in matches:
        faq[code.strip()] = answer.strip()

    print(f"📖 Parsed {len(faq)} FAQ entries.")
    return faq

faq_answers = load_faq()
last_reload = time.time()
reload_interval = 600  # every 10 minutes
replied_comments = set()

# -------------------------
# Handle comments
# -------------------------
def handle_comment(comment):
    try:
        for code, answer in faq_answers.items():
            if code in comment.body:
                comment.reply(answer)
                replied_comments.add(comment.id)
                print(f"💬 Replied to u/{comment.author} with {code}")
                break
    except Exception as e:
        print(f"⚠️ Error replying to comment {comment.id}: {e}")
        traceback.print_exc()

# -------------------------
# Main loop
# -------------------------
def main():
    print("🔍 Monitoring subreddit comments...")

    # Cache bot username for skip check
    bot_username = str(reddit.user.me()).lower()

    while True:
        try:
            for comment in subreddit.stream.comments(skip_existing=True):
                if comment.author and comment.author.name.lower() == bot_username:
                    continue  # skip own comments

                # Reload FAQ periodically
                if time.time() - last_reload > reload_interval:
                    print("🔄 Reloading FAQ from wiki...")
                    globals()["faq_answers"] = load_faq()
                    globals()["last_reload"] = time.time()

                if comment.id not in replied_comments:
                    handle_comment(comment)

                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Stream error: {e}")
            traceback.print_exc()
            time.sleep(30)

if __name__ == "__main__":
    main()
