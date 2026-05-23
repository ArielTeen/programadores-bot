import pytest, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import Database
import tempfile

@pytest.mark.asyncio
async def test_db_connect():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()
    assert db.pool is not None
    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_guild_config_create():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    g = await db.get_guild(12345)
    assert g["guild_id"] == 12345
    assert g.get("prefix", "!") == "!"

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_guild_config_update():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    g = await db.get_guild(12345)
    assert g is not None
    await db.update_guild(12345, prefix="?", language="en")
    g2 = await db.get_guild(12345)
    assert g2.get("prefix") == "?"
    assert g2.get("language") == "en"

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_member_create():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    m = await db.get_member(111, 222)
    assert m["user_id"] == 111
    assert m["guild_id"] == 222
    assert m.get("balance", 0) == 100

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_member_update():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    m = await db.get_member(111, 222)
    assert m["balance"] == 100
    await db.update_member(111, 222, balance=500, reputation=10)
    m2 = await db.get_member(111, 222)
    assert m2["balance"] == 500
    assert m2["reputation"] == 10

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_warnings():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    w = await db.add_warning(111, 222, 333, "Test warn")
    assert w is not None
    warns = await db.get_warnings(111, 222)
    assert len(warns) == 1
    assert warns[0]["reason"] == "Test warn"

    removed = await db.remove_warning(warns[0]["id"], 222)
    assert removed is True

    warns_after = await db.get_warnings(111, 222)
    assert len(warns_after) == 0

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_tickets():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    t = await db.create_ticket(222, 555, 111, "general")
    assert t is not None

    tickets = await db.get_guild_tickets(222)
    assert len(tickets) == 1
    assert tickets[0]["status"] == "open"

    await db.close_ticket(555, 333)
    ticket_check = await db.get_ticket(555)
    assert ticket_check["status"] == "closed"

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_shop():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.add_shop_item(222, "VIP", "VIP Role", 888, 1000, "⭐")
    items = await db.get_shop_items(222)
    assert len(items) == 1
    assert items[0]["name"] == "VIP"
    assert items[0]["price"] == 1000

    await db.remove_shop_item(items[0]["id"], 222)
    items_after = await db.get_shop_items(222)
    assert len(items_after) == 0

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_reaction_roles():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.add_reaction_role(222, 555, 777, 888, "⭐", "reaction")
    roles = await db.get_reaction_roles(222)
    assert len(roles) == 1
    assert roles[0]["emoji"] == "⭐"

    await db.remove_reaction_role(roles[0]["id"], 222)
    roles_after = await db.get_reaction_roles(222)
    assert len(roles_after) == 0

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_suggestions():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.create_suggestion(222, 999, 111, "Great bot!")
    suggestions = await db.get_guild_suggestions(222)
    assert len(suggestions) == 1
    assert suggestions[0]["status"] == "pending"
    assert suggestions[0]["content"] == "Great bot!"

    await db.update_suggestion_status(999, "approved", "Good idea!")
    updated = await db.get_suggestion(999)
    assert updated["status"] == "approved"

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_giveaways():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    gw = await db.create_giveaway(222, 555, 777, "Nitro", 1, time.time() + 3600, 111)
    assert gw is not None

    gws = await db.get_guild_giveaways(222)
    assert len(gws) == 1
    assert gws[0]["prize"] == "Nitro"

    await db.end_giveaway(777)
    ended = await db.fetchone("SELECT finished FROM giveaways WHERE id = ?", gws[0]["id"])
    assert ended["finished"] == 1

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_leaderboard():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.get_member(111, 222)
    await db.get_member(333, 222)
    await db.update_member(111, 222, total_xp=1000, level=5)
    await db.update_member(333, 222, total_xp=2000, level=10)

    lb = await db.get_leaderboard(222, "total_xp", 10)
    assert len(lb) == 2
    assert lb[0]["user_id"] == 333  # highest XP first

    await db.close()
    os.unlink(tmp.name)


