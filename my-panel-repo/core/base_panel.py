import threading
from abc import ABC, abstractmethod


class BasePanel(ABC):
    def __init__(self, name: str, config: dict):
        self.name = name
        self.key = name.lower().strip()
        self.config = config
        self.login_status = "Ready"
        self.sesskey = None
        self.cookie_header = ""
        self.session = None
        self.numbers_cache = []
        self.sms_cache = []
        self.last_numbers_sync = 0
        self.last_sms_sync = 0
        self._lock = threading.RLock()

    @abstractmethod
    def login(self, force: bool = False) -> bool:
        """پینل کا مخصوص لاگ ان طریقہ کار"""
        pass

    @abstractmethod
    def fetch_numbers(self, force: bool = False) -> list:
        """پینل کے نمبرز لانے کا طریقہ کار"""
        pass

    @abstractmethod
    def fetch_sms(self, force: bool = False) -> list:
        """پینل کے SMS لانے کا طریقہ کار"""
        pass

    def get_summary(self) -> dict:
        """پینل کا موجودہ اسٹیٹس اور لائیو کاؤنٹ"""
        return {
            "name": self.name,
            "status": self.config.get("status", "ON"),
            "login_status": self.login_status,
            "login_url": self.config.get("login_url", ""),
            "numbers_url": self.config.get("numbers_url", ""),
            "backend_php_numbers": self.config.get("backend_php_numbers", ""),
            "sms_url": self.config.get("sms_url", "") or self.config.get("msg_link", ""),
            "backend_php_sms": self.config.get("backend_php_sms", ""),
            "has_cookies": bool(self.cookie_header),
            "sesskey": self.sesskey,
            "live_numbers_count": len(self.numbers_cache),
            "live_sms_count": len(self.sms_cache)
        }
