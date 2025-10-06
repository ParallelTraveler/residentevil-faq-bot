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
# Print bot scopes
# -------------------------
print("🔍 Checking bot authentication scopes...")
print("Bot scopes:", reddit.auth.scopes())

# -------------------------
# List all wiki pages the bot can see
# -------------------------
print("\n📘 Listing wiki pages visible to the bot...")
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
    page = subreddit.wiki["faq"].content_md
    print("✅ Successfully loaded the FAQ wiki page!")
    print(f"Page length: {len(page)} characters")
except prawcore.exceptions.NotFound:
    print("❌ Could not find the FAQ wiki page.")
    print("   • Check that the page 'faq' exists in your subreddit.")
    print("   • Check that your bot account has permission to view it.")
except Exception as e:
    print("❌ Unexpected error while loading wiki:")
    print(e)
    traceback.print_exc()
