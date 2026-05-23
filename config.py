import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
PREFIX = os.getenv("PREFIX", "!")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/bot.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5000")
DASHBOARD_SECRET = os.getenv("DASHBOARD_SECRET", "change_this")

COLORS = {
    "default": 0x7C3AED,
    "success": 0x34D399,
    "error": 0xF87171,
    "warning": 0xFBBF24,
    "pink": 0xD946EF,
    "purple": 0x7C3AED,
    "orange": 0xFB923C,
    "green": 0x34D399,
    "red": 0xF87171,
    "blue": 0x4A7DFF,
    "gold": 0xFBBF24,
    "turquoise": 0x2DD4BF,
    "dark": 0x0B1225,
    "darker": 0x060B18,
    "cyan": 0x22D3EE,
    "indigo": 0x818CF8,
}

EMBED_COLOR = COLORS["purple"]
SUCCESS_COLOR = COLORS["success"]
ERROR_COLOR = COLORS["error"]
WARNING_COLOR = COLORS["warning"]

MAX_WARNINGS = 3
MUTE_ROLE_NAME = "Muted"
DEFAULT_DELETE_DAYS = 0
MAX_PURGE = 1000
STAFF_ROLES_DEFAULT = []

FLOOD_WINDOW = 5
FLOOD_LIMIT = 5
MAX_MENTIONS = 5
MAX_LINKS = 3
MAX_CAPS_PERCENT = 70
MAX_EMOJI_COUNT = 5
RAID_JOIN_LIMIT = 5
RAID_WINDOW = 10
ALT_ACCOUNT_AGE = 7

ANTINUKE_CHANNEL_LIMIT = 3
ANTINUKE_ROLE_LIMIT = 3
ANTINUKE_BAN_LIMIT = 3
ANTINUKE_KICK_LIMIT = 3
ANTINUKE_WINDOW = 10

REP_COOLDOWN = 43200
REP_MAX_PER_USER = 100
REP_MIN_LEVEL = 0
REP_STAFF_ONLY = 0
REP_HISTORY_LIMIT = 100

XP_PER_MESSAGE = 15
XP_PER_VOICE_MINUTE = 10
XP_COOLDOWN = 60
LEVEL_MULTIPLIER = 2
XP_VOICE_CHANCE = 0.5

DAILY_REWARD = 100
WEEKLY_REWARD = 500
WORK_MIN = 10
WORK_MAX = 50
CRIME_MIN = 20
CRIME_MAX = 100
CRIME_FAIL_CHANCE = 0.4
ROB_MIN = 5
ROB_MAX = 30
ROB_FAIL_CHANCE = 0.5
STARTING_BALANCE = 100
BANK_INTEREST = 0.01
SLOTS_COST = 10
SLOTS_MULTIPLIERS = {1: 0, 2: 0.5, 3: 2, 4: 5, 5: 10}
COINFLIP_COST = 10
ROULETTE_MAX = 1000

TICKET_CATEGORY_NAME = "Tickets"
TICKET_LOG_CHANNEL_NAME = "ticket-logs"
TICKET_OPEN_LIMIT = 3

WELCOME_DEFAULT_MESSAGE = "Bienvenido {user} a **{guild}**!"
GOODBYE_DEFAULT_MESSAGE = "{user} ha abandonado el servidor."

LOG_IGNORED_CHANNELS = []
LOG_MODULE_DEFAULTS = {
    "messages": True,
    "members": True,
    "moderation": True,
    "channels": True,
    "roles": True,
    "voice": True,
    "invites": True,
    "automod": True,
    "antinuke": True,
    "commands": False,
}

MUSIC_VOLUME_DEFAULT = 50
MUSIC_MAX_QUEUE = 50
MUSIC_TIMEOUT = 300

VERIFY_TIMEOUT = 120
VERIFY_CAPTCHA_LENGTH = 6

GIVEAWAY_DEFAULT_DURATION = 3600
GIVEAWAY_MAX_DURATION = 604800
GIVEAWAY_MIN_WINNERS = 1
GIVEAWAY_MAX_WINNERS = 20

DASHBOARD_OAUTH2_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={DASHBOARD_URL}/callback&response_type=code&scope=identify%20guilds"
DASHBOARD_API_ENDPOINT = "https://discord.com/api/v10"
