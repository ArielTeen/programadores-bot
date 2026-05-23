import os, sys, secrets, time, json, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, redirect, request, session, render_template, jsonify
from functools import wraps
import requests
from dashboard import config as dash_config
from database.db import Database

app = Flask(__name__)
app.secret_key = dash_config.SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,  # True en produccion con HTTPS
    PERMANENT_SESSION_LIFETIME=86400,
)

DISCORD_API = dash_config.DISCORD_API_ENDPOINT

# ─── Cache ─────────────────────────────────────────────────────────────────

_guild_cache = {}
_GUILD_CACHE_TTL = 60

# ─── Niveles de permiso ────────────────────────────────────────────────────

PERMISSION_OWNER = "owner"
PERMISSION_ADMIN = "admin"
PERMISSION_STAFF = "staff"
PERMISSION_MEMBER = "member"

PERMISSION_ADMIN_BIT = 0x8
PERMISSION_KICK_BIT = 0x2
PERMISSION_BAN_BIT = 0x4
PERMISSION_MANAGE_GUILD_BIT = 0x20
PERMISSION_MANAGE_CHANNELS_BIT = 0x10
PERMISSION_MODERATE_MEMBERS_BIT = 0x1000000000

def _get_user_permission_level(user_id: int, guild_data: dict, permissions: int) -> str:
    if int(guild_data.get("owner_id", 0)) == user_id:
        return PERMISSION_OWNER
    if permissions & PERMISSION_ADMIN_BIT:
        return PERMISSION_ADMIN
    if permissions & PERMISSION_BAN_BIT:
        return PERMISSION_STAFF
    if permissions & PERMISSION_KICK_BIT:
        return PERMISSION_STAFF
    if permissions & PERMISSION_MANAGE_GUILD_BIT:
        return PERMISSION_STAFF
    if permissions & PERMISSION_MANAGE_CHANNELS_BIT:
        return PERMISSION_STAFF
    if permissions & PERMISSION_MODERATE_MEMBERS_BIT:
        return PERMISSION_STAFF
    return PERMISSION_MEMBER

def _can_configure(level: str) -> bool:
    return level in (PERMISSION_OWNER, PERMISSION_ADMIN)

def _can_view(level: str) -> bool:
    return level in (PERMISSION_OWNER, PERMISSION_ADMIN, PERMISSION_STAFF)

def _permission_label(level: str) -> str:
    labels = {
        PERMISSION_OWNER: "Propietario",
        PERMISSION_ADMIN: "Administrador",
        PERMISSION_STAFF: "Staff",
        PERMISSION_MEMBER: "Miembro",
    }
    return labels.get(level, "Desconocido")

def _permission_badge_class(level: str) -> str:
    classes = {
        PERMISSION_OWNER: "badge-premium purple",
        PERMISSION_ADMIN: "badge-premium blue",
        PERMISSION_STAFF: "badge-premium green",
        PERMISSION_MEMBER: "badge-premium yellow",
    }
    return classes.get(level, "badge-premium")

# ─── Helpers ───────────────────────────────────────────────────────────────

def _fetch_user_guilds(access_token):
    now = time.time()
    key = f"g_{access_token[:16]}"
    if key in _guild_cache and (now - _guild_cache[key]["ts"]) < _GUILD_CACHE_TTL:
        return _guild_cache[key]["guilds"]

    r = requests.get(f"{DISCORD_API}/users/@me/guilds",
                     headers={"Authorization": f"Bearer {access_token}"})
    if r.status_code != 200:
        return None

    guilds = r.json()
    _guild_cache[key] = {"guilds": guilds, "ts": now}
    return guilds

