import re
import html

KNOWN_SERVICES = (
    "whatsapp", "telegram", "facebook", "google", "tiktok", "viber", "imo",
    "snapchat", "twitter", "microsoft", "apple", "binance", "netflix", "instagram",
    "uber", "amazon", "discord", "line", "wechat", "vk", "paypal", "openai", "chatgpt"
)

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20
}

STANDARD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


def strip_html_tags(val: str) -> str:
    """HTML ٹیگز صاف کرتا ہے"""
    if not val:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(val))
    return html.unescape(text).strip()


def clean_digits_number(val) -> str:
    """فون نمبر کے ہندسے درست کرتا ہے"""
    if not val:
        return ""
    s_clean = strip_html_tags(str(val))
    if s_clean.count(":") >= 1 and s_clean.count("-") >= 2:
        return ""
    clean = re.sub(r"\D", "", s_clean)
    if 7 <= len(clean) <= 16 and clean.replace("0", "") != "":
        return clean
    return ""


def extract_otp_code(msg_text: str) -> str:
    """میسج میں سے OTP نکالتا ہے (G-123456، 884-219 یا 4 سے 8 ہندسے)"""
    if not msg_text:
        return ""
    text = strip_html_tags(str(msg_text))
    m_dash = re.search(r"\b(\d{3})[- ](\d{3})\b", text)
    if m_dash:
        return f"{m_dash.group(1)}{m_dash.group(2)}"
    m_pfx = re.search(r"\b[GgCc]-(\d{4,8})\b", text)
    if m_pfx:
        return m_pfx.group(1)
    m = re.findall(r"\b(?!0+\b)\d{4,8}\b", text)
    return m[0] if m else ""


def detect_service_from_text(text: str) -> str:
    """میسج کے اندر سے سروس کا نام ڈیٹیکٹ کرتا ہے (WhatsApp, Telegram وغیرہ)"""
    if not text:
        return ""
    t_low = str(text).lower()
    for s in KNOWN_SERVICES:
        if s in t_low:
            return s.capitalize()
    return ""


def is_valid_record(num: str, otp: str = "", msg: str = "") -> bool:
    """فالتو خالی یا ڈمی قطاروں کو خارج کرتا ہے"""
    if not clean_digits_number(num):
        return False
    if otp and otp.replace("0", "") == "":
        otp = ""
    clean_msg = strip_html_tags(str(msg)).lower()
    if not otp and (not clean_msg or len(clean_msg) < 4 or clean_msg in ("0", "none", "null", "nan", "[]")):
        return False
    return True


def parse_exact_panel_row(row, headers=None, is_sms=False) -> dict:
    """
    پینل کے ایکزیکٹ کالمز محفوظ کرتا ہے:
    کوئی ڈپلیکیٹ کالم (col_0 وغیرہ) نہیں بنائے گا، صرف پینل کے اصل ہیڈرز آئیں گے۔
    """
    result = {}
    if isinstance(row, dict):
        for k, v in row.items():
            result[k] = strip_html_tags(str(v)) if v is not None else ""
    elif isinstance(row, (list, tuple)):
        for i, cell in enumerate(row):
            val = strip_html_tags(str(cell)) if cell is not None else ""
            if headers and i < len(headers) and headers[i].strip():
                clean_k = re.sub(r"[^a-zA-Z0-9_]", "_", str(headers[i]).strip().lower()).strip("_")
                result[clean_k] = val
            else:
                result[f"col_{i}"] = val
    else:
        return None

    # SMS کے لیے OTP اور سروس ڈیٹیکشن
    if is_sms:
        msg_str = ""
        for k, v in result.items():
            v_s = str(v)
            if len(v_s) > len(msg_str) and (" " in v_s or any(w in v_s.lower() for w in ("code", "otp", "is", "your", "verification"))):
                msg_str = v_s
        if msg_str:
            otp = extract_otp_code(msg_str)
            if otp:
                result["otp"] = otp
            srv = detect_service_from_text(msg_str)
            if srv and ("service" not in result or result["service"] in ("", "-", "ALL")):
                result["service"] = srv

    return result
