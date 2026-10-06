#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import io
import time
import json
import math
import random
import zipfile
import logging
import sqlite3
import datetime
import threading
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from queue import Queue, Empty

import requests
import phonenumbers
from pymongo import MongoClient

try:
    import websocket
except ImportError:
    websocket = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("FullOTPBot")

# ── Dynamic Mongo URI Helper ──────────────────────────────────────────────────
def get_mongo_uri() -> str:
    uri = os.getenv("MONGO_URL", "").strip()
    if uri:
        return uri
    return "mongodb://mongo:AdkDWLhpBFUxAEdrWSVzicubbPLLygyZ@altaria.proxy.rlwy.net:5865"

# ── Global System Configuration Constants & Variables ────────────────────────
BurnOnRefresh = False
AdminIDs = [8418544138, 8122951733]
API_Bases = []

BotToken = "8700723265:AAG9aDY1z10U35gH2feOyVKRPgMah6-Zoqw"
MongoURI = get_mongo_uri()
DBName = "legend_otp_bot"
IvasSocketURL = "None"

WithdrawGroupId = -1003239650798
OtpGroupIDs = [-1003868703042, -1002968061060]

CurrencySymbol = "PKR"
MinWithdrawAmount = 100.0
FixedUSDRate = 280.0
UseCustomEmoji = True
FilesDir = "./countries_data"

DefaultAppIconID = "5906478753906696601"
DefaultServiceIconID = "5906478753906696601"

OtpGroupInviteLink = "https://t.me/teamallnumbers"
MainChannelLink = "https://t.me/+t0CAPbyw77kzYzU0"
WithdrawProofsLink = "https://t.me/teamlegendproofs"
DeveloperLink = "https://t.me/Team_legend_owner"
AdminSupportLink = "https://t.me/legendspot01"
BckpChnl = "https://t.me/teamlegendnumber"

# Telegram UI Custom Emoji IDs
ID_ADD = "6033108614724456536"
ID_USERS = "6025871229758476400"
ID_RECEIPT = "5197269100878907942"
ID_MANAGE = "5197269100878907942"
ID_COPY = "5472308992514464048"
ID_LINK = "5282843764451195532"
ID_ADMIN = "5467406098367521267"
ID_BACK = "5253997076169115797"
ID_TRASH = "5372825386591732174"
ID_TOGGLE = "6066348702363031988"
ID_TICK = "5895458739703517004"
ID_CROSS = "5852812849780362931"
ID_WITHDRAW = "5409048419211682843"
ID_TOPUSERS = "6235445786759402354"
ID_SUPPORT = "5215263059639017128"
ID_STAR = "5424818078833715060"
ID_GLOBE = "5224450179368767019"
EmojiStats = "5231200819986047254"
EmojiBroadcast = "6104927893912030655"
EmojiMobile = "6026092115631543342"
EmojiGift = "5424818078833715060"
ID_USER = "6025871229758476400"
ID_CHNL = "5271604874419647061"
ID_USD = "6206155797722830770"
ID_PTICK = "5208540237524911208"

Top10Medals = [
    '<tg-emoji emoji-id="5778325047282241647">1️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778507987119247519">2️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778355910917231510">3️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778496953348264834">4️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778429230303941569">5️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778634662884676303">6️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778650382464979758">7️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778572626377052504">8️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778317599808950144">9️⃣</tg-emoji>',
    '<tg-emoji emoji-id="5778325047282241647">1️⃣</tg-emoji><tg-emoji emoji-id="5778597459877957448">0️⃣</tg-emoji>',
]

DigitEmojiIDs = [
    "5778597459877957448", "5778325047282241647", "5778507987119247519",
    "5778355910917231510", "5778496953348264834", "5778429230303941569",
    "5778634662884676303", "5778650382464979758", "5778572626377052504",
    "5778317599808950144"
]

serviceIconMap = {
    "telegram": "5330237710655306682",
    "whatsapp": "5334998226636390258",
}

def ce(id_str: str, fallback: str) -> str:
    if not UseCustomEmoji or not id_str:
        return fallback
    return f'<tg-emoji emoji-id="{id_str}">{fallback}</tg-emoji>'

E_MAP = {
    "{E_CROWN}": ce("6237864166879663987", "👑"),
    "{E_ADMIN}": ce("6237864166879663987", "👑"),
    "{E_LIVE}": ce("6235628846855492222", "🔥"),
    "{E_GEAR}": ce("5424818078833715060", "⚙️"),
    "{E_TICK}": ce("5895458739703517004", "✅"),
    "{E_CROSS}": ce("5852812849780362931", "❌"),
    "{E_MOBILE}": ce("6026092115631543342", "📲"),
    "{E_WARN}": ce("5213205860498549992", "⚠️"),
    "{E_USERS}": ce("5453957997418004470", "👥"),
    "{E_GIFT}": ce("5424818078833715060", "🎁"),
    "{E_NUM}": ce("5424818078833715060", "🔢"),
    "{E_PLAY}": ce("5424818078833715060", "▶️"),
    "{E_VIBE}": ce("5424818078833715060", "📳"),
    "{E_RECEIPT}": ce("5424818078833715060", "🧾"),
    "{E_MONEY}": ce("6235459831302460476", "💰"),
    "{E_HEART}": ce("6023924329673135034", "❤️"),
    "{E_MEGA}": ce("5197304993920616826", "📢"),
    "{E_DOWN}": ce("5463123191339715467", "⬇"),
    "{E_DEVIL}": ce("6246543346597104368", "😈"),
    "{E_SAD}": ce("6325636659706594831", "😢"),
    "{E_STAR}": ce("5424818078833715060", "🌟"),
    "{E_BL}": ce("6235459831302460476", "🌟"),
    "{E_DATA}": ce("5447410659077661506", "🌟"),
    "{E_SMS}": ce("5443038326535759644", "🌟"),
    "{E_MINT}": ce("5778379627726640492", "🌟"),
    "{E_JAZZ}": ce("5798631291880477829", "🌟"),
    "{E_M}": ce("5343706594951569383", "🌟"),
    "{E_B}": ce("5343844407567198128", "🌟"),
    "{E_STATS}": ce("5231200819986047254", "🌟"),
    "{E_PKG}": ce("5424818078833715060", "📦"),
    "{E_L1}": ce("5971972727383264364", "🔸"),
    "{E_L2}": ce("5971816626796892111", "🔹"),
    "{E_L3}": ce("5350337715218949216", "🔸"),
    "{E_L4}": ce("5229229911033530793", "🔹"),
    "{E_OK}": ce("6023773095284707791", "👌"),
    "{E_DASH}": ce("6298356878573307709", "➖"),
    "{E_OTP}": ce("6298717844804733009", "🔑"),
    "{E_CHANNEL}": ce("5282843764451195532", "🔗"),
    "{E_A1}": ce("5458701355004735404", "🔹"),
    "{E_M1}": ce("5972124077735807885", "🔹"),
    "{E_LOAD1}": ce("5971972727383264364", "🔸"),
    "{E_LOAD2}": ce("5971816626796892111", "🔹"),
    "{E_LOAD3}": ce("5350337715218949216", "🔸"),
    "{E_LOAD4}": ce("5229229911033530793", "🔹"),
    "{E_PSTORE}": ce("5373130604147654226", "🔹"),
    "{E_CHROME}": ce("5359758030198031389", "🔹"),
    "{E_LOADING}": ce("5211052376781241550", "🔹"),
    "{E_PTICK1}": ce("5208540237524911208", "🔹"),
    "{E_FLY}": ce("5211129162206560202", "🔹"),
    "{E_PTICK2}": ce("5278628026416909103", "🔹"),
    "{E_DOWN1}": ce("6203886371363364022", "🔹"),
    "{E_EYE}": ce("6206366384264320881", "🔹"),
    "{E_BAN}": ce("6206396878532121864", "🔹"),
    "{E_IQ}": ce("6203722870548338074", "🔹"),
    "{E_REDWARN}": ce("6206174450765796040", "🔹"),
    "{E_BELL}": ce("6206508629286196237", "🔹"),
    "{E_HUNDRED}": ce("6203738495639360972", "🔹"),
    "{E_TOP}": ce("6206090539989734881", "🔹"),
    "{E_DOLLAR}": ce("6206155797722830770", "🔹"),
    "{E_LINK}": ce("6206497372176913599", "🔹"),
    "{E_TAJ}": ce("6206096153511990389", "🔹"),
    "{E_LOADER}": ce("6206118633370818254", "🔹"),
    "{E_FREE}": ce("6203750195130274981", "🔹"),
    "{E_HIGH}": ce("6206445639295834047", "🔹"),
    "{E_Q}": ce("6206003549722122915", "🔹"),
    "{E_FIREHEART}": ce("6206041890895172990", "🔹"),
    "{E_DIAMOND}": ce("6206220960966646470", "🔹"),
    "{E_RIGHT1}": ce("6206325217002788818", "🔹"),
    "{E_TGEARN}": ce("6206471194351245524", "🔹"),
    "{E_ONLINE}": ce("6269377265348383859", "🔹"),
    "{E_TICK2}": ce("6269073697059901810", "🔹"),
    "{E_TICK3}": ce("6269243378332864932", "🔹"),
    "{E_LEFT}": ce("5332348837405145999", "🔹"),
    "{E_DOWN2}": ce("6271512469684883558", "🔹"),
    "{E_CROSS2}": ce("6271611232457855630", "🔹"),
    "{E_NEWPACK}": ce("5386340832628462681", "🔹"),
    "{E_RIGHT}": ce("5332684922891025384", "🔹"),
    "{E_CARD}": ce("6305298855688672996", "🔹"),
}

countryFlags = {
    "australia": "5382062173323276195", "austria": "5409096965227031137", "azerbaijan": "5224254431939275524",
    "aland": "5467839726855666731", "albania": "5442808872202942144", "algeria": "5269400778807720624",
    "american_samoa": "5233381108594260837", "anguilla": "5454237677098384174", "angola": "5221978936791017415",
    "andorra": "5229127072336589200", "antarctica": "5222477234601732139", "antigua": "5233687283927892876",
    "argentina": "5262873863036872166", "armenia": "5411455658186778270", "aruba": "5231044964212817289",
    "chagos": "5454408067040952538", "afghanistan": "5341723801824541640", "bahamas": "5429268893313017179",
    "bangladesh": "5222131025877936317", "barbados": "5222119223307807441", "bahrain": "5229186179676517309",
    "belarus": "5382219601054544127", "belize": "5231366665853224722", "belgium": "5411564862025244994",
    "benin": "5429270924832548299", "bermuda": "5454179609140544421", "bulgaria": "5408875181705799521",
    "bolivia": "5357272214796255046", "bonaire": "5233482856369504645", "bosnia": "5382033281078275575",
    "botswana": "5422594827667653377", "brazil": "5202074005346983800", "brunei": "5467415349727083629",
    "burkina": "5474323070183285988", "burkina_faso": "5474323070183285988", "burundi": "5357542359649237058", "bhutan": "5420163176098446088",
    "vanuatu": "5469952197930267656", "vatican": "5443067545198277083", "uk": "5202196682497859879",
    "england": "5229192892710402006", "scotland": "5226852401822057871", "wales": "5228957348113955582",
    "hungary": "5409065547541260699", "venezuela": "5228751795274136090", "virgin_uk": "5453884806880315764",
    "virgin_us": "5231484597065237155", "timor": "5422602597263489621", "vietnam": "5474542319673812606",
    "gabon": "5408983586680350780", "haiti": "5357490485034236365", "guyana": "5420413662886117194",
    "gambia": "5420472705801536529", "ghana": "5188676065320511388", "guadeloupe": "5467664243081886165",
    "guatemala": "5357434603214748263", "guinea": "5408977500711691863", "guinea_bissau": "5429574437286454077",
    "germany": "5409360418520967565", "guernsey": "5229073617173624053", "gibraltar": "5226496954623603888",
    "honduras": "5224205572391315540", "hong_kong": "5222395857856374392", "grenada": "5467787680441976258",
    "greenland": "5221969376193816323", "greece": "5381889099026149370", "georgia": "5440371950708864925",
    "guam": "5233385291892407085", "denmark": "5381854399985366436", "jersey": "5229188988585130961",
    "djibouti": "5458586718032634511", "dominica": "5231486851923069595", "dominican": "5427236235615683748",
    "eu": "5228784522924930237", "egypt": "5226476858471626962", "zambia": "5339279432857171449",
    "sahara": "5431541386279135269", "zimbabwe": "5357255314099943456", "israel": "5332299462461107995",
    "india": "5447419223242449630", "indonesia": "5291937150814661333", "jordan": "5460834231468959552",
    "iraq": "5229059314932528805", "iran": "5271878966347601947", "ireland": "5411194670204069594",
    "iceland": "5226903563472483349", "spain": "5201957744877248121", "italy": "5449723275628259037",
    "yemen": "5408878892557542535", "cape_verde": "5233184244473283152", "kazakhstan": "5228718354658769982",
    "cambodia": "5357374413543062283", "cameroon": "5474681124426884947", "canada": "5382084502858249131",
    "canary": "5233582259092601024", "qatar": "5228799250367788944", "kenya": "5269725950781699509",
    "cyprus": "5228997115216149309", "kyrgyzstan": "5427268877367130483", "kiribati": "5231365287168721267",
    "china": "5431782733376399004", "north_korea": "5341271404329317987", "cocos": "5467863456549978285",
    "colombia": "5341564321098907092", "comoros": "5422342777511886475", "congo_brazza": "5422479718249151727",
    "congo_kin": "5269407491841603689", "kosovo": "5442767700646442025", "costa_rica": "5269494559418629149",
    "ivory_coast": "5411283953984218884", "cuba": "5357035553508308603", "kuwait": "5429154466794317724",
    "curacao": "5233622988267472134", "laos": "5426971433702012873", "latvia": "5269650286342846979",
    "lesotho": "5422515422312281871", "liberia": "5422520224085720580", "lebanon": "5427118703835625983",
    "libya": "5222284437814783192", "lithuania": "5411197345968695511", "liechtenstein": "5226703795953612903",
    "luxembourg": "5411158944666101440", "mauritius": "5269757084999628216", "mauritania": "5422465115360345921",
    "madagascar": "5429165814097913547", "mayotte": "5467780911573514412", "macau": "5420505321783179067",
    "malawi": "5341341330691863561", "malaysia": "5339498171246588311", "mali": "5411259459785730007",
    "maldives": "5233344051616430964", "malta": "5226954282741283529", "morocco": "5260720207520867861",
    "martinique": "5470045239806802915", "marshall": "5469803287119150148", "mexico": "5382126374494417411",
    "micronesia": "5231007765501067757", "mozambique": "5429106139822303027", "moldova": "5442607966517736672",
    "monaco": "5289959262540277451", "mongolia": "5420481703758019034", "montserrat": "5454038304716504375",
    "myanmar": "5188162778073935826", "namibia": "5420229786746239476", "nauru": "5233464284930915439",
    "nepal": "5413521039239955481", "niger": "5339240099546673885", "nigeria": "5411568100430587798",
    "netherlands": "5411124743841524806", "nicaragua": "5426842228200847679", "niue": "5454251094576218954",
    "new_zealand": "5269712902671055050", "new_caledonia": "5233223766762338378", "norway": "5382300771641470186",
    "isle_of_man": "5226538255029121667", "norfolk": "5233192645429312298", "christmas": "5467797026290809748",
    "st_helena": "5454076894997659542", "pitcairn": "5454181382962036548", "turks": "5454045923988488117",
    "uae": "5449495646656537594", "oman": "5269663308683688305", "cayman": "5454177075109839093",
    "cook": "5454192094610473874", "pakistan": "5269660289321679111", "palau": "5222244507503833341",
    "palestine": "5449405314904369668", "panama": "5269271835299560112", "papua": "5426911591922678926",
    "paraguay": "5426992955783134297", "peru": "5409100220812239915", "poland": "5291847690940852675",
    "portugal": "5382075788369605892", "puerto_rico": "5269767070798592290", "south_korea": "5456531898304047227",
    "reunion": "5420322107068267129", "russia": "5449408995691341691", "rwanda": "5359528550095402400",
    "romania": "5411159898148840778", "salvador": "5427301849831061043", "samoa": "5233271161726450295",
    "san_marino": "5228954998766843234", "sao_tome": "5429484951642842713", "saudi": "5202079966761590204",
    "macedonia": "5442634591020003500", "mariana": "5230969196694748793", "seychelles": "5231446105568329752",
    "st_bart": "5233616700435348314", "st_pierre": "5231258308123313128", "senegal": "5474274146210817219",
    "st_vincent": "5467396563540131322", "st_kitts": "5231087492978982103", "st_lucia": "5222280134257551597",
    "serbia": "5384313376136507326", "singapore": "5292144120993686909", "st_martin": "5461113820955027461",
    "syria": "5308002793812955097", "slovakia": "5381967160056755878", "slovenia": "5440874620796284751",
    "usa": "5202021044105257611", "solomon": "5233325407163398971", "somalia": "5474375863921288686",
    "sudan": "5431435781623260953", "suriname": "5467524222853071645", "sierra_leone": "5411093944631044380",
    "tajikistan": "5427304285077516492", "thailand": "5341471408071390957", "taiwan": "5222365101595568847",
    "tanzania": "5269360178481872158", "togo": "5426845148778609404", "tokelau": "5231066898610798438",
    "tonga": "5467490150877508877", "trinidad": "5420380776321533161", "tuvalu": "5454304115947487098",
    "tunisia": "5357130455105679545", "turkmenistan": "5422512652058379683", "turkey": "5226948110873278599",
    "uganda": "5267090670518025063", "uzbekistan": "5449829434334912605", "ukraine": "5447309366568953338",
    "wallis": "5231000034559934302", "uruguay": "5269256068474616775", "faroe": "5228851794997688064",
    "fiji": "5454336104863908516", "philippines": "5460873607729129032", "finland": "5382151560182642075",
    "falkland": "5454214681843481342", "france": "5202132623060640759", "french_guiana": "5233523014313720667",
    "polynesia": "5467450310760874001", "terres_aust": "5233379493686558144", "croatia": "5262677003210860950",
    "central_af": "5422628135139031178", "chad": "5411229867461060921", "montenegro": "5440827745523216914",
    "czech": "5429496861587156146", "chile": "5222427035023977899", "switzerland": "5442703336266543270",
    "sweden": "5384542551296455687", "sri_lanka": "5341732791191091574", "ecuador": "5359624993586034294",
    "equatorial": "5447111931217324976", "eritrea": "5420548035232937623", "eswatini": "5422587427438998925",
    "estonia": "5411174505332615466", "ethiopia": "5269679685393989166", "south_georgia": "5454396500694024535",
    "south_africa": "5341547124049852736", "south_sudan": "5458535642281552190", "jamaica": "5420144630429667484",
    "japan": "5456261908069885892", "japanese_flag": "5413869111979556783", "default": "5224450179368767019",
}

# ── Dynamic Custom Emojis RAM Cache ──────────────────────────────────────────
ram_custom_emojis = {"countries": {}, "services": {}}
ram_custom_emojis_lock = threading.RLock()

# ── Dynamic Regex OTP Extractor ──────────────────────────────────────────────
otpKeywordRegex = re.compile(r'(?i)(?:code|otp|pin|is|verification|código|kod)[:\s#]*([A-Za-z]?-?[0-9]{1,4}[-\s][0-9]{2,6}|[A-Za-z]?-?[0-9]{3,8})\b')
otpHyphenRegex = re.compile(r'\b([0-9]{1,4}[-\s][0-9]{2,6})\b')
otpDigitsRegex = re.compile(r'\b([0-9]{3,8})\b')

def extractOTPS(msg: str) -> str:
    msg = msg.strip() if msg else ""
    if not msg:
        return "000000"

    m1 = otpKeywordRegex.search(msg)
    if m1 and m1.group(1):
        return m1.group(1).strip()

    m2 = otpHyphenRegex.search(msg)
    if m2 and m2.group(1):
        return m2.group(1).strip()

    m3 = otpDigitsRegex.search(msg)
    if m3 and m3.group(1):
        return m3.group(1).strip()

    return "000000"

# ── Fast In-Memory Engine Caches ─────────────────────────────────────────────
ram_numbers = {}          # filename -> list of numbers
ram_numbers_lock = threading.RLock()

ram_used_numbers = {}     # "phone:service" -> bool
ram_used_numbers_lock = threading.RLock()

ram_user_locks = {}       # phone -> {"user_id": int, "country_file": str, "locked_at": datetime}
ram_user_locks_lock = threading.RLock()

ram_processed_otps = {}   # sms_hash -> bool
ram_processed_otps_lock = threading.RLock()

ram_withdraw_tracker = {} # req_id -> list of {"chat_id": int, "message_id": int, "is_admin": bool, "base_text": str}
ram_withdraw_tracker_lock = threading.RLock()

