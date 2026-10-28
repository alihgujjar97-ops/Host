"""
AutoCaptcha API & SMS / Numbers Panel Scraper
Description: Production-ready automated session manager, mathematical captcha solver,
background poller, and Flask API gateway for TempNumbers panel.
Compatible with cloud hosting (Railway, Render, VPS, Heroku) out-of-the-box.
"""

import os
import re
import html
import time
import json
import logging
import threading
from urllib.parse import urljoin, unquote
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("TempNumbersScraper")

# ---------------------------------------------------------
# Configuration (Environment variables with sensible defaults)
# ---------------------------------------------------------
PANEL_CONFIG = {
    "login_url": os.getenv("PANEL_LOGIN_URL", "https://tempnumbers.net/login"),
    "username": os.getenv("PANEL_USER", "gennew"),
    "password": os.getenv("PANEL_PASS", "gennew"),
    "sms_cdr_url": os.getenv("PANEL_SMS_URL", "https://tempnumbers.net/client/SMSCDRStats"),
    "numbers_url": os.getenv("PANEL_NUMBERS_URL", "https://tempnumbers.net/client/GeneratedNumbers"),
    "poll_interval_sec": int(os.getenv("POLL_INTERVAL", "3")),
    "api_key": os.getenv("API_KEY", "")  # Optional API key for your Flask endpoint
}

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive"
}

# ---------------------------------------------------------
# Advanced Math Captcha Solver Engine
# ---------------------------------------------------------
class CaptchaSolverEngine:
    WORD_MAP = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
        "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
        "eighteen": 18, "nineteen": 19, "twenty": 20
    }

    @classmethod
    def solve_math_text(cls, raw_text: str) -> str:
        """
        Parses arithmetic captcha text (e.g. '5 + 3', 'What is 12 - 4', 'two plus seven').
        """
        clean = re.sub(r"[\u200B-\u200D\uFEFF]", "", str(raw_text or "")).strip()
        clean = html.unescape(clean)

        # Standard numeric patterns like "5 + 3", "calculate 12 * 2", "what is 8 - 4"
        numeric_patterns = [
            r"(\d+)\s*([\+\-\*xX])\s*(\d+)",
            r"(?:what\s+is|calculate|solve)?\s*[:\s]?\s*(\d+)\s*([\+\-\*xX])\s*(\d+)"
        ]

        for pat in numeric_patterns:
            match = re.search(pat, clean, re.IGNORECASE)
            if match:
                num1 = int(match.group(1))
                op = match.group(2).lower()
                num2 = int(match.group(3))
                if op == "+":
                    return str(num1 + num2)
                elif op == "-":
                    return str(num1 - num2)
                elif op in ("*", "x"):
                    return str(num1 * num2)

        # Word-based patterns like "five plus three" or "seven - two"
        word_pat = r"(\w+)\s*([\+\-\*]|plus|minus|times|multiplied\s+by)\s*(\w+)"
        w_match = re.search(word_pat, clean, re.IGNORECASE)
        if w_match:
            w1 = w_match.group(1).lower()
            op = w_match.group(2).lower()
            w2 = w_match.group(3).lower()
            
            n1 = cls.WORD_MAP.get(w1, int(w1) if w1.isdigit() else None)
            n2 = cls.WORD_MAP.get(w2, int(w2) if w2.isdigit() else None)

            if n1 is not None and n2 is not None:
                if op in ("+", "plus", "add"):
                    return str(n1 + n2)
                elif op in ("-", "minus"):
                    return str(n1 - n2)
                elif op in ("*", "times", "multiplied by"):
                    return str(n1 * n2)

        logger.warning(f"Unable to parse captcha math from text: '{clean[:50]}'. Falling back to '0'.")
        return "0"

