import os
import sys

# موجودہ ڈائریکٹری کو پائتھن پاتھ میں خودکار شامل کریں تاکہ 'core' فورا مل جائے
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import time
import json
import importlib
import inspect
import pkgutil
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from core.base_panel import BasePanel

PORT = int(os.environ.get("PORT", 8080))
PANEL_REGISTRY = {}
REGISTRY_LOCK = threading.RLock()


def auto_load_all_panels():
    """panels فولڈر کے تمام ماڈیولز خودکار لوڈ کرے گا"""
    import panels
    loaded_count = 0
    for _, module_name, _ in pkgutil.iter_modules(panels.__path__):
        try:
            mod = importlib.import_module(f"panels.{module_name}")
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, BasePanel) and obj is not BasePanel:
                    instance = obj()
                    key = instance.name.lower().strip()
                    PANEL_REGISTRY[key] = instance
                    loaded_count += 1
        except Exception as e:
            print(f"Error loading panels.{module_name}: {e}")

    print(f"✅ Auto-Loaded {loaded_count} panels successfully.")


def _sync_single_panel(panel, do_numbers):
    try:
        panel.fetch_sms(force=True)
        if do_numbers:
            panel.fetch_numbers(force=True)
    except Exception:
        pass


def background_sync_worker():
    last_numbers_sync = 0
    while True:
        try:
            now = time.time()
            do_numbers = (now - last_numbers_sync >= 300)
            if do_numbers:
                last_numbers_sync = now

            with REGISTRY_LOCK:
                panels_list = list(PANEL_REGISTRY.values())

            for p in panels_list:
                threading.Thread(target=_sync_single_panel, args=(p, do_numbers), daemon=True).start()
        except Exception:
            pass
        time.sleep(10)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/").lower()
        qs = urllib.parse.parse_qs(parsed.query)

        req_type = str(qs.get("type", [""])[0]).lower().strip()
        panel_param = str(qs.get("panel", [""])[0]).strip().lower()
        refresh = qs.get("refresh", ["0"])[0] == "1"

        if path in ("", "/", "/api/panels"):
            with REGISTRY_LOCK:
                summary = [p.get_summary() for p in PANEL_REGISTRY.values()]
            self._send_json({"ok": True, "count": len(summary), "panels": summary})
            return

        parts = [x for x in path.strip("/").split("/") if x]
        if len(parts) >= 3 and parts[0] == "api":
            panel_param = parts[1]
            if parts[2] in ("numbers", "number", "num"):
                req_type = "number"
            elif parts[2] in ("sms", "otp"):
                req_type = "sms"
        elif len(parts) == 2 and parts[0] == "api":
            if parts[1] in ("numbers", "number", "num"):
                req_type = "number"
            elif parts[1] in ("sms", "otp"):
                req_type = "sms"

        if req_type in ("number", "numbers", "num"):
            self._serve_numbers(panel_param, refresh)
        elif req_type in ("sms", "otp"):
            self._serve_sms(panel_param, refresh)
        else:
            self._send_json({"ok": False, "error": "Use /api/<panel>/numbers or /api/<panel>/sms"}, 400)

    def _serve_numbers(self, panel_name: str, refresh: bool):
        targets = []
        with REGISTRY_LOCK:
            if panel_name in PANEL_REGISTRY:
                targets = [PANEL_REGISTRY[panel_name]]
            elif not panel_name or panel_name in ("all", "universal"):
                targets = list(PANEL_REGISTRY.values())

        if not targets:
            self._send_json({"ok": False, "error": f"Panel '{panel_name}' not found"}, 404)
            return

        all_nums = []
        for p in targets:
            rows = p.fetch_numbers(force=True) if refresh else p.numbers_cache
            for r in rows:
                item = dict(r)
                item["panel"] = p.name
                all_nums.append(item)

        self._send_json({
            "ok": True,
            "type": "number",
            "count": len(all_nums),
            "panel": panel_name if panel_name else "ALL_PANELS",
            "records": all_nums
        })

    def _serve_sms(self, panel_name: str, refresh: bool):
        targets = []
        with REGISTRY_LOCK:
            if panel_name in PANEL_REGISTRY:
                targets = [PANEL_REGISTRY[panel_name]]
            elif not panel_name or panel_name in ("all", "universal"):
                targets = list(PANEL_REGISTRY.values())

        if not targets:
            self._send_json({"ok": False, "error": f"Panel '{panel_name}' not found"}, 404)
            return

        all_sms = []
        for p in targets:
            rows = p.fetch_sms(force=True) if refresh else p.sms_cache
            all_sms.extend(rows)

        self._send_json({
            "ok": True,
            "type": "sms",
            "count": len(all_sms),
            "panel": panel_name if panel_name else "ALL_PANELS",
            "records": all_sms
        })


def main():
    auto_load_all_panels()
    threading.Thread(target=background_sync_worker, daemon=True).start()
    server_address = ("0.0.0.0", PORT)
    httpd = ThreadedHTTPServer(server_address, APIHandler)
    print(f"🚀 Auto-Modular Panel Bridge Server running at http://0.0.0.0:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == "__main__":
    main()
