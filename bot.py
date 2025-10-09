import praw
import os
import re
import time
import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging.handlers import RotatingFileHandler
from prawcore.exceptions import RequestException, ResponseException, ServerError

# ============================================================
# LOGGING SETUP
# ============================================================
LOG_PATH = "bot.log"

file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setLevel(logging.DEBUG)

class RenderLogFilter(logging.Filter):
    """Reduce repetitive logs in Render console."""
    def filter(self, record):
        msg = record.getMessage()
        if any(kw in msg for kw in ("Replied to", "Loaded", "Stream error", "Retrying")):
            return hash(msg) % 40 == 0  # throttle repetitive logs
        return True

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.addFilter(RenderLogFilter())

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler],
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

try:
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 5 * 1024 * 1024:
        open(LOG_PATH, "w").close()
        logger.info("Trimmed oversized log file on startup.")
except Exception as e:
    logger.warning(f"Could not trim log file: {e}")

# ============================================================
# REDDIT AUTH
# ============================================================
logger.info("Initializing Reddit client...")
try:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "residentevil-faq-bot")
    )
    logger.info("Reddit client initialized successfully.")
    subreddit = reddit.subreddit("residentevil")
    logger.info("Connected to subreddit: residentevil")
except Exception as e:
    logger.critical(f"Failed to initialize Reddit client: {e}", exc_info=True)
    raise SystemExit(1)

WIKI_PAGE = "ifaq"

# ============================================================
# FAQ LOADER (with retry)
# ============================================================
faq_dict = {}

def load_faq():
    """Pulls and parses the FAQ wiki page into a dict, with retry on network errors."""
    global faq_dict
    retries = 0
    while retries < 5:
        try:
            logger.debug("Attempting to fetch FAQ wiki page...")
            page = subreddit.wiki[WIKI_PAGE].content_md
            pattern = r"\[FAQ(\d{3})\]\s*(.+?)(?=\n\[FAQ|\Z)"
            matches = re.findall(pattern, page, flags=re.DOTALL)
            faq_dict = {f"[FAQ{num}]": ans.strip() for num, ans in matches}
            logger.info(f"Loaded {len(faq_dict)} FAQ entries from wiki '{WIKI_PAGE}'.")
            return
        except (RequestException, ResponseException, ServerError) as e:
            wait = (2 ** retries) + 3
            logger.warning(f"Retrying wiki load (attempt {retries+1}/5): {e}")
            time.sleep(wait)
            retries += 1
        except Exception as e:
            logger.error(f"Failed to load FAQ: {e}", exc_info=True)
            break
    logger.error("Exceeded max retries for loading FAQ; keeping last known data.")

def refresh_faq_periodically():
    """Reloads the FAQ every 10 minutes."""
    while True:
        load_faq()
        time.sleep(600)

# ============================================================
# BOT CORE (with retry & backoff)
# ============================================================
def run_bot():
    """Main comment stream handler with retry logic."""
    logger.info("Bot thread started. Monitoring new comments...")
    backoff = 10

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
                        logger.info(f"Replied to comment {comment.id} with {code}.")
                    except Exception as reply_error:
                        logger.error(f"Error replying to {comment.id}: {reply_error}", exc_info=True)

            backoff = 10  # reset after success

        except (RequestException, ResponseException, ServerError) as stream_error:
            logger.warning(f"Reddit connection issue: {stream_error}. Retrying in {backoff}s.")
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)

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
def global_thread_excepthook(args):
    logger.error(f"Uncaught thread exception: {args.exc_type.__name__}: {args.exc_value}", exc_info=True)

threading.excepthook = global_thread_excepthook

if __name__ == "__main__":
    load_faq()
    threading.Thread(target=refresh_faq_periodically, daemon=True).start()
    threading.Thread(target=run_bot, daemon=True).start()
    start_server()