# ---------------------------------------------------------
# Core Panel Session & Scraping Worker
# ---------------------------------------------------------
class PanelSessionWorker:
    def __init__(self, config: dict):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(HTTP_HEADERS)
        self.is_logged_in = False
        self.last_login_time = 0
        self.lock = threading.Lock()

        # In-memory storage for sub-millisecond API responses
        self.latest_sms_cache = []
        self.latest_numbers_cache = []
        self.last_sync_time = 0

    def attempt_login(self) -> bool:
        login_url = self.config["login_url"].strip()
        if not login_url.startswith("http"):
            login_url = "https://" + login_url

        try:
            logger.info(f"Opening login page: {login_url}")
            resp = self.session.get(login_url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            form = soup.find("form")
            if not form:
                logger.error("No login form detected on the login URL.")
                return False

            action = form.get("action")
            post_url = urljoin(login_url, action) if action else login_url

            # Extract CSRF and hidden fields
            form_payload = {}
            for hidden in form.find_all("input", type="hidden"):
                h_name = hidden.get("name")
                if h_name:
                    form_payload[h_name] = hidden.get("value") or ""

            # Detect input fields dynamically
            user_input = (
                form.find("input", {"name": re.compile(r"user|email|username|account|login", re.I)}) or
                form.find("input", {"type": "text"})
            )
            pass_input = (
                form.find("input", {"name": re.compile(r"pass|password", re.I)}) or
                form.find("input", {"type": "password"})
            )
            captcha_input = (
                form.find("input", {"name": re.compile(r"ans|captcha|code|verify|security|math", re.I)}) or
                form.find("input", {"placeholder": re.compile(r"captcha|answer|result", re.I)})
            )

            user_key = user_input.get("name", "username") if user_input else "username"
            pass_key = pass_input.get("name", "password") if pass_input else "password"
            captcha_key = captcha_input.get("name", "answer") if captcha_input else "answer"

            # Locate captcha text query
            math_question_text = ""
            if captcha_input:
                parent_block = captcha_input.find_parent(["div", "tr", "label", "p"])
                if parent_block:
                    math_question_text = parent_block.get_text(separator=" ", strip=True)

            if not math_question_text or not any(sym in math_question_text for sym in ["+", "-", "*"]):
                for el in form.find_all(["label", "div", "span", "p", "strong", "b"]):
                    txt_val = el.get_text(separator=" ", strip=True)
                    if any(sym in txt_val for sym in ["+", "-", "*"]):
                        if re.search(r"\d+\s*[\+\-\*]\s*\d+", txt_val):
                            math_question_text = txt_val
                            break

            if not math_question_text:
                math_question_text = resp.text

            solved_answer = CaptchaSolverEngine.solve_math_text(math_question_text)
            logger.info(f"Math Captcha: [{math_question_text[:35]}...] => Solved: '{solved_answer}'")

            form_payload[user_key] = self.config["username"]
            form_payload[pass_key] = self.config["password"]
            form_payload[captcha_key] = solved_answer

            # Execute authentication POST
            login_resp = self.session.post(post_url, data=form_payload, allow_redirects=True, timeout=15)
            check_text = login_resp.text.lower()

            if any(term in check_text for term in ["logout", "sign out", "dashboard", "smscdrstats", "client"]):
                self.is_logged_in = True
                self.last_login_time = time.time()
                logger.info("[SUCCESS] Panel authenticated successfully.")
                return True
            else:
                logger.warning(f"[FAIL] Authentication unsuccessful. Server returned: {login_resp.status_code}")
                self.is_logged_in = False
                return False

        except Exception as e:
            logger.error(f"Exception during login: {e}")
            self.is_logged_in = False
            return False

    def ensure_authenticated_session(self) -> bool:
        with self.lock:
            # Re-authenticate if session is older than 45 minutes or inactive
            if self.is_logged_in and (time.time() - self.last_login_time < 2700):
                return True
            return self.attempt_login()

    def fetch_sms_data(self) -> list:
        """
        Extracts SMS messages from DataTable sAjaxSource or direct HTML table.
        """
        if not self.ensure_authenticated_session():
            return self.latest_sms_cache

        sms_url = self.config["sms_cdr_url"].strip()
        if not sms_url.startswith("http"):
            sms_url = "https://" + sms_url

        try:
            cache_buster = f"{sms_url}{'&' if '?' in sms_url else '?'}_nc={int(time.time() * 1000)}"
            res = self.session.get(cache_buster, timeout=12)

            if "login" in res.text.lower() and "logout" not in res.text.lower():
                logger.warning("Session expired. Re-authenticating...")
                self.is_logged_in = False
                if self.attempt_login():
                    res = self.session.get(cache_buster, timeout=12)
                else:
                    return self.latest_sms_cache

            soup = BeautifulSoup(res.text, "html.parser")
            s_ajax_source = None
            for script in soup.find_all("script"):
                stext = script.string or ""
                match = re.search(r'sAjaxSource":\s*"([^"]+)"', stext) or re.search(r'url:\s*["\']([^"\']*SMSCDR[^"\']*)["\']', stext)
                if match:
                    s_ajax_source = match.group(1)
                    break

            parsed_rows = []

            # 1. Fetch via DataTable AJAX Source if present
            if s_ajax_source:
                base_domain = sms_url.split("/client")[0].rstrip("/")
                if s_ajax_source.startswith("http"):
                    ajax_url = s_ajax_source
                elif s_ajax_source.startswith("/"):
                    ajax_url = f"{base_domain}{s_ajax_source}"
                else:
                    ajax_url = f"{sms_url.rsplit('/', 1)[0]}/{s_ajax_source}"

                sep = "&" if "?" in ajax_url else "?"
                ajax_params = (
                    f"{sep}sEcho=1&iColumns=7&iDisplayStart=0&iDisplayLength=1000"
                    f"&sSearch=&iSortingCols=1&iSortCol_0=0&sSortDir_0=desc&_nc={int(time.time()*1000)}"
                )
                ajax_full = f"{ajax_url}{ajax_params}"

                ajax_headers = dict(HTTP_HEADERS)
                ajax_headers["X-Requested-With"] = "XMLHttpRequest"
                ajax_headers["Referer"] = sms_url

                try:
                    data_dict = self.session.get(ajax_full, headers=ajax_headers, timeout=12).json()
                    raw_rows = data_dict.get("aaData") or data_dict.get("data") or []
                    for row in raw_rows:
                        if isinstance(row, list) and len(row) >= 3:
                            phone = re.sub(r"\D", "", str(row[1] if len(row) > 1 else row[0]))
                            msg = html.unescape(str(row[2] if len(row) > 2 else row[1])).strip()
                            service = str(row[3] if len(row) > 3 else "SMS").strip()
                            country = str(row[0] if len(row) > 0 else "").strip()
                            if phone and msg:
                                parsed_rows.append([phone, service, msg, country])
                except Exception as ex:
                    logger.debug(f"Ajax fetch returned non-JSON: {ex}")

            # 2. Fallback to HTML Table parsing if AJAX did not populate
            if not parsed_rows:
                tables = soup.find_all("table")
                for table in tables:
                    for tr in table.find_all("tr"):
                        cols = [td.get_text(separator=" ", strip=True) for td in tr.find_all(["td", "th"])]
                        if len(cols) >= 3:
                            phone = re.sub(r"\D", "", cols[1])
                            msg = html.unescape(cols[2]).strip()
                            service = cols[3] if len(cols) > 3 else "SMS"
                            country = cols[0]
                            if phone and len(phone) >= 7 and len(msg) > 1:
                                parsed_rows.append([phone, service, msg, country])

            # Update cache safely
            with self.lock:
                if parsed_rows:
                    self.latest_sms_cache = parsed_rows
                self.last_sync_time = time.time()

            return self.latest_sms_cache

        except Exception as e:
            logger.error(f"Error fetching SMS CDR: {e}")
            return self.latest_sms_cache

    def fetch_numbers_data(self) -> list:
        """
        Extracts Generated Numbers list from DataTable sAjaxSource or direct HTML table.
        """
        if not self.ensure_authenticated_session():
            return self.latest_numbers_cache

        nums_url = self.config.get("numbers_url", "").strip()
        if not nums_url:
            return self.latest_numbers_cache

        if not nums_url.startswith("http"):
            nums_url = "https://" + nums_url

        try:
            cache_url = f"{nums_url}{'&' if '?' in nums_url else '?'}_nc={int(time.time() * 1000)}"
            res = self.session.get(cache_url, timeout=12)

            if "login" in res.text.lower() and "logout" not in res.text.lower():
                self.is_logged_in = False
                if self.attempt_login():
                    res = self.session.get(cache_url, timeout=12)
                else:
                    return self.latest_numbers_cache

            soup = BeautifulSoup(res.text, "html.parser")
            s_ajax_source = None
            for script in soup.find_all("script"):
                stext = script.string or ""
                match = re.search(r'sAjaxSource":\s*"([^"]+)"', stext) or re.search(r'url:\s*["\']([^"\']*Numbers[^"\']*)["\']', stext)
                if match:
                    s_ajax_source = match.group(1)
                    break

            numbers_list = []

            # 1. Fetch via DataTable AJAX Source
            if s_ajax_source:
                base_domain = nums_url.split("/client")[0].rstrip("/")
                ajax_url = s_ajax_source if s_ajax_source.startswith("http") else f"{base_domain}/{s_ajax_source.lstrip('/')}"
                sep = "&" if "?" in ajax_url else "?"
                ajax_full = f"{ajax_url}{sep}sEcho=1&iDisplayStart=0&iDisplayLength=2000&_nc={int(time.time()*1000)}"

                ajax_headers = dict(HTTP_HEADERS)
                ajax_headers["X-Requested-With"] = "XMLHttpRequest"
                ajax_headers["Referer"] = nums_url

                try:
                    data_json = self.session.get(ajax_full, headers=ajax_headers, timeout=12).json()
                    rows = data_json.get("aaData") or data_json.get("data") or []
                    for row in rows:
                        if isinstance(row, list) and len(row) >= 3:
                            country = str(row[0]).strip()
                            range_name = str(row[1]).strip()
                            phone_num = re.sub(r"\D", "", str(row[2]))
                            if phone_num:
                                numbers_list.append([country, range_name, phone_num])
                except Exception as ex:
                    logger.debug(f"Ajax numbers fetch returned non-JSON: {ex}")

            # 2. Fallback to HTML Table parsing
            if not numbers_list:
                for tr in soup.find_all("tr"):
                    tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if len(tds) >= 3:
                        c_val = tds[0]
                        r_val = tds[1]
                        p_val = re.sub(r"\D", "", tds[2])
                        if p_val and len(p_val) >= 7:
                            numbers_list.append([c_val, r_val, p_val])

            # Update cache safely
            with self.lock:
                if numbers_list:
                    self.latest_numbers_cache = numbers_list

            return self.latest_numbers_cache

        except Exception as e:
            logger.error(f"Error fetching Numbers data: {e}")
            return self.latest_numbers_cache

# Initialize worker instance
panel_worker = PanelSessionWorker(PANEL_CONFIG)

# ---------------------------------------------------------
# Background Worker Thread for Live Synchronization
# ---------------------------------------------------------
def background_poller():
    """
    Runs continuously in a separate thread to keep memory cache hot.
    Guarantees that your API endpoints respond instantly with zero delay.
    """
    logger.info("Initializing background synchronization worker...")
    time.sleep(1)
    while True:
        try:
            panel_worker.fetch_sms_data()
            panel_worker.fetch_numbers_data()
        except Exception as e:
            logger.error(f"Background synchronization error: {e}")
        time.sleep(PANEL_CONFIG.get("poll_interval_sec", 3))

# ---------------------------------------------------------
# Flask API Application
# ---------------------------------------------------------
app = Flask(__name__)

@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
@app.route("/gateway", methods=["GET"])
def api_gateway():
    """
    Unified API Gateway:
    - ?type=sms      -> Returns active SMS CDR logs in aaData format
    - ?type=numbers  -> Returns active Numbers list in aaData format
    - ?type=status   -> Returns system health, cache count and session status
    """
    # Optional API key verification
    token = request.args.get("token") or request.args.get("key")
    configured_key = PANEL_CONFIG.get("api_key")
    if configured_key and token != configured_key:
        return jsonify({"ok": False, "error": "Unauthorized: Invalid API key"}), 401

    req_type = request.args.get("type", "sms").lower().strip()
    force_refresh = request.args.get("force", "").lower() in ("1", "true", "yes")

    # 1. SMS CDR Endpoint (?type=sms)
    if req_type == "sms":
        if force_refresh or not panel_worker.latest_sms_cache:
            sms_data = panel_worker.fetch_sms_data()
        else:
            sms_data = panel_worker.latest_sms_cache

        return jsonify({
            "ok": True,
            "type": "sms",
            "total": len(sms_data),
            "aaData": sms_data
        }), 200

    # 2. Generated Numbers Endpoint (?type=numbers or ?type=number)
    elif req_type in ("numbers", "number", "sims", "nums"):
        if force_refresh or not panel_worker.latest_numbers_cache:
            numbers_data = panel_worker.fetch_numbers_data()
        else:
            numbers_data = panel_worker.latest_numbers_cache

        return jsonify({
            "ok": True,
            "type": "numbers",
            "total": len(numbers_data),
            "aaData": numbers_data
        }), 200

    # 3. System Status Endpoint (?type=status)
    elif req_type == "status":
        return jsonify({
            "ok": True,
            "authenticated": panel_worker.is_logged_in,
            "last_login_time": panel_worker.last_login_time,
            "cached_sms": len(panel_worker.latest_sms_cache),
            "cached_numbers": len(panel_worker.latest_numbers_cache),
            "last_sync_timestamp": panel_worker.last_sync_time
        }), 200

    # Invalid Parameter
    return jsonify({
        "ok": False,
        "error": f"Invalid 'type' parameter: '{req_type}'. Use '?type=sms' or '?type=numbers'."
    }), 400

# ---------------------------------------------------------
# Direct Runner / Entry Point
# ---------------------------------------------------------
if __name__ == "__main__":
    # Start background poller daemon
    poller_thread = threading.Thread(target=background_poller, daemon=True)
    poller_thread.start()

    # Cloud hosting dynamic port allocation (Railway, Render, Heroku)
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"API Server listening on port {port} (Ready for Production)")
    app.run(host="0.0.0.0", port=port, debug=False)
