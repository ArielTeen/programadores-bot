# ─── Esquemas SQL para todas las tablas del bot ──────────────────────────────

GUILD_CONFIG = """
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id INTEGER PRIMARY KEY,
    prefix TEXT DEFAULT '!',
    language TEXT DEFAULT 'es',
    mod_log_channel INTEGER,
    mod_ping_role INTEGER,
    mute_role INTEGER,
    suggested_channel INTEGER,
    report_channel INTEGER,
    welcome_channel INTEGER,
    goodbye_channel INTEGER,
    welcome_message TEXT DEFAULT 'Bienvenido {user} a **{guild}**!',
    goodbye_message TEXT DEFAULT '{user} ha abandonado el servidor.',
    welcome_image TEXT,
    welcome_enabled INTEGER DEFAULT 1,
    goodbye_enabled INTEGER DEFAULT 1,
    ticket_category INTEGER,
    ticket_log_channel INTEGER,
    ticket_open_limit INTEGER DEFAULT 3,
    ticket_enabled INTEGER DEFAULT 1,
    verify_channel INTEGER,
    verify_role INTEGER,
    verify_enabled INTEGER DEFAULT 0,
    verify_captcha INTEGER DEFAULT 0,
    level_enabled INTEGER DEFAULT 1,
    level_message TEXT DEFAULT '{user} ha subido al nivel **{level}**!',
    level_channel INTEGER,
    economy_enabled INTEGER DEFAULT 1,
    rep_enabled INTEGER DEFAULT 1,
    rep_cooldown INTEGER DEFAULT 43200,
    rep_channel INTEGER DEFAULT 0,
    rep_log_channel INTEGER DEFAULT 0,
    rep_max_per_user INTEGER DEFAULT 100,
    rep_min_level INTEGER DEFAULT 0,
    rep_staff_only INTEGER DEFAULT 0,
    temp_voice_enabled INTEGER DEFAULT 0,
    temp_voice_category INTEGER,
    temp_voice_channel INTEGER,
    custom_commands_enabled INTEGER DEFAULT 1,
    log_config TEXT DEFAULT '{}',
    staff_roles TEXT DEFAULT '[]',
    automod_enabled INTEGER DEFAULT 0,
    automod_config TEXT DEFAULT '{}',
    antinuke_enabled INTEGER DEFAULT 0,
    antinuke_config TEXT DEFAULT '{}',
    antinuke_trusted TEXT DEFAULT '[]',
    suggestions_enabled INTEGER DEFAULT 1,
    reports_enabled INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

MEMBERS = """
CREATE TABLE IF NOT EXISTS members (
    user_id INTEGER,
    guild_id INTEGER,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    total_xp INTEGER DEFAULT 0,
    voice_xp INTEGER DEFAULT 0,
    reputation INTEGER DEFAULT 0,
    rep_given INTEGER DEFAULT 0,
    balance INTEGER DEFAULT 100,
    bank INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,
    last_xp_time REAL DEFAULT 0,
    last_rep_time REAL DEFAULT 0,
    last_daily_time REAL DEFAULT 0,
    last_weekly_time REAL DEFAULT 0,
    last_work_time REAL DEFAULT 0,
    last_crime_time REAL DEFAULT 0,
    warns INTEGER DEFAULT 0,
    afk_message TEXT,
    afk_since REAL,
    joined_at TEXT,
    PRIMARY KEY (user_id, guild_id)
)
"""

WARNINGS = """
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER DEFAULT 1,
    user_id INTEGER,
    guild_id INTEGER,
    moderator_id INTEGER,
    reason TEXT DEFAULT 'No especificada',
    timestamp REAL,
    active INTEGER DEFAULT 1
)
"""

CASES = """
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    case_number INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    action_type TEXT,
    reason TEXT,
    duration TEXT,
    timestamp REAL
)
"""

TICKETS = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    channel_id INTEGER,
    user_id INTEGER,
    claimer_id INTEGER DEFAULT 0,
    status TEXT DEFAULT 'open',
    category TEXT DEFAULT 'general',
    subject TEXT DEFAULT 'Soporte',
    created_at REAL,
    closed_at REAL,
    rating INTEGER DEFAULT 0,
    closed_by INTEGER
)
"""

TICKET_MESSAGES = """
CREATE TABLE IF NOT EXISTS ticket_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    author_id INTEGER,
    content TEXT,
    timestamp REAL,
    attachment_url TEXT
)
"""

SHOP_ITEMS = """
CREATE TABLE IF NOT EXISTS shop_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    name TEXT,
    description TEXT,
    role_id INTEGER,
    price INTEGER,
    emoji TEXT DEFAULT '🎁',
    color TEXT DEFAULT '#5865F2',
    quantity INTEGER DEFAULT -1
)
"""

INVENTORY = """
CREATE TABLE IF NOT EXISTS inventories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    guild_id INTEGER,
    item_id INTEGER,
    purchased_at REAL,
    equipped INTEGER DEFAULT 0
)
"""

LEVEL_ROLES = """
CREATE TABLE IF NOT EXISTS level_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    level INTEGER,
    role_id INTEGER,
    UNIQUE(guild_id, level)
)
"""