def _get_guilds_with_perms(access_token, user_id):
    guilds = _fetch_user_guilds(access_token)
    if not guilds:
        return []
    result = []
    for g in guilds:
        perms = int(g.get("permissions", "0"))
        g_config = _get_guild_config(g["id"])
        level = _get_user_permission_level(user_id, g_config, perms)
        result.append({
            "id": g["id"],
            "name": g["name"],
            "icon": g.get("icon"),
            "member_count": g.get("approximate_member_count", "N/A"),
            "permission_level": level,
            "permission_label": _permission_label(level),
            "badge_class": _permission_badge_class(level),
            "can_configure": _can_configure(level),
            "can_view": _can_view(level),
        })
    result.sort(key=lambda x: (
        0 if x["permission_level"] == PERMISSION_OWNER else
        1 if x["permission_level"] == PERMISSION_ADMIN else
        2 if x["permission_level"] == PERMISSION_STAFF else 3,
        x["name"].lower()
    ))
    return result

def _get_accessible_guilds(access_token, user_id):
    return [g for g in _get_guilds_with_perms(access_token, user_id) if g["can_view"]]

def _get_admin_guilds(access_token, user_id):
    return [g for g in _get_guilds_with_perms(access_token, user_id) if g["can_configure"]]

def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

def _get_guild_config(guild_id):
    async def _do():
        db = Database()
        await db.connect()
        try:
            return await db.get_guild(int(guild_id))
        finally:
            await db.close()
    return _run_async(_do())

def _save_guild_config(guild_id, data):
    async def _do():
        db = Database()
        await db.connect()
        try:
            await db.update_guild(int(guild_id), **data)
        finally:
            await db.close()
    _run_async(_do())

def _fetch_guild_stats(guild_id):
    async def _do():
        db = Database()
        await db.connect()
        try:
            w = await db.fetchall("SELECT COUNT(*) as c FROM warnings WHERE guild_id = ? AND active = 1", guild_id)
            m = await db.fetchall("SELECT COUNT(*) as c FROM members WHERE guild_id = ?", guild_id)
            t = await db.fetchall("SELECT COUNT(*) as c FROM tickets WHERE guild_id = ?", guild_id)
            xp = await db.get_leaderboard(guild_id, "total_xp", 10)
            bal = await db.get_leaderboard(guild_id, "balance", 5)
            rep = await db.get_leaderboard(guild_id, "reputation", 10)
            rep_stats = await db.get_rep_stats(guild_id)
            recent_rep = await db.get_rep_history(guild_id, None, 5)
            return {
                "warnings": w[0]["c"] if w else 0,
                "members_tracked": m[0]["c"] if m else 0,
                "tickets": t[0]["c"] if t else 0,
                "top_xp": [{"id": r["user_id"], "xp": r["total_xp"], "level": r["level"]} for r in (xp or [])],
                "top_balance": [{"id": r["user_id"], "balance": r["balance"], "bank": r["bank"]} for r in (bal or [])],
                "top_reputation": [{"id": r["user_id"], "rep": r["reputation"]} for r in (rep or [])],
                "rep_total_given": rep_stats.get("total_given", 0),
                "rep_recent": [{"from": r["from_user_id"], "to": r["to_user_id"], "ts": r["timestamp"]} for r in (recent_rep or [])],
            }
        finally:
            await db.close()
    return _run_async(_do())

def _fetch_guild_warnings(guild_id):
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.fetchall("SELECT w.* FROM warnings w WHERE w.guild_id = ? AND w.active = 1 ORDER BY w.timestamp DESC LIMIT 50", guild_id)
            return [dict(r) for r in rows]
        finally:
            await db.close()
    return _run_async(_do())

def _fetch_guild_tickets(guild_id):
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.get_guild_tickets(guild_id)
            return [dict(r) for r in (rows or [])]
        finally:
            await db.close()
    return _run_async(_do())

def _fetch_leaderboard(guild_id, stat, limit=20):
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.get_leaderboard(guild_id, stat, limit)
            return [dict(r) for r in (rows or [])]
        finally:
            await db.close()
    return _run_async(_do())

def _fetch_shop_items(guild_id):
    async def _do():
        db = Database()
        await db.connect()
        try:
            items = await db.get_shop_items(guild_id)
            return [dict(r) for r in (items or [])]
        finally:
            await db.close()
    return _run_async(_do())