ram_processed_withdrawals = {} # req_id -> status ("approved" or "declined")
ram_processed_withdrawals_lock = threading.RLock()

user_state = {}           # user_id -> state
withdraw_amounts = {}     # user_id -> float
state_lock = threading.RLock()

user_without_cc = {}      # user_id -> bool
user_without_cc_lock = threading.RLock()

config_lock = threading.RLock()
api_initial_hit_done = {}
system_online_alerted = False
tracking_lock = threading.RLock()

sqlite_conn = None
sqlite_lock = threading.Lock()

mongo_client = None
users_collection = None
stats_collection = None
admin_records_collection = None

def init_storage():
    global sqlite_conn, mongo_client, users_collection, stats_collection, admin_records_collection
    global AdminIDs, API_Bases

    os.makedirs(FilesDir, exist_ok=True)

    # SQLite Setup (locks.db) with WAL Mode
    sqlite_conn = sqlite3.connect("./locks.db", check_same_thread=False)
    sqlite_conn.execute("PRAGMA journal_mode=WAL;")
    sqlite_conn.execute("PRAGMA busy_timeout=5000;")
    with sqlite_lock:
        sqlite_conn.execute("""CREATE TABLE IF NOT EXISTS user_locks (
            user_id INTEGER NOT NULL,
            phone_number TEXT NOT NULL,
            country_file TEXT NOT NULL,
            locked_at TIMESTAMP,
            PRIMARY KEY(user_id, phone_number)
        );""")
        sqlite_conn.execute("""CREATE TABLE IF NOT EXISTS used_numbers (
            phone_number TEXT NOT NULL,
            service TEXT NOT NULL DEFAULT '',
            used_at TIMESTAMP,
            PRIMARY KEY(phone_number, service)
        );""")
        sqlite_conn.execute("""CREATE TABLE IF NOT EXISTS user_number_messages (
            user_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL
        );""")
        sqlite_conn.execute("""CREATE TABLE IF NOT EXISTS processed_otps (
            sms_hash TEXT PRIMARY KEY,
            created_at TIMESTAMP
        );""")
        sqlite_conn.execute("""CREATE TABLE IF NOT EXISTS withdraw_tracker (
            req_id TEXT,
            chat_id INTEGER,
            message_id INTEGER,
            is_admin INTEGER,
            base_text TEXT,
            PRIMARY KEY(req_id, chat_id, message_id)
        );""")
        sqlite_conn.execute("""CREATE TABLE IF NOT EXISTS processed_withdrawals (
            req_id TEXT PRIMARY KEY,
            status TEXT,
            processed_at TIMESTAMP
        );""")
        sqlite_conn.execute("DELETE FROM user_locks;")
        sqlite_conn.execute("DELETE FROM user_number_messages;")
        sqlite_conn.commit()

    logger.info("Cleared old locks and message references in SQLite.")

    # MongoDB Setup
    try:
        mongo_client = MongoClient(MongoURI, serverSelectionTimeoutMS=8000)
        db = mongo_client[DBName]
        users_collection = db["users"]
        stats_collection = db["stats"]
        admin_records_collection = db["admin_records"]

        cfg = stats_collection.find_one({"id": "config"})
        if cfg:
            with config_lock:
                if "admin_ids" in cfg and isinstance(cfg["admin_ids"], list):
                    AdminIDs = [int(x) for x in cfg["admin_ids"]]
                if "api_bases" in cfg and isinstance(cfg["api_bases"], list):
                    API_Bases = [str(x) for x in cfg["api_bases"]]
            with ram_custom_emojis_lock:
                if "custom_emojis" in cfg and isinstance(cfg["custom_emojis"], dict):
                    ram_custom_emojis["countries"] = dict(cfg["custom_emojis"].get("countries", {}))
                    ram_custom_emojis["services"] = dict(cfg["custom_emojis"].get("services", {}))
        else:
            sync_config_to_db()
        logger.info(f"Connected to MongoDB '{DBName}' successfully.")
    except Exception as e:
        logger.error(f"MongoDB initialization error: {e}")

    init_ram_cache()

def sync_config_to_db():
    if stats_collection is None:
        return
    try:
        with config_lock:
            stats_collection.update_one(
                {"id": "config"},
                {"$set": {"admin_ids": AdminIDs, "api_bases": API_Bases}},
                upsert=True
            )
    except Exception as e:
        logger.error(f"Error syncing config to MongoDB: {e}")

def init_ram_cache():
    logger.info("[RAM ENGINE] Loading files, used numbers, OTP hashes & withdraw tracker...")
    try:
        if os.path.exists(FilesDir):
            for fname in os.listdir(FilesDir):
                if fname.endswith(".txt") and not os.path.isdir(os.path.join(FilesDir, fname)):
                    with open(os.path.join(FilesDir, fname), "r", encoding="utf-8", errors="ignore") as f:
                        lines = [line.strip() for line in f if line.strip()]
                    with ram_numbers_lock:
                        ram_numbers[fname] = lines
    except Exception as e:
        logger.error(f"RAM Cache file load error: {e}")

    with sqlite_lock:
        cursor = sqlite_conn.execute("SELECT phone_number, service FROM used_numbers")
        with ram_used_numbers_lock:
            for p, s in cursor.fetchall():
                ram_used_numbers[f"{p}:{s}"] = True
                ram_used_numbers[p] = True

        cursor2 = sqlite_conn.execute("SELECT sms_hash FROM processed_otps")
        with ram_processed_otps_lock:
            for (h,) in cursor2.fetchall():
                ram_processed_otps[h] = True

        cursor3 = sqlite_conn.execute("SELECT req_id, status FROM processed_withdrawals")
        with ram_processed_withdrawals_lock:
            for r_id, st in cursor3.fetchall():
                ram_processed_withdrawals[r_id] = st

        cursor4 = sqlite_conn.execute("SELECT req_id, chat_id, message_id, is_admin, base_text FROM withdraw_tracker")
        with ram_withdraw_tracker_lock:
            for r_id, cid, mid, is_adm, btxt in cursor4.fetchall():
                if r_id not in ram_withdraw_tracker:
                    ram_withdraw_tracker[r_id] = []
                ram_withdraw_tracker[r_id].append({
                    "chat_id": cid,
                    "message_id": mid,
                    "is_admin": bool(is_adm),
                    "base_text": btxt
                })

    logger.info("[RAM ENGINE] Cache ready with instant execution mode.")

def txt(format_str: str, *args) -> str:
    res = format_str % args if args else format_str
    for k, v in E_MAP.items():
        res = res.replace(k, v)
    return res

def clean_country_name(raw: str) -> str:
    normalized = raw.replace("-", " ").replace("_", " ")
    fields = normalized.split()
    if not fields:
        return "Unknown"
    first = ""
    for char in fields[0]:
        if ('a' <= char <= 'z') or ('A' <= char <= 'Z'):
            first += char
        else:
            break
    first_lower = first.lower()
    if not first_lower:
        return "Unknown"

    code_map = {
        "pk": "Pakistan",
        "in": "India",
        "us": "Usa",
        "uk": "Uk",
        "bd": "Bangladesh",
        "ru": "Russia",
        "ae": "Uae",
    }
    return code_map.get(first_lower, first.capitalize())

def get_flag_id(country: str) -> str:
    c = country.lower()
    c = re.sub(r'[\d\-]', '', c).strip()
    with ram_custom_emojis_lock:
        if c in ram_custom_emojis["countries"]:
            return ram_custom_emojis["countries"][c]
    return countryFlags.get(c, countryFlags.get("default", "5224450179368767019"))

def isAdmin(user_id: int) -> bool:
    with config_lock:
        return user_id in AdminIDs

def mask_phone_number(phone: str) -> str:
    clean = phone.strip().lstrip("+")
    if len(clean) < 7:
        return clean
    prefix = ""
    try:
        obj = phonenumbers.parse("+" + clean, "")
        if obj.country_code:
            prefix = str(obj.country_code)
    except Exception:
        pass
    if not prefix or len(prefix) >= len(clean) - 4:
        prefix = clean[:2]
    suffix = clean[-4:]
    return f"{prefix}{{E_L1}}{suffix}"

def mask_account(text: str) -> str:
    digits = [i for i, ch in enumerate(text) if ch.isdigit()]
    if len(digits) >= 10:
        mask_start = max(0, len(digits) - 6)
        mask_end = min(len(digits), mask_start + 4)
        chars = list(text)
        for idx in range(mask_start, mask_end):
            chars[digits[idx]] = '*'
        return "".join(chars)
    return text

def format_price(price_pkr: float, currency: str) -> str:
    if currency == "usd":
        return f"{price_pkr / FixedUSDRate:.4f} $"
    return f"{price_pkr:.2f} {CurrencySymbol}"

def format_balance(bal_pkr: float, currency: str) -> str:
    if currency == "usd":
        return f"{bal_pkr / FixedUSDRate:.4f} $"
    return f"{bal_pkr:.2f} {CurrencySymbol}"

def get_country_code_and_national(phone: str):
    clean = phone.strip().lstrip("+")
    try:
        num_obj = phonenumbers.parse("+" + clean, "")
        if num_obj.country_code:
            cc = str(num_obj.country_code)
            national = clean[len(cc):]
            return cc, national
    except Exception:
        pass
    if len(clean) > 3:
        return clean[:2], clean[2:]
    return "", clean

def extract_phone_prefix(phone: str) -> str:
    clean = phone.strip().lstrip("+")
    cc, national = get_country_code_and_national(clean)
    if cc and len(national) >= 3:
        return cc + national[:3]
    if cc and len(national) > 0:
        return cc + national
    if len(clean) >= 5:
        return clean[:5]
    return clean

def validate_pakistani_number(input_str: str) -> bool:
    cleaned = re.sub(r'\D', '', input_str)
    length = len(cleaned)
    if length == 11 and cleaned.startswith("03"):
        return True
    if length == 10 and cleaned.startswith("3"):
        return True
    if length == 12 and cleaned.startswith("923"):
        return True
    return False

def get_medal_for_rank(rank: int) -> str:
    if 1 <= rank <= len(Top10Medals):
        return Top10Medals[rank - 1]
    rank_str = str(rank)
    medal = ""
    for ch in rank_str:
        if ch.isdigit():
            idx = int(ch)
            medal += f'<tg-emoji emoji-id="{DigitEmojiIDs[idx]}">{ch}⃣</tg-emoji>'
    return medal

def get_weekly_start_of_week(dt: datetime.datetime) -> datetime.datetime:
    weekday = dt.isoweekday()
    monday = dt - datetime.timedelta(days=weekday - 1)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)

def get_user_currency(u: dict) -> str:
    wd = u.get("wd_account", {})
    if wd.get("is_set") and wd.get("currency"):
        return wd["currency"]
    if u.get("currency"):
        return u["currency"]
    return "pkr"

def get_global_stats() -> dict:
    if stats_collection is None:
        return {}
    res = stats_collection.find_one({"id": "global_records"})
    if not res:
        res = {
            "id": "global_records",
            "total_otps_received": 0,
            "today_otps_received": 0,
            "last_otp_date": datetime.datetime.now(),
            "total_earnings": 0.0,
            "total_withdrawn": 0.0
        }
        stats_collection.insert_one(res)
    return res

def update_global_stats(stats: dict):
    if stats_collection is None:
        return
    def _run():
        try:
            stats_collection.update_one({"id": "global_records"}, {"$set": stats}, upsert=True)
        except Exception as e:
            logger.error(f"Global stats update error: {e}")
    threading.Thread(target=_run, daemon=True).start()

def get_or_create_user(from_user, referrer_id: int = 0) -> dict:
    now = datetime.datetime.now()
    user_id = from_user.get("id")
    username = from_user.get("username", "")
    first_name = from_user.get("first_name", "")

    if users_collection is None:
        return {"id": user_id, "first_name": first_name, "username": username, "balance": 0.0}

    u = users_collection.find_one({"id": user_id})
    if not u:
        final_ref = referrer_id if (referrer_id > 0 and referrer_id != user_id) else 0
        u = {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "balance": 0.0,
            "total_spent": 0.0,
            "total_earned": 0.0,
            "total_withdrawn": 0.0,
            "total_otps": 0,
            "today_otps": 0,
            "weekly_otps": 0,
            "last_weekly_reset": now,
            "last_otp_date": now,
            "joined_at": now,
            "last_active": now,
            "referred_by": final_ref,
            "referral_earnings_earned": 0.0,
            "api_earnings": {},
            "api_total_otps": {},
            "api_cycle_otps": {},
            "api_cycle_earnings": {},
            "currency": "",
            "wd_account": {"is_set": False},
            "without_cc": False
        }
        users_collection.insert_one(u)
    else:
        update_doc = {"last_active": now}
        if username and u.get("username") != username:
            update_doc["username"] = username
        users_collection.update_one({"id": user_id}, {"$set": update_doc})

    with user_without_cc_lock:
        user_without_cc[user_id] = u.get("without_cc", False)
    return u

def extract_api_tag(api_url: str) -> str:
    parsed = urlparse(api_url.rstrip("/"))
    path_parts = [p for p in parsed.path.split("/") if p]
    if path_parts:
        return path_parts[-1]
    return "api"

def build_withdrawal_breakdown(u: dict) -> str:
    api_total = u.get("api_total_otps", {})
    api_cycle = u.get("api_cycle_otps", {})
    api_cycle_earn = u.get("api_cycle_earnings", {})

    all_keys = sorted(list(set(list(api_total.keys()) + list(api_cycle.keys()))))
    lines = []
    idx = 1

    for k in all_keys:
        tot = api_total.get(k, 0)
        if tot == 0:
            continue
        cyc = api_cycle.get(k, 0)
        earn = api_cycle_earn.get(k, 0.0)

        tag = k
        if "http" in k or "_" in k or "." in k:
            tag = extract_api_tag(k)
        elif k == "IVAS_WEBSOCKET" or k.lower() == "ivas":
            tag = "Ivas"

        line = f"{idx}:{tag.capitalize()} = ({cyc}/{tot}) {earn:.2f}{CurrencySymbol}"
        lines.append(line)
        idx += 1

    return "\n".join(lines) if lines else "• No active panel OTPs recorded."

session = requests.Session()

def send_raw_html(chat_id: int, text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{BotToken}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)

    for _ in range(3):
        try:
            resp = session.post(url, json=payload, timeout=12)
            data = resp.json()
            if data.get("ok"):
                return data
            desc = data.get("description", "").lower()
            if "blocked by the user" in desc or "user is deactivated" in desc:
                if chat_id > 0 and users_collection is not None:
                    users_collection.delete_one({"id": chat_id})
                return None
            if "too many requests" in desc or "retry after" in desc:
                match = re.search(r'retry after (\d+)', desc)
                wait_sec = int(match.group(1)) if match else 2
                time.sleep(wait_sec + 1)
                continue
            logger.error(f"Telegram Send Error: {desc}")
            break
        except Exception as e:
            logger.error(f"Telegram Request Exception: {e}")
            time.sleep(1)
    return None

def edit_raw_html(chat_id: int, message_id: int, text: str, reply_markup=None):
    url = f"https://api.telegram.org/bot{BotToken}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)

    for _ in range(3):
        try:
            resp = session.post(url, json=payload, timeout=12)
            data = resp.json()
            if data.get("ok"):
                return data
            desc = data.get("description", "").lower()
            if "too many requests" in desc:
                time.sleep(2)
                continue
            break
        except Exception:
            time.sleep(1)
    return None

def send_copy_message(target_chat_id: int, from_chat_id: int, message_id: int, reply_markup=None):
    url = f"https://api.telegram.org/bot{BotToken}/copyMessage"
    payload = {
        "chat_id": target_chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    }
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        resp = session.post(url, json=payload, timeout=10)
        return resp.json().get("ok", False)
    except Exception:
        return False

def send_telegram_document(chat_id: int, file_bytes: bytes, file_name: str, caption: str = ""):
    url = f"https://api.telegram.org/bot{BotToken}/sendDocument"
    data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    files = {"document": (file_name, file_bytes, "application/zip")}
    try:
        resp = session.post(url, data=data, files=files, timeout=60)
        return resp.json()
    except Exception as e:
        logger.error(f"Send Document Error: {e}")
        return None

group_otp_queue = Queue(maxsize=1500)