MUTED_USERS = """
CREATE TABLE IF NOT EXISTS muted_users (
    user_id INTEGER,
    guild_id INTEGER,
    end_time REAL,
    PRIMARY KEY (user_id, guild_id)
)
"""

REACTION_ROLES = """
CREATE TABLE IF NOT EXISTS reaction_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    channel_id INTEGER,
    message_id INTEGER,
    role_id INTEGER,
    emoji TEXT,
    type TEXT DEFAULT 'reaction'
)
"""

SUGGESTIONS = """
CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    message_id INTEGER,
    author_id INTEGER,
    content TEXT,
    status TEXT DEFAULT 'pending',
    created_at REAL,
    response TEXT
)
"""

REPORTS = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    message_id INTEGER,
    reporter_id INTEGER,
    target_id INTEGER,
    reason TEXT,
    report_type TEXT DEFAULT 'user',
    status TEXT DEFAULT 'pending',
    created_at REAL,
    resolved_by INTEGER,
    resolution TEXT
)
"""

GIVEAWAYS = """
CREATE TABLE IF NOT EXISTS giveaways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    channel_id INTEGER,
    message_id INTEGER,
    prize TEXT,
    winners INTEGER DEFAULT 1,
    end_time REAL,
    hosted_by INTEGER,
    finished INTEGER DEFAULT 0,
    requirements TEXT DEFAULT '{}'
)
"""

GIVEAWAY_ENTRIES = """
CREATE TABLE IF NOT EXISTS giveaway_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    giveaway_id INTEGER,
    user_id INTEGER,
    entered_at REAL
)
"""

VERIFICATION = """
CREATE TABLE IF NOT EXISTS verification (
    user_id INTEGER,
    guild_id INTEGER,
    verified_at REAL,
    captcha TEXT,
    PRIMARY KEY (user_id, guild_id)
)
"""

AUTOMOD_BLACKLIST = """
CREATE TABLE IF NOT EXISTS automod_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    word TEXT,
    created_at REAL
)
"""

AUTOMOD_WHITELIST = """
CREATE TABLE IF NOT EXISTS automod_whitelist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    role_id INTEGER,
    type TEXT DEFAULT 'role',
    UNIQUE(guild_id, role_id, type)
)
"""

ANTINUKE_TRUSTED = """
CREATE TABLE IF NOT EXISTS antinuke_trusted (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    added_by INTEGER,
    added_at REAL
)
"""

ANTINUKE_LOGS = """
CREATE TABLE IF NOT EXISTS antinuke_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    action_type TEXT,
    user_id INTEGER,
    action_detail TEXT,
    timestamp REAL
)
"""

LOG_CONFIG = """
CREATE TABLE IF NOT EXISTS log_config (
    guild_id INTEGER,
    module TEXT,
    channel_id INTEGER,
    enabled INTEGER DEFAULT 1,
    PRIMARY KEY (guild_id, module)
)
"""

DASHBOARD_SESSIONS = """
CREATE TABLE IF NOT EXISTS dashboard_sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    expires_at REAL,
    created_at REAL
)
"""

REP_HISTORY = """
CREATE TABLE IF NOT EXISTS rep_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    from_user_id INTEGER,
    to_user_id INTEGER,
    timestamp REAL,
    reason TEXT DEFAULT ''
)
"""

REP_ROLES = """
CREATE TABLE IF NOT EXISTS rep_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    rep INTEGER,
    role_id INTEGER,
    UNIQUE(guild_id, rep)
)
"""

CUSTOM_COMMANDS = """
CREATE TABLE IF NOT EXISTS custom_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    name TEXT,
    type TEXT DEFAULT 'text',
    content TEXT,
    embed_title TEXT,
    embed_description TEXT,
    embed_color TEXT,
    embed_footer TEXT,
    embed_image TEXT,
    embed_thumbnail TEXT,
    role_required INTEGER DEFAULT 0,
    cooldown INTEGER DEFAULT 0,
    uses INTEGER DEFAULT 0,
    created_at REAL,
    created_by INTEGER
)
"""

TEMP_VOICE = """
CREATE TABLE IF NOT EXISTS temp_voice (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    channel_id INTEGER,
    owner_id INTEGER,
    created_at REAL,
    name TEXT,
    user_limit INTEGER DEFAULT 0,
    bitrate INTEGER DEFAULT 64000
)
"""

DASHBOARD_AUDIT = """
CREATE TABLE IF NOT EXISTS dashboard_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    action TEXT,
    module TEXT,
    details TEXT,
    timestamp REAL
)
"""

ALL_TABLES = [
    GUILD_CONFIG, MEMBERS, WARNINGS, CASES,
    TICKETS, TICKET_MESSAGES,
    SHOP_ITEMS, INVENTORY, LEVEL_ROLES,
    MUTED_USERS, REACTION_ROLES,
    SUGGESTIONS, REPORTS,
    GIVEAWAYS, GIVEAWAY_ENTRIES,
    VERIFICATION, AUTOMOD_BLACKLIST, AUTOMOD_WHITELIST,
    ANTINUKE_TRUSTED, ANTINUKE_LOGS,
    LOG_CONFIG, DASHBOARD_SESSIONS,
    REP_HISTORY, REP_ROLES,
    CUSTOM_COMMANDS, TEMP_VOICE, DASHBOARD_AUDIT,
]