def _mutate_shop(guild_id, action, data):
    async def _do():
        db = Database()
        await db.connect()
        try:
            if action == "add":
                await db.add_shop_item(guild_id, data["name"], data.get("description", ""), int(data.get("role_id", 0)), int(data["price"]), data.get("emoji", ""))
            elif action == "remove":
                await db.remove_shop_item(int(data["id"]), guild_id)
        finally:
            await db.close()
    _run_async(_do())

def _fetch_rep_config(guild_id):
    async def _do():
        db = Database()
        await db.connect()
        try:
            g = await db.get_guild(int(guild_id))
            roles = await db.get_rep_roles(int(guild_id))
            return {
                "enabled": g.get("rep_enabled", 1),
                "cooldown": g.get("rep_cooldown", 43200),
                "channel": g.get("rep_channel", 0),
                "log_channel": g.get("rep_log_channel", 0),
                "max_per_user": g.get("rep_max_per_user", 100),
                "min_level": g.get("rep_min_level", 0),
                "staff_only": g.get("rep_staff_only", 0),
                "roles": [dict(r) for r in (roles or [])],
            }
        finally:
            await db.close()
    return _run_async(_do())

def _fetch_rep_roles(guild_id):
    async def _do():
        db = Database()
        await db.connect()
        try:
            roles = await db.get_rep_roles(int(guild_id))
            return [dict(r) for r in (roles or [])]
        finally:
            await db.close()
    return _run_async(_do())

def _mutate_rep_role(guild_id, action, data):
    async def _do():
        db = Database()
        await db.connect()
        try:
            if action == "add":
                await db.add_rep_role(int(guild_id), int(data["rep_min"]), int(data["role_id"]))
            elif action == "remove":
                await db.remove_rep_role_by_id(int(data["id"]))
        finally:
            await db.close()
    _run_async(_do())

# ─── Auth Decorator ────────────────────────────────────────────────────────

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session or "access_token" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

def guild_access_required(f):
    @wraps(f)
    def decorated(guild_id, *args, **kwargs):
        if "user" not in session or "access_token" not in session:
            return redirect("/login")
        user_id = int(session["user"]["id"])
        guilds = _get_accessible_guilds(session["access_token"], user_id)
        guild = next((g for g in guilds if str(g["id"]) == str(guild_id)), None)
        if not guild:
            return render_template("login.html", error="No tienes acceso a ese servidor.")
        return f(guild_id, guild=guild, *args, **kwargs)
    return decorated

# ─── Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    if session.get("user"):
        return redirect("/dashboard")
    error = request.args.get("error")
    return render_template("login.html", error=error)

