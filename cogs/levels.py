import discord
from discord.ext import commands
from discord import app_commands
import time
import math
import config
from utils.embeds import success_embed, error_embed, info_embed, PremiumEmbed, send_ephemeral
from utils.helpers import get_level_xp, get_level_from_xp, send_log
from utils.paginator import ReactionPaginator


class Levels(commands.Cog):
    """📊 Sistema de niveles y XP — mensajes, voz, roles de nivel."""

    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}
        self.voice_xp = {}

    async def add_xp(self, member: discord.Member, guild_id: int):
        if member.bot:
            return
        g = await self.bot.db.get_guild(guild_id)
        if not g.get("level_enabled", 1):
            return
        now = time.time()
        key = f"{member.id}:{guild_id}"
        if key in self.xp_cooldowns and now - self.xp_cooldowns[key] < config.XP_COOLDOWN:
            return
        self.xp_cooldowns[key] = now

        md = await self.bot.db.get_member(member.id, guild_id)
        md["xp"] = md.get("xp", 0) + config.XP_PER_MESSAGE
        md["total_xp"] = md.get("total_xp", 0) + config.XP_PER_MESSAGE

        old_level = md.get("level", 0)
        new_level = get_level_from_xp(md["total_xp"])

        if new_level > old_level:
            md["level"] = new_level
            md["xp"] = md["total_xp"] - sum(get_level_xp(l) for l in range(new_level))
            await self.bot.db.update_member(member.id, guild_id, xp=md["xp"], level=new_level, total_xp=md["total_xp"])
            await self._level_up(member, new_level, guild_id)
            await self._check_level_roles(member, new_level, guild_id)
        else:
            await self.bot.db.update_member(member.id, guild_id, xp=md["xp"], total_xp=md["total_xp"])

    async def _level_up(self, member, level, guild_id):
        g = await self.bot.db.get_guild(guild_id)
        msg = g.get("level_message", "🎉 ¡{user} ha subido al nivel **{level}**!").format(user=member.mention, level=level, name=member.name)
        ch_id = g.get("level_channel")
        embed = PremiumEmbed(title="¡Subiste de nivel!", description=msg, color=config.COLORS["purple"])
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await member.send(embed=embed)
        except:
            if ch_id:
                ch = member.guild.get_channel(ch_id)
                if ch:
                    await ch.send(embed=embed)
            else:
                guild = self.bot.get_guild(guild_id)
                if guild and guild.system_channel:
                    await guild.system_channel.send(embed=embed)

    async def _check_level_roles(self, member, level, guild_id):
        rows = await self.bot.db.get_level_roles(guild_id)
        for r in rows:
            if level >= r["level"]:
                role = member.guild.get_role(r["role_id"])
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Nivel alcanzado")
                    except:
                        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        await self.add_xp(message.author, message.guild.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        g = await self.bot.db.get_guild(member.guild.id)
        if not g.get("level_enabled", 1):
            return

        if after.channel and not before.channel:
            self.voice_xp[member.id] = {"guild": member.guild.id, "start": time.time()}
        elif not after.channel and before.channel:
            if member.id in self.voice_xp:
                data = self.voice_xp.pop(member.id)
                dur = (time.time() - data["start"]) / 60
                if dur >= 1:
                    xp = int(dur * config.XP_PER_VOICE_MINUTE)
                    md = await self.bot.db.get_member(member.id, member.guild.id)
                    md["voice_xp"] = md.get("voice_xp", 0) + xp
                    md["total_xp"] = md.get("total_xp", 0) + xp
                    old_lv = md.get("level", 0)
                    new_lv = get_level_from_xp(md["total_xp"])
                    if new_lv > old_lv:
                        md["level"] = new_lv
                        await self.bot.db.update_member(member.id, member.guild.id, level=new_lv, total_xp=md["total_xp"], voice_xp=md["voice_xp"])
                        await self._level_up(member, new_lv, member.guild.id)
                        await self._check_level_roles(member, new_lv, member.guild.id)
                    else:
                        await self.bot.db.update_member(member.id, member.guild.id, total_xp=md["total_xp"], voice_xp=md["voice_xp"])

    # ── Comandos ─────────────────────────────────────────────────────────────
    @app_commands.command(name="rank", description="Ver tu nivel")
    @app_commands.describe(user="Usuario (opcional)")
    async def rank(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(user.id, interaction.guild.id)
        level = md.get("level", 0)
        xp = md.get("xp", 0)
        total = md.get("total_xp", 0)
        needed = get_level_xp(level)
        pct = min(xp / needed * 100, 100) if needed else 0
        rank, _ = await self.bot.db.get_rank(user.id, interaction.guild.id, "total_xp")

        bar = "🟩" * int(pct / 100 * 12) + "⬜" * (12 - int(pct / 100 * 12))
        embed = PremiumEmbed(title=f"📊 {user.display_name}", color=user.color or config.EMBED_COLOR)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Nivel", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp:,}/{needed:,}f", inline=True)
        embed.add_field(name="Total XP", value=f"{total:,}f", inline=True)
        embed.add_field(name="Progreso", value=f"{bar} {pct:.0f}%f", inline=False)
        embed.add_field(name="XP Voz", value=str(md.get("voice_xp", 0)), inline=True)
        embed.add_field(name="#⃣ Ranking", value=f"#{rank}f" if rank else "N/A", inline=True)
        await send_ephemeral(interaction, embed=embed)

    @app_commands.command(name="leaderboard", description="Ranking del servidor")
    @app_commands.describe(tipo="xp, level, reputation, balance")
    async def leaderboard(self, interaction: discord.Interaction, tipo: str = "xp"):
        await interaction.response.defer(ephemeral=True)
        stat_map = {"xp": "total_xp", "level": "level", "reputacion": "reputation", "balance": "balance"}
        stat = stat_map.get(tipo.lower(), "total_xp")
        labels = {"total_xp": "✨ XP", "level": "🏆 Nivel", "reputation": "⭐ Rep", "balance": "💰 Monedas"}
        rows = await self.bot.db.get_leaderboard(interaction.guild.id, stat, 50)
        if not rows:
            return await send_ephemeral(interaction, embed=info_embed("🏆", "Sin datos."))
        per_page = 10
        pages = []
        medals = ["🥇", "🥈", "🥉"]
        chunks = [rows[i:i+per_page] for i in range(0, len(rows), per_page)]
        for chunk_idx, chunk in enumerate(chunks):
            embed = PremiumEmbed(
                title=f"🏆 Ranking · {labels.get(stat, stat)} · {interaction.guild.name}",
                color=config.COLORS["gold"],
            )
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            start_rank = chunk_idx * per_page + 1
            for i, r in enumerate(chunk):
                m = interaction.guild.get_member(r["user_id"])
                name = m.display_name if m else f"`{r['user_id']}`"
                rank = start_rank + i
                prefix = medals[i] if i < 3 else f"`#{rank}`"
                val = r.get(stat, 0)
                embed.add_field(name=f"{prefix} {name}f", value=f"{labels.get(stat, stat)}: **{val:,}**f", inline=False)
            pages.append(embed)
        if len(pages) <= 1:
            return await send_ephemeral(interaction, embed=pages[0])
        pag = ReactionPaginator(interaction, pages, timeout=60)
        await pag.start()

    @leaderboard.autocomplete("tipo")
    async def lb_ac(self, interaction: discord.Interaction, current: str):
        opts = [("xp", "xp"), ("level", "level"), ("reputacion", "reputación"), ("balance", "balance")]
        return [app_commands.Choice(name=n, value=v) for n, v in opts if current.lower() in n.lower()]

    xp = app_commands.Group(name="xp", description="Gestionar XP (staff)")

    @xp.command(name="add", description="Añadir XP a un usuario")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario", cantidad="Cantidad")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_add(self, interaction: discord.Interaction, user: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(user.id, interaction.guild.id)
        md["total_xp"] = md.get("total_xp", 0) + cantidad
        new_lv = get_level_from_xp(md["total_xp"])
        md["level"] = new_lv
        md["xp"] = md["total_xp"] - sum(get_level_xp(l) for l in range(new_lv))
        await self.bot.db.update_member(user.id, interaction.guild.id, total_xp=md["total_xp"], level=new_lv, xp=md["xp"])
        await send_ephemeral(interaction, embed=success_embed("➕ XP añadida", f"{user.mention}: +{cantidad} XP"))

    @xp.command(name="remove", description="Quitar XP")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario", cantidad="Cantidad")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_remove(self, interaction: discord.Interaction, user: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(user.id, interaction.guild.id)
        md["total_xp"] = max(0, md.get("total_xp", 0) - cantidad)
        new_lv = get_level_from_xp(md["total_xp"])
        md["level"] = new_lv
        md["xp"] = md["total_xp"] - sum(get_level_xp(l) for l in range(new_lv))
        await self.bot.db.update_member(user.id, interaction.guild.id, total_xp=md["total_xp"], level=new_lv, xp=md["xp"])
        await send_ephemeral(interaction, embed=success_embed("➖ XP quitada", f"{user.mention}: -{cantidad} XP"))

    @xp.command(name="set", description="Establecer XP total")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario", cantidad="Nuevo total XP")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_set(self, interaction: discord.Interaction, user: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(user.id, interaction.guild.id)
        md["total_xp"] = max(0, cantidad)
        new_lv = get_level_from_xp(md["total_xp"])
        md["level"] = new_lv
        md["xp"] = md["total_xp"] - sum(get_level_xp(l) for l in range(new_lv))
        await self.bot.db.update_member(user.id, interaction.guild.id, total_xp=md["total_xp"], level=new_lv, xp=md["xp"])
        await send_ephemeral(interaction, embed=success_embed("🔧 XP establecida", f"{user.mention}: {cantidad} XP"))

    @xp.command(name="reset", description="Resetear XP de un usuario")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(administrator=True)
    async def xp_reset(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.update_member(user.id, interaction.guild.id, xp=0, level=0, total_xp=0)
        await send_ephemeral(interaction, embed=success_embed("🔄 XP reseteada", user.mention))

    levelroles = app_commands.Group(name="levelroles", description="Roles de nivel")

    @levelroles.command(name="add", description="Añadir rol por nivel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(level="Nivel requerido", role="Rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def lr_add(self, interaction: discord.Interaction, level: int, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.add_level_role(interaction.guild.id, level, role.id)
        await send_ephemeral(interaction, embed=success_embed("🎭 Rol de nivel", f"Nivel {level} → {role.mention}"))

    @levelroles.command(name="remove", description="Quitar rol por nivel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(level="Nivel")
    @app_commands.checks.has_permissions(administrator=True)
    async def lr_remove(self, interaction: discord.Interaction, level: int):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.remove_level_role(interaction.guild.id, level)
        await send_ephemeral(interaction, embed=success_embed("➖ Rol de nivel quitado", f"Nivel {level}"))

    @levelroles.command(name="list", description="Listar roles de nivel")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def lr_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows = await self.bot.db.get_level_roles(interaction.guild.id)
        if not rows:
            return await send_ephemeral(interaction, embed=info_embed("📋", "No hay roles de nivel."))
        embed = PremiumEmbed(title="Roles de nivel", color=config.EMBED_COLOR)
        for r in rows:
            role = interaction.guild.get_role(r["role_id"])
            embed.add_field(name=f"Nivel {r['level']}f", value=role.mention if role else "Rol eliminado", inline=False)
        await send_ephemeral(interaction, embed=embed)

    @app_commands.command(name="levelconfig", description="Configurar sistema de niveles")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal de notificaciones (0=DM)", message="Mensaje de subida de nivel")
    @app_commands.checks.has_permissions(administrator=True)
    async def levelconfig(self, interaction: discord.Interaction, channel: discord.TextChannel = None, message: str = None):
        await interaction.response.defer(ephemeral=True)
        if channel:
            await self.bot.db.update_guild(interaction.guild.id, level_channel=channel.id)
        if message:
            await self.bot.db.update_guild(interaction.guild.id, level_message=message)
        await send_ephemeral(interaction, embed=success_embed("⚙️ Level config actualizada"))

    @app_commands.command(name="levelmessage", description="Ver mensaje de nivel actual")
    async def levelmessage(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        g = await self.bot.db.get_guild(interaction.guild.id)
        msg = g.get("level_message", "🎉 ¡{user} ha subido al nivel **{level}**!")
        embed = info_embed("📝 Mensaje de nivel", f"`{msg}`\nUsa `{{user}}`, `{{level}}`, `{{name}}`")
        await send_ephemeral(interaction, embed=embed)


async def setup(bot):
    await bot.add_cog(Levels(bot))
