import os
import socket

# -------------------------
# Dummy port binding first (for Render)
# -------------------------
port = int(os.environ.get("PORT", 10000))
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', port))
s.listen(1)
print(f"🟢 Bound to port {port} (dummy server to satisfy Render)")

# -------------------------
# Now import other modules and start bot
# -------------------------
import praw
import time
import re

# -------------------------
# Load credentials from environment variables
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
print(f"Monitoring subreddit: r/{subreddit_name}")

# -------------------------
# Function to load FAQ from wiki
# -------------------------
def load_faq():
    try:
        page = subreddit.wiki["faq"].content_md
    except Exception as e:
        print(f"⚠️ Error loading wiki: {e}")
        return {}
    
    faq = {}
    matches = re.findall(r"(\[FAQ\d+\])\s*\n(.+?)(?=\n\[FAQ|\Z)", page, re.S)
    for code, answer in matches:
        faq[code.strip()] = answer.strip()
    return faq

# -------------------------
# Initial load of FAQ
# -------------------------
faq_answers = load_faq()
print(f"Loaded {len(faq_answers)} FAQ entries from wiki.")

# -------------------------
# Auto-refresh variables
# -------------------------
last_reload = time.time()
reload_interval = 300  # seconds

# -------------------------
# Track comments already replied to
# -------------------------
replied_comments = set()

# -------------------------
# Main loop: monitor comments
# -------------------------
for comment in subreddit.stream.comments(skip_existing=True):
    # Reload FAQ periodically
    if time.time() - last_reload > reload_interval:
        faq_answers = load_faq()
        last_reload = time.time()
        print(f"🔄 Reloaded FAQ from wiki ({len(faq_answers)} entries)")

    # Skip if already replied
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
