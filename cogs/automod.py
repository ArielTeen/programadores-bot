import discord
from discord.ext import commands
from discord import app_commands
import time
import re
import json
import config
from utils.embeds import success_embed, error_embed, info_embed, PremiumEmbed
from utils.helpers import send_log


class AutoMod(commands.Cog):
    """🤖 Automod — anti-spam, anti-link, anti-raid, blacklist, etc."""

    def __init__(self, bot):
        self.bot = bot
        self.flood_cache = {}
        self.raid_cache = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        g = await self.bot.db.get_guild(message.guild.id)
        if not g.get("automod_enabled", 0):
            return
        amc = g.get("automod_config", {})
        if isinstance(amc, str):
            try:
                amc = json.loads(amc)
            except:
                amc = {}

        author = message.author

        # Whitelist check
        wl_roles = await self.bot.db.get_automod_whitelist(message.guild.id, "role")
        if any(message.guild.get_role(rid) in author.roles for rid in wl_roles if message.guild.get_role(rid)):
            return

        # Anti-flood
        if amc.get("flood", True):
            await self._check_flood(message, g)

        # Anti-links
        if amc.get("links", True):
            await self._check_links(message, g)

        # Anti-invites
        if amc.get("invites", True):
            await self._check_invites(message, g)

        # Anti-mentions
        if amc.get("mentions", True):
            await self._check_mentions(message, g)

        # Anti-caps
        if amc.get("caps", True):
            await self._check_caps(message, g)

        # Anti-emoji
        if amc.get("emoji_spam", True):
            await self._check_emoji(message, g)

        # Anti-zalgo
        if amc.get("zalgo", True):
            await self._check_zalgo(message, g)

        # Blacklist words
        if amc.get("bad_words", True):
            await self._check_bad_words(message, g)

    async def _punish(self, message, guild_conf, action="warn"):
        punishment = guild_conf.get("automod_config", {}).get("punishment", "warn")
        if isinstance(punishment, str) and punishment:
            action = punishment
        try:
            if action == "delete":
                await message.delete()
            elif action == "warn":
                await message.delete()
                await self.bot.db.add_warning(message.author.id, message.guild.id, message.guild.me.id, "Automod")
            elif action == "mute":
                await message.delete()
                role = discord.utils.get(message.guild.roles, name=config.MUTE_ROLE_NAME)
                if role:
                    await message.author.add_roles(role, reason="Automod")
                    await self.bot.db.add_muted(message.author.id, message.guild.id, time.time() + 3600)
            elif action == "kick":
                await message.author.kick(reason="Automod")
            elif action == "ban":
                await message.author.ban(reason="Automod")
        except:
            pass

    async def _check_flood(self, msg, g):
        now = time.time()
        key = f"{msg.author.id}:{msg.channel.id}"
        if key not in self.flood_cache:
            self.flood_cache[key] = []
        self.flood_cache[key].append(now)
        self.flood_cache[key] = [t for t in self.flood_cache[key] if now - t < config.FLOOD_WINDOW]
        if len(self.flood_cache[key]) > config.FLOOD_LIMIT:
            await self._punish(msg, g)
            emb = warning_embed("🚫 Anti-Flood", f"{msg.author.mention} no hagas spam.")
            await msg.channel.send(embed=emb, delete_after=5)
            await send_log(self.bot, msg.guild.id, "automod", emb)

    async def _check_links(self, msg, g):
        if "http://" in msg.content or "https://" in msg.content:
            count = sum(1 for w in msg.content.split() if w.startswith(("http://", "https://")))
            if count > config.MAX_LINKS:
                await self._punish(msg, g)
                emb = warning_embed("🚫 Anti-Links", f"{msg.author.mention} demasiados enlaces.")
                await msg.channel.send(embed=emb, delete_after=5)

    async def _check_invites(self, msg, g):
        if re.search(r"(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)", msg.content, re.I):
            await self._punish(msg, g)
            emb = warning_embed("🚫 Anti-Invites", f"{msg.author.mention} no envíes invitaciones.")
            await msg.channel.send(embed=emb, delete_after=5)

    async def _check_mentions(self, msg, g):
        if len(msg.mentions) > config.MAX_MENTIONS:
            await self._punish(msg, g)
            emb = warning_embed("🚫 Anti-Menciones", f"{msg.author.mention} demasiadas menciones.")
            await msg.channel.send(embed=emb, delete_after=5)

    async def _check_caps(self, msg, g):
        if len(msg.content) > 10:
            caps = sum(1 for c in msg.content if c.isupper())
            if caps / len(msg.content) * 100 > config.MAX_CAPS_PERCENT:
                await self._punish(msg, g, "delete")
                emb = warning_embed("🚫 Anti-Caps", f"{msg.author.mention} demasiadas mayúsculas.")
                await msg.channel.send(embed=emb, delete_after=5)

    async def _check_emoji(self, msg, g):
        emoji_pattern = re.compile(r"<a?:\w+:\d+>|[\U0001F300-\U0001FFFF\u2600-\u27BF]")
        emojis = emoji_pattern.findall(msg.content)
        if len(emojis) > config.MAX_EMOJI_COUNT:
            await self._punish(msg, g, "delete")
            emb = warning_embed("🚫 Anti-Emoji", f"{msg.author.mention} demasiados emojis.")
            await msg.channel.send(embed=emb, delete_after=5)

    async def _check_zalgo(self, msg, g):
        zalgo = re.findall(r"[\u0300-\u036f\u0483-\u0489\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e4\u06e7-\u06e8\u06ea-\u06ed]", msg.content)
        if len(zalgo) > 10:
            await self._punish(msg, g, "delete")
            emb = warning_embed("🚫 Anti-Zalgo", f"{msg.author.mention} texto corrupto.")
            await msg.channel.send(embed=emb, delete_after=5)

    async def _check_bad_words(self, msg, g):
        words = await self.bot.db.get_blacklist_words(msg.guild.id)
        if not words:
            return
        content = msg.content.lower()
        for word in words:
            if word.lower() in content.split():
                await self._punish(msg, g)
                emb = warning_embed("🚫 Palabra prohibida", f"{msg.author.mention} contenido no permitido.")
                await msg.channel.send(embed=emb, delete_after=5)
                break

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        g = await self.bot.db.get_guild(member.guild.id)
        if not g.get("automod_enabled", 0):
            return
        amc = g.get("automod_config", {})
        if isinstance(amc, str):
            try:
                amc = json.loads(amc)
            except:
                amc = {}

        # Anti-raid
        if amc.get("raid", True):
            now = time.time()
            gid = member.guild.id
            if gid not in self.raid_cache:
                self.raid_cache[gid] = []
            self.raid_cache[gid].append(now)
            self.raid_cache[gid] = [t for t in self.raid_cache[gid] if now - t < config.RAID_WINDOW]
            if len(self.raid_cache[gid]) > config.RAID_JOIN_LIMIT:
                try:
                    await member.guild.edit(verification_level=discord.VerificationLevel.high, reason="Anti-raid")
                    emb = warning_embed("🚨 Anti-Raid", "Posible raid detectada. Verificación aumentada.")
                    await send_log(self.bot, member.guild.id, "automod", emb)
                except:
                    pass

        # Anti-alt
        if amc.get("alt_account", False):
            age = (discord.utils.utcnow() - member.created_at).days
            if age < config.ALT_ACCOUNT_AGE:
                emb = warning_embed("⚠️ Cuenta nueva", f"{member.mention} cuenta creada hace {age} días.")
                await send_log(self.bot, member.guild.id, "automod", emb)

    # ── Comandos ─────────────────────────────────────────────────────────────
    automod = app_commands.Group(name="automod", description="🤖 Configurar automod")

    @automod.command(name="enable", description="✅ Activar automod")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def am_enable(self, interaction: discord.Interaction):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        await self.bot.db.update_guild(interaction.guild.id, automod_enabled=1)
        await interaction.followup.send(embed=success_embed("✅ Automod activado"))

    @automod.command(name="disable", description="❌ Desactivar automod")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def am_disable(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, automod_enabled=0)
        await interaction.followup.send(embed=success_embed("❌ Automod desactivado"))

    @automod.command(name="status", description="📊 Estado del automod")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def am_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        amc = g.get("automod_config", {})
        if isinstance(amc, str):
            try:
                amc = json.loads(amc)
            except:
                amc = {}
        enabled = g.get("automod_enabled", 0)
        embed = PremiumEmbed(
            title="🤖 Automod Status",
            description="✅ Activado" if enabled else "❌ Desactivado",
            color=config.SUCCESS_COLOR if enabled else config.ERROR_COLOR,
        )
        modules = {
            "flood": "Anti-Flood", "links": "Anti-Links", "invites": "Anti-Invites",
            "mentions": "Anti-Menciones", "caps": "Anti-Caps", "emoji_spam": "Anti-Emoji",
            "zalgo": "Anti-Zalgo", "bad_words": "Palabras prohibidas", "raid": "Anti-Raid",
        }
        for key, name in modules.items():
            val = amc.get(key, True)
            embed.add_field(name=name, value="✅" if val else "❌", inline=True)
        words = await self.bot.db.get_blacklist_words(interaction.guild.id)
        embed.add_field(name="📝 Palabras en blacklist", value=str(len(words)), inline=False)
        embed.add_field(name="⚡ Castigo", value=amc.get("punishment", "warn"), inline=True)
        await interaction.followup.send(embed=embed)

    @automod.command(name="config", description="⚙️ Configurar módulo de automod")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(module="Módulo", enabled="Activar/Desactivar")
    @app_commands.checks.has_permissions(administrator=True)
    async def am_config(self, interaction: discord.Interaction, module: str, enabled: bool):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        amc = g.get("automod_config", {})
        if isinstance(amc, str):
            try:
                amc = json.loads(amc)
            except:
                amc = {}
        amc[module] = enabled
        await self.bot.db.update_guild(interaction.guild.id, automod_config=amc)
        await interaction.followup.send(embed=success_embed("⚙️ Config actualizada", f"{module}: {'✅' if enabled else '❌'}"))

    @am_config.autocomplete("module")
    async def am_config_ac(self, interaction: discord.Interaction, current: str):
        opts = ["flood", "links", "invites", "mentions", "caps", "emoji_spam", "zalgo", "bad_words", "raid", "alt_account"]
        return [app_commands.Choice(name=o, value=o) for o in opts if current.lower() in o.lower()]

    @automod.command(name="punishment", description="⚡ Configurar castigo de automod")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(action="Acción: delete, warn, mute, kick, ban")
    @app_commands.checks.has_permissions(administrator=True)
    async def am_punishment(self, interaction: discord.Interaction, action: str):
        await interaction.response.defer()
        if action not in ("delete", "warn", "mute", "kick", "ban"):
            return await interaction.followup.send(embed=error_embed("❌", "Opciones: delete, warn, mute, kick, ban"))
        g = await self.bot.db.get_guild(interaction.guild.id)
        amc = g.get("automod_config", {})
        if isinstance(amc, str):
            try:
                amc = json.loads(amc)
            except:
                amc = {}
        amc["punishment"] = action
        await self.bot.db.update_guild(interaction.guild.id, automod_config=amc)
        await interaction.followup.send(embed=success_embed("⚡ Castigo actualizado", action))

    @automod.command(name="whitelist", description="➕ Añadir rol a whitelist de automod")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="Rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def am_whitelist(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer()
        await self.bot.db.add_automod_whitelist(interaction.guild.id, role.id, "role")
        await interaction.followup.send(embed=success_embed("➕ Rol en whitelist", role.mention))

    blacklist = app_commands.Group(name="automod_blacklist", description="📝 Gestionar blacklist de palabras")

    @blacklist.command(name="add", description="➕ Añadir palabra a blacklist")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(word="Palabra")
    @app_commands.checks.has_permissions(administrator=True)
    async def bl_add(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer()
        await self.bot.db.add_blacklist_word(interaction.guild.id, word)
        await interaction.followup.send(embed=success_embed("➕ Palabra añadida", f"`{word}`"))

    @blacklist.command(name="remove", description="➖ Quitar palabra de blacklist")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(word="Palabra")
    @app_commands.checks.has_permissions(administrator=True)
    async def bl_remove(self, interaction: discord.Interaction, word: str):
        await interaction.response.defer()
        await self.bot.db.remove_blacklist_word(interaction.guild.id, word)
        await interaction.followup.send(embed=success_embed("➖ Palabra quitada", f"`{word}`"))

    @blacklist.command(name="list", description="📋 Listar palabras en blacklist")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def bl_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        words = await self.bot.db.get_blacklist_words(interaction.guild.id)
        if not words:
            return await interaction.followup.send(embed=info_embed("📋 Blacklist", "No hay palabras."))
        embed = PremiumEmbed(title="📋 Blacklist de palabras", description="\n".join(f"`{w}`" for w in words), color=config.EMBED_COLOR)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
