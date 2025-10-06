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
print("\n🔍 Checking bot authentication scopes...")
print("Bot scopes:", reddit.auth.scopes())

# -------------------------
# List all wiki pages the bot can see
# -------------------------
print("\n📘 Listing all wiki pages via PRAW...")
try:
    pages = list(subreddit.wiki)
    if pages:
        print("Wiki pages detected:")
        for p in pages:
            print(f"   • '{p.name}'")  # print exact PRAW page name
    else:
        print("⚠️ No wiki pages detected.")
except Exception as e:
    print("❌ Error fetching wiki pages:")
    print(e)
    traceback.print_exc()

# -------------------------
# Test: attempt to load FAQ
# -------------------------
print("\n📘 Attempting to load the FAQ wiki page...")
faq_variations = ["faq", "FAQ", "Faq"]  # you can add more variations if needed
faq_loaded = False

for name in faq_variations:
    try:
        page = subreddit.wiki[name].content_md
        print(f"✅ Successfully loaded FAQ page as: '{name}'")
        print(f"First 500 characters:\n{page[:500]}")
        faq_loaded = True
        break  # stop after first successful load
    except prawcore.exceptions.NotFound:
        print(f"❌ Could not find page: '{name}'")
    except Exception as e:
        print(f"⚠️ Unexpected error loading page '{name}':")
        print(e)
        traceback.print_exc()

if not faq_loaded:
    print("\n❌ FAQ page could not be loaded.")
    print("   • Check exact wiki page name and spelling (case-sensitive).")
    print("   • Ensure the bot is approved as a wiki editor or has proper permissions.")
