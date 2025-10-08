import praw
import os
import re
import time
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging.handlers import RotatingFileHandler

# ============================================================
# LOGGING SETUP
# ============================================================
LOG_PATH = "bot.log"

# File handler (keeps detailed logs locally)
file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setLevel(logging.DEBUG)

# Define filter to reduce Render console spam
class RenderLogFilter(logging.Filter):
    """Filter to reduce repetitive or noisy logs on Render."""
    def filter(self, record):
        msg = record.getMessage()
        # Skip repetitive info messages (tune as needed)
        if "Replied to" in msg or "Loaded" in msg or "Stream error" in msg:
            # Only keep ~1 of every 50 similar logs
            return hash(msg) % 50 == 0
        return True

# Console handler for Render output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.addFilter(RenderLogFilter())

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler],
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

# Trim oversized local log file if needed
try:
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 5 * 1024 * 1024:
        open(LOG_PATH, "w").close()
        logger.info("Trimmed oversized log file on startup.")
except Exception as e:
    logger.warning(f"Could not trim log file: {e}")

# ============================================================
# REDDIT AUTH
# ============================================================
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT", "residentevil-faq-bot")
)

subreddit = reddit.subreddit("residentevil")   # change if needed
WIKI_PAGE = "ifaq"

# ============================================================
# FAQ LOADER
# ============================================================
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

# ============================================================
# BOT CORE
# ============================================================
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

# ============================================================
# KEEP-ALIVE HTTP SERVER
# ============================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception:
            # Always return OK to avoid crashing on probe disconnects
            self.send_response(200)
            self.end_headers()
            try:
                self.wfile.write(b"OK")
            except:
                pass

    def do_HEAD(self):
        try:
            self.send_response(200)
            self.end_headers()
        except Exception:
            self.send_response(200)
            self.end_headers()

def start_server():
    """Runs the minimal keep-alive HTTP server."""
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server running on port {port}")
    try:
        server.serve_forever()
    except Exception as e:
        logger.error(f"HTTP server error: {e}", exc_info=True)
        time.sleep(10)
        start_server()

# ============================================================
# THREADING & MAIN
# ============================================================
if __name__ == "__main__":
    load_faq()
    threading.Thread(target=refresh_faq_periodically, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    start_server()
