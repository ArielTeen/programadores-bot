import discord
from discord.ext import commands
from discord import app_commands
import time
import json
import config
from utils.embeds import success_embed, error_embed, info_embed, PremiumEmbed
from utils.helpers import send_log


class AntiNuke(commands.Cog):
    """☢️ Anti-Nuke — protección contra acciones destructivas masivas."""

    def __init__(self, bot):
        self.bot = bot
        self.action_cache = {}

    def _track(self, guild_id, action_type):
        now = time.time()
        key = f"{guild_id}:{action_type}"
        if key not in self.action_cache:
            self.action_cache[key] = []
        self.action_cache[key].append(now)
        self.action_cache[key] = [t for t in self.action_cache[key] if now - t < config.ANTINUKE_WINDOW]
        return len(self.action_cache[key])

    async def _handle_nuke(self, guild, action_type, user, detail=""):
        g = await self.bot.db.get_guild(guild.id)
        if not g.get("antinuke_enabled", 0):
            return False
        anc = g.get("antinuke_config", {})
        if isinstance(anc, str):
            try:
                anc = json.loads(anc)
            except:
                anc = {}

        if await self.bot.db.is_trusted(guild.id, user.id):
            return False

        limits = {
            "channel_delete": anc.get("channel_limit", config.ANTINUKE_CHANNEL_LIMIT),
            "channel_create": anc.get("channel_limit", config.ANTINUKE_CHANNEL_LIMIT),
            "role_delete": anc.get("role_limit", config.ANTINUKE_ROLE_LIMIT),
            "role_create": anc.get("role_limit", config.ANTINUKE_ROLE_LIMIT),
            "ban": anc.get("ban_limit", config.ANTINUKE_BAN_LIMIT),
            "kick": anc.get("kick_limit", config.ANTINUKE_KICK_LIMIT),
        }

        count = self._track(guild.id, action_type)
        limit = limits.get(action_type, 3)

        if count >= limit:
            embed = PremiumEmbed(
                title="☢️ Anti-Nuke Activado",
                description=f"**Usuario:** {user.mention} (`{user.id}`)\n**Acción:** {action_type}\n**Detalle:** {detail}",
                color=config.ERROR_COLOR,
            )
            punishment = anc.get("punishment", "ban")
            try:
                if punishment == "ban":
                    await guild.ban(user, reason=f"Anti-Nuke: {action_type}", delete_message_days=1)
                elif punishment == "kick":
                    await user.kick(reason=f"Anti-Nuke: {action_type}")
                elif punishment == "timeout":
                    await user.timeout(discord.utils.utcnow() + discord.timedelta(hours=24), reason=f"Anti-Nuke: {action_type}")
            except:
                pass
            embed.add_field(name="⚡ Castigo", value=punishment)
            await send_log(self.bot, guild.id, "antinuke", embed)

            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    await ch.send(embed=embed)
                    break
            return True
        return False

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            await self._handle_nuke(channel.guild, "channel_delete", entry.user, f"#{channel.name}")
            break

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            await self._handle_nuke(channel.guild, "channel_create", entry.user, f"#{channel.name}")
            break

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            await self._handle_nuke(role.guild, "role_delete", entry.user, f"@{role.name}")
            break

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            await self._handle_nuke(role.guild, "role_create", entry.user, f"@{role.name}")
            break

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.user.id != self.bot.user.id:
                await self._handle_nuke(guild, "ban", entry.user, f"{user}")
            break

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot:
            return
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.user.id != self.bot.user.id:
                await self._handle_nuke(member.guild, "kick", entry.user, f"{member}")
            break

    # ── Comandos ─────────────────────────────────────────────────────────────
    antinuke = app_commands.Group(name="antinuke", description="☢️ Configurar anti-nuke")

    @antinuke.command(name="enable", description="✅ Activar anti-nuke")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def an_enable(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, antinuke_enabled=1)
        await interaction.followup.send(embed=success_embed("☢️ Anti-Nuke activado"))

    @antinuke.command(name="disable", description="❌ Desactivar anti-nuke")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def an_disable(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, antinuke_enabled=0)
        await interaction.followup.send(embed=success_embed("☢️ Anti-Nuke desactivado"))

    @antinuke.command(name="status", description="📊 Estado del anti-nuke")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def an_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        anc = g.get("antinuke_config", {})
        if isinstance(anc, str):
            try:
                anc = json.loads(anc)
            except:
                anc = {}
        trusted = await self.bot.db.get_trusted_users(interaction.guild.id)
        embed = PremiumEmbed(
            title="☢️ Anti-Nuke Status",
            description="✅ Activado" if g.get("antinuke_enabled", 0) else "❌ Desactivado",
            color=config.SUCCESS_COLOR if g.get("antinuke_enabled", 0) else config.ERROR_COLOR,
        )
        embed.add_field(name="👥 Usuarios de confianza", value=str(len(trusted)), inline=True)
        embed.add_field(name="⚡ Castigo", value=anc.get("punishment", "ban"), inline=True)
        embed.add_field(name="📊 Límites", value=f"Canales: {anc.get('channel_limit', 3)} | Roles: {anc.get('role_limit', 3)} | Bans: {anc.get('ban_limit', 3)}", inline=False)
        await interaction.followup.send(embed=embed)

    @antinuke.command(name="trust", description="➕ Confiar en un usuario")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(administrator=True)
    async def an_trust(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.bot.db.add_trusted_user(interaction.guild.id, user.id, interaction.user.id)
        await interaction.followup.send(embed=success_embed("➕ Usuario de confianza", user.mention))

    @antinuke.command(name="untrust", description="➖ Quitar confianza a un usuario")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(administrator=True)
    async def an_untrust(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer()
        await self.bot.db.remove_trusted_user(interaction.guild.id, user.id)
        await interaction.followup.send(embed=success_embed("➖ Confianza quitada", user.mention))

    @antinuke.command(name="trusted", description="📋 Listar usuarios de confianza")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def an_trusted(self, interaction: discord.Interaction):
        await interaction.response.defer()
        uids = await self.bot.db.get_trusted_users(interaction.guild.id)
        if not uids:
            return await interaction.followup.send(embed=info_embed("📋", "No hay usuarios de confianza."))
        lines = []
        for uid in uids:
            u = interaction.guild.get_member(uid) or await self.bot.fetch_user(uid)
            lines.append(f"• {u.mention} (`{uid}`)")
        embed = PremiumEmbed(title="👥 Usuarios de confianza", description="\n".join(lines), color=config.EMBED_COLOR)
        await interaction.followup.send(embed=embed)

    @antinuke.command(name="punishment", description="⚡ Configurar castigo")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(action="ban, kick, timeout")
    @app_commands.checks.has_permissions(administrator=True)
    async def an_punishment(self, interaction: discord.Interaction, action: str):
        await interaction.response.defer()
        if action not in ("ban", "kick", "timeout"):
            return await interaction.followup.send(embed=error_embed("❌", "ban, kick o timeout"))
        g = await self.bot.db.get_guild(interaction.guild.id)
        anc = g.get("antinuke_config", {})
        if isinstance(anc, str):
            try:
                anc = json.loads(anc)
            except:
                anc = {}
        anc["punishment"] = action
        await self.bot.db.update_guild(interaction.guild.id, antinuke_config=anc)
        await interaction.followup.send(embed=success_embed("⚡ Castigo", action))


async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
