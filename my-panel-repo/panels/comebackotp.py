import os
import sys

# پروجیکٹ کا اصل پاتھ خودکار طریقے سے رجسٹر کریں
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import re
import html
import time
import urllib.parse
from bs4 import BeautifulSoup
import requests
from core.base_panel import BasePanel
from core.common import (
    STANDARD_HEADERS, WORD_NUMBERS, parse_exact_panel_row
)

NUMBERS_HEADERS = ["id", "range", "number", "cli", "status", "created_at"]
SMS_HEADERS = ["id", "date", "range", "number", "cli", "message", "status"]


class ComebackOtpPanel(BasePanel):
    def __init__(self):
        config = {
            "name": "Comebackotp",
            "status": "ON",
            "login_url": "https://tempnumbers.net/login",
            "numbers_url": "https://tempnumbers.net/client/res/data_smsnumbers.php",
            "sms_url": "https://tempnumbers.net/client/res/data_smscdr.php",
            "username": "comebackotp",
            "password": "comebackotp",
            "useSesskey": True
        }
        super().__init__("Comebackotp", config)

    def _solve_captcha(self, text):
        clean = html.unescape(str(text)).replace("\xa0", " ")
        soup = BeautifulSoup(clean, "html.parser")
        capt = soup.find("input", {"name": re.compile(r"capt", re.I)}) or soup.find("input", {"placeholder": re.compile(r"answer|math", re.I)})
        raw = capt.parent.get_text(" ", strip=True) if (capt and capt.parent) else clean
        for w, n in WORD_NUMBERS.items():
            raw = re.sub(rf"\b{w}\b", str(n), raw, flags=re.I)
        m = re.search(r"(\b\d{1,3}\b)\s*([+\-*xX×/÷]|plus|minus|times|divided\s+by)\s*(\b\d{1,3}\b)", raw, re.I)
        if m:
            n1, op, n2 = int(m.group(1)), m.group(2).lower().strip(), int(m.group(3))
            ans = n1 + n2 if op in ("+", "plus") else (n1 - n2 if op in ("-", "minus") else (n1 * n2 if op in ("*", "x", "×", "times") else (n1 // n2 if n2 != 0 else 0)))
            return str(ans), capt.get("name") if capt else "capt"
        return None, None

    def login(self, force: bool = False) -> bool:
        with self._lock:
            if self.session and self.cookie_header and "Logged In" in self.login_status and not force:
                return True
            self.session = requests.Session()
            self.session.verify = False
            self.session.headers.update(STANDARD_HEADERS)
            try:
                r1 = self.session.get(self.config["login_url"], timeout=18, verify=False)
                ans, c_field = self._solve_captcha(r1.text or "")
                payload = {
                    "username": self.config["username"],
                    "password": self.config["password"]
                }
                if ans:
                    payload[c_field or "capt"] = ans
                r2 = self.session.post(self.config["login_url"], data=payload, headers=STANDARD_HEADERS, timeout=18, allow_redirects=True, verify=False)
                if "logout" in r2.text.lower() or "client" in r2.url.lower():
                    self.cookie_header = "; ".join([f"{c.name}={c.value}" for c in self.session.cookies])
                    self.login_status = "✅ Logged In"
                    return True
            except Exception:
                pass
            return False

    def fetch_numbers(self, force: bool = False) -> list:
        if not self.session or not self.cookie_header or "Logged In" not in self.login_status:
            if not self.login():
                return []
        all_nums, seen, offset, seq = [], set(), 0, 1
        headers = dict(STANDARD_HEADERS, **{
            "Accept": "application/json, text/javascript, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": self.cookie_header
        })
        while len(all_nums) < 30000:
            params = [
                ("sEcho", str(seq)), ("draw", str(seq)), ("iColumns", "7"),
                ("sColumns", ",,,,,,"), ("start", str(offset)), ("length", "1000"),
                ("iDisplayStart", str(offset)), ("iDisplayLength", "1000"),
                ("_", str(int(time.time() * 1000)))
            ]
            try:
                res = self.session.get(f"{self.config['numbers_url']}?{urllib.parse.urlencode(params)}", headers=headers, timeout=15, verify=False)
                data = res.json()
                srv_cols = [c.strip() for c in (data.get("sColumns") or "").split(",") if c.strip()]
                use_headers = srv_cols if srv_cols else NUMBERS_HEADERS
                batch = data.get("aaData") or data.get("data") or []
                if not batch:
                    break
                for row in batch:
                    p = parse_exact_panel_row(row, headers=use_headers, is_sms=False)
                    num_val = p.get("number") or p.get("col_2")
                    if num_val and num_val not in seen:
                        seen.add(num_val)
                        all_nums.append(p)
                tot = int(data.get("recordsTotal") or data.get("iTotalDisplayRecords") or 0)
                if len(batch) < 1000 or (tot > 0 and len(all_nums) >= tot):
                    break
                offset += len(batch)
                seq += 1
            except Exception:
                break
        with self._lock:
            self.numbers_cache = all_nums
            self.last_numbers_sync = time.time()
        return all_nums

    def fetch_sms(self, force: bool = False) -> list:
        if not self.session or not self.cookie_header or "Logged In" not in self.login_status:
            if not self.login():
                return []
        headers = dict(STANDARD_HEADERS, **{
            "Accept": "application/json, text/javascript, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": self.cookie_header
        })
        params = [
            ("fdate1", ""), ("fdate2", ""), ("draw", "1"), ("start", "0"),
            ("length", "100"), ("sEcho", "1"), ("iColumns", "7"), ("sColumns", ",,,,,,"),
            ("iDisplayStart", "0"), ("iDisplayLength", "100"), ("iSortCol_0", "1"),
            ("sSortDir_0", "desc"), ("_", str(int(time.time() * 1000)))
        ]
        all_sms = []
        try:
            res = self.session.get(f"{self.config['sms_url']}?{urllib.parse.urlencode(params)}", headers=headers, timeout=15, verify=False)
            data = res.json()
            srv_cols = [c.strip() for c in (data.get("sColumns") or "").split(",") if c.strip()]
            use_headers = srv_cols if srv_cols else SMS_HEADERS
            for row in (data.get("aaData") or data.get("data") or []):
                p = parse_exact_panel_row(row, headers=use_headers, is_sms=True)
                if p:
                    all_sms.append(p)
        except Exception:
            pass
        with self._lock:
            self.sms_cache = all_sms
            self.last_sms_sync = time.time()
        return all_sms
