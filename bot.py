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
    print(f"🌐 Web server running on port {port}", flush=True)
    server.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

# -------------------------
# Startup message
# -------------------------
print("🚀 bot.py started...", flush=True)

# -------------------------
# Environment check
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
    raise EnvironmentError(f"❌ Missing environment variables: {', '.join(missing)}")
else:
    print("✅ All required environment variables found.", flush=True)

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

print(f"✅ Logged in as: {reddit.user.me()}", flush=True)
print(f"📍 Target subreddit: r/{subreddit_name}", flush=True)

# -------------------------
# Load FAQ from wiki
# -------------------------
def load_faq():
    wiki_page_name = "ifaq"  # confirmed readable page
    print(f"📘 Checking wiki page '{wiki_page_name}'...", flush=True)
    try:
        page = subreddit.wiki[wiki_page_name].content_md
        print(f"✅ Loaded '{wiki_page_name}' page successfully ({len(page)} characters).", flush=True)
    except prawcore.exceptions.NotFound:
        print(f"❌ Could not find the '{wiki_page_name}' wiki page.", flush=True)
        return {}
    except Exception as e:
        print(f"❌ Error loading wiki: {e}", flush=True)
        traceback.print_exc()
        return {}

    faq = {}
    # Parse codes and answers, store codes lowercase
    matches = re.findall(r"(\[FAQ\d+\])\s*\n(.+?)(?=\n\[FAQ|\Z)", page, re.S)
    for code, answer in matches:
        faq[code.strip().lower()] = answer.strip()
    print(f"📖 Parsed {len(faq)} FAQ entries.", flush=True)
    return faq

faq_answers = load_faq()
last_reload = time.time()
reload_interval = 600  # 10 minutes
replied_comments = set()

# -------------------------
# Handle comment replies
# -------------------------
def handle_comment(comment):
    body = re.sub(r"\s+", " ", comment.body.lower()).strip()  # normalize spaces and lowercase
    for code, answer in faq_answers.items():
        # match code anywhere in the comment, case-insensitive
        if re.search(rf"\b{re.escape(code)}\b", body):
            try:
                comment.reply(answer)
                replied_comments.add(comment.id)
                print(f"💬 Replied to u/{comment.author} with {code}", flush=True)
            except Exception as e:
                print(f"⚠️ Error replying to comment {comment.id}: {e}", flush=True)
                traceback.print_exc()
            return True  # matched
    return False  # no match

# -------------------------
# Main loop
# -------------------------
def main():
    print("🔍 Monitoring subreddit comments...", flush=True)
    bot_username = str(reddit.user.me()).lower()

    while True:
        try:
            for comment in subreddit.stream.comments(skip_existing=True):
                author_name = comment.author.name if comment.author else "[deleted]"
                print(f"👀 Seen comment {comment.id} by {author_name}", flush=True)

                # Skip own comments
                if comment.author and comment.author.name.lower() == bot_username:
                    continue

                # Reload FAQ periodically
                if time.time() - last_reload > reload_interval:
                    print("🔄 Reloading FAQ from wiki...", flush=True)
                    globals()["faq_answers"] = load_faq()
                    globals()["last_reload"] = time.time()

                if comment.id not in replied_comments:
                    matched = handle_comment(comment)
                    if not matched:
                        print(f"⚡ No FAQ code found in comment {comment.id}", flush=True)

                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Stream error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(30)

if __name__ == "__main__":
    main()
