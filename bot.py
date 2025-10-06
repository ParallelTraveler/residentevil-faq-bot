import os
import re
import time
import traceback
import praw
import prawcore
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

# -------------------------
# Dummy web server (keeps Render alive)
# -------------------------
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running.")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("", port), SimpleHandler)
    print(f"🌐 Web server running on port {port}")
    server.serve_forever()

Thread(target=run_server, daemon=True).start()

# -------------------------
# Reddit setup
# -------------------------
print("🚀 bot.py started...")

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
# Load FAQ from wiki
# -------------------------
def load_faq():
    print("📘 Checking wiki page 'ifaq'...")
    try:
        page = subreddit.wiki["ifaq"].content_md
        faq = {}
        matches = re.findall(r"(\[FAQ\d+\])\s*\n(.+?)(?=\n\[FAQ|\Z)", page, re.S)
        for code, answer in matches:
            faq[code.strip().upper()] = answer.strip()
        print(f"✅ Loaded {len(faq)} FAQ entries.")
        return faq
    except prawcore.exceptions.NotFound:
        print("❌ Could not find the 'ifaq' wiki page.")
        return {}
    except Exception as e:
        print(f"⚠️ Error loading wiki: {e}")
        traceback.print_exc()
        return {}

faq_answers = load_faq()

# -------------------------
# Reply to FAQ codes in comments
# -------------------------
def handle_comment(comment):
    text = comment.body.upper()
    for code, answer in faq_answers.items():
        if code in text:
            print(f"💬 Match found: {code} in comment {comment.id}")
            try:
                comment.reply(answer)
                print(f"✅ Replied to comment {comment.id} with {code}")
            except Exception as e:
                print(f"⚠️ Error replying to comment {comment.id}: {e}")
            break  # Stop after first match

# -------------------------
# Main loop
# -------------------------
def main():
    print("🔍 Monitoring subreddit comments...")
    while True:
        try:
            for comment in subreddit.stream.comments(skip_existing=True):
                if comment.author and comment.author.name.lower() == reddit.user.me().lower():
                    continue  # skip own comments
                handle_comment(comment)
        except Exception as e:
            print(f"⚠️ Stream error: {e}")
            traceback.print_exc()
            time.sleep(30)

if __name__ == "__main__":
    main()