def queue_group_message(chat_id: int, text: str, reply_markup=None):
    try:
        group_otp_queue.put_nowait({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
    except Exception:
        logger.warning("Group OTP queue is full! Dropping item.")

def start_group_queue_worker():
    def _worker():
        logger.info("[GROUP QUEUE] OTP Group Rate-Limiter Worker Activated.")
        while True:
            item = group_otp_queue.get()
            try:
                send_raw_html(item["chat_id"], item["text"], item["reply_markup"])
            except Exception as e:
                logger.error(f"Group Queue Worker Error: {e}")
            time.sleep(0.4)
    threading.Thread(target=_worker, daemon=True).start()

def get_service_icon(service: str) -> str:
    s_clean = service.strip().lower()
    with ram_custom_emojis_lock:
        if s_clean in ram_custom_emojis["services"]:
            return ram_custom_emojis["services"][s_clean]
    apps = get_active_apps()
    for app in apps:
        if app.get("name", "").strip().lower() == s_clean:
            return app.get("icon_id") or DefaultServiceIconID
    return serviceIconMap.get(s_clean, DefaultServiceIconID)

def send_otp_to_user(target_user_id: int, phone_num: str, service: str, country_file: str, otp_message: str, price: float):
    flag_id = get_flag_id(country_file.replace(".txt", ""))
    service_icon = get_service_icon(service)

    flag_emoji = ce(flag_id, "🏳")
    service_emoji = ce(service_icon, "📲")
    user_icon_emoji = ce(ID_USER, "👤")
    money_emoji = ce(ID_USD, "💵")

    price_display = f"{price:.2f}PKR"
    masked_phone = mask_phone_number(phone_num)
    user_mention = f'<a href="tg://user?id={target_user_id}">{target_user_id}</a>'

    base_text = txt(
        "<blockquote expandable>{E_A1} %s {E_M1} %s\n{E_A1} %s {E_M1} %s\n{E_A1} %s {E_M1} %s\n{E_A1} %s {E_M1} %s</blockquote>",
        user_icon_emoji, user_mention,
        flag_emoji, masked_phone,
        service_emoji, service,
        money_emoji, price_display
    )

    otp_code = extractOTPS(otp_message)
    kb_user = {
        "inline_keyboard": [[
            {"text": "Copy OTP Code", "copy_text": {"text": otp_code}, "icon_custom_emoji_id": ID_COPY, "style": "primary"}
        ]]
    }
    threading.Thread(target=send_raw_html, args=(target_user_id, base_text, kb_user), daemon=True).start()

def send_otp_to_groups(target_user_id: int, phone_num: str, service: str, country_file: str, otp_message: str, bot_link: str, price: float):
    flag_id = get_flag_id(country_file.replace(".txt", ""))
    service_icon = get_service_icon(service)

    flag_emoji = ce(flag_id, "🏳️")
    service_emoji = ce(service_icon, "📲")
    masked_phone = mask_phone_number(phone_num)

    base_text_group = txt("<blockquote expandable>{E_A1}%s{E_M1}%s{E_M1}%s</blockquote>",
                          flag_emoji, service_emoji, masked_phone)

    otp_code = extractOTPS(otp_message)
    kb_group = {
        "inline_keyboard": [
            [{"text": "Copy OTP Code", "copy_text": {"text": otp_code}, "icon_custom_emoji_id": ID_COPY, "style": "primary"}],
            [
                {"text": "Bot", "url": bot_link, "icon_custom_emoji_id": ID_LINK, "style": "success"},
                {"text": "Channel", "url": MainChannelLink, "icon_custom_emoji_id": ID_CHNL, "style": "danger"}
            ]
        ]
    }

    for g_id in OtpGroupIDs:
        if g_id:
            queue_group_message(g_id, base_text_group, kb_group)

def get_price_for_country(country_file: str) -> float:
    clean_file = country_file.replace(".txt", "")
    full_key = clean_file.strip().lower()
    panel_key = full_key.split("-")[0] if "-" in full_key else full_key
    base_country_key = clean_country_name(clean_file).strip().lower()

    if stats_collection is not None:
        try:
            res = stats_collection.find_one({"id": "config"})
            if res and "country_prices" in res and isinstance(res["country_prices"], dict):
                prices = res["country_prices"]
                if full_key in prices:
                    return float(prices[full_key])
                if panel_key in prices:
                    return float(prices[panel_key])
                if base_country_key in prices:
                    return float(prices[base_country_key])
            if res and "otp_price" in res:
                return float(res["otp_price"])
        except Exception:
            pass
    return 5.0

def get_min_withdraw_amount() -> float:
    if stats_collection is not None:
        try:
            cfg = stats_collection.find_one({"id": "config"})
            if cfg and "min_withdraw" in cfg:
                return float(cfg["min_withdraw"])
        except Exception:
            pass
    return MinWithdrawAmount

def get_withdraw_time_config():
    if stats_collection is not None:
        try:
            cfg = stats_collection.find_one({"id": "config"})
            if cfg:
                start = cfg.get("withdraw_start_hour", 17)
                end = cfg.get("withdraw_end_hour", 20)
                time_str = cfg.get("withdraw_time_str", "5PM 8PM")
                return int(start), int(end), str(time_str)
        except Exception:
            pass
    return 17, 20, "5PM 8PM"

def is_withdraw_time() -> bool:
    start, end, _ = get_withdraw_time_config()
    now_hour = datetime.datetime.now().hour
    if start <= end:
        return start <= now_hour < end
    return now_hour >= start or now_hour < end

def parse_time_token(token: str) -> int:
    token = token.strip().upper()
    m = re.match(r'^(\d{1,2})(?::\d{2})?\s*(AM|PM)?$', token)
    if not m:
        raise ValueError("Invalid time format")
    h = int(m.group(1))
    ampm = m.group(2)
    if ampm == "PM" and h < 12:
        h += 12
    elif ampm == "AM" and h == 12:
        h = 0
    return h

def parse_withdraw_time_input(input_str: str):
    parts = input_str.strip().split()
    if len(parts) != 2:
        raise ValueError("Enter two time values separated by space (e.g. 5PM 8PM)")
    start_h = parse_time_token(parts[0])
    end_h = parse_time_token(parts[1])
    display_str = f"{parts[0].upper()} {parts[1].upper()}"
    return start_h, end_h, display_str

def get_active_ranges() -> list:
    if stats_collection is not None:
        try:
            res = stats_collection.find_one({"id": "config"})
            if res and "active_ranges" in res:
                return list(res["active_ranges"])
        except Exception:
            pass
    return []

def add_active_range(range_name: str):
    if stats_collection is not None:
        stats_collection.update_one({"id": "config"}, {"$addToSet": {"active_ranges": range_name}}, upsert=True)

def remove_active_range(range_name: str):
    if stats_collection is not None:
        stats_collection.update_one({"id": "config"}, {"$pull": {"active_ranges": range_name}}, upsert=True)

def get_unpaid_services() -> list:
    if stats_collection is not None:
        try:
            res = stats_collection.find_one({"id": "config"})
            if res and "unpaid_services" in res:
                return list(res["unpaid_services"])
        except Exception:
            pass
    return []

def add_unpaid_service(service_name: str):
    if stats_collection is not None:
        stats_collection.update_one({"id": "config"}, {"$addToSet": {"unpaid_services": service_name}}, upsert=True)

def remove_unpaid_service(service_name: str):
    if stats_collection is not None:
        stats_collection.update_one({"id": "config"}, {"$pull": {"unpaid_services": service_name}}, upsert=True)

def get_active_apps() -> list:
    if stats_collection is not None:
        try:
            res = stats_collection.find_one({"id": "config"})
            if res and "active_apps" in res and isinstance(res["active_apps"], list):
                return res["active_apps"]
        except Exception:
            pass
    return []

def save_active_apps(apps: list):
    if stats_collection is not None:
        stats_collection.update_one({"id": "config"}, {"$set": {"active_apps": apps}}, upsert=True)

def add_app(app_info: dict):
    apps = get_active_apps()
    apps.append(app_info)
    save_active_apps(apps)

def delete_app_by_name(name: str):
    apps = get_active_apps()
    new_apps = [a for a in apps if a.get("name") != name]
    save_active_apps(new_apps)

def add_country_to_app(app_name: str, country: str):
    apps = get_active_apps()
    for a in apps:
        if a.get("name") == app_name:
            countries = a.get("countries", [])
            if country not in countries:
                countries.append(country)
                a["countries"] = countries
            break
    save_active_apps(apps)

def remove_country_from_app(app_name: str, country: str):
    apps = get_active_apps()
    for a in apps:
        if a.get("name") == app_name:
            a["countries"] = [c for c in a.get("countries", []) if c != country]
            break
    save_active_apps(apps)

def update_app(old_name: str, new_name: str, new_icon: str):
    apps = get_active_apps()
    for a in apps:
        if a.get("name") == old_name:
            a["name"] = new_name
            a["icon_id"] = new_icon if new_icon else DefaultAppIconID
            break
    save_active_apps(apps)

def get_custom_prices_list() -> list:
    out = []
    if stats_collection is not None:
        try:
            res = stats_collection.find_one({"id": "config"})
            if res and "country_prices" in res and isinstance(res["country_prices"], dict):
                for k, v in res["country_prices"].items():
                    out.append({"key": k, "price": float(v)})
        except Exception:
            pass
    return out

def delete_custom_price(country_key: str):
    if stats_collection is not None:
        path = f"country_prices.{country_key.strip().lower()}"
        stats_collection.update_one({"id": "config"}, {"$unset": {path: ""}})

def get_global_used_numbers() -> dict:
    with ram_used_numbers_lock:
        used = {}
        for k, v in ram_used_numbers.items():
            p_num = k.split(":")[0] if ":" in k else k
            used[p_num] = v
        return used

def get_service_used_numbers(service: str) -> dict:
    srv = service.strip().lower()
    with ram_used_numbers_lock:
        used = {}
        for k, v in ram_used_numbers.items():
            if k.endswith(":" + srv):
                used[k.split(":")[0]] = v
        return used

def get_valid_numbers_for_target(target: str, service_filter: str = "") -> list:
    clean_target = target.replace(".txt", "").strip().lower()
    base_target = clean_target.split("-")[0] if "-" in clean_target else clean_target

    global_used = get_global_used_numbers()
    service_used = get_service_used_numbers(service_filter) if service_filter else {}

    now = datetime.datetime.now()
    active_locks = set()
    with ram_user_locks_lock:
        for phone, info in ram_user_locks.items():
            if (now - info["locked_at"]).total_seconds() < 600:
                active_locks.add(phone)

    results = []
    with ram_numbers_lock:
        for file_name, lines in ram_numbers.items():
            if not file_name.endswith(".txt"):
                continue
            clean_file = file_name.replace(".txt", "").strip().lower()
            if clean_file == clean_target or clean_file == base_target or clean_file.startswith(base_target + "-"):
                for line in lines:
                    n = line.strip()
                    if not n:
                        continue
                    is_used = service_used.get(n, False) if service_filter else global_used.get(n, False)
                    if not is_used and n not in active_locks:
                        results.append({"phone": n, "file_name": file_name})
    return results

def enforce_user_lock_limit(user_id: int, new_count: int):
    now = datetime.datetime.now()
    user_active_locks = []
    with ram_user_locks_lock:
        for phone, info in list(ram_user_locks.items()):
            if info["user_id"] == user_id:
                if (now - info["locked_at"]).total_seconds() < 600:
                    user_active_locks.append((phone, info["locked_at"]))
                else:
                    del ram_user_locks[phone]

        user_active_locks.sort(key=lambda x: x[1])
        max_allowed = max(0, 10 - new_count)
        to_unlock = []
        if len(user_active_locks) > max_allowed:
            num_unlock = len(user_active_locks) - max_allowed
            for i in range(num_unlock):
                p = user_active_locks[i][0]
                to_unlock.append(p)
                if p in ram_user_locks:
                    del ram_user_locks[p]

    if to_unlock:
        def _delete_locks():
            with sqlite_lock:
                for p in to_unlock:
                    sqlite_conn.execute("DELETE FROM user_locks WHERE user_id = ? AND phone_number = ?", (user_id, p))
                sqlite_conn.commit()
        threading.Thread(target=_delete_locks, daemon=True).start()

def get_user_active_numbers(user_id: int) -> list:
    now = datetime.datetime.now()
    active = []
    with ram_user_locks_lock:
        for p, info in ram_user_locks.items():
            if info["user_id"] == user_id and (now - info["locked_at"]).total_seconds() < 600:
                active.append((p, info["locked_at"]))
    active.sort(key=lambda x: x[1])
    return [x[0] for x in active]

def is_duplicate_sms(phone_num: str, service: str, sms_text: str) -> bool:
    sms_hash = f"{phone_num.strip()}:{service.strip()}:{sms_text.strip()}"
    with ram_processed_otps_lock:
        if ram_processed_otps.get(sms_hash):
            return True
        ram_processed_otps[sms_hash] = True

    def _save():
        with sqlite_lock:
            sqlite_conn.execute("INSERT OR IGNORE INTO processed_otps (sms_hash, created_at) VALUES (?, ?)", (sms_hash, datetime.datetime.now()))
            sqlite_conn.commit()
    threading.Thread(target=_save, daemon=True).start()
    return False

def extract_all_ranges_from_zip_xlsx(file_data: bytes) -> dict:
    country_ranges_map = {}
    try:
        with zipfile.ZipFile(io.BytesIO(file_data)) as z:
            shared_strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                xml_data = z.read("xl/sharedStrings.xml")
                root = ET.fromstring(xml_data)
                for si in root.findall("{*}si"):
                    t = si.find("{*}t")
                    shared_strings.append(t.text if t is not None and t.text else "")

            sheet_files = [f for f in z.namelist() if f.startswith("xl/worksheets/sheet") and f.endswith(".xml")]

            for sf in sheet_files:
                sheet_xml = z.read(sf)
                s_root = ET.fromstring(sheet_xml)
                for row in s_root.findall(".//{*}row"):
                    raw_range = ""
                    raw_phone = ""
                    for cell in row.findall("{*}c"):
                        col_ref = cell.attrib.get("r", "")
                        cell_type = cell.attrib.get("t", "")
                        v_el = cell.find("{*}v")
                        val = v_el.text.strip() if (v_el is not None and v_el.text) else ""

                        if col_ref.startswith("A"):
                            if cell_type == "s" and val.isdigit():
                                idx = int(val)
                                if idx < len(shared_strings):
                                    raw_range = shared_strings[idx]
                            else:
                                raw_range = val
                        elif col_ref.startswith("B"):
                            raw_phone = val

                    if raw_phone:
                        if "e+" in raw_phone.lower():
                            try:
                                raw_phone = f"{float(raw_phone):.0f}"
                            except Exception:
                                pass
                        if "." in raw_phone:
                            raw_phone = raw_phone.split(".")[0]

                        digits = "".join(re.findall(r'\d+', raw_phone))
                        if 7 <= len(digits) <= 15:
                            base_c = clean_country_name(raw_range)
                            if not base_c or base_c == "Unknown":
                                try:
                                    n_obj = phonenumbers.parse("+" + digits, "")
                                    reg = phonenumbers.region_code_for_number(n_obj)
                                    base_c = clean_country_name(reg)
                                except Exception:
                                    pass

                            if base_c and base_c != "Unknown":
                                if base_c not in country_ranges_map:
                                    country_ranges_map[base_c] = {}
                                range_tag = raw_range or base_c
                                if range_tag not in country_ranges_map[base_c]:
                                    country_ranges_map[base_c][range_tag] = []
                                country_ranges_map[base_c][range_tag].append(digits)
    except Exception as e:
        logger.error(f"XLSX Extraction error: {e}")
    return country_ranges_map

def process_ivas_file_upload(file_data: bytes, orig_file_name: str, is_xlsx_or_zip: bool):
    report = {}
    total_saved = 0

    if is_xlsx_or_zip:
        ranges_map = extract_all_ranges_from_zip_xlsx(file_data)
        if not ranges_map:
            raise ValueError("No valid numbers or ranges extracted from uploaded archive.")

        for base_country, r_map in ranges_map.items():
            base_prefix = base_country + "0"
            if len(r_map) == 1:
                for nums in r_map.values():
                    fname = f"{base_prefix}.txt"
                    fpath = os.path.join(FilesDir, fname)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write("\n".join(nums))
                    with ram_numbers_lock:
                        ram_numbers[fname] = nums
                    report[fname] = len(nums)
                    total_saved += len(nums)
            else:
                sorted_keys = sorted(list(r_map.keys()))
                for idx, r_key in enumerate(sorted_keys):
                    nums = r_map[r_key]
                    if not nums:
                        continue
                    fname = f"{base_prefix}-{idx+1}.txt"
                    fpath = os.path.join(FilesDir, fname)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write("\n".join(nums))
                    with ram_numbers_lock:
                        ram_numbers[fname] = nums
                    report[fname] = len(nums)
                    total_saved += len(nums)
    else:
        c_name = clean_country_name(orig_file_name)
        fname = f"{c_name}0.txt"
        fpath = os.path.join(FilesDir, fname)
        lines = [line.strip() for line in file_data.decode("utf-8", errors="ignore").splitlines() if line.strip()]
        if not lines:
            raise ValueError("No phone numbers found in TXT file.")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        with ram_numbers_lock:
            ram_numbers[fname] = lines
        report[fname] = len(lines)
        total_saved = len(lines)

    return report, total_saved

def append_ivas_numbers_from_bytes(file_name: str, file_data: bytes, is_xlsx_or_zip: bool) -> int:
    fpath = os.path.join(FilesDir, file_name)
    existing = []
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            existing = [l.strip() for l in f if l.strip()]

    new_nums = []
    if is_xlsx_or_zip:
        r_map = extract_all_ranges_from_zip_xlsx(file_data)
        for _, ranges in r_map.items():
            for _, nums in ranges.items():
                new_nums.extend(nums)
    else:
        new_nums = [l.strip() for l in file_data.decode("utf-8", errors="ignore").splitlines() if l.strip()]

    combined = existing + new_nums
    unique_nums = list(dict.fromkeys(combined))

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(unique_nums))
    with ram_numbers_lock:
        ram_numbers[file_name] = unique_nums

    return len(unique_nums)

def get_ivas_grouped_countries():
    groups = {}
    global_used = get_global_used_numbers()

    with ram_numbers_lock:
        for name, lines in ram_numbers.items():
            if name.endswith(".txt") and "0" in name:
                count = sum(1 for n in lines if n and not global_used.get(n, False))
                raw_base = name.replace(".txt", "")
                c_name = clean_country_name(raw_base)

                if c_name not in groups:
                    groups[c_name] = {"CountryName": c_name, "TotalNums": 0, "FilesCount": 0}
                groups[c_name]["TotalNums"] += count
                groups[c_name]["FilesCount"] += 1

    res = [g for g in groups.values() if g["TotalNums"] > 0 or g["FilesCount"] > 0]
    res.sort(key=lambda x: x["CountryName"])
    return res

def get_ivas_country_ranges(target_country: str):
    ranges = []
    global_used = get_global_used_numbers()
    target_clean = clean_country_name(target_country).lower()

    with ram_numbers_lock:
        for name, lines in ram_numbers.items():
            if name.endswith(".txt") and "0" in name:
                raw_base = name.replace(".txt", "")
                c_name = clean_country_name(raw_base).lower()

                if c_name == target_clean:
                    count = sum(1 for n in lines if n and not global_used.get(n, False))
                    price = get_price_for_country(name)
                    ranges.append({
                        "FileName": name,
                        "RangeName": raw_base,
                        "Count": count,
                        "Price": price
                    })
    ranges.sort(key=lambda x: x["FileName"])
    return ranges

def process_ivas_sms(bot_username: str, sms_payload: dict):
    phone_num = str(sms_payload.get("recipient", "")).strip()
    service = str(sms_payload.get("originator", "")).strip() or "SMS Service"
    sms_text = str(sms_payload.get("message", "")).strip()
    sms_range = str(sms_payload.get("range", "")).strip()

    if not phone_num:
        return

    if is_duplicate_sms(phone_num, service, sms_text):
        return

    with ram_used_numbers_lock:
        ram_used_numbers[f"{phone_num}:{service}"] = True

    def _ins_used():
        with sqlite_lock:
            sqlite_conn.execute("INSERT OR IGNORE INTO used_numbers (phone_number, service, used_at) VALUES (?, ?, ?)",
                                (phone_num, service, datetime.datetime.now()))
            sqlite_conn.commit()
    threading.Thread(target=_ins_used, daemon=True).start()

    clean_phone = phone_num.lstrip("+")
    now = datetime.datetime.now()
    target_user_id = 0
    country_file = ""

    with ram_user_locks_lock:
        for p, info in ram_user_locks.items():
            if (p.lstrip("+") == clean_phone or p == phone_num) and (now - info["locked_at"]).total_seconds() <= 600:
                target_user_id = info["user_id"]
                country_file = info["country_file"]
                break

    if target_user_id == 0:
        cutoff = now - datetime.timedelta(seconds=600)
        with sqlite_lock:
            cursor = sqlite_conn.execute("""
                SELECT user_id, country_file FROM user_locks
                WHERE (phone_number = ? OR phone_number = ? OR phone_number = ?)
                  AND locked_at >= ?
                ORDER BY locked_at DESC LIMIT 1
            """, (phone_num, clean_phone, "+" + clean_phone, cutoff))
            row = cursor.fetchone()
            if row:
                target_user_id, country_file = row[0], row[1]

    if not country_file:
        country_file = f"{clean_country_name(sms_range)}0.txt"

    price = get_price_for_country(country_file)
    for unpaid in get_unpaid_services():
        if service.lower() == unpaid.lower():
            price = 0.0
            break

    bot_link = f"https://t.me/{bot_username}"

    if target_user_id > 0:
        send_otp_to_user(target_user_id, phone_num, service, country_file, sms_text, price)
        send_otp_to_groups(target_user_id, phone_num, service, country_file, sms_text, bot_link, price)

        if users_collection is not None:
            now_dt = datetime.datetime.now()
            now_str = now_dt.strftime("%Y-%m-%d")
            u = users_collection.find_one({"id": target_user_id}) or {}

            inc_fields = {
                "balance": price,
                "total_earned": price,
                "total_otps": 1,
                "api_earnings.IVAS_WEBSOCKET": price,
                "api_total_otps.IVAS_WEBSOCKET": 1,
                "api_cycle_otps.IVAS_WEBSOCKET": 1,
                "api_cycle_earnings.IVAS_WEBSOCKET": price,
            }
            set_fields = {"last_active": now_dt}

            last_otp_dt = u.get("last_otp_date")
            if not last_otp_dt or last_otp_dt.strftime("%Y-%m-%d") != now_str:
                set_fields["today_otps"] = 1
                set_fields["last_otp_date"] = now_dt
            else:
                inc_fields["today_otps"] = 1

            users_collection.update_one(
                {"id": target_user_id},
                {"$inc": inc_fields, "$set": set_fields}
            )

            ref_id = u.get("referred_by", 0)
            if ref_id > 0 and price > 0:
                ref_bonus = price * 0.10
                res_ref = users_collection.update_one(
                    {"id": ref_id},
                    {"$inc": {"balance": ref_bonus, "referral_earnings_earned": ref_bonus}}
                )
                if res_ref.modified_count > 0:
                    msg = txt("{E_GIFT} <b>Referral Profit!</b>\n\nReceived <b>+%.2f %s</b>.", ref_bonus, CurrencySymbol)
                    send_raw_html(ref_id, msg)

            g = get_global_stats()
            g["total_otps_received"] = g.get("total_otps_received", 0) + 1
            g["total_earnings"] = g.get("total_earnings", 0.0) + price
            last_g_dt = g.get("last_otp_date")
            if not last_g_dt or last_g_dt.strftime("%Y-%m-%d") != now_str:
                g["today_otps_received"] = 1
                g["last_otp_date"] = now_dt
            else:
                g["today_otps_received"] = g.get("today_otps_received", 0) + 1
            update_global_stats(g)
    else:
        send_otp_to_groups(0, phone_num, service, country_file, sms_text, bot_link, price)

def start_ivas_worker(bot_username: str):
    clean_url = IvasSocketURL.strip()
    if not clean_url or clean_url.lower() == "none" or websocket is None:
        logger.info("[IVAS] Background worker disabled (URL set to 'None').")
        return

    def _worker():
        while True:
            logger.info("[IVAS] Connecting to WebSocket...")
            try:
                ws = websocket.create_connection(IvasSocketURL, timeout=10, sslopt={"cert_reqs": 0})
                logger.info("[IVAS] Connected successfully!")
                ws.send("40/livesms,")

                def _heartbeat():
                    while True:
                        time.sleep(20)
                        try:
                            ws.send("3")
                        except Exception:
                            break
                threading.Thread(target=_heartbeat, daemon=True).start()

                while True:
                    msg = ws.recv()
                    if not msg:
                        break
                    if str(msg).startswith("42/livesms,"):
                        idx = msg.find("[")
                        if idx != -1:
                            try:
                                data = json.loads(msg[idx:])
                                if len(data) > 1:
                                    process_ivas_sms(bot_username, data[1])
                            except Exception as e:
                                logger.error(f"IVAS parse error: {e}")
            except Exception as e:
                logger.warning(f"[IVAS] Disconnected: {e}. Reconnecting in 5s...")
                time.sleep(5)

    threading.Thread(target=_worker, daemon=True).start()

def build_api_url(base: str, api_type: str) -> str:
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}type={api_type}"

