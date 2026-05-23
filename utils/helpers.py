import re
import time
import discord


def format_duration(seconds: int) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h {m}m"
    d, h = divmod(h, 24)
    return f"{d}d {h}h {m}m"

def parse_duration(text: str) -> int:
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    m = re.match(r"(\d+)\s*([smhdw])", text.lower().strip())
    if not m:
        return 0
    return int(m.group(1)) * units.get(m.group(2), 1)

def get_level_xp(level: int) -> int:
    return 5 * (level ** 2) + 50 * level + 100

def get_level_from_xp(xp: int) -> int:
    level = 0
    while get_level_xp(level) <= xp:
        xp -= get_level_xp(level)
        level += 1
    return level

def clean_text(text: str) -> str:
    return discord.utils.escape_markdown(text)

async def send_log(bot, guild_id: int, module: str, embed: discord.Embed):
    channels = await bot.db.get_log_channels(guild_id)
    ch_id = channels.get(module)
    if not ch_id:
        return
    guild = bot.get_guild(guild_id)
    if not guild:
        return
    ch = guild.get_channel(ch_id)
    if ch and ch.permissions_for(guild.me).send_messages:
        try:
            await ch.send(embed=embed)
        except:
            pass
