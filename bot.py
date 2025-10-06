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
print(f"Checking wiki pages in subreddit: r/{subreddit_name}")

# -------------------------
# List all wiki pages the bot can see
# -------------------------
print("\n📘 Listing all wiki pages via PRAW...")
try:
    pages = list(subreddit.wiki)
    if pages:
        print("Wiki pages detected:")
        for p in pages:
            print(f"   • '{p.name}'")  # exact name PRAW sees
    else:
        print("⚠️ No wiki pages detected.")
except Exception as e:
    print("❌ Error fetching wiki pages:")
    print(e)
    traceback.print_exc()

# -------------------------
# Test: attempt to load FAQ page(s)
# -------------------------
faq_variations = ["faq", "FAQ", "Faq"]  # add variations as needed
faq_loaded = False

print("\n📘 Attempting to load FAQ page variations...")
for name in faq_variations:
    try:
        page = subreddit.wiki[name].content_md
        print(f"✅ Successfully loaded FAQ page as: '{name}'")
        print(f"First 500 characters of content:\n{page[:500]}")
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
    print("   • Check exact wiki page name (case-sensitive).")
    print("   • Check the bot has permission to read this page.")