@pytest.mark.asyncio
async def test_custom_commands():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.add_custom_command(222, "hola", "text", "Hola mundo!", 111)
    await db.add_custom_command(222, "info", "embed", "", 111, embed_title="Info", embed_description="Server info")
    cmds = await db.get_custom_commands(222)
    assert len(cmds) == 2
    assert cmds[0]["name"] == "hola"

    cmd = await db.get_custom_command(222, "hola")
    assert cmd is not None
    assert cmd["content"] == "Hola mundo!"

    await db.remove_custom_command(cmds[0]["id"], 222)
    cmds_after = await db.get_custom_commands(222)
    assert len(cmds_after) == 1

    await db.close()
    os.unlink(tmp.name)


@pytest.mark.asyncio
async def test_temp_voice():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.create_temp_voice(222, 555, 111, "Mi canal")
    voices = await db.get_guild_temp_voices(222)
    assert len(voices) == 1
    assert voices[0]["name"] == "Mi canal"

    tv = await db.get_user_temp_voice(111, 222)
    assert tv is not None
    assert tv["channel_id"] == 555

    await db.update_temp_voice(555, name="Nuevo nombre")
    updated = await db.get_temp_voice(555)
    assert updated["name"] == "Nuevo nombre"

    await db.remove_temp_voice(555)
    voices_after = await db.get_guild_temp_voices(222)
    assert len(voices_after) == 0

    await db.close()
    os.unlink(tmp.name)


@pytest.mark.asyncio
async def test_audit_log():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.add_audit_log(222, 111, "config_update", "general", "Updated prefix")
    await db.add_audit_log(222, 111, "warn_add", "moderation", "Warned user 333")
    logs = await db.get_audit_logs(222)
    assert len(logs) == 2
    assert logs[0]["action"] == "warn_add"
    assert logs[0]["module"] == "moderation"

    await db.close()
    os.unlink(tmp.name)


@pytest.mark.asyncio
async def test_member_search():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.get_member(111, 222)
    await db.get_member(333, 222)
    await db.get_member(555, 222)

    all_members = await db.search_members(222, "", 10)
    assert len(all_members) == 3

    await db.close()
    os.unlink(tmp.name)


@pytest.mark.asyncio
async def test_rep_system():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.add_rep_history(222, 111, 333, "Great help!")
    await db.add_rep_history(222, 444, 333, "Thanks!")

    stats = await db.get_rep_stats(222)
    assert stats["total_given"] == 2

    history = await db.get_rep_history(222, 333, 10)
    assert len(history) == 2

    await db.add_rep_role(222, 10, 888)
    await db.add_rep_role(222, 20, 999)
    roles = await db.get_rep_roles(222)
    assert len(roles) == 2

    await db.remove_rep_role_by_id(roles[0]["id"])
    roles_after = await db.get_rep_roles(222)
    assert len(roles_after) == 1

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_automod():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.add_blacklist_word(222, "badword")
    words = await db.get_blacklist_words(222)
    assert "badword" in words

    await db.remove_blacklist_word(222, "badword")
    words_after = await db.get_blacklist_words(222)
    assert "badword" not in words_after

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_antinuke():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.add_trusted_user(222, 111, 333)
    assert await db.is_trusted(222, 111) is True
    assert await db.is_trusted(222, 444) is False

    trusted = await db.get_trusted_users(222)
    assert 111 in trusted

    await db.remove_trusted_user(222, 111)
    assert await db.is_trusted(222, 111) is False

    await db.close()
    os.unlink(tmp.name)

@pytest.mark.asyncio
async def test_sessions():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = Database(tmp.name)
    await db.connect()

    await db.create_session("sess_123", 111, time.time() + 3600)
    sess = await db.get_session("sess_123")
    assert sess is not None
    assert sess["user_id"] == 111

    await db.delete_session("sess_123")
    sess_after = await db.get_session("sess_123")
    assert sess_after is None

    await db.close()
    os.unlink(tmp.name)
