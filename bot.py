import praw
import os
import re
import time
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging.handlers import RotatingFileHandler

# ------------------ Logging ------------------
LOG_PATH = "bot.log"
handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------ Reddit Auth ------------------
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT", "residentevil-faq-bot")
)

subreddit = reddit.subreddit("residentevil")   # change if needed
WIKI_PAGE = "ifaq"

# ------------------ FAQ Loader ------------------
faq_dict = {}

def load_faq():
    """Pulls and parses the FAQ wiki page into a dict."""
    global faq_dict
    try:
        page = subreddit.wiki[WIKI_PAGE].content_md
        # Pattern: [FAQ001]\nAnswer text until next [FAQ...]
        pattern = r"\[FAQ(\d{3})\]\s*(.+?)(?=\n\[FAQ|\Z)"
        matches = re.findall(pattern, page, flags=re.DOTALL)

        faq_dict = {f"[FAQ{num}]": ans.strip() for num, ans in matches}
        logger.info(f"Loaded {len(faq_dict)} FAQ entries from wiki '{WIKI_PAGE}'.")
    except Exception as e:
        logger.error(f"Failed to load FAQ from wiki: {e}", exc_info=True)

def refresh_faq_periodically():
    """Reloads the FAQ every 10 minutes."""
    while True:
        load_faq()
        time.sleep(600)

# ------------------ Bot Core ------------------
def run_bot():
    """Main comment stream handler."""
    logger.info("Bot started successfully and monitoring comments.")
    while True:
        try:
            for comment in subreddit.stream.comments(skip_existing=True):
                body = comment.body.strip()
                match = re.search(r"\[FAQ\d{3}\]", body, flags=re.IGNORECASE)
                if not match:
                    continue

                code = match.group(0).upper()
                if code in faq_dict:
                    answer = faq_dict[code]
                    footer = "\n\n---\n^(Answer pulled from the [Resident Evil FAQ Wiki](https://www.reddit.com/r/residentevil/wiki/ifaq))"
                    reply_text = f"{answer}{footer}"

                    try:
                        comment.reply(reply_text)
                        logger.info(f"Replied to {comment.id} with {code}.")
                    except Exception as reply_error:
                        logger.error(f"Error replying to {comment.id}: {reply_error}", exc_info=True)
        except Exception as stream_error:
            logger.error(f"Stream error: {stream_error}", exc_info=True)
            time.sleep(60)

# ------------------ Dummy Keep-Alive Server ------------------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def start_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Keep-alive server running on port {port}")
    server.serve_forever()

# ------------------ Threading ------------------
if __name__ == "__main__":
    # Load FAQ immediately and start background refresh
    load_faq()
    threading.Thread(target=refresh_faq_periodically, daemon=True).start()

    # Start Reddit bot and HTTP server
    threading.Thread(target=run_bot, daemon=True).start()
    start_server()