def start_background_workers(bot_username: str):
    start_ivas_worker(bot_username)
    start_group_queue_worker()

    # Numbers Poller Worker (Every 30s)
    def _numbers_worker():
        while True:
            time.sleep(30)
            with config_lock:
                bases = list(API_Bases)

            country_numbers = {}
            for idx, base in enumerate(bases):
                try:
                    url = build_api_url(base, "numbers")
                    resp = session.get(url, timeout=12)
                    data = resp.json().get("aaData", [])
                    panel_ranges = {}
                    for row in data:
                        if len(row) > 2:
                            full_country = str(row[0])
                            phone_num = str(row[2])
                            base_c = clean_country_name(full_country)
                            if base_c not in panel_ranges:
                                panel_ranges[base_c] = {}
                            if full_country not in panel_ranges[base_c]:
                                panel_ranges[base_c][full_country] = []
                            panel_ranges[base_c][full_country].append(phone_num)

                    panel_num = idx + 1
                    for base_c, r_map in panel_ranges.items():
                        if len(r_map) == 1:
                            k = f"{base_c}{panel_num}"
                            country_numbers.setdefault(k, []).extend(list(r_map.values())[0])
                        else:
                            sorted_keys = sorted(list(r_map.keys()))
                            for r_idx, r_key in enumerate(sorted_keys):
                                k = f"{base_c}{panel_num}-{r_idx+1}"
                                country_numbers.setdefault(k, []).extend(r_map[r_key])
                except Exception:
                    continue

            try:
                for fname in os.listdir(FilesDir):
                    if not fname.endswith(".txt") or "0.txt" in fname or "0-" in fname:
                        continue
                    prefix = fname.replace(".txt", "")
                    if prefix in country_numbers and country_numbers[prefix]:
                        nums = country_numbers[prefix]
                        fpath = os.path.join(FilesDir, fname)
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write("\n".join(nums))
                        with ram_numbers_lock:
                            ram_numbers[fname] = nums
                    else:
                        fpath = os.path.join(FilesDir, fname)
                        if os.path.exists(fpath):
                            os.remove(fpath)
                        with ram_numbers_lock:
                            ram_numbers.pop(fname, None)

                for name, nums in country_numbers.items():
                    fname = f"{name}.txt"
                    fpath = os.path.join(FilesDir, fname)
                    if not os.path.exists(fpath) and nums:
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write("\n".join(nums))
                        with ram_numbers_lock:
                            ram_numbers[fname] = nums
            except Exception as e:
                logger.error(f"Numbers Sync Error: {e}")

    threading.Thread(target=_numbers_worker, daemon=True).start()

    # SMS Poller Worker (Every 5s)
    def _sms_worker():
        bot_link = f"https://t.me/{bot_username}"
        while True:
            time.sleep(5)
            with config_lock:
                bases = list(API_Bases)

            for api_base in bases:
                try:
                    url = build_api_url(api_base, "sms")
                    resp = session.get(url, timeout=10)
                    data = resp.json().get("aaData", [])

                    with tracking_lock:
                        is_initial = not api_initial_hit_done.get(api_base, False)
                        if is_initial:
                            api_initial_hit_done[api_base] = True
                            for row in data:
                                if len(row) > 4:
                                    is_duplicate_sms(str(row[2]), str(row[3]), str(row[4]))
                            continue

                    unpaid_services = get_unpaid_services()

                    for row in data:
                        if len(row) > 4:
                            phone_num = str(row[2]).strip()
                            service = str(row[3]).strip()
                            sms_text = str(row[4]).strip()

                            if is_duplicate_sms(phone_num, service, sms_text):
                                continue

                            with ram_used_numbers_lock:
                                ram_used_numbers[f"{phone_num}:{service}"] = True

                            def _ins(p, s):
                                with sqlite_lock:
                                    sqlite_conn.execute("INSERT OR IGNORE INTO used_numbers (phone_number, service, used_at) VALUES (?, ?, ?)",
                                                        (p, s, datetime.datetime.now()))
                                    sqlite_conn.commit()
                            threading.Thread(target=_ins, args=(phone_num, service), daemon=True).start()

                            clean_phone = phone_num.lstrip("+")
                            now = datetime.datetime.now()
                            target_user_id = 0
                            country_file = ""

                            with ram_user_locks_lock:
                                for p, info in ram_user_locks.items():
                                    if (p.lstrip("+") == clean_phone or p == phone_num) and (now - info["locked_at"]).total_seconds() <= 600:
                                        target_user_id = info["user_id"]
                                        country_file = info["country_file"]
                                        break

                            if target_user_id == 0:
                                cutoff = now - datetime.timedelta(seconds=600)
                                with sqlite_lock:
                                    cur = sqlite_conn.execute("""
                                        SELECT user_id, country_file FROM user_locks
                                        WHERE (phone_number = ? OR phone_number = ? OR phone_number = ?)
                                          AND locked_at >= ?
                                        ORDER BY locked_at DESC LIMIT 1
                                    """, (phone_num, clean_phone, "+" + clean_phone, cutoff))
                                    r = cur.fetchone()
                                    if r:
                                        target_user_id, country_file = r[0], r[1]

                            if not country_file:
                                country_file = f"{clean_country_name(str(row[0]))}0.txt"

                            price = get_price_for_country(country_file)
                            for unpaid in unpaid_services:
                                if service.lower() == unpaid.lower():
                                    price = 0.0
                                    break

                            safe_api_tag = extract_api_tag(api_base) or "default_api"

                            if target_user_id > 0:
                                send_otp_to_user(target_user_id, phone_num, service, country_file, sms_text, price)
                                send_otp_to_groups(target_user_id, phone_num, service, country_file, sms_text, bot_link, price)

                                if users_collection is not None:
                                    now_str = now.strftime("%Y-%m-%d")
                                    current_week_start = get_weekly_start_of_week(now)
                                    u = users_collection.find_one({"id": target_user_id}) or {}

                                    inc_fields = {
                                        "balance": price,
                                        "total_earned": price,
                                        "total_otps": 1,
                                        f"api_earnings.{safe_api_tag}": price,
                                        f"api_total_otps.{safe_api_tag}": 1,
                                        f"api_cycle_otps.{safe_api_tag}": 1,
                                        f"api_cycle_earnings.{safe_api_tag}": price,
                                    }
                                    set_fields = {"last_active": now}

                                    last_otp_dt = u.get("last_otp_date")
                                    if not last_otp_dt or last_otp_dt.strftime("%Y-%m-%d") != now_str:
                                        set_fields["today_otps"] = 1
                                        set_fields["last_otp_date"] = now
                                    else:
                                        inc_fields["today_otps"] = 1

                                    last_reset = u.get("last_weekly_reset")
                                    if not last_reset or last_reset < current_week_start:
                                        set_fields["weekly_otps"] = 1
                                        set_fields["last_weekly_reset"] = now
                                    else:
                                        inc_fields["weekly_otps"] = 1

                                    users_collection.update_one(
                                        {"id": target_user_id},
                                        {"$inc": inc_fields, "$set": set_fields}
                                    )

                                    ref_id = u.get("referred_by", 0)
                                    if ref_id > 0 and price > 0:
                                        ref_bonus = price * 0.10
                                        res_ref = users_collection.update_one(
                                            {"id": ref_id},
                                            {"$inc": {"balance": ref_bonus, "referral_earnings_earned": ref_bonus}}
                                        )
                                        if res_ref.modified_count > 0:
                                            msg = txt("{E_GIFT} <b>Referral Profit!</b>\n\nReceived <b>+%.2f %s</b>.", ref_bonus, CurrencySymbol)
                                            send_raw_html(ref_id, msg)

                                    g = get_global_stats()
                                    g["total_otps_received"] = g.get("total_otps_received", 0) + 1
                                    g["total_earnings"] = g.get("total_earnings", 0.0) + price
                                    last_g_dt = g.get("last_otp_date")
                                    if not last_g_dt or last_g_dt.strftime("%Y-%m-%d") != now_str:
                                        g["today_otps_received"] = 1
                                        g["last_otp_date"] = now
                                    else:
                                        g["today_otps_received"] = g.get("today_otps_received", 0) + 1
                                    update_global_stats(g)
                            else:
                                send_otp_to_groups(0, phone_num, service, country_file, sms_text, bot_link, price)
                except Exception:
                    continue

    threading.Thread(target=_sms_worker, daemon=True).start()

    # Lock GC Worker
    def _locks_worker():
        while True:
            time.sleep(60)
            cutoff = datetime.datetime.now() - datetime.timedelta(minutes=10)
            try:
                with sqlite_lock:
                    cur = sqlite_conn.execute("SELECT DISTINCT user_id FROM user_locks WHERE locked_at < ?", (cutoff,))
                    expired_users = [row[0] for row in cur.fetchall()]
                    sqlite_conn.execute("DELETE FROM user_locks WHERE locked_at < ?", (cutoff,))
                    sqlite_conn.commit()

                for uid in expired_users:
                    with sqlite_lock:
                        cur = sqlite_conn.execute("SELECT COUNT(*) FROM user_locks WHERE user_id = ?", (uid,))
                        cnt = cur.fetchone()[0]
                        if cnt == 0:
                            cur2 = sqlite_conn.execute("SELECT chat_id, message_id FROM user_number_messages WHERE user_id = ?", (uid,))
                            msg_info = cur2.fetchone()
                            if msg_info:
                                cid, mid = msg_info[0], msg_info[1]
                                edit_raw_html(cid, mid, txt("{E_CROSS} <b>Session Expired</b>\nYour number allocation limit (10 mins) has ended. Request new numbers."))
                                sqlite_conn.execute("DELETE FROM user_number_messages WHERE user_id = ?", (uid,))
                                sqlite_conn.commit()
            except Exception as e:
                logger.error(f"Locks GC Worker error: {e}")

    threading.Thread(target=_locks_worker, daemon=True).start()

def smart_kb(user_id: int):
    kb = [
        [
            {"text": "Get Number", "icon_custom_emoji_id": EmojiMobile, "style": "primary"},
            {"text": "My Account", "icon_custom_emoji_id": ID_MANAGE, "style": "danger"},
        ],
        [
            {"text": "Search Prefix", "icon_custom_emoji_id": ID_GLOBE, "style": "success"},
        ],
        [
            {"text": "Stats", "icon_custom_emoji_id": EmojiStats, "style": "success"},
            {"text": "Withdraw", "icon_custom_emoji_id": ID_WITHDRAW, "style": "primary"},
        ],
        [
            {"text": "Top Users", "icon_custom_emoji_id": ID_TOPUSERS, "style": "danger"},
            {"text": "Rewards", "icon_custom_emoji_id": EmojiGift, "style": "success"},
        ],
        [
            {"text": "Support", "icon_custom_emoji_id": ID_SUPPORT, "style": "primary"},
            {"text": "Main Channel", "icon_custom_emoji_id": ID_CHNL, "style": "danger"},
        ]
    ]
    if isAdmin(user_id):
        kb.append([{"text": "Admin Panel", "icon_custom_emoji_id": ID_ADMIN, "style": "success"}])
    return {"keyboard": kb, "resize_keyboard": True}

