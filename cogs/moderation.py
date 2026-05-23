import discord
from discord.ext import commands
from discord import app_commands
import time
import asyncio
import config
from utils.embeds import success_embed, error_embed, warning_embed, info_embed, mod_embed, PremiumEmbed, send_ephemeral
from utils.helpers import parse_duration, format_duration, send_log


class Moderation(commands.Cog):
    """🛡️ Moderación completa — ban, kick, mute, warn, purge, etc."""

    def __init__(self, bot):
        self.bot = bot

    async def _get_mute_role(self, guild):
        g = await self.bot.db.get_guild(guild.id)
        rid = g.get("mute_role")
        if rid:
            r = guild.get_role(rid)
            if r:
                return r
        r = discord.utils.get(guild.roles, name=config.MUTE_ROLE_NAME)
        if not r:
            r = await guild.create_role(
                name=config.MUTE_ROLE_NAME,
                color=discord.Color(0x2C2F33),
                permissions=discord.Permissions(send_messages=False, add_reactions=False, speak=False),
            )
            for ch in guild.channels:
                try:
                    await ch.set_permissions(r, send_messages=False, add_reactions=False, speak=False)
                except:
                    pass
        await self.bot.db.update_guild(guild.id, mute_role=r.id)
        return r

    # ── Ban ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="ban", description="Banear un usuario del servidor")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Usuario a banear", reason="Motivo", delete_days="Días de mensajes a eliminar", duration="Duración (opcional, ej: 1h 7d)")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: str = "No especificado", delete_days: int = 0, duration: str = None):
        await interaction.response.defer(ephemeral=True)
        try:
            if duration:
                secs = parse_duration(duration)
                until = discord.utils.utcnow() + discord.timedelta(seconds=secs)
                await interaction.guild.ban(user, reason=reason, delete_message_days=delete_days)
                await interaction.guild.unban(user, reason="Temp ban expirado")
                await interaction.guild.ban(user, reason=reason, delete_message_days=0)
            else:
                await interaction.guild.ban(user, reason=reason, delete_message_days=delete_days)
            case = await self.bot.db.add_case(interaction.guild.id, user.id, interaction.user.id, "ban", reason, duration or "")
            embed = mod_embed("🔨 Ban", user, interaction.user, reason, config.ERROR_COLOR)
            if duration:
                embed.add_field(name="Duración", value=format_duration(secs))
            embed.add_field(name="Case", value=f"#{case}f")
            await send_ephemeral(interaction, embed=embed)
            await send_log(self.bot, interaction.guild.id, "moderation", embed)
        except discord.Forbidden:
            await send_ephemeral(interaction, embed=error_embed("🚫 Error", "No puedo banear a ese usuario."))

    # ── Unban ────────────────────────────────────────────────────────────────
    @app_commands.command(name="unban", description="Desbanear un usuario")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user_id="ID del usuario", reason="Motivo")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No especificado"):
        await interaction.response.defer(ephemeral=True)
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
            embed = mod_embed("🔓 Unban", user, interaction.user, reason, config.SUCCESS_COLOR)
            await send_ephemeral(interaction, embed=embed)
            await send_log(self.bot, interaction.guild.id, "moderation", embed)
        except discord.NotFound:
            await send_ephemeral(interaction, embed=error_embed("❌ Error", "Usuario no encontrado en la lista de bans."))
        except Exception as e:
            await send_ephemeral(interaction, embed=error_embed("❌ Error", str(e)))

    # ── Softban ──────────────────────────────────────────────────────────────
    @app_commands.command(name="softban", description="Banear y desbanear para limpiar mensajes")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Usuario", reason="Motivo", delete_days="Días de mensajes")
    @app_commands.checks.has_permissions(ban_members=True)
    async def softban(self, interaction: discord.Interaction, user: discord.User, reason: str = "No especificado", delete_days: int = 1):
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.guild.ban(user, reason=reason, delete_message_days=delete_days)
            await interaction.guild.unban(user, reason="Softban completado")
            embed = mod_embed("👢 Softban", user, interaction.user, reason, config.WARNING_COLOR)
            await send_ephemeral(interaction, embed=embed)
            await send_log(self.bot, interaction.guild.id, "moderation", embed)
        except discord.Forbidden:
            await send_ephemeral(interaction, embed=error_embed("🚫 Error", "No puedo softbanear a ese usuario."))

    # ── Kick ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="kick", description="Expulsar un usuario")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(user="Usuario", reason="Motivo")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No especificado"):
        await interaction.response.defer(ephemeral=True)
        try:
            await user.kick(reason=reason)
            case = await self.bot.db.add_case(interaction.guild.id, user.id, interaction.user.id, "kick", reason)
            embed = mod_embed("👢 Kick", user, interaction.user, reason, config.WARNING_COLOR)
            embed.add_field(name="Case", value=f"#{case}f")
            await send_ephemeral(interaction, embed=embed)
            await send_log(self.bot, interaction.guild.id, "moderation", embed)
        except discord.Forbidden:
            await send_ephemeral(interaction, embed=error_embed("🚫 Error", "No puedo expulsar a ese usuario."))

    # ── Timeout ──────────────────────────────────────────────────────────────
    @app_commands.command(name="timeout", description="Timeout a un usuario")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario", duration="Duración (ej: 10m, 1h, 7d)", reason="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "No especificado"):
        await interaction.response.defer(ephemeral=True)
        secs = parse_duration(duration)
        if secs <= 0:
            return await send_ephemeral(interaction, embed=error_embed("❌ Error", "Duración inválida. Usa: 10m, 1h, 7d"))
        until = discord.utils.utcnow() + discord.timedelta(seconds=secs)
        try:
            await user.timeout(until, reason=reason)
            case = await self.bot.db.add_case(interaction.guild.id, user.id, interaction.user.id, "timeout", reason, duration)
            embed = mod_embed("⏰ Timeout", user, interaction.user, reason, config.WARNING_COLOR)
            embed.add_field(name="Duración", value=format_duration(secs))
            embed.add_field(name="Termina", value=f"<t:{int(time.time()+secs)}:R>f")
            embed.add_field(name="Case", value=f"#{case}f")
            await send_ephemeral(interaction, embed=embed)
            await send_log(self.bot, interaction.guild.id, "moderation", embed)
        except discord.Forbidden:
            await send_ephemeral(interaction, embed=error_embed("🚫 Error", "No puedo aplicar timeout."))

    # ── Untimeout ────────────────────────────────────────────────────────────
    @app_commands.command(name="untimeout", description="Quitar timeout a un usuario")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario", reason="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No especificado"):
        await interaction.response.defer(ephemeral=True)
        try:
            await user.timeout(None, reason=reason)
            embed = mod_embed("🔓 Untimeout", user, interaction.user, reason, config.SUCCESS_COLOR)
            await send_ephemeral(interaction, embed=embed)
            await send_log(self.bot, interaction.guild.id, "moderation", embed)
        except:
            await send_ephemeral(interaction, embed=error_embed("❌ Error", "No pude quitar el timeout."))

    # ── Mute ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="mute", description="Silenciar un usuario")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario", duration="Duración (ej: 10m, 1h, 7d)", reason="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, user: discord.Member, duration: str, reason: str = "No especificado"):
        await interaction.response.defer(ephemeral=True)
        secs = parse_duration(duration)
        if secs <= 0:
            return await send_ephemeral(interaction, embed=error_embed("❌ Error", "Duración inválida."))
        role = await self._get_mute_role(interaction.guild)
        if role in user.roles:
            return await send_ephemeral(interaction, embed=warning_embed("⚠️", "Ya está muteado."))
        try:
            await user.add_roles(role, reason=reason)
            end = time.time() + secs
            await self.bot.db.add_muted(user.id, interaction.guild.id, end)
            case = await self.bot.db.add_case(interaction.guild.id, user.id, interaction.user.id, "mute", reason, duration)
            embed = mod_embed("🔇 Mute", user, interaction.user, reason, config.WARNING_COLOR)
            embed.add_field(name="Duración", value=format_duration(secs))
            embed.add_field(name="Termina", value=f"<t:{int(end)}:R>f")
            embed.add_field(name="Case", value=f"#{case}f")
            await send_ephemeral(interaction, embed=embed)
            await send_log(self.bot, interaction.guild.id, "moderation", embed)
            asyncio.create_task(self._auto_unmute(user.id, interaction.guild.id, secs, role))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌ Error", "No pude mutear."))

    async def _auto_unmute(self, uid, gid, delay, role):
        await asyncio.sleep(delay)
        guild = self.bot.get_guild(gid)
        if not guild:
            return
        member = guild.get_member(uid)
        if member and role in member.roles:
            try:
                await member.remove_roles(role, reason="Auto-unmute")
                await self.bot.db.remove_muted(uid, gid)
            except:
                pass

    # ── Unmute ───────────────────────────────────────────────────────────────
    @app_commands.command(name="unmute", description="Desilenciar un usuario")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario", reason="Motivo")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No especificado"):
        await interaction.response.defer(ephemeral=True)
        role = await self._get_mute_role(interaction.guild)
        if role not in user.roles:
            return await send_ephemeral(interaction, embed=warning_embed("⚠️", "No está muteado."))
        try:
            await user.remove_roles(role, reason=reason)
            await self.bot.db.remove_muted(user.id, interaction.guild.id)
            embed = mod_embed("🔊 Unmute", user, interaction.user, reason, config.SUCCESS_COLOR)
            await send_ephemeral(interaction, embed=embed)
            await send_log(self.bot, interaction.guild.id, "moderation", embed)
        except:
            await send_ephemeral(interaction, embed=error_embed("❌ Error", "No pude unmutear."))

    # ── Warn ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="warn", description="Advertir a un usuario")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(user="Usuario", reason="Motivo")
    @app_commands.checks.has_permissions(kick_members=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No especificado"):
        await interaction.response.defer(ephemeral=True)
        warn_row = await self.bot.db.add_warning(user.id, interaction.guild.id, interaction.user.id, reason)
        mid = await self.bot.db.get_member(user.id, interaction.guild.id)
        wcount = mid.get("warns", 1)
        case = await self.bot.db.add_case(interaction.guild.id, user.id, interaction.user.id, "warn", reason)
        embed = mod_embed("⚠️ Warn", user, interaction.user, reason, config.WARNING_COLOR)
        embed.add_field(name="Total warns", value=str(wcount))
        embed.add_field(name="Case", value=f"#{case}f")
        await send_ephemeral(interaction, embed=embed)
        await send_log(self.bot, interaction.guild.id, "moderation", embed)

        if wcount >= config.MAX_WARNINGS:
            role = await self._get_mute_role(interaction.guild)
            try:
                await user.add_roles(role, reason="Mute automático por warns máximos")
                await self.bot.db.add_muted(user.id, interaction.guild.id, time.time() + 3600)
                await interaction.channel.send(embed=warning_embed(
                    "🔇 Mute Automático",
                    f"{user.mention} muteado por alcanzar {config.MAX_WARNINGS} warns."
                ))
            except:
                pass

    # ── Warnings ─────────────────────────────────────────────────────────────
    @app_commands.command(name="warnings", description="Ver warns de un usuario")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(kick_members=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        rows = await self.bot.db.get_warnings(user.id, interaction.guild.id)
        if not rows:
            return await send_ephemeral(interaction, embed=info_embed("📋 Warns", f"{user.mention} no tiene warns."))
        embed = PremiumEmbed(title=f"📋 Warns de {user.display_name}", color=config.WARNING_COLOR)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Total activos", value=str(len(rows)), inline=False)
        for r in rows[:10]:
            mod = interaction.guild.get_member(r["moderator_id"])
            mn = mod.mention if mod else f"`{r['moderator_id']}`"
            embed.add_field(
                name=f"#{r['id']} · <t:{int(r['timestamp'])}:R>f",
                value=f"**Mod:** {mn}\n**Razón:** {r['reason']}f",
                inline=False,
            )
        await send_ephemeral(interaction, embed=embed)

    # ── Clearwarnings / Delwarn ─────────────────────────────────────────────
    @app_commands.command(name="clearwarnings", description="Limpiar todos los warns de un usuario")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearwarnings(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.clear_warnings(user.id, interaction.guild.id)
        await send_ephemeral(interaction, embed=success_embed("🧹 Warns limpiados", f"Warns de {user.mention} eliminados."))

    @app_commands.command(name="delwarn", description="Eliminar un warn específico por ID")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(warn_id="ID del warn")
    @app_commands.checks.has_permissions(kick_members=True)
    async def delwarn(self, interaction: discord.Interaction, warn_id: int):
        await interaction.response.defer(ephemeral=True)
        ok = await self.bot.db.remove_warning(warn_id, interaction.guild.id)
        if ok:
            await send_ephemeral(interaction, embed=success_embed("✅ Warn eliminado", f"Warn #{warn_id} eliminado."))
        else:
            await send_ephemeral(interaction, embed=error_embed("❌ Error", "Warn no encontrado."))

    # ── Case(s) ─────────────────────────────────────────────────────────────
    @app_commands.command(name="case", description="Ver detalle de un case")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(case_number="Número de case")
    @app_commands.checks.has_permissions(kick_members=True)
    async def case(self, interaction: discord.Interaction, case_number: int):
        await interaction.response.defer(ephemeral=True)
        row = await self.bot.db.fetchone(
            "SELECT * FROM cases WHERE guild_id = ? AND case_number = ?",
            interaction.guild.id, case_number
        )
        if not row:
            return await send_ephemeral(interaction, embed=error_embed("❌ Error", "Case no encontrado."))
        user = interaction.guild.get_member(row["user_id"]) or await self.bot.fetch_user(row["user_id"])
        mod = interaction.guild.get_member(row["moderator_id"]) or f"`{row['moderator_id']}`"
        embed = PremiumEmbed(
            title=f"📋 Case #{row['case_number']}",
            description=f"**Acción:** {row['action_type']}\n**Usuario:** {user.mention if isinstance(user, discord.User) else user} (`{row['user_id']}`)\n**Mod:** {mod.mention if isinstance(mod, discord.Member) else mod}\n**Razón:** {row['reason']}\n**Duración:** {row['duration'] or 'N/A'}\n**Fecha:** <t:{int(row['timestamp'])}:F>f",
            color=config.EMBED_COLOR,
        )
        await send_ephemeral(interaction, embed=embed)

    @app_commands.command(name="modlogs", description="Ver todos los cases de un usuario")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(kick_members=True)
    async def modlogs(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        rows = await self.bot.db.fetchall(
            "SELECT * FROM cases WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC LIMIT 15",
            interaction.guild.id, user.id
        )
        if not rows:
            return await send_ephemeral(interaction, embed=info_embed("📋 Mod Logs", f"{user.mention} no tiene casos."))
        embed = PremiumEmbed(title=f"📋 Mod Logs · {user.display_name}", color=config.EMBED_COLOR)
        embed.set_thumbnail(url=user.display_avatar.url)
        for r in rows[:10]:
            embed.add_field(
                name=f"#{r['case_number']} · {r['action_type']} · <t:{int(r['timestamp'])}:R>f",
                value=f"**Razón:** {r['reason'][:100]}f",
                inline=False,
            )
        await send_ephemeral(interaction, embed=embed)

    # ── Purge ────────────────────────────────────────────────────────────────
    @app_commands.command(name="purge", description="Eliminar mensajes del canal")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(cantidad="Cantidad (1-1000)", usuario="Filtrar por usuario (opcional)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, cantidad: int, usuario: discord.User = None):
        await interaction.response.defer(ephemeral=True)
        if cantidad < 1 or cantidad > config.MAX_PURGE:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Cantidad entre 1 y 1000."))
        try:
            def check(m):
                return usuario is None or m.author.id == usuario.id
            deleted = await interaction.channel.purge(limit=cantidad, check=check)
            emb = success_embed("🗑️ Purga completada", f"{len(deleted)} mensajes eliminados.")
            if usuario:
                emb.description += f" (filtro: {usuario.mention})"
            await send_ephemeral(interaction, embed=emb)
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "Error al purgar."))

    # ── Slowmode ─────────────────────────────────────────────────────────────
    @app_commands.command(name="slowmode", description="Establecer slowmode")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(seconds="Segundos (0 para desactivar)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            txt = f"Slowmode: {seconds}s" if seconds else "Slowmode desactivado"
            await send_ephemeral(interaction, embed=success_embed("🐢 " + txt))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "No pude cambiar el slowmode."))

    # ── Lock / Unlock ────────────────────────────────────────────────────────
    @app_commands.command(name="lock", description="Bloquear canal")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(canal="Canal (opcional)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, canal: discord.TextChannel = None):
        canal = canal or interaction.channel
        await interaction.response.defer(ephemeral=True)
        try:
            await canal.set_permissions(interaction.guild.default_role, send_messages=False)
            await send_ephemeral(interaction, embed=success_embed("🔒 Canal bloqueado", canal.mention))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "No pude bloquear."))

    @app_commands.command(name="unlock", description="Desbloquear canal")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(canal="Canal (opcional)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, canal: discord.TextChannel = None):
        canal = canal or interaction.channel
        await interaction.response.defer(ephemeral=True)
        try:
            await canal.set_permissions(interaction.guild.default_role, send_messages=None)
            await send_ephemeral(interaction, embed=success_embed("🔓 Canal desbloqueado", canal.mention))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "No pude desbloquear."))

    @app_commands.command(name="lockdown", description="Bloquear TODO el servidor")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        count = 0
        for ch in interaction.guild.channels:
            try:
                await ch.set_permissions(interaction.guild.default_role, send_messages=False)
                count += 1
            except:
                pass
        await send_ephemeral(interaction, embed=success_embed("🔒 Lockdown", f"{count} canales bloqueados."))

    @app_commands.command(name="unlockdown", description="Desbloquear TODO el servidor")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def unlockdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        count = 0
        for ch in interaction.guild.channels:
            try:
                await ch.set_permissions(interaction.guild.default_role, send_messages=None)
                count += 1
            except:
                pass
        await send_ephemeral(interaction, embed=success_embed("🔓 Unlockdown", f"{count} canales desbloqueados."))

    # ── Nick ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="nick", description="Cambiar apodo a un usuario")
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.describe(user="Usuario", nickname="Nuevo apodo (dejar vacío para reset)")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def nick(self, interaction: discord.Interaction, user: discord.Member, nickname: str = None):
        await interaction.response.defer(ephemeral=True)
        try:
            await user.edit(nick=nickname, reason=f"Nick cambiado por {interaction.user}")
            txt = f"Apodo cambiado a **{nickname}**" if nickname else "Apodo reseteado"
            await send_ephemeral(interaction, embed=success_embed("✏️ " + txt, user.mention))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "No pude cambiar el apodo."))

    @app_commands.command(name="resetnick", description="Resetear apodo de un usuario")
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.describe(user="Usuario")
    async def resetnick(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        try:
            await user.edit(nick=None, reason=f"Nick reseteado por {interaction.user}")
            await send_ephemeral(interaction, embed=success_embed("🔄 Nick reseteado", user.mention))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "No pude resetear."))

    # ── Role management ──────────────────────────────────────────────────────
    @app_commands.command(name="roleadd", description="Añadir rol a un usuario")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(user="Usuario", role="Rol")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def roleadd(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        if role >= interaction.guild.me.top_role:
            return await send_ephemeral(interaction, embed=error_embed("❌", "El rol está por encima del mío."))
        try:
            await user.add_roles(role, reason=f"Rol añadido por {interaction.user}")
            await send_ephemeral(interaction, embed=success_embed("➕ Rol añadido", f"{role.mention} a {user.mention}"))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "No pude añadir el rol."))

    @app_commands.command(name="roleremove", description="Quitar rol a un usuario")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(user="Usuario", role="Rol")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def roleremove(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        if role >= interaction.guild.me.top_role:
            return await send_ephemeral(interaction, embed=error_embed("❌", "El rol está por encima del mío."))
        try:
            await user.remove_roles(role, reason=f"Rol quitado por {interaction.user}")
            await send_ephemeral(interaction, embed=success_embed("➖ Rol quitado", f"{role.mention} de {user.mention}"))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "No pude quitar el rol."))

    # ── Clean subcommands ────────────────────────────────────────────────────
    clean = app_commands.Group(name="clean", description="Limpiar mensajes por tipo")

    @clean.command(name="all", description="Limpiar mensajes")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean_all(self, interaction: discord.Interaction, cantidad: int = 20):
        await interaction.response.defer(ephemeral=True)
        d = await interaction.channel.purge(limit=cantidad)
        await send_ephemeral(interaction, embed=success_embed("🗑️", f"{len(d)} mensajes eliminados."))

    @clean.command(name="bots", description="Limpiar mensajes de bots")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean_bots(self, interaction: discord.Interaction, cantidad: int = 20):
        await interaction.response.defer(ephemeral=True)
        d = await interaction.channel.purge(limit=cantidad, check=lambda m: m.author.bot)
        await send_ephemeral(interaction, embed=success_embed("🗑️", f"{len(d)} mensajes de bots eliminados."))

    @clean.command(name="user", description="Limpiar mensajes de un usuario")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean_user(self, interaction: discord.Interaction, user: discord.User, cantidad: int = 20):
        await interaction.response.defer(ephemeral=True)
        d = await interaction.channel.purge(limit=cantidad, check=lambda m: m.author.id == user.id)
        await send_ephemeral(interaction, embed=success_embed("🗑️", f"{len(d)} mensajes de {user} eliminados."))

    @clean.command(name="links", description="Limpiar mensajes con enlaces")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean_links(self, interaction: discord.Interaction, cantidad: int = 20):
        await interaction.response.defer(ephemeral=True)
        d = await interaction.channel.purge(limit=cantidad, check=lambda m: "http" in m.content.lower())
        await send_ephemeral(interaction, embed=success_embed("🗑️", f"{len(d)} mensajes con links eliminados."))

    @clean.command(name="invites", description="Limpiar mensajes con invitaciones")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean_invites(self, interaction: discord.Interaction, cantidad: int = 20):
        await interaction.response.defer(ephemeral=True)
        d = await interaction.channel.purge(limit=cantidad, check=lambda m: "discord.gg/" in m.content.lower() or "discord.com/invite" in m.content.lower())
        await send_ephemeral(interaction, embed=success_embed("🗑️", f"{len(d)} invites eliminados."))

    @clean.command(name="embeds", description="Limpiar mensajes con embeds")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean_embeds(self, interaction: discord.Interaction, cantidad: int = 20):
        await interaction.response.defer(ephemeral=True)
        d = await interaction.channel.purge(limit=cantidad, check=lambda m: m.embeds)
        await send_ephemeral(interaction, embed=success_embed("🗑️", f"{len(d)} embeds eliminados."))

    @clean.command(name="files", description="Limpiar mensajes con archivos")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean_files(self, interaction: discord.Interaction, cantidad: int = 20):
        await interaction.response.defer(ephemeral=True)
        d = await interaction.channel.purge(limit=cantidad, check=lambda m: m.attachments)
        await send_ephemeral(interaction, embed=success_embed("🗑️", f"{len(d)} archivos eliminados."))

    @clean.command(name="mentions", description="Limpiar mensajes con menciones")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clean_mentions(self, interaction: discord.Interaction, cantidad: int = 20):
        await interaction.response.defer(ephemeral=True)
        d = await interaction.channel.purge(limit=cantidad, check=lambda m: m.mentions)
        await send_ephemeral(interaction, embed=success_embed("🗑️", f"{len(d)} menciones eliminadas."))

    # ── Purge All (cross-channel nuke) ────────────────────────────────────────
    @app_commands.command(name="purgeall", description="Eliminar TODOS los mensajes de un usuario/rol en todos los canales")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        usuario="Usuario objetivo (si usas este, no pongas rol)",
        rol="Rol objetivo (si usas este, no pongas usuario)",
        limite="Máx mensajes a revisar por canal (default 100)",
        dias="Solo mensajes de los últimos N días (default 7)",
    )
    async def purgeall(
        self, interaction: discord.Interaction,
        usuario: discord.Member = None,
        rol: discord.Role = None,
        limite: int = 100,
        dias: int = 7,
    ):
        await interaction.response.defer(ephemeral=True)

        if not usuario and not rol:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Debes especificar un **usuario** o un **rol**."))
        if usuario and rol:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Elige solo **uno**: usuario O rol, no ambos."))
        if limite < 1 or limite > 500:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Límite entre 1 y 500 mensajes por canal."))
        if dias < 1 or dias > 30:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Días entre 1 y 30."))

        target_name = usuario.mention if usuario else f"rol {rol.mention}"
        label = usuario.display_name if usuario else rol.name
        target_id = usuario.id if usuario else rol.id
        cutoff = time.time() - (dias * 86400)

        # Count available text channels
        channels = [
            ch for ch in interaction.guild.text_channels
            if ch.permissions_for(interaction.guild.me).read_message_history
            and ch.permissions_for(interaction.guild.me).manage_messages
        ]
        if not channels:
            return await send_ephemeral(interaction, embed=error_embed("❌", "No tengo permisos en ningún canal."))

        # ── Confirmation ──────────────────────────────────────────────────
        confirm_embed = PremiumEmbed(
            title="Purga Masiva — Confirmación",
            description=(
                f"**Objetivo:** {target_name}\n"
                f"**Canales:** `{len(channels)}` canales de texto\n"
                f"**Límite:** `{limite}` mensajes por canal\n"
                f"**Ventana:** últimos `{dias}` días\n\n"
                "Esta acción **NO se puede deshacer**. Los mensajes se eliminarán permanentemente."
            ),
            color=config.WARNING_COLOR,
        )

        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.confirmed = False

            @discord.ui.button(label="Ejecutar purga", style=discord.ButtonStyle.danger, emoji="🗑️")
            async def confirm(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                if btn_interaction.user.id != interaction.user.id:
                    return await btn_interaction.response.send_message("❌ No puedes confirmar esto.", ephemeral=True)
                self.confirmed = True
                for child in self.children:
                    child.disabled = True
                await btn_interaction.response.edit_message(view=self)
                self.stop()

            @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
            async def cancel(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                if btn_interaction.user.id != interaction.user.id:
                    return await btn_interaction.response.send_message("❌ No puedes cancelar.", ephemeral=True)
                self.confirmed = False
                for child in self.children:
                    child.disabled = True
                await btn_interaction.response.edit_message(view=self)
                self.stop()

        view = ConfirmView()
        await interaction.followup.send(embed=confirm_embed, view=view, ephemeral=True)
        await view.wait()

        if not view.confirmed:
            return await send_ephemeral(interaction, embed=info_embed("❌ Cancelado", "Purga cancelada."))

        # ── Execute purge ────────────────────────────────────────────────
        progress = PremiumEmbed(
            title="Purga masiva en progreso",
            description="Iniciando...",
            color=config.EMBED_COLOR,
        )
        progress_msg = await interaction.followup.send(embed=progress, ephemeral=True)

        total_deleted = 0
        total_errors = 0
        start_time = time.time()

        for idx, channel in enumerate(channels):
            try:
                deleted = 0
                check_fn = (lambda m: m.author.id == target_id) if usuario else (lambda m: rol in m.author.roles)

                async for msg in channel.history(limit=limite):
                    if msg.created_at.timestamp() < cutoff:
                        continue
                    if check_fn(msg):
                        try:
                            await msg.delete()
                            deleted += 1
                            await asyncio.sleep(0.35)
                        except discord.HTTPException:
                            total_errors += 1

                total_deleted += deleted

                if idx % 5 == 0 or idx == len(channels) - 1:
                    pct = (idx + 1) / len(channels) * 100
                    bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    progress.description = (
                        f"**Progreso:** `{idx+1}/{len(channels)}` canales\n"
                        f"`{bar}` `{pct:.0f}%`\n"
                        f"✅ Eliminados: `{total_deleted}`\n"
                        f"❌ Errores: `{total_errors}`\n"
                        f"📊 Canal: `#{channel.name}` ({deleted} msgs)"
                    )
                    await progress_msg.edit(embed=progress)

            except discord.Forbidden:
                total_errors += 1
            except Exception:
                total_errors += 1

            await asyncio.sleep(0.35)

        elapsed = time.time() - start_time
        summary = PremiumEmbed(
            title="Purga completada",
            description=(
                f"**Objetivo:** {target_name}\n"
                f"**Canales procesados:** `{len(channels)}`\n"
                f"**✅ Mensajes eliminados:** `{total_deleted}`\n"
                f"**❌ Errores:** `{total_errors}`\n"
                f"**⏱️ Tiempo:** `{elapsed:.1f}s`"
            ),
            color=config.SUCCESS_COLOR if total_deleted > 0 else config.EMBED_COLOR,
        )
        await send_ephemeral(interaction, embed=summary)

    # ── Voice Moderation ─────────────────────────────────────────────────────
    @app_commands.command(name="voicekick", description="Expulsar a un usuario de un canal de voz")
    @app_commands.default_permissions(move_members=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(move_members=True)
    async def voicekick(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if user.voice and user.voice.channel:
            try:
                await user.move_to(None, reason=f"Voice kick por {interaction.user}")
                await send_ephemeral(interaction, embed=success_embed("👢 Voice Kick", f"{user.mention} expulsado de voz."))
            except:
                await send_ephemeral(interaction, embed=error_embed("❌", "No pude expulsar."))
        else:
            await send_ephemeral(interaction, embed=warning_embed("⚠️", "No está en un canal de voz."))

    @app_commands.command(name="deafen", description="Ensordecer a un usuario en voz")
    @app_commands.default_permissions(mute_members=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(mute_members=True)
    async def deafen(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        try:
            await user.edit(deafen=True, reason=f"Deafen por {interaction.user}")
            await send_ephemeral(interaction, embed=success_embed("🔇 Deafen", f"{user.mention} ensordecido."))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "Error."))

    @app_commands.command(name="undeafen", description="Quitar ensordecimiento")
    @app_commands.default_permissions(mute_members=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(mute_members=True)
    async def undeafen(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        try:
            await user.edit(deafen=False, reason=f"Undeafen por {interaction.user}")
            await send_ephemeral(interaction, embed=success_embed("🔊 Undeafen", f"{user.mention} ya no está ensordecido."))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "Error."))

    @app_commands.command(name="move", description="Mover un usuario a otro canal de voz")
    @app_commands.default_permissions(move_members=True)
    @app_commands.describe(user="Usuario", canal="Canal destino")
    @app_commands.checks.has_permissions(move_members=True)
    async def move(self, interaction: discord.Interaction, user: discord.Member, canal: discord.VoiceChannel):
        await interaction.response.defer(ephemeral=True)
        try:
            await user.move_to(canal, reason=f"Movido por {interaction.user}")
            await send_ephemeral(interaction, embed=success_embed("🚚 Movido", f"{user.mention} → {canal.mention}"))
        except:
            await send_ephemeral(interaction, embed=error_embed("❌", "Error al mover."))

    # ── Reason ───────────────────────────────────────────────────────────────
    @app_commands.command(name="reason", description="Cambiar la razón de un case")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(case_number="Número de case", reason="Nueva razón")
    @app_commands.checks.has_permissions(kick_members=True)
    async def reason(self, interaction: discord.Interaction, case_number: int, reason: str):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.execute(
            "UPDATE cases SET reason = ? WHERE guild_id = ? AND case_number = ?",
            reason, interaction.guild.id, case_number,
        )
        await send_ephemeral(interaction, embed=success_embed("✏️ Razón actualizada", f"Case #{case_number}"))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