@app.route("/login")
def login():
    url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={dash_config.DISCORD_CLIENT_ID}"
        f"&redirect_uri={dash_config.DISCORD_REDIRECT_URI}"
        f"&response_type=code&scope=identify%20guilds"
    )
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/")

    data = {
        "client_id": dash_config.DISCORD_CLIENT_ID,
        "client_secret": dash_config.DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": dash_config.DISCORD_REDIRECT_URI,
        "scope": "identify guilds",
    }
    r = requests.post(f"{DISCORD_API}/oauth2/token", data=data,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return redirect("/?error=Error+de+autenticacion+con+Discord")

    token_data = r.json()
    access_token = token_data["access_token"]

    user_r = requests.get(f"{DISCORD_API}/users/@me",
                          headers={"Authorization": f"Bearer {access_token}"})
    if user_r.status_code != 200:
        return redirect("/?error=Error+obteniendo+usuario")

    user = user_r.json()
    session["user"] = user
    session["access_token"] = access_token

    app.logger.info(f"Usuario {user.get('username')} ({user.get('id')}) inicio sesion")

    try:
        async def _save():
            db = Database()
            await db.connect()
            await db.create_session(secrets.token_hex(16), int(user["id"]), time.time() + 86400)
            await db.close()
        _run_async(_save())
    except Exception as e:
        app.logger.warning(f"No se pudo crear sesion en DB: {e}")

    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/dashboard")
@auth_required
def dashboard():
    user = session.get("user")
    user_id = int(user["id"])
    guilds = _get_guilds_with_perms(session["access_token"], user_id)
    admin_guilds = [g for g in guilds if g["can_configure"]]
    stats = {
        "total_guilds": len(guilds),
        "admin_guilds": len(admin_guilds),
        "staff_guilds": len([g for g in guilds if g["permission_level"] == PERMISSION_STAFF]),
    }
    return render_template("dashboard.html", user=user, guilds=guilds, admin_guilds=admin_guilds, stats=stats, active_page="dashboard")

@app.route("/dashboard/servers")
@auth_required
def servers():
    user = session.get("user")
    user_id = int(user["id"])
    guilds = _get_guilds_with_perms(session["access_token"], user_id)
    return render_template("servers.html", user=user, guilds=guilds, active_page="servers")

@app.route("/dashboard/<guild_id>")
@auth_required
def server_overview(guild_id):
    user = session.get("user")
    user_id = int(user["id"])
    guilds = _get_guilds_with_perms(session["access_token"], user_id)
    guild = next((g for g in guilds if str(g["id"]) == str(guild_id) and g["can_view"]), None)
    if not guild:
        return render_template("login.html", error="No tienes acceso a ese servidor.")
    config = _get_guild_config(guild_id)
    return render_template("config.html", user=user, guild=guild, guilds=guilds, config=config, active_page="config", module="overview")

@app.route("/dashboard/<guild_id>/<module>")
@auth_required
def server_module(guild_id, module):
    user = session.get("user")
    user_id = int(user["id"])
    guilds = _get_guilds_with_perms(session["access_token"], user_id)
    guild = next((g for g in guilds if str(g["id"]) == str(guild_id) and g["can_view"]), None)
    if not guild:
        return render_template("login.html", error="No tienes acceso a ese servidor.")
    valid = ["moderation", "automod", "antinuke", "tickets", "welcome", "levels", "economy", "reputation", "logs", "reaction-roles", "verification", "giveaways", "suggestions", "members", "commands", "embed-builder", "audit", "temp-voice", "general"]
    if module not in valid:
        return redirect(f"/dashboard/{guild_id}")
    config = _get_guild_config(guild_id)
    return render_template("config.html", user=user, guild=guild, guilds=guilds, config=config, active_page="config", module=module)

# ─── API ────────────────────────────────────────────────────────────────────

def _check_guild_access(guild_id):
    user_id = int(session["user"]["id"])
    guilds = _get_accessible_guilds(session["access_token"], user_id)
    return next((g for g in guilds if str(g["id"]) == str(guild_id)), None)

def _check_admin_access(guild_id):
    user_id = int(session["user"]["id"])
    guilds = _get_admin_guilds(session["access_token"], user_id)
    return next((g for g in guilds if str(g["id"]) == str(guild_id)), None)

@app.route("/api/guild/<guild_id>/config", methods=["GET", "POST"])
@auth_required
def api_guild_config(guild_id):
    if request.method == "POST":
        guild = _check_admin_access(guild_id)
        if not guild:
            return jsonify({"error": "Se requieren permisos de administrador"}), 403
        data = request.json
        if not data:
            return jsonify({"error": "No data"}), 400
        async def _audit():
            db = Database()
            await db.connect()
            try:
                keys = list(data.keys())[:3]
                await db.add_audit_log(int(guild_id), int(session["user"]["id"]), "config_update", "general", f"Updated: {', '.join(keys)}")
            finally:
                await db.close()
        _run_async(_audit())
        _save_guild_config(guild_id, data)
        return jsonify({"success": True})
    guild = _check_guild_access(guild_id)
    if not guild:
        return jsonify({"error": "Acceso denegado"}), 403
    return jsonify(_get_guild_config(guild_id))

@app.route("/api/guild/<guild_id>/stats")
@auth_required
def api_guild_stats(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    return jsonify(_fetch_guild_stats(guild_id))

@app.route("/api/guild/<guild_id>/rep-config")
@auth_required
def api_rep_config(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    return jsonify(_fetch_rep_config(guild_id))

@app.route("/api/guild/<guild_id>/warnings")
@auth_required
def api_guild_warnings(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    return jsonify(_fetch_guild_warnings(guild_id))

@app.route("/api/guild/<guild_id>/tickets")
@auth_required
def api_guild_tickets(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    return jsonify(_fetch_guild_tickets(guild_id))

@app.route("/api/guild/<guild_id>/leaderboard")
@auth_required
def api_guild_leaderboard(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    stat = request.args.get("stat", "total_xp")
    return jsonify(_fetch_leaderboard(guild_id, stat, 20))

@app.route("/api/guild/<guild_id>/shop", methods=["GET", "POST"])
@auth_required
def api_guild_shop(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    if request.method == "POST":
        guild = _check_admin_access(guild_id)
        if not guild:
            return jsonify({"error": "Se requieren permisos de administrador"}), 403
        data = request.json
        _mutate_shop(guild_id, data.get("action"), data)
        return jsonify({"success": True})
    return jsonify(_fetch_shop_items(guild_id))

@app.route("/api/guild/<guild_id>/rep-roles", methods=["GET", "POST"])
@auth_required
def api_guild_rep_roles(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    if request.method == "POST":
        guild = _check_admin_access(guild_id)
        if not guild:
            return jsonify({"error": "Se requieren permisos de administrador"}), 403
        data = request.json
        _mutate_rep_role(guild_id, data.get("action"), data)
        return jsonify({"success": True})
    return jsonify(_fetch_rep_roles(guild_id))

@app.route("/api/guild/<guild_id>/members", methods=["GET"])
@auth_required
def api_guild_members(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.fetchall("SELECT user_id, level, total_xp, reputation, balance FROM members WHERE guild_id = ? ORDER BY total_xp DESC LIMIT 100", guild_id)
            return [dict(r) for r in rows]
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/warn", methods=["POST"])
@auth_required
def api_guild_warn(guild_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    data = request.json
    user_id = data.get("user_id")
    reason = data.get("reason", "Sin motivo")
    mod_id = session["user"]["id"]
    async def _do():
        db = Database()
        await db.connect()
        try:
            c = await db.fetchone("SELECT COUNT(*) as c FROM warnings WHERE guild_id = ? AND user_id = ? AND active = 1", guild_id, user_id)
            case = (c["c"] if c else 0) + 1
            await db.execute("INSERT INTO warnings (guild_id, user_id, moderator_id, reason, case_number, active) VALUES (?, ?, ?, ?, ?, 1)", guild_id, user_id, mod_id, reason, case)
            return {"success": True, "case": case}
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/warn/<int:warn_id>", methods=["DELETE"])
@auth_required
def api_guild_warn_delete(guild_id, warn_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    async def _do():
        db = Database()
        await db.connect()
        try:
            await db.execute("UPDATE warnings SET active = 0 WHERE id = ? AND guild_id = ?", warn_id, guild_id)
            return {"success": True}
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/warns/clear", methods=["POST"])
@auth_required
def api_guild_warns_clear(guild_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    user_id = request.json.get("user_id")
    async def _do():
        db = Database()
        await db.connect()
        try:
            if user_id:
                await db.execute("UPDATE warnings SET active = 0 WHERE guild_id = ? AND user_id = ? AND active = 1", guild_id, user_id)
            else:
                await db.execute("UPDATE warnings SET active = 0 WHERE guild_id = ? AND active = 1", guild_id)
            return {"success": True}
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

# ─── Reaction Roles API ───────────────────────────────────────────────
@app.route("/api/guild/<guild_id>/reaction-roles", methods=["GET", "POST"])
@auth_required
def api_guild_reaction_roles(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    if request.method == "POST":
        guild = _check_admin_access(guild_id)
        if not guild:
            return jsonify({"error": "Se requieren permisos de administrador"}), 403
        data = request.json or {}
        action = data.get("action")
        async def _do():
            db = Database()
            await db.connect()
            try:
                if action == "add":
                    msg_id = int(data.get("message_id", 0))
                    role_id = int(data.get("role_id", 0))
                    emoji = data.get("emoji", "⭐")
                    await db.add_reaction_role(int(guild_id), 0, msg_id, role_id, emoji)
                elif action == "remove":
                    await db.remove_reaction_role(int(data.get("id", 0)), int(guild_id))
                return {"success": True}
            finally:
                await db.close()
        return jsonify(_run_async(_do()))
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.get_reaction_roles(int(guild_id))
            return [dict(r) for r in (rows or [])]
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

# ─── Giveaways API ───────────────────────────────────────────────────
@app.route("/api/guild/<guild_id>/giveaways", methods=["GET"])
@auth_required
def api_guild_giveaways(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.get_guild_giveaways(int(guild_id))
            return [dict(r) for r in (rows or [])]
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/giveaway", methods=["POST"])
@auth_required
def api_guild_giveaway(guild_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    data = request.json or {}
    action = data.get("action")
    async def _do():
        db = Database()
        await db.connect()
        try:
            if action == "start":
                prize = data.get("prize", "Sorteo")
                duration = int(data.get("duration", 3600))
                winners = int(data.get("winners", 1))
                channel_id = int(data.get("channel_id", 0))
                end_time = time.time() + duration
                await db.create_giveaway(int(guild_id), channel_id, 0, prize, winners, end_time, int(session["user"]["id"]))
            elif action == "end":
                gw_id = int(data.get("id", 0))
                row = await db.fetchone("SELECT message_id FROM giveaways WHERE id = ? AND guild_id = ?", gw_id, guild_id)
                if row:
                    await db.end_giveaway(row["message_id"])
            return {"success": True}
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

# ─── Suggestions API ─────────────────────────────────────────────────
@app.route("/api/guild/<guild_id>/suggestions", methods=["GET"])
@auth_required
def api_guild_suggestions(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.get_guild_suggestions(int(guild_id))
            return [dict(r) for r in (rows or [])]
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

# ─── Warns API (limit param) ─────────────────────────────────────────
@app.route("/api/guild/<guild_id>/warns", methods=["GET"])
@auth_required
def api_guild_warns(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    limit = request.args.get("limit", 50, type=int)
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.fetchall("SELECT w.* FROM warnings w WHERE w.guild_id = ? AND w.active = 1 ORDER BY w.timestamp DESC LIMIT ?", guild_id, limit)
            return [dict(r) for r in rows]
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/ticket/create", methods=["POST"])
@auth_required
def api_guild_ticket_create(guild_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    data = request.json
    user_id_val = data.get("user_id", session["user"]["id"])
    subject = data.get("subject", "Soporte")
    async def _do():
        db = Database()
        await db.connect()
        try:
            await db.execute("INSERT INTO tickets (guild_id, user_id, subject, status, created_at) VALUES (?, ?, ?, 'open', ?)", guild_id, user_id_val, subject, time.time())
            return {"success": True}
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/ticket/<int:ticket_id>/close", methods=["POST"])
@auth_required
def api_guild_ticket_close(guild_id, ticket_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    async def _do():
        db = Database()
        await db.connect()
        try:
            await db.execute("UPDATE tickets SET status = 'closed' WHERE id = ? AND guild_id = ?", ticket_id, guild_id)
            return {"success": True}
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/rep/manage", methods=["POST"])
@auth_required
def api_guild_rep_manage(guild_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    data = request.json
    action = data.get("action")
    target_id = data.get("user_id")
    amount = data.get("amount", 0)
    async def _do():
        db = Database()
        await db.connect()
        try:
            if action == "set":
                await db.update_member(int(guild_id), int(target_id), reputation=amount)
            elif action == "add":
                await db.add_reputation(int(guild_id), int(target_id), int(amount), session["user"]["id"])
            elif action == "remove":
                await db.add_reputation(int(guild_id), int(target_id), -int(amount), session["user"]["id"])
            elif action == "reset":
                await db.update_member(int(guild_id), int(target_id), reputation=0)
            return {"success": True}
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/user/guilds")
@auth_required
def api_user_guilds():
    user = session.get("user")
    user_id = int(user["id"])
    guilds = _get_guilds_with_perms(session["access_token"], user_id)
    return jsonify(guilds)

# ─── Members API ──────────────────────────────────────────────────────────
@app.route("/api/guild/<guild_id>/members/search", methods=["GET"])
@auth_required
def api_members_search(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    query = request.args.get("q", "")
    limit = request.args.get("limit", 50, type=int)
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.search_members(int(guild_id), query, limit)
            return [dict(r) for r in rows]
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/member/<user_id>", methods=["GET"])
@auth_required
def api_member_detail(guild_id, user_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    async def _do():
        db = Database()
        await db.connect()
        try:
            m = await db.get_member(int(user_id), int(guild_id))
            warns = await db.get_warnings(int(user_id), int(guild_id))
            m["warnings"] = [dict(r) for r in warns]
            rank_xp, _ = await db.get_rank(int(user_id), int(guild_id), "total_xp")
            rank_rep, _ = await db.get_rank(int(user_id), int(guild_id), "reputation")
            m["rank_xp"] = rank_xp
            m["rank_rep"] = rank_rep
            return m
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

# ─── Custom Commands API ─────────────────────────────────────────────────
@app.route("/api/guild/<guild_id>/commands", methods=["GET"])
@auth_required
def api_custom_commands(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.get_custom_commands(int(guild_id))
            return [dict(r) for r in rows]
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

@app.route("/api/guild/<guild_id>/commands", methods=["POST"])
@auth_required
def api_custom_command_create(guild_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    data = request.json or {}
    action = data.get("action", "add")
    async def _do():
        db = Database()
        await db.connect()
        try:
            if action == "add":
                await db.add_custom_command(
                    int(guild_id), data["name"], data.get("type", "text"),
                    data.get("content", ""), int(session["user"]["id"]),
                    embed_title=data.get("embed_title"),
                    embed_description=data.get("embed_description"),
                    embed_color=data.get("embed_color", "#7c3aed"),
                    embed_footer=data.get("embed_footer"),
                    embed_image=data.get("embed_image"),
                    embed_thumbnail=data.get("embed_thumbnail"),
                    role_required=int(data.get("role_required", 0)),
                    cooldown=int(data.get("cooldown", 0)),
                )
            elif action == "remove":
                await db.remove_custom_command(int(data["id"]), int(guild_id))
            await db.add_audit_log(int(guild_id), int(session["user"]["id"]), action, "custom_commands", f"Command: {data.get('name', '')}")
            return {"success": True}
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

# ─── Audit Log API ───────────────────────────────────────────────────────
@app.route("/api/guild/<guild_id>/audit", methods=["GET"])
@auth_required
def api_audit_log(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    limit = request.args.get("limit", 50, type=int)
    async def _do():
        db = Database()
        await db.connect()
        try:
            return await db.get_audit_logs(int(guild_id), limit)
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

# ─── Temp Voice API ──────────────────────────────────────────────────────
@app.route("/api/guild/<guild_id>/temp-voice", methods=["GET"])
@auth_required
def api_temp_voice(guild_id):
    if not _check_guild_access(guild_id):
        return jsonify({"error": "Acceso denegado"}), 403
    async def _do():
        db = Database()
        await db.connect()
        try:
            rows = await db.get_guild_temp_voices(int(guild_id))
            return [dict(r) for r in rows]
        finally:
            await db.close()
    return jsonify(_run_async(_do()))

# ─── Embed Builder API ───────────────────────────────────────────────────
@app.route("/api/guild/<guild_id>/embed/send", methods=["POST"])
@auth_required
def api_embed_send(guild_id):
    guild = _check_admin_access(guild_id)
    if not guild:
        return jsonify({"error": "Se requieren permisos de administrador"}), 403
    return jsonify({"success": True, "message": "Embed enviado. Usa el bot en Discord para enviar embeds."})

# ─── Error Handlers ────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("login.html", error="Pagina no encontrada"), 404

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Error interno del servidor"}), 500
    return render_template("login.html", error="Error interno del servidor. Intenta de nuevo."), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
