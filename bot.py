import os
import time
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
import praw
import prawcore
import traceback
import sys

# -------------------------
# Startup confirmation
# -------------------------
print("🚀 bot.py started...", flush=True)

# -------------------------
# Reddit bot setup
# -------------------------
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
    print(f"❌ Missing environment variables: {', '.join(missing)}", flush=True)
    sys.exit(1)

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
# Tiny web server for Render
# -------------------------
def run_http():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"🌐 Web server running on port {port}", flush=True)
    server.serve_forever()

threading.Thread(target=run_http, daemon=True).start()

# -------------------------
# Main bot loop
# -------------------------
def check_wiki():
    try:
        print("📘 Checking wiki page 'ifaq'...", flush=True)
        page = subreddit.wiki["ifaq"].content_md
        print(f"✅ Loaded 'ifaq' page successfully ({len(page)} characters).", flush=True)
    except prawcore.exceptions.NotFound:
        print("❌ Could not find the 'ifaq' wiki page.", flush=True)
        print("   • Ensure it exists and the bot has permission to read it.")
    except Exception as e:
        print("⚠️ Unexpected error while loading 'ifaq':", e, flush=True)
        traceback.print_exc()

# -------------------------
# Run continuously
# -------------------------
if __name__ == "__main__":
    while True:
        check_wiki()
        print("⏳ Waiting 10 minutes before next check...", flush=True)
        time.sleep(600)