def admin_kb(page: int = 1):
    rows = []
    if page == 1:
        rows.append([
            {"text": "Broadcast Omni Message", "callback_data": "adm_flow:broadcast", "icon_custom_emoji_id": EmojiBroadcast, "style": "primary"},
            {"text": "Check User Detail", "callback_data": "adm_flow:check_user_trig", "icon_custom_emoji_id": ID_USER, "style": "success"}
        ])
        rows.append([
            {"text": "Admin Records / Notes", "callback_data": "adm_flow:admin_records:1", "icon_custom_emoji_id": ID_RECEIPT, "style": "primary"},
            {"text": "Manage Withdraw Settings", "callback_data": "adm_flow:manage_withdraw", "icon_custom_emoji_id": ID_WITHDRAW, "style": "success"}
        ])
        rows.append([
            {"text": "Manage OTP Price", "callback_data": "adm_flow:manage_price", "icon_custom_emoji_id": ID_WITHDRAW, "style": "success"},
            {"text": "Manage Active Ranges", "callback_data": "adm_flow:manage_active_ranges", "icon_custom_emoji_id": ID_TOGGLE, "style": "danger"}
        ])
        rows.append([
            {"text": "Download Backup", "callback_data": "adm_flow:download_backup", "icon_custom_emoji_id": ID_RECEIPT, "style": "success"},
            {"text": "Next Page", "callback_data": "adm_page:2", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])
    else:
        rows.append([
            {"text": "Custom Emojis", "callback_data": "adm_flow:manage_emojis", "icon_custom_emoji_id": ID_STAR, "style": "primary"},
            {"text": "Manage Active Services", "callback_data": "adm_flow:manage_active_apps", "icon_custom_emoji_id": ID_MANAGE, "style": "primary"}
        ])
        rows.append([
            {"text": "Manage Unpaid Services", "callback_data": "adm_flow:manage_unpaid", "icon_custom_emoji_id": ID_TRASH, "style": "danger"},
            {"text": "Manage Administrators", "callback_data": "adm_flow:manage_admins", "icon_custom_emoji_id": ID_ADMIN, "style": "success"}
        ])
        rows.append([
            {"text": "Manage API Nodes", "callback_data": "adm_flow:manage_apis", "icon_custom_emoji_id": ID_LINK, "style": "danger"},
            {"text": "View Live Stats", "callback_data": "adm_flow:live_stats", "icon_custom_emoji_id": EmojiStats, "style": "primary"}
        ])
        rows.append([
            {"text": "Manage IVAS Numbers", "callback_data": "adm_flow:manage_ivas", "icon_custom_emoji_id": ID_GLOBE, "style": "success"},
            {"text": "Back Page", "callback_data": "adm_page:1", "icon_custom_emoji_id": ID_BACK, "style": "danger"}
        ])
    return {"inline_keyboard": rows}

def admin_manage_emojis_kb():
    return {"inline_keyboard": [
        [{"text": "Add/Update Country Flags", "callback_data": "adm_flow:add_country_emoji_trig", "icon_custom_emoji_id": ID_ADD, "style": "primary"}],
        [{"text": "Add/Update Service Icons", "callback_data": "adm_flow:add_service_emoji_trig", "icon_custom_emoji_id": ID_ADD, "style": "success"}],
        [{"text": "View Custom Emojis", "callback_data": "adm_flow:view_custom_emojis", "icon_custom_emoji_id": ID_RECEIPT, "style": "primary"}],
        [{"text": "Reset Custom Emojis", "callback_data": "adm_flow:reset_custom_emojis", "icon_custom_emoji_id": ID_TRASH, "style": "danger"}],
        [{"text": "Back to Dashboard", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}]
    ]}

def numbers_action_kb(file_name: str, nums: list, without_cc: bool):
    rows = []
    main_cc = ""
    if nums:
        cc, _ = get_country_code_and_national(nums[0])
        main_cc = cc

    for n in nums:
        clean = n.strip().lstrip("+")
        display_num = "+" + clean
        copy_val = "+" + clean
        if without_cc:
            _, nat = get_country_code_and_national(clean)
            display_num = nat
            copy_val = nat
        rows.append([{
            "text": "Copy: " + display_num,
            "icon_custom_emoji_id": ID_COPY,
            "style": "success",
            "copy_text": {"text": copy_val}
        }])

    toggle_text = f"Without +{main_cc}" if not without_cc else f"With +{main_cc}"
    if not main_cc:
        toggle_text = "Without Country Code" if not without_cc else "With Country Code"

    refresh_cb = f"pfx_alloc:{file_name[4:].replace('_', ':', 1)}" if file_name.startswith("pfx_") else f"country_select:{file_name}"

    rows.append([
        {"text": toggle_text, "callback_data": f"tgcc_toggle:{file_name}", "icon_custom_emoji_id": ID_PTICK, "style": "primary"},
        {"text": "Refresh Numbers", "callback_data": refresh_cb, "icon_custom_emoji_id": ID_TOGGLE, "style": "success"}
    ])
    rows.append([
        {"text": "Change Country", "callback_data": "menu:change_country", "icon_custom_emoji_id": ID_LINK, "style": "primary"},
        {"text": "OTP Group", "url": OtpGroupInviteLink, "icon_custom_emoji_id": ID_USERS, "style": "danger"}
    ])
    return {"inline_keyboard": rows}

def countries_inline_kb(page: int = 1):
    global_used = get_global_used_numbers()
    grouped = {}

    with ram_numbers_lock:
        for fname, lines in ram_numbers.items():
            if fname.endswith(".txt"):
                cnt = sum(1 for n in lines if n and not global_used.get(n, False))
                if cnt > 0:
                    c_name = clean_country_name(fname.replace(".txt", ""))
                    if c_name not in grouped:
                        grouped[c_name] = {"name": c_name, "count": 0, "ranges_count": 0}
                    grouped[c_name]["count"] += cnt
                    grouped[c_name]["ranges_count"] += 1

    valid_items = list(grouped.values())
    valid_items.sort(key=lambda x: x["name"].lower())
    page_size = 10
    total_pages = max(1, math.ceil(len(valid_items) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    items = valid_items[start:start + page_size]

    rows = []
    if items:
        for i in range(0, len(items), 2):
            row = []
            c1 = items[i]
            flag_id1 = get_flag_id(c1["name"])
            row.append({
                "text": f"{c1['name']} ({c1['count']})",
                "callback_data": f"cgroup_select:{c1['name']}",
                "icon_custom_emoji_id": flag_id1,
                "style": "primary"
            })
            if i + 1 < len(items):
                c2 = items[i + 1]
                flag_id2 = get_flag_id(c2["name"])
                row.append({
                    "text": f"{c2['name']} ({c2['count']})",
                    "callback_data": f"cgroup_select:{c2['name']}",
                    "icon_custom_emoji_id": flag_id2,
                    "style": "primary"
                })
            rows.append(row)

        if total_pages > 1:
            prev_p = total_pages if page == 1 else page - 1
            next_p = 1 if page == total_pages else page + 1
            rows.append([
                {"text": "Back", "callback_data": f"country_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
                {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
                {"text": "Next", "callback_data": f"country_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
            ])
    else:
        rows.append([{"text": "No Countries Available", "callback_data": "noop", "icon_custom_emoji_id": ID_CROSS, "style": "danger"}])

    rows.append([{"text": "Back to Menu", "callback_data": "menu:change_country", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def country_ranges_sub_kb(country_name: str, page: int = 1):
    global_used = get_global_used_numbers()
    ranges = []
    target_clean = clean_country_name(country_name).lower()

    with ram_numbers_lock:
        for fname, lines in ram_numbers.items():
            if fname.endswith(".txt"):
                c_clean = clean_country_name(fname.replace(".txt", "")).lower()
                if c_clean == target_clean:
                    cnt = sum(1 for n in lines if n and not global_used.get(n, False))
                    if cnt > 0:
                        price = get_price_for_country(fname)
                        ranges.append({
                            "file": fname,
                            "name": fname.replace(".txt", ""),
                            "count": cnt,
                            "price": price
                        })

    ranges.sort(key=lambda x: x["name"].lower())
    page_size = 5
    total_pages = max(1, math.ceil(len(ranges) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    items = ranges[start:start + page_size]

    rows = []
    flag_id = get_flag_id(country_name)
    for item in items:
        rows.append([{
            "text": f"{item['name']} ({item['count']}) - {item['price']:.2f} {CurrencySymbol}",
            "callback_data": f"country_select:{item['file']}",
            "icon_custom_emoji_id": flag_id,
            "style": "primary"
        }])

    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"cgroup_subpage:{country_name}:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"cgroup_subpage:{country_name}:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([{"text": "Back to Countries", "callback_data": "menu:getnum_all", "icon_custom_emoji_id": ID_BACK, "style": "danger"}])
    rows.append([{"text": "Main Menu", "callback_data": "menu:change_country", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def active_countries_inline_kb(page: int = 1):
    active_list = get_active_ranges()
    valid_items = []
    for target in active_list:
        v_nums = get_valid_numbers_for_target(target, "")
        if v_nums:
            valid_items.append({"name": target, "count": len(v_nums), "file": target})

    valid_items.sort(key=lambda x: x["name"].lower())
    page_size = 5
    total_pages = max(1, math.ceil(len(valid_items) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    items = valid_items[start:start + page_size]

    rows = []
    if items:
        for item in items:
            flag_id = get_flag_id(item["name"])
            rows.append([{
                "text": f"{item['name']} ({item['count']})",
                "callback_data": f"country_select:{item['file']}",
                "icon_custom_emoji_id": flag_id,
                "style": "primary"
            }])
        if total_pages > 1:
            prev_p = total_pages if page == 1 else page - 1
            next_p = 1 if page == total_pages else page + 1
            rows.append([
                {"text": "Back", "callback_data": f"active_country_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
                {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
                {"text": "Next", "callback_data": f"active_country_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
            ])
    else:
        rows.append([{"text": "No Active Ranges Configured", "callback_data": "noop", "icon_custom_emoji_id": ID_CROSS, "style": "danger"}])

    rows.append([{"text": "Back to Menu", "callback_data": "menu:change_country", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def active_services_inline_kb(page: int = 1):
    apps = get_active_apps()
    styles = ["primary", "success", "danger"]
    if not apps:
        return {"inline_keyboard": [
            [{"text": "No Active Services Configured", "callback_data": "noop", "icon_custom_emoji_id": ID_CROSS, "style": "danger"}],
            [{"text": "Back to Menu", "callback_data": "menu:change_country", "icon_custom_emoji_id": ID_BACK, "style": "primary"}]
        ]}

    page_size = 10
    total_pages = max(1, math.ceil(len(apps) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    items = apps[start:start + page_size]

    rows = []
    for i in range(0, len(items), 2):
        row = []
        app1 = items[i]
        row.append({
            "text": app1.get("name", ""),
            "callback_data": f"app_select:{app1.get('name')}",
            "icon_custom_emoji_id": app1.get("icon_id") or DefaultAppIconID,
            "style": styles[i % len(styles)]
        })
        if i + 1 < len(items):
            app2 = items[i + 1]
            row.append({
                "text": app2.get("name", ""),
                "callback_data": f"app_select:{app2.get('name')}",
                "icon_custom_emoji_id": app2.get("icon_id") or DefaultAppIconID,
                "style": styles[(i + 1) % len(styles)]
            })
        rows.append(row)

    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"services_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"services_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([{"text": "Back to Menu", "callback_data": "menu:change_country", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def app_countries_inline_kb(app_name: str, page: int = 1):
    apps = get_active_apps()
    app_countries = []
    for a in apps:
        if a.get("name") == app_name:
            app_countries = a.get("countries", [])
            break

    valid_items = []
    for target in app_countries:
        nums = get_valid_numbers_for_target(target, app_name)
        if nums:
            valid_items.append({"name": target, "count": len(nums), "file": target})

    if not valid_items:
        return {"inline_keyboard": [
            [{"text": "No Countries Available", "callback_data": "noop", "icon_custom_emoji_id": ID_CROSS, "style": "danger"}],
            [{"text": "Back to Services", "callback_data": "menu:getnum_apps", "icon_custom_emoji_id": ID_BACK, "style": "danger"}]
        ]}

    page_size = 5
    total_pages = max(1, math.ceil(len(valid_items) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    items = valid_items[start:start + page_size]

    rows = []
    for item in items:
        flag_id = get_flag_id(item["name"])
        rows.append([{
            "text": f"{item['name']} ({item['count']})",
            "callback_data": f"app_cselect:{app_name}:{item['file']}",
            "icon_custom_emoji_id": flag_id,
            "style": "primary"
        }])

    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"appc_page:{app_name}:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"appc_page:{app_name}:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([
        {"text": "Back to Services", "callback_data": "menu:getnum_apps", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
        {"text": "Back to Menu", "callback_data": "menu:change_country", "icon_custom_emoji_id": ID_BACK, "style": "primary"}
    ])
    return {"inline_keyboard": rows}

def admin_ivas_manage_kb():
    groups = get_ivas_grouped_countries()
    rows = []
    for g in groups:
        flag_id = get_flag_id(g["CountryName"])
        rows.append([{
            "text": f"{g['CountryName']} ({g['TotalNums']} Nums - {g['FilesCount']} Ranges)",
            "callback_data": f"ivas_view_c:{g['CountryName']}",
            "icon_custom_emoji_id": flag_id,
            "style": "primary"
        }])
    rows.append([{"text": "Upload / Add IVAS File (XLSX/ZIP/TXT)", "callback_data": "ivas_add_country_trig", "icon_custom_emoji_id": ID_ADD, "style": "success"}])
    rows.append([{"text": "Back to Dashboard", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def admin_ivas_country_ranges_kb(country_name: str):
    ranges = get_ivas_country_ranges(country_name)
    rows = []
    for r in ranges:
        rows.append([{
            "text": f"Delete Range: {r['RangeName']} ({r['Count']} Nums)",
            "callback_data": f"ivas_del_range:{r['FileName']}",
            "icon_custom_emoji_id": ID_TRASH,
            "style": "danger"
        }])
    rows.append([{"text": "Back to IVAS Countries", "callback_data": "adm_flow:manage_ivas", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def admin_manage_withdraw_kb():
    return {"inline_keyboard": [
        [{"text": "Set Minimum Withdraw", "callback_data": "adm_flow:set_min_wd_trig", "icon_custom_emoji_id": ID_MANAGE, "style": "primary"}],
        [{"text": "Set Withdraw Time", "callback_data": "adm_flow:set_wd_time_trig", "icon_custom_emoji_id": ID_TOGGLE, "style": "success"}],
        [{"text": "Back to Dashboard", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}]
    ]}

def admin_manage_prices_kb(page: int = 1):
    items = get_custom_prices_list()
    page_size = 5
    total_pages = max(1, math.ceil(len(items) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    sub = items[start:start + page_size]
    rows = []
    for item in sub:
        rows.append([{
            "text": f"❌ {item['key'].capitalize()}: {item['price']:.2f} {CurrencySymbol}",
            "callback_data": f"adm_del_price:{item['key']}",
            "icon_custom_emoji_id": ID_TRASH,
            "style": "danger"
        }])

    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"adm_prices_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"adm_prices_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([{"text": "Set New Price Rates", "callback_data": "adm_flow:set_price_trigger", "icon_custom_emoji_id": ID_ADD, "style": "success"}])
    rows.append([{"text": "Back to Dashboard", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def admin_manage_services_kb(page: int = 1):
    apps = get_active_apps()
    styles = ["primary", "success", "danger"]
    page_size = 4
    total_pages = max(1, math.ceil(len(apps) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    sub = apps[start:start + page_size]
    rows = []
    for i in range(0, len(sub), 2):
        row = []
        a1 = sub[i]
        row.append({
            "text": a1.get("name", ""),
            "callback_data": f"app_adm:{a1.get('name')}",
            "icon_custom_emoji_id": a1.get("icon_id") or DefaultAppIconID,
            "style": styles[i % len(styles)]
        })
        if i + 1 < len(sub):
            a2 = sub[i + 1]
            row.append({
                "text": a2.get("name", ""),
                "callback_data": f"app_adm:{a2.get('name')}",
                "icon_custom_emoji_id": a2.get("icon_id") or DefaultAppIconID,
                "style": styles[(i + 1) % len(styles)]
            })
        rows.append(row)

    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"adm_services_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"adm_services_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([{"text": "Add Active Service", "callback_data": "adm_flow:add_app_trigger", "icon_custom_emoji_id": ID_ADD, "style": "success"}])
    rows.append([{"text": "Back to Dashboard", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def admin_edit_service_kb(app_name: str):
    rows = [
        [{"text": "Edit Service Name/Icon", "callback_data": f"app_edit:{app_name}", "icon_custom_emoji_id": ID_MANAGE, "style": "primary"}],
        [{"text": "Add Country to Service", "callback_data": f"app_addcountry:{app_name}", "icon_custom_emoji_id": ID_ADD, "style": "success"}]
    ]
    apps = get_active_apps()
    for a in apps:
        if a.get("name") == app_name:
            for c in a.get("countries", []):
                rows.append([{"text": f"❌ Delete: {c}", "callback_data": f"app_delcountry:{app_name}:{c}", "icon_custom_emoji_id": ID_TRASH, "style": "danger"}])
            break
    rows.append([{"text": "Delete Service", "callback_data": f"app_delete:{app_name}", "icon_custom_emoji_id": ID_TRASH, "style": "danger"}])
    rows.append([{"text": "Back to Services", "callback_data": "adm_flow:manage_active_apps", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def admin_active_ranges_kb(page: int = 1):
    ranges = get_active_ranges()
    page_size = 5
    total_pages = max(1, math.ceil(len(ranges) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    sub = ranges[start:start + page_size]
    rows = []
    for r in sub:
        rows.append([{"text": f"Delete: {r}", "callback_data": f"adm_del_range:{r}", "icon_custom_emoji_id": ID_TRASH, "style": "danger"}])

    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"adm_ranges_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"adm_ranges_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([{"text": "Add Active Range", "callback_data": "adm_flow:add_active_range_trigger", "icon_custom_emoji_id": ID_ADD, "style": "success"}])
    rows.append([{"text": "Back to Panel", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def admin_manage_unpaid_kb(page: int = 1):
    services = get_unpaid_services()
    page_size = 5
    total_pages = max(1, math.ceil(len(services) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    sub = services[start:start + page_size]
    rows = []
    for s in sub:
        rows.append([{"text": f"❌ Delete: {s}", "callback_data": f"adm_del_unpaid:{s}", "icon_custom_emoji_id": ID_TRASH, "style": "danger"}])

    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"adm_unpaid_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"adm_unpaid_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([{"text": "Add Unpaid Service", "callback_data": "adm_flow:add_unpaid_trigger", "icon_custom_emoji_id": ID_ADD, "style": "success"}])
    rows.append([{"text": "Back to Panel", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def admin_manage_admins_kb():
    with config_lock:
        admins = list(AdminIDs)
    rows = []
    for aid in admins:
        rows.append([{"text": f"Remove Admin: {aid}", "callback_data": f"adm_del_admin:{aid}", "icon_custom_emoji_id": ID_TRASH, "style": "danger"}])
    rows.append([{"text": "Add New Admin Profile", "callback_data": "adm_flow:add_admin_trigger", "icon_custom_emoji_id": ID_ADD, "style": "success"}])
    rows.append([{"text": "Back to Dashboard", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def admin_manage_apis_kb(page: int = 1):
    with config_lock:
        apis = list(API_Bases)
    page_size = 5
    total_pages = max(1, math.ceil(len(apis) / page_size))
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    sub = apis[start:start + page_size]
    rows = []
    for idx_offset, api in enumerate(sub):
        actual_idx = start + idx_offset
        tag = extract_api_tag(api)
        disp = api if len(api) <= 22 else api[:19] + "..."
        rows.append([{
            "text": f"Delete{actual_idx+1} [{tag}] {disp}",
            "callback_data": f"adm_del_api:{actual_idx}",
            "icon_custom_emoji_id": ID_TRASH,
            "style": "danger"
        }])

    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"adm_apis_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"adm_apis_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([{"text": "Register New API Link", "callback_data": "adm_flow:add_api_trigger", "icon_custom_emoji_id": ID_ADD, "style": "success"}])
    rows.append([{"text": "Back to Dashboard", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return {"inline_keyboard": rows}

def get_admin_records_text_and_kb(page: int = 1):
    page_size = 5
    total = admin_records_collection.count_documents({}) if admin_records_collection is not None else 0
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))

    skip = (page - 1) * page_size
    records = []
    if admin_records_collection is not None:
        records = list(admin_records_collection.find({}).sort("id", -1).skip(skip).limit(page_size))

    text = txt("{E_RECEIPT} <b>Admin Accounting & Record Logs</b>\n\n")
    if not records:
        text += "<i>No saved admin records found.</i>\n\n"
    else:
        for r in records:
            created_str = r.get("created_at", datetime.datetime.now()).strftime("%Y-%m-%d %H:%M")
            text += f"📌 <b>Record #{r.get('id')}</b> [{created_str}]\n<code>{r.get('text')}</code>\n───────────────\n"

    rows = []
    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"adm_rec_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"adm_rec_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])

    rows.append([
        {"text": "Add New Record", "callback_data": "adm_flow:add_record_trig", "icon_custom_emoji_id": ID_ADD, "style": "success"},
        {"text": "Delete Record", "callback_data": "adm_flow:del_record_trig", "icon_custom_emoji_id": ID_TRASH, "style": "danger"}
    ])
    rows.append([{"text": "Back to Dashboard", "callback_data": "menu:back_to_admin", "icon_custom_emoji_id": ID_BACK, "style": "primary"}])
    return text, {"inline_keyboard": rows}

def get_top_users_text_and_kb(page: int = 1):
    page_size = 10
    total = users_collection.count_documents({"total_otps": {"$gt": 0}}) if users_collection is not None else 0
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))

    skip = (page - 1) * page_size
    user_list = []
    if users_collection is not None:
        user_list = list(users_collection.find({"total_otps": {"$gt": 0}}).sort("total_otps", -1).skip(skip).limit(page_size))

    text = txt("{E_LIVE} <b>Top Active Users (Overall)</b>\n\n")
    for i, u in enumerate(user_list):
        m_name = u.get("first_name", "")
        if u.get(""):
            m_name = f"<a href=\"https://t.me/{u['username']}\">{m_name}</a>"
        global_rank = skip + i + 1
        medal = get_medal_for_rank(global_rank)
        text += f"{medal} {m_name} — <b>{u.get('total_otps', 0)}</b> OTPs\n"

    rows = []
    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"top_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"top_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])
    rows.append([{"text": "Weekly Top Users", "callback_data": "top_weekly_page:1", "icon_custom_emoji_id": ID_TOPUSERS, "style": "success"}])
    return text, {"inline_keyboard": rows}

def get_weekly_top_users_text_and_kb(page: int = 1):
    page_size = 10
    filt = {"weekly_otps": {"$gte": 100}}
    total = users_collection.count_documents(filt) if users_collection is not None else 0

    if total == 0:
        text = txt("{E_WARN} <b>No Weekly Top Users Yet!</b>\n\n"
                   "To feature on the <b>Weekly Top Users</b> leaderboard, you must complete <b>100+ OTPs</b> in the active week.\n\n"
                   "💡 <i>Weekly rankings automatically reset every Monday night at 12:00 AM PKT. Keep grinding!</i>")
        return text, {"inline_keyboard": [[{"text": "Overall Top Users", "callback_data": "top_page:1", "icon_custom_emoji_id": ID_TOPUSERS, "style": "primary"}]]}

    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size

    user_list = list(users_collection.find(filt).sort("weekly_otps", -1).skip(skip).limit(page_size))
    text = txt("{E_LIVE} <b>Weekly Top Users</b>\n<i>{E_PTICK1} Resets every Monday night at 12:00 AM</i>\n\n")

    for i, u in enumerate(user_list):
        m_name = u.get("first_name", "")
        if u.get("username"):
            m_name = f"<a href=\"https://t.me/{u['username']}\">{m_name}</a>"
        global_rank = skip + i + 1
        medal = get_medal_for_rank(global_rank)
        text += f"{medal} {m_name} — <b>{u.get('weekly_otps', 0)}</b> OTPs\n"

    rows = []
    if total_pages > 1:
        prev_p = total_pages if page == 1 else page - 1
        next_p = 1 if page == total_pages else page + 1
        rows.append([
            {"text": "Back", "callback_data": f"top_weekly_page:{prev_p}", "icon_custom_emoji_id": ID_BACK, "style": "danger"},
            {"text": f"{page}/{total_pages}", "callback_data": "noop", "icon_custom_emoji_id": ID_TICK, "style": "success"},
            {"text": "Next", "callback_data": f"top_weekly_page:{next_p}", "icon_custom_emoji_id": ID_COPY, "style": "danger"}
        ])
    rows.append([{"text": "Overall Top Users", "callback_data": "top_page:1", "icon_custom_emoji_id": ID_TOPUSERS, "style": "primary"}])
    return text, {"inline_keyboard": rows}

def format_broadcast_text(raw_text: str) -> str:
    formatted = raw_text

    protected = []
    def _prot_sub(m):
        placeholder = f"___PROT_HTML_{len(protected)}___"
        protected.append(m.group(0))
        return placeholder

    formatted = re.sub(r'(?i)<[^>]+>.*?</[^>]+>|<[^>]+/>', _prot_sub, formatted)

    def _serv_sub(m):
        prefix = m.group(1)
        s_name = m.group(2)
        custom_id = m.group(4)
        icon_id = custom_id if custom_id else get_service_icon(s_name)
        return f"{prefix}{s_name} ___EMJ_{icon_id}_📲___"

    formatted = re.sub(r'(?i)(Service:\s*)([a-zA-Z0-9_\-]+)(\s+(\d{18,20}))?', _serv_sub, formatted)

    for c_key, flag_id in countryFlags.items():
        if c_key == "default":
            continue
        c_title = c_key.replace("_", " ").title()
        if re.search(r'\b' + re.escape(c_title) + r'\b', formatted, re.IGNORECASE):
            pl = f"___EMJ_{flag_id}_🏳️___"
            if pl not in formatted:
                formatted = re.sub(r'\b(' + re.escape(c_title) + r')\b', r'\1 ' + pl, formatted, flags=re.IGNORECASE)

    formatted = re.sub(r'\b(\d{18,20})\b', r'___EMJ_\1_⭐___', formatted)

    for k, v in E_MAP.items():
        formatted = formatted.replace(k, v)

    def _res_sub(m):
        eid = m.group(1)
        fb = m.group(2)
        if not UseCustomEmoji or not eid:
            return fb
        return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'

    formatted = re.sub(r'___EMJ_(\d{18,20})_([^_]+)___', _res_sub, formatted)

    for i, p in enumerate(protected):
        formatted = formatted.replace(f"___PROT_HTML_{i}___", p)

    return formatted

def parse_broadcast_payload(bot_username: str, input_str: str):
    lines = input_str.split("\n")
    text_lines = []
    btn_lines = []
    for l in lines:
        tr = l.strip()
        if tr.lower().startswith("[button]"):
            btn_lines.append(tr)
        else:
            text_lines.append(l)

    body_text = format_broadcast_text("\n".join(text_lines))
    if not btn_lines:
        return body_text, None, None

    p_rows = []
    g_rows = []
    bot_link = f"https://t.me/{bot_username}"

    for bl in btn_lines:
        clean = bl[8:].strip()
        if "=" in clean:
            parts = clean.split("=", 1)
            b_name = parts[0].strip()
            b_url = parts[1].strip()
            p_btn = {"text": b_name, "url": b_url, "icon_custom_emoji_id": ID_LINK, "style": "success"}
            g_btn = {"text": b_name, "url": b_url, "icon_custom_emoji_id": ID_LINK, "style": "success"}
            p_rows.append([p_btn])
            g_rows.append([g_btn])
        else:
            b_name = clean.strip()
            cb_data = "menu:getnum_apps"
            if b_name.lower() in ["withdraw"]:
                cb_data = "user:initiate_wd_v2"
            p_btn = {"text": b_name, "callback_data": cb_data, "icon_custom_emoji_id": EmojiMobile, "style": "primary"}
            g_btn = {"text": "Bot Link", "url": bot_link, "icon_custom_emoji_id": ID_LINK, "style": "primary"}
            p_rows.append([p_btn])
            g_rows.append([g_btn])

    pkb = {"inline_keyboard": p_rows} if p_rows else None
    gkb = {"inline_keyboard": g_rows} if g_rows else None
    return body_text, pkb, gkb

def parse_emoji_batch(input_str: str) -> dict:
    parsed = {}
    for line in input_str.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            parts = line.split(":", 1)
        elif "=" in line:
            parts = line.split("=", 1)
        else:
            parts = line.split()

        if len(parts) >= 2:
            raw_key = parts[0].strip().lower().replace("_", " ")
            clean_k = re.sub(r'[\d\-]', '', raw_key).strip()
            val = parts[1].strip()
            digits = "".join(re.findall(r'\d+', val))
            if digits and clean_k:
                parsed[clean_k] = digits
    return parsed

def create_and_send_backup(chat_id: int):
    try:
        timestamp_str = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
        zip_filename = f"legend_bot_backup_{timestamp_str}.zip"
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            script_path = sys.argv[0]
            if os.path.exists(script_path):
                with open(script_path, "rb") as f:
                    z.writestr(os.path.basename(script_path), f.read())
            elif os.path.exists("main(Copy).py"):
                with open("main(Copy).py", "rb") as f:
                    z.writestr("main(Copy).py", f.read())

            if os.path.exists("./locks.db"):
                try:
                    with sqlite_lock:
                        backup_db_bytes = sqlite_conn.iterdump()
                        sql_dump_str = "\n".join(backup_db_bytes)
                    z.writestr("locks_dump.sql", sql_dump_str.encode("utf-8"))
                except Exception as e:
                    logger.error(f"SQLite Dump Error: {e}")

            if users_collection is not None:
                users_data = list(users_collection.find({}))
                z.writestr("users_collection.json", json.dumps(users_data, default=str, indent=2).encode("utf-8"))

            if stats_collection is not None:
                stats_data = list(stats_collection.find({}))
                z.writestr("stats_collection.json", json.dumps(stats_data, default=str, indent=2).encode("utf-8"))

            if admin_records_collection is not None:
                admin_records_data = list(admin_records_collection.find({}))
                z.writestr("admin_records.json", json.dumps(admin_records_data, default=str, indent=2).encode("utf-8"))

            if os.path.exists(FilesDir):
                for fn in os.listdir(FilesDir):
                    full_p = os.path.join(FilesDir, fn)
                    if os.path.isfile(full_p):
                        with open(full_p, "rb") as f:
                            z.writestr(f"countries_data/{fn}", f.read())

        zip_buffer.seek(0)
        cap = txt("{E_TICK} <b>Full System Backup Generated!</b>\n\n"
                  "📦 <b>Archive:</b> <code>%s</code>\n"
                  "📊 <b>Includes:</b> Script, MongoDB, SQLite & Countries Data.", zip_filename)
        res = send_telegram_document(chat_id, zip_buffer.getvalue(), zip_filename, cap)
        if not res or not res.get("ok"):
            send_raw_html(chat_id, txt("{E_CROSS} <b>Failed to upload backup document to Telegram!</b>"))
    except Exception as e:
        logger.error(f"Backup Error: {e}")
        send_raw_html(chat_id, txt("{E_CROSS} <b>Backup Process Error:</b> %s", str(e)))

def handle_document_message(msg: dict):
    user_id = msg.get("from", {}).get("id")
    chat_id = msg.get("chat", {}).get("id")
    doc = msg.get("document")

    with state_lock:
        state = user_state.get(user_id)

    if not state or not doc:
        return

    file_id = doc.get("file_id")
    file_name = doc.get("file_name", "unknown")
    res = session.get(f"https://api.telegram.org/bot{BotToken}/getFile?file_id={file_id}").json()
    if not res.get("ok"):
        send_raw_html(chat_id, txt("{E_CROSS} <b>File Download Failed!</b>"), smart_kb(user_id))
        return

    f_path = res["result"]["file_path"]
    d_url = f"https://api.telegram.org/file/bot{BotToken}/{f_path}"
    file_bytes = session.get(d_url).content
    is_xlsx_zip = file_name.lower().endswith(".xlsx") or file_name.lower().endswith(".zip")

    if state == "ivas_await_upload":
        with state_lock:
            user_state.pop(user_id, None)
        try:
            report, count = process_ivas_file_upload(file_bytes, file_name, is_xlsx_zip)
            report_text = txt("{E_TICK} <b>IVAS Archive Processed Successfully!</b>\n\n• <b>Total Numbers:</b> %d\n• <b>Files Generated:</b>\n", count)
            for fn, cnt in report.items():
                report_text += f"  ├ <code>{fn}</code> — <b>{cnt} Nums</b>\n"
            send_raw_html(chat_id, report_text, smart_kb(user_id))
        except Exception as e:
            send_raw_html(chat_id, txt("{E_CROSS} <b>Processing Error: %s</b>", str(e)), smart_kb(user_id))

    elif state.startswith("ivas_await_append_file:"):
        f_name = state.split(":", 1)[1]
        with state_lock:
            user_state.pop(user_id, None)
        try:
            tot = append_ivas_numbers_from_bytes(f_name, file_bytes, is_xlsx_zip)
            send_raw_html(chat_id, txt("{E_TICK} File <code>%s</code> Updated! Total: <b>%d</b>", f_name, tot), smart_kb(user_id))
        except Exception as e:
            send_raw_html(chat_id, txt("{E_CROSS} <b>Failed to append numbers: %s</b>", str(e)), smart_kb(user_id))

def handle_text_message(msg: dict):
    user = msg.get("from", {})
    user_id = user.get("id")
    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or msg.get("caption") or "").strip()

    menu_buttons = ["Get Number", "My Account", "Search Prefix", "Stats", "Withdraw", "Top Users", "Rewards", "Support", "Main Channel", "Admin Panel"]
    if text in menu_buttons or text.startswith("/"):
        with state_lock:
            user_state.pop(user_id, None)
            withdraw_amounts.pop(user_id, None)

    with state_lock:
        state = user_state.get(user_id)

    if state:
        if state == "await_prefix_search":
            clean_pfx = re.sub(r'\D', '', text)
            if len(clean_pfx) < 3 or len(clean_pfx) > 7:
                send_raw_html(chat_id, txt("{E_WARN} <b>Invalid Prefix Length!</b>\nPlease enter between 3 to 6 digits (e.g. <code>92300</code> or <code>23480</code>):"))
                return

            with state_lock:
                del user_state[user_id]

            global_used = get_global_used_numbers()
            now = datetime.datetime.now()
            active_locks = set()
            with ram_user_locks_lock:
                for phone, info in ram_user_locks.items():
                    if (now - info["locked_at"]).total_seconds() < 600:
                        active_locks.add(phone)

            matching_ranges = {}
            total_found = 0
            with ram_numbers_lock:
                for fname, lines in ram_numbers.items():
                    if not fname.endswith(".txt"):
                        continue
                    avail_matching = []
                    for line in lines:
                        n = line.strip()
                        if not n:
                            continue
                        clean_n = n.lstrip("+")
                        if clean_n.startswith(clean_pfx):
                            if not global_used.get(n, False) and n not in active_locks:
                                avail_matching.append(n)
                    if avail_matching:
                        c_name = clean_country_name(fname.replace(".txt", ""))
                        matching_ranges[fname] = {
                            "file": fname,
                            "country": c_name,
                            "count": len(avail_matching),
                            "nums": avail_matching
                        }
                        total_found += len(avail_matching)

            if total_found == 0:
                send_raw_html(chat_id, txt("{E_CROSS} <b>No Numbers Available for Prefix +%s!</b>\n\nPlease try searching another prefix or select from All Ranges.", clean_pfx), smart_kb(user_id))
                return

            rows = []
            for fname, data_item in matching_ranges.items():
                flag_id = get_flag_id(data_item["country"])
                price = get_price_for_country(fname)
                btn_text = f"{data_item['country']} (+{clean_pfx}) [{data_item['count']} Nums] - {price:.2f} {CurrencySymbol}"
                rows.append([{
                    "text": btn_text,
                    "callback_data": f"pfx_alloc:{clean_pfx}:{fname}",
                    "icon_custom_emoji_id": flag_id,
                    "style": "primary"
                }])
            rows.append([{"text": "Back to Menu", "callback_data": "menu:change_country", "icon_custom_emoji_id": ID_BACK, "style": "danger"}])

            resp_text = txt(
                "{E_LIVE} <b>Prefix Search Results for +%s</b>\n\n"
                "• <b>Total Available Numbers:</b> %d\n"
                "• <b>Matching Ranges Found:</b> %d\n\n"
                "Tap a button below to allocate numbers for this prefix:",
                clean_pfx, total_found, len(matching_ranges)
            )
            send_raw_html(chat_id, resp_text, {"inline_keyboard": rows})
            return

        elif state == "adm_await_min_wd":
            with state_lock:
                del user_state[user_id]
            try:
                min_val = float(text)
                stats_collection.update_one({"id": "config"}, {"$set": {"min_withdraw": min_val}}, upsert=True)
                send_raw_html(chat_id, txt("{E_TICK} <b>Minimum Withdraw updated to: %.0f %s</b>", min_val, CurrencySymbol), smart_kb(user_id))
            except Exception:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid amount entered!</b>"), smart_kb(user_id))
            return

        elif state == "adm_await_wd_time":
            with state_lock:
                del user_state[user_id]
            try:
                s_h, e_h, d_str = parse_withdraw_time_input(text)
                stats_collection.update_one({"id": "config"}, {"$set": {
                    "withdraw_start_hour": s_h,
                    "withdraw_end_hour": e_h,
                    "withdraw_time_str": d_str
                }}, upsert=True)
                send_raw_html(chat_id, txt("{E_TICK} <b>Withdraw Timing updated to: %s (PKT)</b>", d_str), smart_kb(user_id))
            except Exception as e:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Error: %s</b>", str(e)), smart_kb(user_id))
            return

        elif state == "await_wd_amount_v2":
            u = get_or_create_user(user)
            curr = get_user_currency(u)
            try:
                amount = float(text)
            except Exception:
                amount = 0.0

            if curr == "usd":
                user_usd = u.get("balance", 0.0) / FixedUSDRate
                if amount >= 1.0 and amount <= user_usd:
                    req_pkr = amount * FixedUSDRate
                    valid = True
                else:
                    valid = False
            else:
                min_pkr = get_min_withdraw_amount()
                bal_pkr = u.get("balance", 0.0)
                if amount >= min_pkr and amount <= bal_pkr:
                    req_pkr = amount
                    valid = True
                else:
                    valid = False

            if not valid:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid Amount Format or Limits!</b>"))
                return

            with state_lock:
                del user_state[user_id]

            res = users_collection.update_one(
                {"id": user_id, "balance": {"$gte": req_pkr}},
                {"$inc": {"balance": -req_pkr}}
            )
            if res.modified_count == 0:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Processing Error or Insufficient Balance!</b>"), smart_kb(user_id))
                return

            amt_display = f"{amount:.2f} $" if curr == "usd" else f"{amount:.2f} {CurrencySymbol}"
            u_mention = f"@{u.get('username')}" if u.get("username") else f"<code>{u['id']}</code>"
            breakdown = build_withdrawal_breakdown(u)

            wd = u.get("wd_account", {})
            if wd.get("currency") == "usd":
                acc_details_str = f"Network: {wd.get('network', '').upper()}\nAddress: <code>{wd.get('wallet_addr', '')}</code>"
            else:
                acc_details_str = f"Bank/Wallet: {wd.get('bank_name', 'N/A')}\nAccount: <code>{wd.get('account_no', 'N/A')}</code>\nTitle: {wd.get('account_name', 'N/A')}"

            wid = f"{user_id}_{int(time.time())}"

            # Group Message: User full name strictly as plain text (no clickable link)
            user_full_name = u.get("first_name", "User")
            group_text = txt("{E_GEAR} <b>New Cashout Request Pending Evaluation</b>\n\n"
                             "{E_USERS} User: <b>%s</b>\n"
                             "{E_MONEY} Amount: <b>%s</b>\n\n"
                             "📊 <b>Panel Earnings Breakdown:</b>\n<code>%s</code>",
                             user_full_name, amt_display, breakdown)

            admin_inbox_text = txt(
                "{E_CROWN} <b>🚨 New Cashout Alert for Admin!</b>\n\n"
                "{E_USERS} <b>User:</b> %s\n"
                "{E_ADMIN} <b>User ID:</b> <code>%d</code>\n"
                "{E_ADMIN} <b>Name:</b> <b>%s</b>\n"
                "{E_MONEY} <b>Amount:</b> <b>%s</b>\n\n"
                "💳 <b>Saved Account Details:</b>\n%s\n\n"
                "📊 <b>Panel Breakdown:</b>\n<code>%s</code>",
                u_mention, u['id'], u.get("first_name", ""), amt_display, acc_details_str, breakdown
            )

            act_kb = {
                "inline_keyboard": [[
                    {"text": "Approve Payment", "callback_data": f"adm_wd:app:{wid}:{u['id']}:{req_pkr}", "icon_custom_emoji_id": ID_TICK, "style": "success"},
                    {"text": "Decline Payment", "callback_data": f"adm_wd:dec:{wid}:{u['id']}:{req_pkr}", "icon_custom_emoji_id": ID_CROSS, "style": "danger"}
                ]]
            }

            def _dispatch_wd_alerts():
                tracked = []
                res_grp = send_raw_html(WithdrawGroupId, group_text, act_kb)
                if res_grp and res_grp.get("ok"):
                    g_mid = res_grp["result"]["message_id"]
                    tracked.append((WithdrawGroupId, g_mid, 0, group_text))

                with config_lock:
                    admins_to_alert = list(AdminIDs)

                for aid in admins_to_alert:
                    res_adm = send_raw_html(aid, admin_inbox_text, act_kb)
                    if res_adm and res_adm.get("ok"):
                        a_mid = res_adm["result"]["message_id"]
                        tracked.append((aid, a_mid, 1, admin_inbox_text))

                with ram_withdraw_tracker_lock:
                    ram_withdraw_tracker[wid] = [
                        {"chat_id": cid, "message_id": mid, "is_admin": is_adm, "base_text": btxt}
                        for cid, mid, is_adm, btxt in tracked
                    ]

                with sqlite_lock:
                    for cid, mid, is_adm, btxt in tracked:
                        sqlite_conn.execute(
                            "INSERT OR REPLACE INTO withdraw_tracker (req_id, chat_id, message_id, is_admin, base_text) VALUES (?, ?, ?, ?, ?)",
                            (wid, cid, mid, is_adm, btxt)
                        )
                    sqlite_conn.commit()

            threading.Thread(target=_dispatch_wd_alerts, daemon=True).start()

            send_raw_html(chat_id, txt("{E_TICK} <b>Withdrawal Request Submitted Successfully!</b>\n\nAmount: <b>%s</b>", amt_display), smart_kb(user_id))
            return

        elif state == "await_wd_bank_name":
            with state_lock:
                user_state[user_id] = f"await_wd_account_no:{text}"
            send_raw_html(chat_id, txt("{E_MOBILE} <b>Please Enter Your Account Number:</b>\n\n<i>Valid Pakistani formats: 03001234567, 3001234567, 923001234567</i>"))
            return

        elif state.startswith("await_wd_account_no:"):
            b_name = state.split(":", 1)[1]
            if not validate_pakistani_number(text):
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid Pakistani Number Format!</b> Please re-enter:"))
                return
            with state_lock:
                user_state[user_id] = f"await_wd_account_name:{b_name}:{text}"
            send_raw_html(chat_id, txt("{E_USERS} <b>Please Enter Correct Account Holder Name:</b>"))
            return

        elif state.startswith("await_wd_account_name:"):
            parts = state.split(":", 2)
            b_name = parts[1]
            acc_no = parts[2]
            acc_name = text
            with state_lock:
                del user_state[user_id]

            wd_acc = {
                "currency": "pkr",
                "bank_name": b_name,
                "account_no": acc_no,
                "account_name": acc_name,
                "is_set": True
            }
            users_collection.update_one({"id": user_id}, {"$set": {"wd_account": wd_acc, "currency": "pkr"}})
            send_raw_html(chat_id, txt("{E_TICK} <b>Withdrawal Account Saved Successfully!</b>\n\n• Bank: %s\n• Acc: <code>%s</code>\n• Name: %s",
                                       b_name, acc_no, acc_name), smart_kb(user_id))
            return

        elif state.startswith("await_wd_wallet_address:"):
            net = state.split(":", 1)[1]
            wallet = text.strip()
            with state_lock:
                del user_state[user_id]
            wd_acc = {
                "currency": "usd",
                "network": net,
                "wallet_addr": wallet,
                "is_set": True
            }
            users_collection.update_one({"id": user_id}, {"$set": {"wd_account": wd_acc, "currency": "usd"}})
            send_raw_html(chat_id, txt("{E_TICK} <b>Withdrawal Account Saved!</b>\n\n• Network: %s\n• Address: <code>%s</code>", net.upper(), wallet), smart_kb(user_id))
            return

        elif state == "adm_await_price":
            with state_lock:
                del user_state[user_id]
            parts = text.split()
            if len(parts) == 1:
                try:
                    p = float(parts[0])
                    stats_collection.update_one({"id": "config"}, {"$set": {"otp_price": p}}, upsert=True)
                    send_raw_html(chat_id, txt("{E_TICK} <b>Global default price updated to: %.2f %s</b>", p, CurrencySymbol), smart_kb(user_id))
                except Exception:
                    send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid numeric parameter.</b>"), smart_kb(user_id))
            elif len(parts) >= 2:
                try:
                    p = float(parts[-1])
                    r_key = "".join(parts[:-1]).lower()
                    stats_collection.update_one({"id": "config"}, {"$set": {f"country_prices.{r_key}": p}}, upsert=True)
                    send_raw_html(chat_id, txt("{E_TICK} <b>Price rate for '%s' configured to: %.2f %s</b>", r_key, p, CurrencySymbol), smart_kb(user_id))
                except Exception:
                    send_raw_html(chat_id, txt("{E_CROSS} <b>Syntax error! Format: Country Price</b>"), smart_kb(user_id))
            return

        elif state == "adm_await_new_admin":
            with state_lock:
                del user_state[user_id]
            try:
                new_aid = int(text)
                with config_lock:
                    if new_aid not in AdminIDs:
                        AdminIDs.append(new_aid)
                sync_config_to_db()
                send_raw_html(chat_id, txt("{E_TICK} <b>Admin Added: %d</b>", new_aid), smart_kb(user_id))
            except Exception:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid Admin ID!</b>"), smart_kb(user_id))
            return

        elif state == "adm_await_new_api":
            with state_lock:
                del user_state[user_id]
            if text.startswith("http"):
                with config_lock:
                    API_Bases.append(text)
                sync_config_to_db()
                send_raw_html(chat_id, txt("{E_TICK} <b>API Endpoint Gateway linked and integrated.</b>"), smart_kb(user_id))
            else:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid URL format!</b>"), smart_kb(user_id))
            return

        elif state == "adm_await_active_range":
            with state_lock:
                del user_state[user_id]
            add_active_range(text.strip())
            send_raw_html(chat_id, txt("{E_TICK} <b>Active range target configured: %s</b>", text.strip()), smart_kb(user_id))
            return

        elif state == "adm_await_new_app":
            with state_lock:
                del user_state[user_id]
            pts = text.split()
            if pts:
                icon_id = pts[-1] if pts[-1].isdigit() and len(pts) > 1 else DefaultAppIconID
                app_n = " ".join(pts[:-1]) if icon_id != DefaultAppIconID else " ".join(pts)
                add_app({"name": app_n, "icon_id": icon_id, "countries": []})
                send_raw_html(chat_id, txt("{E_TICK} <b>Service '%s' added successfully.</b>", app_n), smart_kb(user_id))
            return

        elif state == "adm_await_unpaid_app":
            with state_lock:
                del user_state[user_id]
            add_unpaid_service(text.strip())
            send_raw_html(chat_id, txt("{E_TICK} <b>Service '%s' marked as Unpaid.</b>", text.strip()), smart_kb(user_id))
            return

        elif state.startswith("adm_await_edit_app:"):
            old_app = state.split(":", 1)[1]
            with state_lock:
                del user_state[user_id]
            pts = text.split()
            if pts:
                new_icon = pts[-1] if pts[-1].isdigit() and len(pts) > 1 else DefaultAppIconID
                new_n = " ".join(pts[:-1]) if new_icon != DefaultAppIconID else " ".join(pts)
                update_app(old_app, new_n, new_icon)
                send_raw_html(chat_id, txt("{E_TICK} <b>Service updated successfully.</b>"), smart_kb(user_id))
            return

        elif state.startswith("adm_await_add_app_country:"):
            app_n = state.split(":", 1)[1]
            with state_lock:
                del user_state[user_id]
            add_country_to_app(app_n, text.strip())
            send_raw_html(chat_id, txt("{E_TICK} <b>Country added to service '%s'.</b>", app_n), smart_kb(user_id))
            return

        elif state == "adm_await_check_user_id":
            with state_lock:
                del user_state[user_id]
            try:
                t_uid = int(text)
                target_u = users_collection.find_one({"id": t_uid}) if users_collection is not None else None
                if not target_u:
                    send_raw_html(chat_id, txt("{E_CROSS} <b>User ID %d not found!</b>", t_uid), smart_kb(user_id))
                    return
                exp_bal = target_u.get("total_earned", 0.0) - target_u.get("total_withdrawn", 0.0) - target_u.get("total_spent", 0.0)
                mismatch = abs(target_u.get("balance", 0.0) - exp_bal) > 1.0
                audit_st = txt("{E_CROSS} <b>MISMATCH DETECTED!</b> Expected: %.2f | Stored: %.2f", exp_bal, target_u.get("balance", 0.0)) if mismatch else txt("{E_TICK} <b>Normal (No Mismatch)</b>")
                breakdown = build_withdrawal_breakdown(target_u)
                u_m = f"@{target_u.get('username')}" if target_u.get("username") else f"<code>{target_u.get('id')}</code>"

                rep = txt("{E_CROWN} <b>USER ACCOUNT AUDIT REPORT</b>\n\n"
                          "{E_USERS} <b>User:</b> %s (%s)\n"
                          "{E_ADMIN} <b>User ID:</b> <code>%d</code>\n\n"
                          "{E_MOBILE} <b>Total OTPs:</b> <b>%d</b>\n"
                          "{E_MONEY} <b>Current Balance:</b> <b>%.2f %s</b>\n"
                          "{E_STAR} <b>Total Earned:</b> <b>%.2f %s</b>\n"
                          "{E_GEAR} <b>Withdrawn:</b> <b>%.2f %s</b>\n\n"
                          "{E_STATS} <b>Audit Status:</b>\n%s\n\n"
                          "{E_RECEIPT} <b>Breakdown:</b>\n<code>%s</code>",
                          target_u.get("first_name", ""), u_m, target_u.get("id"),
                          target_u.get("total_otps", 0), target_u.get("balance", 0.0), CurrencySymbol,
                          target_u.get("total_earned", 0.0), CurrencySymbol, target_u.get("total_withdrawn", 0.0), CurrencySymbol,
                          audit_st, breakdown)
                send_raw_html(chat_id, rep, smart_kb(user_id))
            except Exception:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid User ID!</b>"), smart_kb(user_id))
            return

        elif state == "adm_await_add_record":
            with state_lock:
                del user_state[user_id]
            cnt = admin_records_collection.count_documents({}) if admin_records_collection is not None else 0
            n_id = cnt + 1
            admin_records_collection.insert_one({"id": n_id, "text": text, "created_at": datetime.datetime.now()})
            rec_text, rec_kb = get_admin_records_text_and_kb(1)
            send_raw_html(chat_id, txt("{E_TICK} <b>Record #%d saved!</b>\n\n%s", n_id, rec_text), rec_kb)
            return

        elif state == "adm_await_del_record":
            with state_lock:
                del user_state[user_id]
            try:
                rid = int(text)
                admin_records_collection.delete_one({"id": rid})
                rec_text, rec_kb = get_admin_records_text_and_kb(1)
                send_raw_html(chat_id, txt("{E_TICK} <b>Record #%d deleted!</b>\n\n%s", rid, rec_text), rec_kb)
            except Exception:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid Record ID!</b>"), smart_kb(user_id))
            return

        elif state == "adm_await_broadcast":
            with state_lock:
                del user_state[user_id]
            bot_info = session.get(f"https://api.telegram.org/bot{BotToken}/getMe").json()
            b_username = bot_info["result"]["username"] if bot_info.get("ok") else ""
            b_text, p_kb, g_kb = parse_broadcast_payload(b_username, text)

            send_raw_html(chat_id, txt("{E_MEGA} <b>Broadcasting omni payload started in background!</b>"), smart_kb(user_id))
            def _broadcast_thread():
                for g_id in OtpGroupIDs:
                    if g_id:
                        send_copy_message(g_id, chat_id, msg.get("message_id"), g_kb)
                count = 0
                if users_collection is not None:
                    users_list = list(users_collection.find({}, {"id": 1}))
                    for u_item in users_list:
                        time.sleep(0.035)
                        if send_copy_message(u_item["id"], chat_id, msg.get("message_id"), p_kb):
                            count += 1
                send_raw_html(chat_id, txt("{E_TICK} <b>Broadcast successfully finished for %d users!</b>", count), smart_kb(user_id))
            threading.Thread(target=_broadcast_thread, daemon=True).start()
            return

        elif state == "adm_await_country_emojis":
            with state_lock:
                del user_state[user_id]
            batch = parse_emoji_batch(text)
            if not batch:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid input format!</b>\nUse: <code>country:emoji_id</code>"), smart_kb(user_id))
                return

            with ram_custom_emojis_lock:
                for k, v in batch.items():
                    ram_custom_emojis["countries"][k] = v

            if stats_collection is not None:
                set_fields = {f"custom_emojis.countries.{k}": v for k, v in batch.items()}
                stats_collection.update_one({"id": "config"}, {"$set": set_fields}, upsert=True)

            res_txt = txt("{E_TICK} <b>Country Custom Emojis Saved (%d Mulk)!</b>\n\n", len(batch))
            for k, v in batch.items():
                res_txt += f"• <b>{k.capitalize()}:</b> {ce(v, '🏳️')} (<code>{v}</code>)\n"
            send_raw_html(chat_id, res_txt, admin_manage_emojis_kb())
            return

        elif state == "adm_await_service_emojis":
            with state_lock:
                del user_state[user_id]
            batch = parse_emoji_batch(text)
            if not batch:
                send_raw_html(chat_id, txt("{E_CROSS} <b>Invalid input format!</b>\nUse: <code>service:emoji_id</code>"), smart_kb(user_id))
                return

            with ram_custom_emojis_lock:
                for k, v in batch.items():
                    ram_custom_emojis["services"][k] = v

            if stats_collection is not None:
                set_fields = {f"custom_emojis.services.{k}": v for k, v in batch.items()}
                stats_collection.update_one({"id": "config"}, {"$set": set_fields}, upsert=True)

            res_txt = txt("{E_TICK} <b>Service Custom Emojis Saved (%d Services)!</b>\n\n", len(batch))
            for k, v in batch.items():
                res_txt += f"• <b>{k.capitalize()}:</b> {ce(v, '📲')} (<code>{v}</code>)\n"
            send_raw_html(chat_id, res_txt, admin_manage_emojis_kb())
            return

    # Normal Commands
    if text.startswith("/start"):
        arg_part = text.split()[1] if len(text.split()) > 1 else ""
        ref_id = int(arg_part) if arg_part.isdigit() and int(arg_part) != user_id else 0
        u = get_or_create_user(user, ref_id)

        if not u.get("currency") and not u.get("wd_account", {}).get("is_set"):
            w_text = txt("{E_CROWN} <b>Welcome to Premium OTP Bot!</b>\n\nPlease select your preferred display currency:")
            w_kb = {"inline_keyboard": [[
                {"text": "🇵🇰 PKR (Rs)", "callback_data": "set_pref_curr:pkr", "icon_custom_emoji_id": ID_PTICK, "style": "success"},
                {"text": "🇺🇸 USD ($)", "callback_data": "set_pref_curr:usd", "icon_custom_emoji_id": ID_USD, "style": "primary"}
            ]]}
            send_raw_html(chat_id, w_text, w_kb)
            return

        body = txt("{E_CROWN} <b>Welcome to Premium OTP Bot!</b>\n\n"
                   "{E_MOBILE} High quality virtual numbers available instantly.\n"
                   "{E_STAR} Easy earning and fast withdrawals.")
        send_raw_html(chat_id, body, smart_kb(user_id))

    elif text == "Search Prefix" or text.startswith("/prefix"):
        with state_lock:
            user_state[user_id] = "await_prefix_search"
        msg = txt(
            "{E_MOBILE} <b>Search Numbers by Prefix</b>\n\n"
            "Please send the prefix number you want to search.\n"
            "<i>Example:</i> <code>92300</code>, <code>23480</code>, <code>9198</code>\n\n"
            "<i>Minimum: 3 digits | Maximum: 6 digits</i>"
        )
        send_raw_html(chat_id, msg, smart_kb(user_id))

    elif text == "Get Number":
        kb = {"inline_keyboard": [
            [
                {"text": "Active Ranges", "callback_data": "menu:getnum_active", "icon_custom_emoji_id": ID_STAR, "style": "success"},
                {"text": "All Ranges", "callback_data": "menu:getnum_all", "icon_custom_emoji_id": ID_GLOBE, "style": "primary"}
            ],
            [
                {"text": "Active Services", "callback_data": "menu:getnum_apps", "icon_custom_emoji_id": EmojiMobile, "style": "danger"}
            ]
        ]}
        send_raw_html(chat_id, txt("{E_CHANNEL} <b>Select Allocation Route Option:</b>"), kb)

    elif text == "My Account":
        u = get_or_create_user(user)
        curr = get_user_currency(u)
        bal_str = format_balance(u.get("balance", 0.0), curr)
        earned_str = format_balance(u.get("total_earned", 0.0), curr)
        withdrawn_str = format_balance(u.get("total_withdrawn", 0.0), curr)
        acc_text = "<code>Not Set</code>"
        btn_text = "Set Withdraw Account"
        wd = u.get("wd_account", {})
        if wd.get("is_set"):
            btn_text = "Change Withdraw Account"
            if wd.get("currency") == "usd":
                acc_text = f"\n• USD ($) - {wd.get('network', '').upper()}: <code>{wd.get('wallet_addr', '')}</code>"
            else:
                acc_text = f"\n• PKR (Rs) - {wd.get('bank_name')}: <code>{wd.get('account_no')}</code> ({wd.get('account_name')})"

        body = txt("{E_USERS} <b>Your Account Info</b>\n\n"
                   "{E_USERS} Name: <b>%s</b>\n"
                   "{E_ADMIN} ID: <code>%d</code>\n\n"
                   "{E_MOBILE} Total OTPs: <b>%d</b>\n"
                   "{E_MONEY} Balance: <b>%s</b>\n"
                   "{E_STAR} Total Earned: <b>%s</b>\n"
                   "{E_GEAR} Withdrawn: <b>%s</b>\n\n"
                   "{E_CARD} <b>Withdrawal Account:</b> %s",
                   u.get("first_name", ""), u.get("id"), u.get("total_otps", 0),
                   bal_str, earned_str, withdrawn_str, acc_text)
        kb = {"inline_keyboard": [[{"text": btn_text, "callback_data": "menu:setup_wd_acc", "icon_custom_emoji_id": ID_MANAGE, "style": "primary"}]]}
        send_raw_html(chat_id, body, kb)

    elif text == "Withdraw":
        u = get_or_create_user(user)
        if not u.get("wd_account", {}).get("is_set"):
            send_raw_html(chat_id, txt("{E_WARN} <b>Withdrawal Account Not Set!</b>\nGo to <b>My Account</b> -> <b>Set Withdraw Account</b>."), smart_kb(user_id))
            return
        curr = get_user_currency(u)
        is_open = is_withdraw_time()
        bal_pkr = u.get("balance", 0.0)
        min_pkr = get_min_withdraw_amount()
        has_min = (bal_pkr / FixedUSDRate >= 1.0) if curr == "usd" else (bal_pkr >= min_pkr)

        msg = txt("{E_GEAR} <b>Withdraw System</b>\n\n"
                  "{E_MONEY} Available Balance: <b>%s</b>\n"
                  "{E_RECEIPT} Minimum Limit: <b>%.0f</b>\n"
                  "{E_STAR} Status: %s\n\nPayouts will be sent directly to your configured account.",
                  format_balance(bal_pkr, curr), min_pkr,
                  "OPEN" if is_open else "CLOSED")
        kb = None
        if has_min and is_open:
            kb = {"inline_keyboard": [[{"text": "Request Cashout", "callback_data": "user:initiate_wd_v2", "icon_custom_emoji_id": ID_MANAGE, "style": "success"}]]}
        send_raw_html(chat_id, msg, kb)

    elif text == "Stats":
        total_u = users_collection.count_documents({}) if users_collection is not None else 0
        g = get_global_stats()
        msg = txt("{E_STATS} <b>Live Bot Statistics</b>\n\n"
                  "{E_USERS} Total Active Users: <b>%d</b>\n"
                  "{E_MOBILE} Total OTPs Delivered: <b>%d</b>\n"
                  "{E_MONEY} Total Network Earnings: <b>%.2f %s</b>",
                  total_u, g.get("total_otps_received", 0), g.get("total_earnings", 0.0), CurrencySymbol)
        send_raw_html(chat_id, msg, smart_kb(user_id))

    elif text == "Top Users":
        t_text, t_kb = get_top_users_text_and_kb(1)
        send_raw_html(chat_id, t_text, t_kb)

    elif text == "Rewards":
        u = get_or_create_user(user)
        bot_info = session.get(f"https://api.telegram.org/bot{BotToken}/getMe").json()
        b_username = bot_info["result"]["username"] if bot_info.get("ok") else ""
        ref_link = f"https://t.me/{b_username}?start={user_id}"
        team_count = users_collection.count_documents({"referred_by": user_id}) if users_collection is not None else 0
        body = txt("{E_GIFT} <b>Referral Rewards (10%%)</b>\n\n"
                   "{E_CHANNEL} Link: <code>%s</code>\n\n"
                   "{E_USERS} Team: <b>%d</b>\n"
                   "{E_GEAR} Your Ref Earnings: <b>%.2f %s</b>",
                   ref_link, team_count, u.get("referral_earnings_earned", 0.0), CurrencySymbol)
        send_raw_html(chat_id, body, smart_kb(user_id))

    elif text == "Support":
        kb = {"inline_keyboard": [
            [{"text": "Developer", "url": DeveloperLink, "icon_custom_emoji_id": ID_ADMIN, "style": "primary"}],
            [{"text": "Admin Support", "url": AdminSupportLink, "icon_custom_emoji_id": ID_SUPPORT, "style": "success"}]
        ]}
        send_raw_html(chat_id, txt("{E_CHANNEL} <b>Customer Support Channel</b>\n\nWe are available 24/7."), kb)

    elif text == "Main Channel":
        kb = {"inline_keyboard": [
            [{"text": "Main Channel", "url": MainChannelLink, "icon_custom_emoji_id": ID_CHNL, "style": "primary"}],
            [{"text": "OTP Group", "url": OtpGroupInviteLink, "icon_custom_emoji_id": ID_USERS, "style": "success"}],
            [{"text": "Withdraw Proofs", "url": WithdrawProofsLink, "icon_custom_emoji_id": ID_RECEIPT, "style": "danger"}],
            [{"text": "Backup Channel", "url": BckpChnl, "icon_custom_emoji_id": ID_RECEIPT, "style": "primary"}]
        ]}
        send_raw_html(chat_id, txt("{E_MEGA} <b>Our Official Channels & Groups</b>"), kb)

    elif text == "Admin Panel" and isAdmin(user_id):
        send_raw_html(chat_id, txt("{E_ADMIN} <b>Premium Control Center Admin Panel</b>"), admin_kb(1))

def handle_callback(cb: dict):
    user = cb.get("from", {})
    user_id = user.get("id")
    msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    data = cb.get("data", "")

    session.post(f"https://api.telegram.org/bot{BotToken}/answerCallbackQuery", json={"callback_query_id": cb.get("id")}, timeout=5)

    if data.startswith("set_pref_curr:"):
        c_code = data.split(":", 1)[1]
        users_collection.update_one({"id": user_id}, {"$set": {"currency": c_code}})
        edit_raw_html(chat_id, message_id, txt("{E_CROWN} <b>Currency Set to %s!</b>", c_code.upper()))
        send_raw_html(chat_id, txt("{E_ADMIN} Main Menu \n{E_PTICK1}Welcome To Team legend Bot {E_HEART}"), smart_kb(user_id))
        return

    elif data == "menu:getnum_active":
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Active Range Country:</b>"), active_countries_inline_kb(1))
        return

    elif data == "menu:getnum_all":
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Country:</b>"), countries_inline_kb(1))
        return

    elif data == "menu:getnum_apps":
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Active Service:</b>"), active_services_inline_kb(1))
        return

    elif data.startswith("country_page:"):
        p = int(data.split(":")[1])
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Country:</b>"), countries_inline_kb(p))
        return

    elif data.startswith("cgroup_select:"):
        c_name = data.split(":", 1)[1]
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select %s Range/API:</b>", c_name), country_ranges_sub_kb(c_name, 1))
        return

    elif data.startswith("cgroup_subpage:"):
        parts = data.split(":")
        c_name, p = parts[1], int(parts[2])
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select %s Range/API:</b>", c_name), country_ranges_sub_kb(c_name, p))
        return

    elif data.startswith("active_country_page:"):
        p = int(data.split(":")[1])
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Active Range Country:</b>"), active_countries_inline_kb(p))
        return

    elif data.startswith("services_page:"):
        p = int(data.split(":")[1])
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Active Service:</b>"), active_services_inline_kb(p))
        return

    elif data.startswith("app_select:"):
        app_name = data.split(":", 1)[1]
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Country for %s</b>", app_name), app_countries_inline_kb(app_name, 1))
        return

    elif data.startswith("appc_page:"):
        parts = data.split(":")
        app_name, p = parts[1], int(parts[2])
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Country for %s</b>", app_name), app_countries_inline_kb(app_name, p))
        return

    elif data.startswith("pfx_alloc:"):
        parts = data.split(":", 2)
        clean_pfx = parts[1]
        fname = parts[2]

        global_used = get_global_used_numbers()
        now = datetime.datetime.now()
        active_locks = set()
        with ram_user_locks_lock:
            for phone, info in ram_user_locks.items():
                if (now - info["locked_at"]).total_seconds() < 600:
                    active_locks.add(phone)

        matching = []
        with ram_numbers_lock:
            lines = ram_numbers.get(fname, [])
            for line in lines:
                n = line.strip()
                if not n:
                    continue
                if n.lstrip("+").startswith(clean_pfx):
                    if not global_used.get(n, False) and n not in active_locks:
                        matching.append(n)

        if not matching:
            session.post(f"https://api.telegram.org/bot{BotToken}/answerCallbackQuery", json={"callback_query_id": cb.get("id"), "text": "No numbers available right now! Try again.", "show_alert": True})
            return

        random.shuffle(matching)
        selected = matching[:5]
        enforce_user_lock_limit(user_id, len(selected))

        with ram_user_locks_lock:
            for n in selected:
                ram_user_locks[n] = {"user_id": user_id, "country_file": fname, "locked_at": now}

        def _save_pfx_locks():
            with sqlite_lock:
                for n in selected:
                    sqlite_conn.execute("INSERT OR REPLACE INTO user_locks (user_id, phone_number, country_file, locked_at) VALUES (?, ?, ?, ?)",
                                        (user_id, n, fname, now))
                sqlite_conn.commit()
        threading.Thread(target=_save_pfx_locks, daemon=True).start()

        u = get_or_create_user(user)
        price_str = format_price(get_price_for_country(fname), get_user_currency(u))
        with user_without_cc_lock:
            without_cc = user_without_cc.get(user_id, False)

        body = txt("{E_MOBILE} <b>PREFIX ALLOCATION: +%s</b>\n\nHere are the numbers matching your searched prefix. Tap to copy.\n\n<b>Per OTP Price:</b> %s\n⏱️ <i>Refreshed: %s</i>\n\nOTP Will Come Here.",
                   clean_pfx, price_str, now.strftime("%I:%M:%S %p"))
        edit_raw_html(chat_id, message_id, body, numbers_action_kb(f"pfx_{clean_pfx}_{fname}", selected, without_cc))
        return

    elif data.startswith("country_select:") or data.startswith("app_cselect:"):
        fname = data.split(":")[-1]
        valid_nums = get_valid_numbers_for_target(fname)
        if not valid_nums:
            session.post(f"https://api.telegram.org/bot{BotToken}/answerCallbackQuery", json={"callback_query_id": cb.get("id"), "text": "Cool Down.", "show_alert": True})
            return

        random.shuffle(valid_nums)
        selected = valid_nums[:5]
        enforce_user_lock_limit(user_id, len(selected))

        now = datetime.datetime.now()
        num_strings = []
        with ram_user_locks_lock:
            for item in selected:
                num_strings.append(item["phone"])
                ram_user_locks[item["phone"]] = {"user_id": user_id, "country_file": item["file_name"], "locked_at": now}

        def _save_locks():
            with sqlite_lock:
                for item in selected:
                    sqlite_conn.execute("INSERT OR REPLACE INTO user_locks (user_id, phone_number, country_file, locked_at) VALUES (?, ?, ?, ?)",
                                        (user_id, item["phone"], item["file_name"], now))
                sqlite_conn.commit()
        threading.Thread(target=_save_locks, daemon=True).start()

        u = get_or_create_user(user)
        price_str = format_price(get_price_for_country(fname), get_user_currency(u))
        with user_without_cc_lock:
            without_cc = user_without_cc.get(user_id, False)

        body = txt("{E_MOBILE} <b>NUMBERS ALLOCATED</b>\n\nYour Numbers Are Here. Tap To Copy.\n\n<b>Per OTP Price:</b> %s\n⏱️ <i>Refreshed: %s</i>\n\nOTP Will Come Here.",
                   price_str, now.strftime("%I:%M:%S %p"))
        edit_raw_html(chat_id, message_id, body, numbers_action_kb(fname, num_strings, without_cc))
        return

    elif data.startswith("tgcc_toggle:"):
        fname = data.split(":", 1)[1]
        with user_without_cc_lock:
            cur_val = user_without_cc.get(user_id, False)
            new_val = not cur_val
            user_without_cc[user_id] = new_val

        users_collection.update_one({"id": user_id}, {"$set": {"without_cc": new_val}})
        active_nums = get_user_active_numbers(user_id)[-5:]
        edit_raw_html(chat_id, message_id, msg.get("text", ""), numbers_action_kb(fname, active_nums, new_val))
        return

    elif data == "menu:setup_wd_acc":
        kb = {"inline_keyboard": [
            [{"text": "PKR (EasyPaisa/JazzCash/Bank)", "callback_data": "wd_acc_curr:pkr", "icon_custom_emoji_id": ID_PTICK, "style": "success"}],
            [{"text": "USD (USDT Crypto Wallet)", "callback_data": "wd_acc_curr:usd", "icon_custom_emoji_id": ID_USD, "style": "primary"}]
        ]}
        edit_raw_html(chat_id, message_id, txt("{E_MONEY} <b>Select Withdrawal Currency:</b>"), kb)
        return

    elif data == "wd_acc_curr:pkr":
        with state_lock:
            user_state[user_id] = "await_wd_bank_name"
        send_raw_html(chat_id, txt("{E_GEAR} <b>Enter Your Bank or Wallet Name:</b>\n<i>Example: EasyPaisa, JazzCash</i>"))
        return

    elif data == "wd_acc_curr:usd":
        kb = {"inline_keyboard": [[
            {"text": "TRC20 (TRON)", "callback_data": "wd_acc_net:trc20", "icon_custom_emoji_id": ID_LINK, "style": "primary"},
            {"text": "BEP20 (BNB)", "callback_data": "wd_acc_net:bep20", "icon_custom_emoji_id": ID_LINK, "style": "success"}
        ]]}
        edit_raw_html(chat_id, message_id, txt("{E_LINK} <b>Select Crypto Network Protocol:</b>"), kb)
        return

    elif data.startswith("wd_acc_net:"):
        net = data.split(":", 1)[1]
        with state_lock:
            user_state[user_id] = f"await_wd_wallet_address:{net}"
        send_raw_html(chat_id, txt("{E_LINK} <b>Enter Your Correct %s Wallet Address:</b>", net.upper()))
        return

    elif data == "user:initiate_wd_v2":
        u = get_or_create_user(user)
        with state_lock:
            user_state[user_id] = "await_wd_amount_v2"
        curr = get_user_currency(u)
        max_str = f"{u.get('balance', 0.0)/FixedUSDRate:.2f} $" if curr == "usd" else f"{u.get('balance', 0.0):.2f} Rs"
        send_raw_html(chat_id, txt("{E_MONEY} <b>Enter Cashout Amount:</b>\n\nMax Available: <b>%s</b>", max_str))
        return

    elif data.startswith("top_page:"):
        p = int(data.split(":")[1])
        t_text, t_kb = get_top_users_text_and_kb(p)
        edit_raw_html(chat_id, message_id, t_text, t_kb)
        return

    elif data.startswith("top_weekly_page:"):
        p = int(data.split(":")[1])
        t_text, t_kb = get_weekly_top_users_text_and_kb(p)
        edit_raw_html(chat_id, message_id, t_text, t_kb)
        return

    elif data == "menu:change_country":
        kb = {"inline_keyboard": [
            [
                {"text": "Active Ranges", "callback_data": "menu:getnum_active", "icon_custom_emoji_id": ID_STAR, "style": "success"},
                {"text": "All Ranges", "callback_data": "menu:getnum_all", "icon_custom_emoji_id": ID_GLOBE, "style": "primary"}
            ],
            [
                {"text": "Active Services", "callback_data": "menu:getnum_apps", "icon_custom_emoji_id": EmojiMobile, "style": "danger"}
            ]
        ]}
        edit_raw_html(chat_id, message_id, txt("{E_CHANNEL} <b>Select Allocation Route Option:</b>"), kb)
        return

    elif data == "menu:main_close":
        edit_raw_html(chat_id, message_id, txt("{E_TICK} Session closed."))
        return

    # Admin Callbacks
    elif data.startswith("adm_page:") and isAdmin(user_id):
        p = int(data.split(":")[1])
        edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Premium Control Center Admin Panel</b>"), admin_kb(p))
        return

    elif data.startswith("adm_services_page:") and isAdmin(user_id):
        p = int(data.split(":")[1])
        edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Active Services Dashboard</b>"), admin_manage_services_kb(p))
        return

    elif data == "menu:back_to_admin" and isAdmin(user_id):
        edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Premium Control Center Admin Panel</b>"), admin_kb(1))
        return

    elif data.startswith("adm_flow:") and isAdmin(user_id):
        flow = data.split(":", 1)[1]
        if flow == "broadcast":
            with state_lock:
                user_state[user_id] = "adm_await_broadcast"
            send_raw_html(chat_id, txt("{E_MOBILE} Send broadcast payload message text:"))
        elif flow == "check_user_trig":
            with state_lock:
                user_state[user_id] = "adm_await_check_user_id"
            send_raw_html(chat_id, txt("{E_USERS} <b>Enter Target Telegram User ID:</b>"))
        elif flow.startswith("admin_records:"):
            p = int(flow.split(":")[1])
            t, k = get_admin_records_text_and_kb(p)
            edit_raw_html(chat_id, message_id, t, k)
        elif flow == "manage_withdraw":
            edit_raw_html(chat_id, message_id, txt("{E_GEAR} <b>Withdrawal Management Panel</b>"), admin_manage_withdraw_kb())
        elif flow == "set_min_wd_trig":
            with state_lock:
                user_state[user_id] = "adm_await_min_wd"
            send_raw_html(chat_id, txt("{E_MONEY} <b>Enter new Minimum Withdraw amount:</b>"))
        elif flow == "set_wd_time_trig":
            with state_lock:
                user_state[user_id] = "adm_await_wd_time"
            send_raw_html(chat_id, txt("{E_GEAR} <b>Enter Withdraw Time range:</b>\nExample: <code>5PM 8PM</code>"))
        elif flow == "manage_price":
            edit_raw_html(chat_id, message_id, txt("{E_GEAR} <b>Rate Setup Dashboard</b>"), admin_manage_prices_kb(1))
        elif flow == "set_price_trigger":
            with state_lock:
                user_state[user_id] = "adm_await_price"
            send_raw_html(chat_id, "<b>Set Price Parameters:</b>\nSend global numeric (e.g. <code>2.5</code>) or specific (e.g. <code>Pakistan 3</code>)")
        elif flow == "manage_active_ranges":
            edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Active Ranges Control Dashboard</b>"), admin_active_ranges_kb(1))
        elif flow == "add_active_range_trigger":
            with state_lock:
                user_state[user_id] = "adm_await_active_range"
            send_raw_html(chat_id, txt("{E_DASH} Input Range Identifier String (e.g. <code>Pakistan1</code>):"))
        elif flow == "manage_active_apps":
            edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Active Services Dashboard</b>"), admin_manage_services_kb(1))
        elif flow == "add_app_trigger":
            with state_lock:
                user_state[user_id] = "adm_await_new_app"
            send_raw_html(chat_id, "Send service name and optional icon ID (e.g. <code>Telegram 6237864166879663987</code>):")
        elif flow == "manage_unpaid":
            edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Unpaid Services Dashboard</b>"), admin_manage_unpaid_kb(1))
        elif flow == "add_unpaid_trigger":
            with state_lock:
                user_state[user_id] = "adm_await_unpaid_app"
            send_raw_html(chat_id, txt("{E_DASH} Send exact service name to mark unpaid:"))
        elif flow == "manage_admins":
            edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Administrators Access Registry</b>"), admin_manage_admins_kb())
        elif flow == "add_admin_trigger":
            with state_lock:
                user_state[user_id] = "adm_await_new_admin"
            send_raw_html(chat_id, txt("{E_USERS} Provide Telegram User ID for new admin:"))
        elif flow == "manage_apis":
            edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>API Endpoint Infrastructure Access</b>"), admin_manage_apis_kb(1))
        elif flow == "add_api_trigger":
            with state_lock:
                user_state[user_id] = "adm_await_new_api"
            send_raw_html(chat_id, txt("{E_CHANNEL} Input Smart API Base URL string:"))
        elif flow == "live_stats":
            tot_u = users_collection.count_documents({}) if users_collection is not None else 0
            g = get_global_stats()
            t_nums = sum(len(lines) for lines in ram_numbers.values())
            st_text = txt("{E_STATS} <b>Dashboard Metrics Engine</b>\n\n"
                          "{E_USERS} Total Users: <b>%d</b>\n"
                          "{E_MOBILE} Loaded Numbers: <b>%d</b>\n"
                          "{E_STATS} Processed OTPs: <b>%d</b>\n"
                          "{E_MONEY} Total Network Earnings: <b>%.2f %s</b>\n"
                          "{E_GEAR} Withdrawn Overall: <b>%.2f %s</b>",
                          tot_u, t_nums, g.get("total_otps_received", 0),
                          g.get("total_earnings", 0.0), CurrencySymbol,
                          g.get("total_withdrawn", 0.0), CurrencySymbol)
            edit_raw_html(chat_id, message_id, st_text, admin_kb(1))
        elif flow == "manage_ivas":
            edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>IVAS Dedicated Numbers Manager</b>"), admin_ivas_manage_kb())
        elif flow == "add_record_trig":
            with state_lock:
                user_state[user_id] = "adm_await_add_record"
            send_raw_html(chat_id, txt("{E_RECEIPT} <b>Send accounting record text payload:</b>"))
        elif flow == "del_record_trig":
            with state_lock:
                user_state[user_id] = "adm_await_del_record"
            send_raw_html(chat_id, txt("{E_TRASH} <b>Send Record ID number to delete:</b>"))
        elif flow == "manage_emojis":
            edit_raw_html(chat_id, message_id, txt("{E_CROWN} <b>Dynamic Custom Emoji Management</b>\n\nConfigure custom country flags and app icons without editing code:"), admin_manage_emojis_kb())
        elif flow == "add_country_emoji_trig":
            with state_lock:
                user_state[user_id] = "adm_await_country_emojis"
            send_raw_html(chat_id, txt("{E_DASH} <b>Send Country Emojis (Single or Multi-Line):</b>\n\n"
                                       "Format:\n<code>country_name:emoji_id</code>\n\n"
                                       "<i>Example:</i>\n<code>pakistan:5269660289321679111\nindia:5447419223242449630</code>"))
        elif flow == "add_service_emoji_trig":
            with state_lock:
                user_state[user_id] = "adm_await_service_emojis"
            send_raw_html(chat_id, txt("{E_DASH} <b>Send Service Emojis (Single or Multi-Line):</b>\n\n"
                                       "Format:\n<code>service_name:emoji_id</code>\n\n"
                                       "<i>Example:</i>\n<code>telegram:5330237710655306682\nwhatsapp:5334998226636390258</code>"))
        elif flow == "view_custom_emojis":
            with ram_custom_emojis_lock:
                c_map = dict(ram_custom_emojis["countries"])
                s_map = dict(ram_custom_emojis["services"])
            v_text = txt("{E_CROWN} <b>Current Active Custom Emojis:</b>\n\n")
            v_text += "🚩 <b>Countries:</b>\n"
            if c_map:
                for k, v in c_map.items():
                    v_text += f"• {k.capitalize()}: {ce(v, '🏳️')} (<code>{v}</code>)\n"
            else:
                v_text += "<i>Using standard code defaults.</i>\n"
            v_text += "\n📲 <b>Services:</b>\n"
            if s_map:
                for k, v in s_map.items():
                    v_text += f"• {k.capitalize()}: {ce(v, '📲')} (<code>{v}</code>)\n"
            else:
                v_text += "<i>Using standard code defaults.</i>\n"
            edit_raw_html(chat_id, message_id, v_text, admin_manage_emojis_kb())
        elif flow == "reset_custom_emojis":
            with ram_custom_emojis_lock:
                ram_custom_emojis["countries"] = {}
                ram_custom_emojis["services"] = {}
            if stats_collection is not None:
                stats_collection.update_one({"id": "config"}, {"$unset": {"custom_emojis": ""}})
            edit_raw_html(chat_id, message_id, txt("{E_TICK} <b>All Custom Emojis have been reset to default!</b>"), admin_manage_emojis_kb())
        elif flow == "download_backup":
            send_raw_html(chat_id, txt("{E_LOADER} <b>Generating Full System & Database Backup...</b>\nPlease wait a moment."))
            threading.Thread(target=create_and_send_backup, args=(chat_id,), daemon=True).start()
        return

    elif data.startswith("adm_del_price:") and isAdmin(user_id):
        k = data.split(":", 1)[1]
        delete_custom_price(k)
        edit_raw_html(chat_id, message_id, txt("{E_TICK} <b>Price reset for %s</b>", k), admin_manage_prices_kb(1))
        return

    elif data.startswith("adm_del_range:") and isAdmin(user_id):
        remove_active_range(data.split(":", 1)[1])
        edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Active Ranges Control Dashboard</b>"), admin_active_ranges_kb(1))
        return

    elif data.startswith("adm_del_unpaid:") and isAdmin(user_id):
        remove_unpaid_service(data.split(":", 1)[1])
        edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Unpaid Services Dashboard</b>"), admin_manage_unpaid_kb(1))
        return

    elif data.startswith("adm_del_admin:") and isAdmin(user_id):
        target_aid = int(data.split(":", 1)[1])
        with config_lock:
            if target_aid in AdminIDs:
                AdminIDs.remove(target_aid)
        sync_config_to_db()
        edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>Administrators Access Registry</b>"), admin_manage_admins_kb())
        return

    elif data.startswith("adm_del_api:") and isAdmin(user_id):
        target_idx = int(data.split(":", 1)[1])
        with config_lock:
            if 0 <= target_idx < len(API_Bases):
                API_Bases.pop(target_idx)
        sync_config_to_db()
        edit_raw_html(chat_id, message_id, txt("{E_ADMIN} <b>API Endpoint Access</b>"), admin_manage_apis_kb(1))
        return

    elif data.startswith("app_adm:") and isAdmin(user_id):
        app_n = data.split(":", 1)[1]
        edit_raw_html(chat_id, message_id, txt("{E_GEAR} <b>Manage Service: %s</b>", app_n), admin_edit_service_kb(app_n))
        return

    elif data.startswith("app_delete:") and isAdmin(user_id):
        delete_app_by_name(data.split(":", 1)[1])
        edit_raw_html(chat_id, message_id, txt("{E_TICK} Service deleted."), admin_manage_services_kb(1))
        return

    elif data.startswith("app_delcountry:") and isAdmin(user_id):
        parts = data.split(":", 2)
        remove_country_from_app(parts[1], parts[2])
        edit_raw_html(chat_id, message_id, txt("{E_GEAR} <b>Manage Service: %s</b>", parts[1]), admin_edit_service_kb(parts[1]))
        return

    elif data.startswith("app_edit:") and isAdmin(user_id):
        app_n = data.split(":", 1)[1]
        with state_lock:
            user_state[user_id] = f"adm_await_edit_app:{app_n}"
        send_raw_html(chat_id, f"Send new name and optional icon ID for <b>{app_n}</b>:")
        return

    elif data.startswith("app_addcountry:") and isAdmin(user_id):
        app_n = data.split(":", 1)[1]
        with state_lock:
            user_state[user_id] = f"adm_await_add_app_country:{app_n}"
        send_raw_html(chat_id, f"Send country identifier to add to <b>{app_n}</b>:")
        return

    elif data.startswith("ivas_view_c:") and isAdmin(user_id):
        c_name = data.split(":", 1)[1]
        edit_raw_html(chat_id, message_id, txt("{E_GEAR} <b>Managing Ranges for %s</b>", c_name), admin_ivas_country_ranges_kb(c_name))
        return

    elif data.startswith("ivas_del_range:") and isAdmin(user_id):
        f_name = data.split(":", 1)[1]
        f_path = os.path.join(FilesDir, f_name)
        if os.path.exists(f_path):
            os.remove(f_path)
        with ram_numbers_lock:
            ram_numbers.pop(f_name, None)
        edit_raw_html(chat_id, message_id, txt("{E_TICK} Range deleted: <code>%s</code>", f_name), admin_ivas_manage_kb())
        return

    elif data == "ivas_add_country_trig" and isAdmin(user_id):
        with state_lock:
            user_state[user_id] = "ivas_await_upload"
        send_raw_html(chat_id, txt("{E_DASH} <b>Upload your IVAS File (.xlsx, .zip, or .txt):</b>"))
        return

    elif data.startswith("adm_wd:") and isAdmin(user_id):
        parts = data.split(":")
        if len(parts) >= 5:
            act_token = parts[1]
            wid = parts[2]
            target_uid = int(parts[3])
            amt = float(parts[4])
        else:
            act_token = parts[1]
            wid = f"{parts[2]}_legacy"
            target_uid = int(parts[2])
            amt = float(parts[3])

        act = "approve" if act_token in ["app", "approve"] else "decline"

        with ram_processed_withdrawals_lock:
            if wid in ram_processed_withdrawals:
                session.post(f"https://api.telegram.org/bot{BotToken}/answerCallbackQuery", json={
                    "callback_query_id": cb.get("id"),
                    "text": f"⚠️ Already processed as {ram_processed_withdrawals[wid].upper()}!",
                    "show_alert": True
                })
                return
            ram_processed_withdrawals[wid] = act

        with sqlite_lock:
            sqlite_conn.execute("INSERT OR REPLACE INTO processed_withdrawals (req_id, status, processed_at) VALUES (?, ?, ?)",
                                (wid, act, datetime.datetime.now()))
            sqlite_conn.commit()

        if act == "approve":
            users_collection.update_one(
                {"id": target_uid},
                {"$inc": {"total_withdrawn": amt}, "$set": {"api_cycle_otps": {}, "api_cycle_earnings": {}}}
            )
            g = get_global_stats()
            g["total_withdrawn"] = g.get("total_withdrawn", 0.0) + amt
            update_global_stats(g)
            send_raw_html(target_uid, txt("{E_TICK} <b>Withdraw Approved!</b> %.2f %s transferred.", amt, CurrencySymbol), smart_kb(target_uid))
            status_line = txt("\n\n{E_PTICK1} <b>STATUS: APPROVED</b> {E_TICK}")
        else:
            users_collection.update_one({"id": target_uid}, {"$inc": {"balance": amt}})
            send_raw_html(target_uid, txt("{E_CROSS} <b>Withdraw Declined!</b> %.2f %s returned to balance.", amt, CurrencySymbol), smart_kb(target_uid))
            status_line = txt("\n\n{E_CROSS} <b>STATUS: DECLINED</b> {E_CROSS2}")

        tracked_msgs = []
        with ram_withdraw_tracker_lock:
            tracked_msgs = list(ram_withdraw_tracker.get(wid, []))

        if not tracked_msgs:
            with sqlite_lock:
                cur = sqlite_conn.execute("SELECT chat_id, message_id, is_admin, base_text FROM withdraw_tracker WHERE req_id = ?", (wid,))
                for cid, mid, is_adm, btxt in cur.fetchall():
                    tracked_msgs.append({"chat_id": cid, "message_id": mid, "is_admin": is_adm, "base_text": btxt})

        if tracked_msgs:
            def _sync_edit_all():
                for m_item in tracked_msgs:
                    cid = m_item["chat_id"]
                    mid = m_item["message_id"]
                    base = m_item["base_text"]
                    updated_text = base + status_line
                    edit_raw_html(cid, mid, updated_text, reply_markup=None)
            threading.Thread(target=_sync_edit_all, daemon=True).start()
        else:
            current_text = msg.get("text", "")
            edit_raw_html(chat_id, message_id, current_text + status_line, reply_markup=None)
        return

user_workers = {}
user_workers_lock = threading.Lock()

def dispatch_update(update: dict):
    msg = update.get("message")
    cb = update.get("callback_query")
    user_id = (msg.get("from") or {}).get("id") if msg else ((cb.get("from") or {}).get("id") if cb else 0)

    if not user_id:
        return

    with user_workers_lock:
        if user_id not in user_workers:
            q = Queue(maxsize=10)
            user_workers[user_id] = q

            def _dedicated_worker(uid, queue_ref):
                while True:
                    try:
                        upd = queue_ref.get(timeout=30)
                        if upd.get("callback_query"):
                            handle_callback(upd["callback_query"])
                        elif upd.get("message"):
                            m = upd["message"]
                            if m.get("document"):
                                handle_document_message(m)
                            else:
                                handle_text_message(m)
                    except Empty:
                        with user_workers_lock:
                            user_workers.pop(uid, None)
                        break
                    except Exception as e:
                        logger.error(f"Worker exception for user {uid}: {e}")

            threading.Thread(target=_dedicated_worker, args=(user_id, q), daemon=True).start()

    try:
        user_workers[user_id].put_nowait(update)
    except Exception:
        pass

def main():
    logger.info("Initializing system...")
    init_storage()

    bot_info = session.get(f"https://api.telegram.org/bot{BotToken}/getMe").json()
    if not bot_info.get("ok"):
        logger.error("Failed to connect to Telegram Bot API. Verify BotToken.")
        return

    bot_username = bot_info["result"]["username"]
    logger.info(f"Bot Operational: @{bot_username}")
    start_background_workers(bot_username)

    offset = 0
    while True:
        try:
            res = session.get(f"https://api.telegram.org/bot{BotToken}/getUpdates",
                              params={"offset": offset, "timeout": 45}, timeout=50).json()
            if not res.get("ok"):
                time.sleep(3)
                continue

            for upd in res.get("result", []):
                offset = max(offset, upd["update_id"] + 1)
                dispatch_update(upd)
        except Exception as e:
            logger.error(f"Polling loop exception: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
