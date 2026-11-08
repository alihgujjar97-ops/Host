import re
import html
import time
import urllib.parse
from bs4 import BeautifulSoup
import requests
from core.base_panel import BasePanel
from core.common import (
    STANDARD_HEADERS, parse_exact_panel_row
)

# 135.125 کے اصل ٹیبل کالمز
NUMBERS_HEADERS = ["id", "range", "number", "cli", "status", "created_at"]
SMS_HEADERS = ["id", "date", "range", "number", "cli", "message", "status"]


class Ints135Panel(BasePanel):
    def __init__(self):
        config = {
            "name": "teamlegend097_135.125",
            "status": "ON",
            "login_url": "http://135.125.222.224/ints/login",
            "numbers_url": "http://135.125.222.224/ints/agent/res/data_smsnumbers.php",
            "sms_url": "http://135.125.222.224/ints/agent/res/data_smscdr.php",
            "probe_url": "http://135.125.222.224/ints/agent/MySMSNumbers",
            "username": "teamlegend097",
            "password": "teamlegend097",
            "useSesskey": True
        }
        super().__init__("teamlegend097_135.125", config)

    def login(self, force: bool = False) -> bool:
        with self._lock:
            if self.session and self.cookie_header and "Logged In" in self.login_status and not force:
                return True
            self.session = requests.Session()
            self.session.verify = False
            self.session.headers.update(STANDARD_HEADERS)
            try:
                payload = {
                    "username": self.config["username"],
                    "password": self.config["password"]
                }
                self.session.post(self.config["login_url"], data=payload, headers=STANDARD_HEADERS, timeout=20, allow_redirects=True, verify=False)
                self.cookie_header = "; ".join([f"{c.name}={c.value}" for c in self.session.cookies])
                r_pr = self.session.get(self.config["probe_url"], headers=STANDARD_HEADERS, timeout=10, verify=False)
                m = re.search(r"""sesskey["'\s:=]+["']([a-zA-Z0-9_\-]+)["']""", r_pr.text or "") or re.search(r"sesskey=([a-zA-Z0-9_\-]+)", r_pr.text or "")
                if m:
                    self.sesskey = m.group(1).strip()
                elif "PHPSESSID" in self.cookie_header:
                    mp = re.search(r"PHPSESSID=([a-zA-Z0-9_\-]+)", self.cookie_header)
                    if mp:
                        self.sesskey = mp.group(1)
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
            if self.sesskey:
                params.append(("sesskey", str(self.sesskey)))
            try:
                res = self.session.get(f"{self.config['numbers_url']}?{urllib.parse.urlencode(params)}", headers=headers, timeout=18, verify=False)
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
        if self.sesskey:
            params.append(("sesskey", str(self.sesskey)))
        all_sms = []
        try:
            res = self.session.get(f"{self.config['sms_url']}?{urllib.parse.urlencode(params)}", headers=headers, timeout=18, verify=False)
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
