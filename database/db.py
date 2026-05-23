import aiosqlite
import os
import json
import time
from .models import ALL_TABLES


class Database:
    def __init__(self, db_path: str = "data/bot.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.pool = None

    async def connect(self):
        self.pool = await aiosqlite.connect(self.db_path)
        self.pool.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def _create_tables(self):
        for table_sql in ALL_TABLES:
            await self.pool.execute(table_sql)
        await self.pool.commit()

    async def execute(self, sql: str, *params):
        cur = await self.pool.execute(sql, params)
        await self.pool.commit()
        return cur

    async def fetchone(self, sql: str, *params):
        cur = await self.pool.execute(sql, params)
        return await cur.fetchone()

    async def fetchall(self, sql: str, *params):
        cur = await self.pool.execute(sql, params)
        return await cur.fetchall()

    # ─── Guild Config ───────────────────────────────────────────────────────

    async def get_guild(self, guild_id: int) -> dict:
        row = await self.fetchone("SELECT * FROM guild_config WHERE guild_id = ?", guild_id)
        if not row:
            await self.execute("INSERT INTO guild_config (guild_id) VALUES (?)", guild_id)
            return {"guild_id": guild_id}
        d = dict(row)
        for key in ("staff_roles", "log_config", "automod_config", "antinuke_config", "antinuke_trusted"):
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except:
                    d[key] = [] if key != "log_config" else {}
        return d

    async def update_guild(self, guild_id: int, **kwargs):
        clean = {}
        for k, v in kwargs.items():
            if isinstance(v, (list, dict)):
                clean[k] = json.dumps(v)
            else:
                clean[k] = v
        if not clean:
            return
        sets = ", ".join(f"{k} = ?" for k in clean)
        vals = list(clean.values()) + [guild_id]
        await self.execute(f"UPDATE guild_config SET {sets} WHERE guild_id = ?", *vals)

    # ─── Members ────────────────────────────────────────────────────────────

    async def get_member(self, user_id: int, guild_id: int) -> dict:
        row = await self.fetchone(
            "SELECT * FROM members WHERE user_id = ? AND guild_id = ?", user_id, guild_id
        )
        if not row:
            await self.execute(
                "INSERT INTO members (user_id, guild_id) VALUES (?, ?)", user_id, guild_id
            )
            return {"user_id": user_id, "guild_id": guild_id, "balance": 100}
        return dict(row)

    async def update_member(self, user_id: int, guild_id: int, **kwargs):
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [user_id, guild_id]
        await self.execute(f"UPDATE members SET {sets} WHERE user_id = ? AND guild_id = ?", *vals)

    # ─── Warnings / Cases ───────────────────────────────────────────────────

    async def add_warning(self, user_id: int, guild_id: int, mod_id: int, reason: str):
        ts = time.time()
        await self.execute(
            "INSERT INTO warnings (user_id, guild_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
            user_id, guild_id, mod_id, reason, ts,
        )
        await self.execute(
            "UPDATE members SET warns = warns + 1 WHERE user_id = ? AND guild_id = ?",
            user_id, guild_id,
        )
        return await self.fetchone(
            "SELECT id FROM warnings WHERE user_id = ? AND guild_id = ? ORDER BY id DESC LIMIT 1",
            user_id, guild_id,
        )

    async def get_warnings(self, user_id: int, guild_id: int, active: bool = True):
        if active:
            return await self.fetchall(
                "SELECT * FROM warnings WHERE user_id = ? AND guild_id = ? AND active = 1 ORDER BY timestamp DESC",
                user_id, guild_id,
            )
        return await self.fetchall(
            "SELECT * FROM warnings WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC",
            user_id, guild_id,
        )

    async def remove_warning(self, warn_id: int, guild_id: int) -> bool:
        row = await self.fetchone(
            "SELECT * FROM warnings WHERE id = ? AND guild_id = ?", warn_id, guild_id
        )
        if not row:
            return False
        await self.execute("UPDATE warnings SET active = 0 WHERE id = ?", warn_id)
        await self.execute(
            "UPDATE members SET warns = warns - 1 WHERE user_id = ? AND guild_id = ?",
            row["user_id"], guild_id,
        )
        return True

    async def clear_warnings(self, user_id: int, guild_id: int):
        await self.execute(
            "UPDATE warnings SET active = 0 WHERE user_id = ? AND guild_id = ?",
            user_id, guild_id,
        )
        await self.execute(
            "UPDATE members SET warns = 0 WHERE user_id = ? AND guild_id = ?",
            user_id, guild_id,
        )

    async def add_case(self, guild_id: int, user_id: int, mod_id: int, action: str, reason: str, duration: str = ""):
        ts = time.time()
        row = await self.fetchone(
            "SELECT COALESCE(MAX(case_number), 0) + 1 as num FROM cases WHERE guild_id = ?", guild_id
        )
        case_num = row["num"] if row else 1
        await self.execute(
            "INSERT INTO cases (guild_id, case_number, user_id, moderator_id, action_type, reason, duration, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            guild_id, case_num, user_id, mod_id, action, reason, duration, ts,
        )
        return case_num

    # ─── Tickets ────────────────────────────────────────────────────────────

    async def create_ticket(self, guild_id: int, channel_id: int, user_id: int, category: str = "general"):
        ts = time.time()
        await self.execute(
            "INSERT INTO tickets (guild_id, channel_id, user_id, category, created_at) VALUES (?, ?, ?, ?, ?)",
            guild_id, channel_id, user_id, category, ts,
        )
        return await self.fetchone("SELECT id FROM tickets WHERE channel_id = ?", channel_id)

    async def close_ticket(self, channel_id: int, closed_by: int = 0):
        await self.execute(
            "UPDATE tickets SET status = 'closed', closed_at = ?, closed_by = ? WHERE channel_id = ?",
            time.time(), closed_by, channel_id,
        )

    async def reopen_ticket(self, channel_id: int):
        await self.execute(
            "UPDATE tickets SET status = 'open', closed_at = NULL WHERE channel_id = ?", channel_id
        )

    async def claim_ticket(self, channel_id: int, claimer_id: int):
        await self.execute(
            "UPDATE tickets SET claimer_id = ?, status = 'claimed' WHERE channel_id = ?",
            claimer_id, channel_id,
        )

    async def unclaim_ticket(self, channel_id: int):
        await self.execute(
            "UPDATE tickets SET claimer_id = 0, status = 'open' WHERE channel_id = ?", channel_id
        )

    async def get_ticket(self, channel_id: int):
        return await self.fetchone("SELECT * FROM tickets WHERE channel_id = ?", channel_id)

    async def get_user_open_ticket(self, user_id: int, guild_id: int):
        return await self.fetchone(
            "SELECT * FROM tickets WHERE user_id = ? AND guild_id = ? AND status IN ('open','claimed')",
            user_id, guild_id,
        )

    async def get_guild_tickets(self, guild_id: int):
        return await self.fetchall(
            "SELECT * FROM tickets WHERE guild_id = ? ORDER BY created_at DESC", guild_id
        )

    async def add_ticket_message(self, ticket_id: int, author_id: int, content: str, attachment: str = ""):
        await self.execute(
            "INSERT INTO ticket_messages (ticket_id, author_id, content, timestamp, attachment_url) VALUES (?, ?, ?, ?, ?)",
            ticket_id, author_id, content, time.time(), attachment,
        )

    async def rate_ticket(self, channel_id: int, rating: int):
        await self.execute("UPDATE tickets SET rating = ? WHERE channel_id = ?", rating, channel_id)

    # ─── Shop ───────────────────────────────────────────────────────────────

    async def add_shop_item(self, guild_id: int, name: str, desc: str, role_id: int, price: int, emoji: str = "🎁"):
        await self.execute(
            "INSERT INTO shop_items (guild_id, name, description, role_id, price, emoji) VALUES (?, ?, ?, ?, ?, ?)",
            guild_id, name, desc, role_id, price, emoji,
        )

    async def remove_shop_item(self, item_id: int, guild_id: int):
        await self.execute("DELETE FROM shop_items WHERE id = ? AND guild_id = ?", item_id, guild_id)

    async def get_shop_items(self, guild_id: int):
        return await self.fetchall("SELECT * FROM shop_items WHERE guild_id = ? ORDER BY price ASC", guild_id)

    async def get_shop_item(self, item_id: int):
        return await self.fetchone("SELECT * FROM shop_items WHERE id = ?", item_id)

    async def buy_item(self, user_id: int, guild_id: int, item_id: int):
        await self.execute(
            "INSERT INTO inventories (user_id, guild_id, item_id, purchased_at) VALUES (?, ?, ?, ?)",
            user_id, guild_id, item_id, time.time(),
        )

    async def has_item(self, user_id: int, guild_id: int, item_id: int) -> bool:
        row = await self.fetchone(
            "SELECT * FROM inventories WHERE user_id = ? AND guild_id = ? AND item_id = ?",
            user_id, guild_id, item_id,
        )
        return row is not None

    async def get_inventory(self, user_id: int, guild_id: int):
        return await self.fetchall(
            "SELECT i.*, s.name, s.description, s.emoji, s.role_id, s.price FROM inventories i JOIN shop_items s ON i.item_id = s.id WHERE i.user_id = ? AND i.guild_id = ?",
            user_id, guild_id,
        )

    async def sell_item(self, user_id: int, guild_id: int, item_id: int) -> bool:
        row = await self.fetchone(
            "SELECT i.id as inv_id, s.price FROM inventories i JOIN shop_items s ON i.item_id = s.id WHERE i.user_id = ? AND i.guild_id = ? AND i.item_id = ?",
            user_id, guild_id, item_id,
        )
        if not row:
            return False
        await self.execute("DELETE FROM inventories WHERE id = ?", row["inv_id"])
        return row["price"] // 2

    # ─── Level Roles ────────────────────────────────────────────────────────

    async def add_level_role(self, guild_id: int, level: int, role_id: int):
        await self.execute(
            "INSERT OR REPLACE INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)",
            guild_id, level, role_id,
        )

    async def remove_level_role(self, guild_id: int, level: int):
        await self.execute(
            "DELETE FROM level_roles WHERE guild_id = ? AND level = ?", guild_id, level
        )

    async def get_level_roles(self, guild_id: int):
        return await self.fetchall(
            "SELECT * FROM level_roles WHERE guild_id = ? ORDER BY level ASC", guild_id
        )

    # ─── Muted Users ────────────────────────────────────────────────────────

    async def add_muted(self, user_id: int, guild_id: int, end_time: float):
        await self.execute(
            "INSERT OR REPLACE INTO muted_users (user_id, guild_id, end_time) VALUES (?, ?, ?)",
            user_id, guild_id, end_time,
        )

    async def remove_muted(self, user_id: int, guild_id: int):
        await self.execute("DELETE FROM muted_users WHERE user_id = ? AND guild_id = ?", user_id, guild_id)

    async def is_muted(self, user_id: int, guild_id: int) -> bool:
        row = await self.fetchone(
            "SELECT * FROM muted_users WHERE user_id = ? AND guild_id = ?", user_id, guild_id
        )
        if row and row["end_time"] < time.time():
            await self.remove_muted(user_id, guild_id)
            return False
        return row is not None

    async def get_all_muted(self):
        return await self.fetchall("SELECT * FROM muted_users WHERE end_time > ?", time.time())

    # ─── Reaction Roles ─────────────────────────────────────────────────────

    async def add_reaction_role(self, guild_id: int, channel_id: int, message_id: int, role_id: int, emoji: str, rtype: str = "reaction"):
        await self.execute(
            "INSERT INTO reaction_roles (guild_id, channel_id, message_id, role_id, emoji, type) VALUES (?, ?, ?, ?, ?, ?)",
            guild_id, channel_id, message_id, role_id, emoji, rtype,
        )

    async def remove_reaction_role(self, rr_id: int, guild_id: int):
        await self.execute("DELETE FROM reaction_roles WHERE id = ? AND guild_id = ?", rr_id, guild_id)

    async def get_reaction_roles(self, guild_id: int):
        return await self.fetchall("SELECT * FROM reaction_roles WHERE guild_id = ?", guild_id)

    async def get_reaction_roles_for_message(self, message_id: int):
        return await self.fetchall("SELECT * FROM reaction_roles WHERE message_id = ?", message_id)

    # ─── Suggestions ────────────────────────────────────────────────────────

    async def create_suggestion(self, guild_id: int, message_id: int, author_id: int, content: str):
        await self.execute(
            "INSERT INTO suggestions (guild_id, message_id, author_id, content, created_at) VALUES (?, ?, ?, ?, ?)",
            guild_id, message_id, author_id, content, time.time(),
        )

    async def update_suggestion_status(self, message_id: int, status: str, response: str = ""):
        await self.execute(
            "UPDATE suggestions SET status = ?, response = ? WHERE message_id = ?",
            status, response, message_id,
        )

    async def get_suggestion(self, message_id: int):
        return await self.fetchone("SELECT * FROM suggestions WHERE message_id = ?", message_id)

    async def get_guild_suggestions(self, guild_id: int, status: str = None):
        if status:
            return await self.fetchall(
                "SELECT * FROM suggestions WHERE guild_id = ? AND status = ? ORDER BY created_at DESC",
                guild_id, status,
            )
        return await self.fetchall(
            "SELECT * FROM suggestions WHERE guild_id = ? ORDER BY created_at DESC", guild_id
        )

    # ─── Reports ────────────────────────────────────────────────────────────

    async def create_report(self, guild_id: int, message_id: int, reporter_id: int, target_id: int, reason: str, rtype: str = "user"):
        await self.execute(
            "INSERT INTO reports (guild_id, message_id, reporter_id, target_id, reason, report_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            guild_id, message_id, reporter_id, target_id, reason, rtype, time.time(),
        )

    async def resolve_report(self, report_id: int, resolved_by: int, resolution: str):
        await self.execute(
            "UPDATE reports SET status = 'resolved', resolved_by = ?, resolution = ? WHERE id = ?",
            resolved_by, resolution, report_id,
        )

    # ─── Giveaways ──────────────────────────────────────────────────────────

    async def create_giveaway(self, guild_id: int, channel_id: int, message_id: int, prize: str, winners: int, end_time: float, hosted_by: int):
        await self.execute(
            "INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winners, end_time, hosted_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            guild_id, channel_id, message_id, prize, winners, end_time, hosted_by,
        )
        return await self.fetchone("SELECT id FROM giveaways WHERE message_id = ?", message_id)

    async def end_giveaway(self, message_id: int):
        await self.execute("UPDATE giveaways SET finished = 1 WHERE message_id = ?", message_id)

    async def get_active_giveaways(self):
        return await self.fetchall(
            "SELECT * FROM giveaways WHERE finished = 0 AND end_time < ?", time.time()
        )

    async def get_guild_giveaways(self, guild_id: int):
        return await self.fetchall(
            "SELECT * FROM giveaways WHERE guild_id = ? ORDER BY end_time DESC", guild_id
        )

    async def add_giveaway_entry(self, giveaway_id: int, user_id: int):
        await self.execute(
            "INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id, entered_at) VALUES (?, ?, ?)",
            giveaway_id, user_id, time.time(),
        )

    async def get_giveaway_entries(self, giveaway_id: int):
        return await self.fetchall(
            "SELECT * FROM giveaway_entries WHERE giveaway_id = ?", giveaway_id
        )

    # ─── Verification ───────────────────────────────────────────────────────

    async def set_verified(self, user_id: int, guild_id: int, captcha: str = ""):
        await self.execute(
            "INSERT OR REPLACE INTO verification (user_id, guild_id, verified_at, captcha) VALUES (?, ?, ?, ?)",
            user_id, guild_id, time.time(), captcha,
        )

    async def is_verified(self, user_id: int, guild_id: int) -> bool:
        row = await self.fetchone(
            "SELECT * FROM verification WHERE user_id = ? AND guild_id = ?", user_id, guild_id
        )
        return row is not None

    # ─── Automod ────────────────────────────────────────────────────────────

    async def add_blacklist_word(self, guild_id: int, word: str):
        await self.execute(
            "INSERT OR IGNORE INTO automod_blacklist (guild_id, word, created_at) VALUES (?, ?, ?)",
            guild_id, word.lower(), time.time(),
        )

    async def remove_blacklist_word(self, guild_id: int, word: str):
        await self.execute(
            "DELETE FROM automod_blacklist WHERE guild_id = ? AND word = ?", guild_id, word.lower()
        )

    async def get_blacklist_words(self, guild_id: int):
        rows = await self.fetchall(
            "SELECT * FROM automod_blacklist WHERE guild_id = ? ORDER BY created_at DESC", guild_id
        )
        return [r["word"] for r in rows] if rows else []

    async def add_automod_whitelist(self, guild_id: int, role_id: int, wtype: str = "role"):
        await self.execute(
            "INSERT OR IGNORE INTO automod_whitelist (guild_id, role_id, type) VALUES (?, ?, ?)",
            guild_id, role_id, wtype,
        )

    async def remove_automod_whitelist(self, guild_id: int, role_id: int):
        await self.execute(
            "DELETE FROM automod_whitelist WHERE guild_id = ? AND role_id = ?", guild_id, role_id
        )

    async def get_automod_whitelist(self, guild_id: int, wtype: str = "role"):
        rows = await self.fetchall(
            "SELECT * FROM automod_whitelist WHERE guild_id = ? AND type = ?", guild_id, wtype
        )
        return [r["role_id"] for r in rows] if rows else []

    # ─── Anti-Nuke ──────────────────────────────────────────────────────────

    async def add_trusted_user(self, guild_id: int, user_id: int, added_by: int):
        await self.execute(
            "INSERT OR IGNORE INTO antinuke_trusted (guild_id, user_id, added_by, added_at) VALUES (?, ?, ?, ?)",
            guild_id, user_id, added_by, time.time(),
        )

    async def remove_trusted_user(self, guild_id: int, user_id: int):
        await self.execute(
            "DELETE FROM antinuke_trusted WHERE guild_id = ? AND user_id = ?", guild_id, user_id
        )

    async def get_trusted_users(self, guild_id: int):
        rows = await self.fetchall(
            "SELECT * FROM antinuke_trusted WHERE guild_id = ?", guild_id
        )
        return [r["user_id"] for r in rows] if rows else []

    async def is_trusted(self, guild_id: int, user_id: int) -> bool:
        row = await self.fetchone(
            "SELECT * FROM antinuke_trusted WHERE guild_id = ? AND user_id = ?", guild_id, user_id
        )
        return row is not None

    # ─── Logs ───────────────────────────────────────────────────────────────

    async def set_log_channel(self, guild_id: int, module: str, channel_id: int):
        await self.execute(
            "INSERT OR REPLACE INTO log_config (guild_id, module, channel_id, enabled) VALUES (?, ?, ?, 1)",
            guild_id, module, channel_id,
        )

    async def toggle_log_module(self, guild_id: int, module: str, enabled: bool):
        await self.execute(
            "UPDATE log_config SET enabled = ? WHERE guild_id = ? AND module = ?",
            1 if enabled else 0, guild_id, module,
        )

    async def get_log_channels(self, guild_id: int):
        rows = await self.fetchall(
            "SELECT * FROM log_config WHERE guild_id = ? AND enabled = 1", guild_id
        )
        result = {}
        for r in rows:
            result[r["module"]] = r["channel_id"]
        return result

    # ─── Dashboard Sessions ─────────────────────────────────────────────────

    async def create_session(self, session_id: str, user_id: int, expires_at: float):
        await self.execute(
            "INSERT OR REPLACE INTO dashboard_sessions (id, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            session_id, user_id, expires_at, time.time(),
        )

    async def get_session(self, session_id: str):
        row = await self.fetchone("SELECT * FROM dashboard_sessions WHERE id = ?", session_id)
        if not row:
            return None
        if row["expires_at"] < time.time():
            await self.execute("DELETE FROM dashboard_sessions WHERE id = ?", session_id)
            return None
        return dict(row)

    async def delete_session(self, session_id: str):
        await self.execute("DELETE FROM dashboard_sessions WHERE id = ?", session_id)

    # ─── Reputation History ─────────────────────────────────────────────────

    async def add_rep_history(self, guild_id: int, from_user_id: int, to_user_id: int, reason: str = ""):
        await self.execute(
            "INSERT INTO rep_history (guild_id, from_user_id, to_user_id, timestamp, reason) VALUES (?, ?, ?, ?, ?)",
            guild_id, from_user_id, to_user_id, time.time(), reason,
        )

    async def get_rep_history(self, guild_id: int, user_id: int = None, limit: int = 50):
        if user_id:
            return await self.fetchall(
                "SELECT * FROM rep_history WHERE guild_id = ? AND (from_user_id = ? OR to_user_id = ?) ORDER BY timestamp DESC LIMIT ?",
                guild_id, user_id, user_id, limit,
            )
        return await self.fetchall(
            "SELECT * FROM rep_history WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?",
            guild_id, limit,
        )

    async def get_rep_stats(self, guild_id: int) -> dict:
        rows = await self.fetchall(
            "SELECT to_user_id, COUNT(*) as c FROM rep_history WHERE guild_id = ? GROUP BY to_user_id ORDER BY c DESC LIMIT 10",
            guild_id,
        )
        total = await self.fetchone(
            "SELECT COUNT(*) as c FROM rep_history WHERE guild_id = ?", guild_id
        )
        return {
            "top_received": [dict(r) for r in (rows or [])],
            "total_given": total["c"] if total else 0,
        }

    # ─── Rep Roles ──────────────────────────────────────────────────────────

    async def add_rep_role(self, guild_id: int, rep: int, role_id: int):
        await self.execute(
            "INSERT OR REPLACE INTO rep_roles (guild_id, rep, role_id) VALUES (?, ?, ?)",
            guild_id, rep, role_id,
        )

    async def remove_rep_role(self, guild_id: int, rep: int):
        await self.execute(
            "DELETE FROM rep_roles WHERE guild_id = ? AND rep = ?", guild_id, rep
        )

    async def remove_rep_role_by_id(self, role_id: int):
        await self.execute("DELETE FROM rep_roles WHERE id = ?", role_id)

    async def get_rep_roles(self, guild_id: int):
        return await self.fetchall(
            "SELECT * FROM rep_roles WHERE guild_id = ? ORDER BY rep ASC", guild_id
        )

    async def check_rep_roles(self, guild_id: int, rep: int):
        rows = await self.fetchall(
            "SELECT * FROM rep_roles WHERE guild_id = ? AND rep <= ? ORDER BY rep DESC LIMIT 1",
            guild_id, rep,
        )
        return rows[0] if rows else None

    # ─── Leaderboards ───────────────────────────────────────────────────────

    async def get_leaderboard(self, guild_id: int, stat: str = "total_xp", limit: int = 15):
        valid = {"total_xp", "level", "reputation", "balance", "bank", "total_earned", "warns"}
        if stat not in valid:
            stat = "total_xp"
        return await self.fetchall(
            f"SELECT * FROM members WHERE guild_id = ? ORDER BY {stat} DESC LIMIT ?",
            guild_id, limit,
        )

    async def get_rank(self, user_id: int, guild_id: int, stat: str = "total_xp"):
        rows = await self.get_leaderboard(guild_id, stat, 1000)
        for i, r in enumerate(rows, 1):
            if r["user_id"] == user_id:
                return i, r
        return 0, None

    # ─── Custom Commands ───────────────────────────────────────────────────

    async def add_custom_command(self, guild_id: int, name: str, ctype: str, content: str, created_by: int, **kwargs):
        await self.execute(
            "INSERT INTO custom_commands (guild_id, name, type, content, embed_title, embed_description, embed_color, embed_footer, embed_image, embed_thumbnail, role_required, cooldown, created_at, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            guild_id, name.lower(), ctype, content,
            kwargs.get("embed_title", ""), kwargs.get("embed_description", ""),
            kwargs.get("embed_color", "#7c3aed"), kwargs.get("embed_footer", ""),
            kwargs.get("embed_image", ""), kwargs.get("embed_thumbnail", ""),
            kwargs.get("role_required", 0), kwargs.get("cooldown", 0),
            time.time(), created_by,
        )

    async def remove_custom_command(self, cmd_id: int, guild_id: int):
        await self.execute("DELETE FROM custom_commands WHERE id = ? AND guild_id = ?", cmd_id, guild_id)

    async def get_custom_commands(self, guild_id: int):
        return await self.fetchall("SELECT * FROM custom_commands WHERE guild_id = ? ORDER BY name ASC", guild_id)

    async def get_custom_command(self, guild_id: int, name: str):
        return await self.fetchone("SELECT * FROM custom_commands WHERE guild_id = ? AND name = ?", guild_id, name.lower())

    async def increment_cmd_uses(self, cmd_id: int):
        await self.execute("UPDATE custom_commands SET uses = uses + 1 WHERE id = ?", cmd_id)

    # ─── Temp Voice ─────────────────────────────────────────────────────────

    async def create_temp_voice(self, guild_id: int, channel_id: int, owner_id: int, name: str = ""):
        await self.execute(
            "INSERT INTO temp_voice (guild_id, channel_id, owner_id, created_at, name) VALUES (?, ?, ?, ?, ?)",
            guild_id, channel_id, owner_id, time.time(), name,
        )

    async def remove_temp_voice(self, channel_id: int):
        await self.execute("DELETE FROM temp_voice WHERE channel_id = ?", channel_id)

    async def get_temp_voice(self, channel_id: int):
        return await self.fetchone("SELECT * FROM temp_voice WHERE channel_id = ?", channel_id)

    async def get_user_temp_voice(self, user_id: int, guild_id: int):
        return await self.fetchone("SELECT * FROM temp_voice WHERE owner_id = ? AND guild_id = ?", user_id, guild_id)

    async def update_temp_voice(self, channel_id: int, **kwargs):
        if not kwargs: return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [channel_id]
        await self.execute(f"UPDATE temp_voice SET {sets} WHERE channel_id = ?", *vals)

    async def get_guild_temp_voices(self, guild_id: int):
        return await self.fetchall("SELECT * FROM temp_voice WHERE guild_id = ?", guild_id)

    # ─── Dashboard Audit ────────────────────────────────────────────────────

    async def add_audit_log(self, guild_id: int, user_id: int, action: str, module: str, details: str = ""):
        await self.execute(
            "INSERT INTO dashboard_audit (guild_id, user_id, action, module, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            guild_id, user_id, action, module, details, time.time(),
        )

    async def get_audit_logs(self, guild_id: int, limit: int = 50):
        rows = await self.fetchall(
            "SELECT * FROM dashboard_audit WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?",
            guild_id, limit,
        )
        return [dict(r) for r in rows]

    # ─── Member Search ──────────────────────────────────────────────────────

    async def search_members(self, guild_id: int, query: str = "", limit: int = 50):
        if query:
            q = f"%{query}%"
            return await self.fetchall(
                "SELECT * FROM members WHERE guild_id = ? AND (user_id LIKE ?) ORDER BY total_xp DESC LIMIT ?",
                guild_id, q, limit,
            )
        return await self.fetchall(
            "SELECT * FROM members WHERE guild_id = ? ORDER BY total_xp DESC LIMIT ?",
            guild_id, limit,
        )
