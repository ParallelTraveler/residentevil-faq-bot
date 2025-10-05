import os
import praw
import prawcore
import traceback

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
print(f"Checking wiki page in subreddit: r/{subreddit_name}")

# -------------------------
# Test: load wiki FAQ
# -------------------------
try:
    page = subreddit.wiki["faq"].content_md
    print("📘 Wiki page content:")
    print(page)
except prawcore.exceptions.NotFound:
    print("❌ Could not find the FAQ wiki page.")
    print("   • Check that the page 'faq' exists in your subreddit.")
    print("   • Check that your bot account has permission to view it.")
except Exception as e:
    print("❌ Unexpected error while loading wiki:")
    print(e)
    traceback.print_exc()
