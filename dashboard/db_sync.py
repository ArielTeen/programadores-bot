import sqlite3
import json
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bot.db")


def get(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetchone(sql, *params):
    conn = get()
    try:
        return dict(conn.execute(sql, params).fetchone() or {})
    finally:
        conn.close()


def fetchall(sql, *params):
    conn = get()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def execute(sql, *params):
    conn = get()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur
    finally:
        conn.close()


def get_guild(guild_id):
    row = fetchone("SELECT * FROM guild_config WHERE guild_id = ?", guild_id)
    if not row:
        execute("INSERT INTO guild_config (guild_id) VALUES (?)", guild_id)
        return {"guild_id": guild_id}
    for key in ("staff_roles", "log_config", "automod_config", "antinuke_config", "antinuke_trusted"):
        if key in row and isinstance(row[key], str):
            try:
                row[key] = json.loads(row[key])
            except:
                row[key] = [] if key != "log_config" else {}
    return row


def update_guild(guild_id, **kwargs):
    clean = {}
    for k, v in kwargs.items():
        if isinstance(v, (list, dict)):
            clean[k] = json.dumps(v)
        elif isinstance(v, bool):
            clean[k] = int(v)
        else:
            clean[k] = v
    if not clean:
        return
    sets = ", ".join(f"{k} = ?" for k in clean)
    vals = list(clean.values()) + [guild_id]
    execute(f"UPDATE guild_config SET {sets} WHERE guild_id = ?", *vals)


def get_leaderboard(guild_id, stat, limit=20):
    col = {"total_xp": "total_xp", "balance": "balance", "reputation": "reputation"}
    c = col.get(stat, "total_xp")
    return fetchall(
        f"SELECT user_id, {c} as value, level FROM members WHERE guild_id = ? ORDER BY {c} DESC LIMIT ?",
        guild_id, limit
    )


def get_rep_stats(guild_id):
    return fetchone(
        "SELECT COUNT(*) as total_given, COUNT(DISTINCT from_user_id) as total_users FROM rep_history WHERE guild_id = ? AND timestamp > ?",
        guild_id, 0
    )


def get_rep_history(guild_id, user_id, limit=5):
    if user_id:
        return fetchall("SELECT * FROM rep_history WHERE guild_id = ? AND (from_user_id = ? OR to_user_id = ?) ORDER BY timestamp DESC LIMIT ?", guild_id, user_id, user_id, limit)
    return fetchall("SELECT * FROM rep_history WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?", guild_id, limit)


def get_rep_roles(guild_id):
    return fetchall("SELECT * FROM rep_roles WHERE guild_id = ? ORDER BY rep_min ASC", guild_id)


def add_rep_role(guild_id, rep_min, role_id):
    execute("INSERT INTO rep_roles (guild_id, rep_min, role_id) VALUES (?, ?, ?)", guild_id, rep_min, role_id)


def remove_rep_role_by_id(rid):
    execute("DELETE FROM rep_roles WHERE id = ?", rid)


def get_shop_items(guild_id):
    return fetchall("SELECT * FROM shop_items WHERE guild_id = ?", guild_id)


def add_shop_item(guild_id, name, description, role_id, price, emoji):
    execute("INSERT INTO shop_items (guild_id, name, description, role_id, price, emoji) VALUES (?, ?, ?, ?, ?, ?)", guild_id, name, description, role_id, price, emoji)


def remove_shop_item(item_id, guild_id):
    execute("DELETE FROM shop_items WHERE id = ? AND guild_id = ?", item_id, guild_id)


def get_guild_tickets(guild_id):
    return fetchall("SELECT * FROM tickets WHERE guild_id = ? ORDER BY created_at DESC", guild_id)


def add_audit_log(guild_id, user_id, action, module, details):
    execute("INSERT INTO dashboard_audit (guild_id, user_id, action, module, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)", guild_id, user_id, action, module, details, time.time())

def get_audit_logs(guild_id, limit=50):
    return fetchall("SELECT * FROM dashboard_audit WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?", guild_id, limit)

# ─── Dashboard Sessions ───────────────────────────────────────────────

def create_session(session_id, user_id, expires_at):
    execute(
        "INSERT OR REPLACE INTO dashboard_sessions (id, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        session_id, user_id, expires_at, time.time()
    )

# ─── Reaction Roles ─────────────────────────────────────────────────

def get_reaction_roles(guild_id):
    return fetchall("SELECT * FROM reaction_roles WHERE guild_id = ?", guild_id)

def add_reaction_role(guild_id, channel_id, message_id, role_id, emoji):
    execute(
        "INSERT INTO reaction_roles (guild_id, channel_id, message_id, role_id, emoji) VALUES (?, ?, ?, ?, ?)",
        guild_id, channel_id, message_id, role_id, emoji
    )

def remove_reaction_role(rr_id, guild_id):
    execute("DELETE FROM reaction_roles WHERE id = ? AND guild_id = ?", rr_id, guild_id)

# ─── Giveaways ──────────────────────────────────────────────────────

def get_guild_giveaways(guild_id):
    return fetchall("SELECT * FROM giveaways WHERE guild_id = ? ORDER BY end_time DESC", guild_id)

def create_giveaway(guild_id, channel_id, message_id, prize, winners, end_at, hosted_by):
    execute(
        "INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, end_time, hosted_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
        guild_id, channel_id, message_id, prize, winners, end_at, hosted_by
    )

def end_giveaway(message_id):
    execute("UPDATE giveaways SET finished = 1 WHERE message_id = ?", message_id)

# ─── Suggestions ────────────────────────────────────────────────────

def get_guild_suggestions(guild_id):
    return fetchall("SELECT * FROM suggestions WHERE guild_id = ? ORDER BY created_at DESC", guild_id)

# ─── Members (extended) ─────────────────────────────────────────────

def get_member(user_id, guild_id):
    row = fetchone("SELECT * FROM members WHERE user_id = ? AND guild_id = ?", user_id, guild_id)
    if not row:
        execute("INSERT INTO members (user_id, guild_id) VALUES (?, ?)", user_id, guild_id)
        return {"user_id": user_id, "guild_id": guild_id, "balance": 100}
    return row

def update_member(guild_id, user_id, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id, guild_id]
    execute(f"UPDATE members SET {sets} WHERE user_id = ? AND guild_id = ?", *vals)

def add_reputation(guild_id, user_id, amount, mod_id=None):
    execute("UPDATE members SET reputation = COALESCE(reputation, 0) + ? WHERE guild_id = ? AND user_id = ?", amount, guild_id, user_id)
    execute("INSERT INTO rep_history (guild_id, from_user_id, to_user_id, timestamp, reason) VALUES (?, ?, ?, ?, ?)", guild_id, mod_id or 0, user_id, time.time(), f"Mod: {'add' if amount >= 0 else 'remove'} {abs(amount)}")

def get_warnings(user_id, guild_id):
    return fetchall("SELECT * FROM warnings WHERE user_id = ? AND guild_id = ? AND active = 1 ORDER BY timestamp DESC", user_id, guild_id)

def get_rank(user_id, guild_id, stat="total_xp"):
    rows = fetchall(f"SELECT user_id, {stat} as value FROM members WHERE guild_id = ? ORDER BY {stat} DESC", guild_id)
    for i, r in enumerate(rows, 1):
        if r["user_id"] == user_id:
            return i, r
    return 0, None

# ─── Custom Commands ────────────────────────────────────────────────

def get_custom_commands(guild_id):
    return fetchall("SELECT * FROM custom_commands WHERE guild_id = ? ORDER BY name ASC", guild_id)

def add_custom_command(guild_id, name, ctype, content, created_by, **kwargs):
    execute(
        "INSERT INTO custom_commands (guild_id, name, type, content, embed_title, embed_description, embed_color, embed_footer, embed_image, embed_thumbnail, role_required, cooldown, created_at, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        guild_id, name.lower(), ctype, content,
        kwargs.get("embed_title", ""), kwargs.get("embed_description", ""),
        kwargs.get("embed_color", "#7c3aed"), kwargs.get("embed_footer", ""),
        kwargs.get("embed_image", ""), kwargs.get("embed_thumbnail", ""),
        kwargs.get("role_required", 0), kwargs.get("cooldown", 0),
        time.time(), created_by,
    )

def remove_custom_command(cmd_id, guild_id):
    execute("DELETE FROM custom_commands WHERE id = ? AND guild_id = ?", cmd_id, guild_id)

# ─── Temp Voice ─────────────────────────────────────────────────────

def get_guild_temp_voices(guild_id):
    return fetchall("SELECT * FROM temp_voice WHERE guild_id = ?", guild_id)

# ─── Members Search ─────────────────────────────────────────────────

def search_members(guild_id, query="", limit=50):
    if query:
        q = f"%{query}%"
        return fetchall("SELECT * FROM members WHERE guild_id = ? AND (user_id LIKE ?) ORDER BY total_xp DESC LIMIT ?", guild_id, q, limit)
    return fetchall("SELECT * FROM members WHERE guild_id = ? ORDER BY total_xp DESC LIMIT ?", guild_id, limit)
