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
print(f"Checking wiki access in subreddit: r/{subreddit_name}")

# -------------------------
# List all wiki pages the bot can see
# -------------------------
print("📘 Listing wiki pages visible to the bot...")
try:
    pages = list(subreddit.wiki)
    if pages:
        print("✅ Bot can see the following wiki pages:")
        for page in pages:
            print(f"   • {page}")
    else:
        print("⚠️ Bot cannot see any wiki pages.")
except Exception as e:
    print("❌ Error while fetching wiki pages:")
    print(e)
    traceback.print_exc()

# -------------------------
# Test: load wiki FAQ
# -------------------------
print("\n📘 Attempting to load the 'faq' wiki page...")
try:
    print("🔍 Listing accessible wiki pages...")
    for page in subreddit.wiki:
        print("   •", page.name)

    print("\n📘 Trying to load 'faq' page...")
    page = subreddit.wiki["faq"].content_md
    print("✅ Successfully loaded FAQ page!")
    print(page[:500])  # show first 500 characters
except prawcore.exceptions.NotFound:
    print("❌ Still could not find 'faq' wiki page via API.")
except Exception as e:
    print("⚠️ Other error:")
    print(e)
    traceback.print_exc()

