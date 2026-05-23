import discord
from discord.ext import commands
from discord import app_commands
import time
import asyncio
import datetime
import config
from utils.embeds import success_embed, error_embed, info_embed, GuildEmbed
from utils.helpers import send_log, parse_duration


class Moderation(commands.Cog):
    """🛡️ Comandos de moderación — ban, kick, mute, purge, etc."""

    def __init__(self, bot):
        self.bot = bot

    def _check_hierarchy(self, mod, target):
        return mod.top_role > target.top_role or mod.id == mod.guild.owner_id

    async def _apply_mute(self, member, duration_seconds, reason, mod_id):
        until = int(time.time()) + duration_seconds
        muted_role = discord.utils.get(member.guild.roles, name="Silenciado")
        if not muted_role:
            muted_role = await member.guild.create_role(name="Silenciado", reason="Rol de mute automático")
            for ch in member.guild.channels:
                try:
                    await ch.set_permissions(muted_role, send_messages=False, add_reactions=False, speak=False)
                except:
                    pass
        await member.add_roles(muted_role, reason=reason)
        await self.bot.db.create_mute(member.id, member.guild.id, mod_id, reason, until)

    async def _harm(self, members: list, action: str, reason: str, duration=None):
        results = {"ok": [], "fail": []}
        for m in members:
            try:
                if action == "ban":
                    await m.ban(reason=reason)
                elif action == "kick":
                    await m.kick(reason=reason)
                elif action == "softban":
                    await m.ban(reason=reason)
                    await m.unban(reason="Softban completado")
                results["ok"].append(m)
            except:
                results["fail"].append(m)
        return results

    @app_commands.command(name="ban", description="Banear usuarios del servidor")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(users="Usuarios separados por espacio/coma", reason="Razón", delete_days="Días de mensajes a eliminar")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, users: str, reason: str = None, delete_days: int = 0):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if not reason:
            reason = self.bot.t(lang, "moderation.default_reason")
        members = []
        for u in users.replace(",", " ").split():
            try:
                uid = int(u.strip("<@!>"))
                m = interaction.guild.get_member(uid)
                if not m:
                    try:
                        m = await interaction.guild.fetch_member(uid)
                    except:
                        pass
                if m:
                    if m == interaction.user:
                        continue
                    if m.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
                        continue
                    members.append(m)
            except:
                pass
        if not members:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.no_valid_members")))
        results = await self._harm(members, "ban", reason)
        ok_names = ", ".join(f"**{m}**" for m in results["ok"])
        fail_names = ", ".join(f"**{m}**" for m in results["fail"])
        embed = GuildEmbed(title=self.bot.t(lang, "moderation.banned_title"), color=config.COLORS["dark_red"])
        if ok_names:
            embed.add_field(name=self.bot.t(lang, "moderation.banned"), value=ok_names, inline=False)
        if fail_names:
            embed.add_field(name=self.bot.t(lang, "moderation.failed"), value=fail_names, inline=False)
        embed.add_field(name=self.bot.t(lang, "moderation.reason"), value=reason, inline=False)
        await interaction.followup.send(embed=embed)
        for m in results["ok"]:
            try:
                e = GuildEmbed(title=self.bot.t(lang, "moderation.banned_notification"), description=self.bot.t(lang, "moderation.ban_notify", guild=interaction.guild.name, reason=reason), color=config.COLORS["dark_red"])
                await m.send(embed=e)
            except:
                pass

    @app_commands.command(name="kick", description="Expulsar usuarios")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(users="Usuarios separados por espacio/coma", reason="Razón")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, users: str, reason: str = None):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if not reason:
            reason = self.bot.t(lang, "moderation.default_reason")
        members = []
        for u in users.replace(",", " ").split():
            try:
                uid = int(u.strip("<@!>"))
                m = interaction.guild.get_member(uid)
                if m and m != interaction.user and (m.top_role < interaction.user.top_role or interaction.user.id == interaction.guild.owner_id):
                    members.append(m)
            except:
                pass
        if not members:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.no_valid_members")))
        results = await self._harm(members, "kick", reason)
        ok_names = ", ".join(f"**{m}**" for m in results["ok"])
        fail_names = ", ".join(f"**{m}**" for m in results["fail"])
        embed = GuildEmbed(title=self.bot.t(lang, "moderation.kicked_title"), color=config.COLORS["orange"])
        if ok_names:
            embed.add_field(name=self.bot.t(lang, "moderation.kicked"), value=ok_names, inline=False)
        if fail_names:
            embed.add_field(name=self.bot.t(lang, "moderation.failed"), value=fail_names, inline=False)
        embed.add_field(name=self.bot.t(lang, "moderation.reason"), value=reason, inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="mute", description="Silenciar usuario temporalmente")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario", duration="Duración (ej: 10m, 1h, 2d)", reason="Razón")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def mute(self, interaction: discord.Interaction, user: discord.Member, duration: str = "10m", reason: str = None):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if not reason:
            reason = self.bot.t(lang, "moderation.default_reason")
        if user == interaction.user:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.self_mute")))
        if user.top_role >= interaction.user.top_role:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.hierarchy_error")))
        secs = parse_duration(duration)
        if secs is None or secs <= 0:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.invalid_duration")))
        try:
            until = discord.utils.utcnow() + datetime.timedelta(seconds=secs)
            await user.timeout(until, reason=reason)
            embed = success_embed(self.bot.t(lang, "moderation.muted_title"), self.bot.t(lang, "moderation.muted_desc", user=user.mention, duration=parse_duration(secs, readable=True) if not isinstance(secs, int) else duration, reason=reason))
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="unmute", description="Quitar silencio")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            await user.timeout(None, reason="Unmute manual")
            embed = success_embed(self.bot.t(lang, "moderation.unmuted_title"), self.bot.t(lang, "moderation.unmuted_desc", user=user.mention))
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="warn", description="Advertir a un usuario")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario", reason="Razón")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if not reason:
            reason = self.bot.t(lang, "moderation.default_reason")
        if user == interaction.user:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.self_warn")))
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.hierarchy_error")))
        case_id = await self.bot.db.create_case(interaction.guild.id, user.id, interaction.user.id, "warn", reason)
        embed = success_embed(self.bot.t(lang, "moderation.warned_title"), self.bot.t(lang, "moderation.warned_desc", user=user.mention, reason=reason, case=case_id))
        await interaction.followup.send(embed=embed)
        try:
            e = GuildEmbed(title=self.bot.t(lang, "moderation.warned_notification"), description=self.bot.t(lang, "moderation.warn_notify", guild=interaction.guild.name, reason=reason, moderator=interaction.user), color=config.COLORS["yellow"])
            await user.send(embed=e)
        except:
            pass

    @app_commands.command(name="warnings", description="Ver advertencias de un usuario")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        rows = await self.bot.db.get_user_warnings(user.id, interaction.guild.id)
        if not rows:
            return await interaction.followup.send(embed=info_embed(self.bot.t(lang, "moderation.warnings_title"), self.bot.t(lang, "moderation.no_warnings", user=user.mention)))
        embed = GuildEmbed(title=self.bot.t(lang, "moderation.warnings_user", user=user.display_name), color=config.COLORS["yellow"])
        for r in rows:
            mod = interaction.guild.get_member(r["moderator_id"])
            embed.add_field(
                name=f"#{r['id']}",
                value=self.bot.t(lang, "moderation.warning_entry", reason=r['reason'], moderator=mod.mention if mod else f"`{r['moderator_id']}`", date=f"<t:{int(r['created_at'])}:d>"),
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="clearwarn", description="Eliminar advertencia específica")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(case_id="ID del caso")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def clearwarn(self, interaction: discord.Interaction, case_id: int):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            await self.bot.db.update_case(case_id, interaction.guild.id, status="cleared")
            embed = success_embed(self.bot.t(lang, "moderation.warning_cleared"), self.bot.t(lang, "moderation.warning_cleared_desc", case=case_id))
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="purge", description="Eliminar mensajes de un canal")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(cantidad="Número (1-500)", usuario="Filtrar por usuario (opcional)")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, cantidad: int, usuario: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if cantidad < 1 or cantidad > 500:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.invalid_purge")))
        try:
            def check(m):
                return m.author == usuario if usuario else True
            deleted = await interaction.channel.purge(limit=min(cantidad, 500), check=check, bulk=True)
            embed = success_embed(self.bot.t(lang, "moderation.purged_title"), self.bot.t(lang, "moderation.purged_desc", count=len(deleted)))
            await interaction.followup.send(embed=embed, delete_after=5)
        except Exception as e:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="purgeall", description="Eliminar mensajes de un usuario en todo el servidor")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(user="Usuario", limit="Máximo de mensajes")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def purgeall(self, interaction: discord.Interaction, user: discord.Member, limit: int = 100):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        total = 0
        for ch in interaction.guild.text_channels:
            try:
                def check(m):
                    return m.author == user
                deleted = await ch.purge(limit=min(limit, 100), check=check, bulk=True)
                total += len(deleted)
            except:
                pass
        embed = success_embed(self.bot.t(lang, "moderation.purgeall_title"), self.bot.t(lang, "moderation.purgeall_desc", user=user.mention, count=total))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="slowmode", description="Establecer slowmode en el canal")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(seconds="Segundos (0 para desactivar)")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if seconds < 0 or seconds > 21600:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.invalid_slowmode")))
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            embed = success_embed(self.bot.t(lang, "moderation.slowmode_title"), self.bot.t(lang, "moderation.slowmode_set", seconds=seconds) if seconds else self.bot.t(lang, "moderation.slowmode_disabled"))
            await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="lock", description="Cerrar canal para menciones @everyone")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(reason="Razón")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, reason: str = "Sin razón especificada"):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
            embed = success_embed(self.bot.t(lang, "moderation.locked_title"), self.bot.t(lang, "moderation.locked_desc", channel=interaction.channel.mention))
            await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="unlock", description="Abrir canal")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(reason="Razón")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, reason: str = "Sin razón especificada"):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
            embed = success_embed(self.bot.t(lang, "moderation.unlocked_title"), self.bot.t(lang, "moderation.unlocked_desc", channel=interaction.channel.mention))
            await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="nick", description="Cambiar apodo de un usuario")
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.describe(user="Usuario", nick="Nuevo apodo (dejar vacío para resetear)")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    @app_commands.checks.bot_has_permissions(manage_nicknames=True)
    async def nick(self, interaction: discord.Interaction, user: discord.Member, nick: str = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if user.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.hierarchy_error")))
        try:
            await user.edit(nick=nick, reason=f"Por {interaction.user}")
            embed = success_embed(self.bot.t(lang, "moderation.nick_changed"), self.bot.t(lang, "moderation.nick_changed_desc", user=user.mention, nick=nick or user.name))
            await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="role", description="Añadir/quitar rol a usuarios")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(role="Rol", action="add/remove/toggle", users="Usuarios separados por espacio")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    async def role(self, interaction: discord.Interaction, role: discord.Role, action: str, users: str):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.role_hierarchy")))
        if role >= interaction.guild.me.top_role:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.role_bot_hierarchy")))
        members = []
        for u in users.replace(",", " ").split():
            try:
                uid = int(u.strip("<@!>"))
                m = interaction.guild.get_member(uid)
                if m:
                    members.append(m)
            except:
                pass
        if not members:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.no_valid_members")))
        action_lower = action.lower()
        if action_lower == "add":
            for m in members:
                await m.add_roles(role, reason=f"Por {interaction.user}")
            embed = success_embed(self.bot.t(lang, "moderation.role_added"), self.bot.t(lang, "moderation.role_added_desc", role=role.mention, count=len(members)))
        elif action_lower == "remove":
            for m in members:
                await m.remove_roles(role, reason=f"Por {interaction.user}")
            embed = success_embed(self.bot.t(lang, "moderation.role_removed"), self.bot.t(lang, "moderation.role_removed_desc", role=role.mention, count=len(members)))
        else:
            for m in members:
                if role in m.roles:
                    await m.remove_roles(role, reason=f"Por {interaction.user}")
                else:
                    await m.add_roles(role, reason=f"Por {interaction.user}")
            embed = success_embed(self.bot.t(lang, "moderation.role_toggled"), self.bot.t(lang, "moderation.role_toggled_desc", role=role.mention, count=len(members)))
        await interaction.followup.send(embed=embed)

    @role.autocomplete("action")
    async def role_ac(self, interaction: discord.Interaction, current: str):
        opts = ["add", "remove", "toggle"]
        return [app_commands.Choice(name=o, value=o) for o in opts if current.lower() in o.lower()]

    @app_commands.command(name="voice", description="Gestionar canales de voz (mover, desconectar)")
    @app_commands.default_permissions(move_members=True)
    @app_commands.describe(action="mute, unmute, deafen, undeafen, move, disconnect", user="Usuario", target="Canal de destino (solo move)")
    @app_commands.checks.has_permissions(move_members=True)
    @app_commands.checks.bot_has_permissions(move_members=True)
    async def voice(self, interaction: discord.Interaction, action: str, user: discord.Member, target: discord.VoiceChannel = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if not user.voice or not user.voice.channel:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.not_in_voice")))
        try:
            a = action.lower()
            if a == "mute":
                await user.edit(mute=True)
            elif a == "unmute":
                await user.edit(mute=False)
            elif a == "deafen":
                await user.edit(deafen=True)
            elif a == "undeafen":
                await user.edit(deafen=False)
            elif a == "move":
                if not target:
                    return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.specify_target")))
                await user.move_to(target)
            elif a == "disconnect":
                await user.move_to(None)
            else:
                return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.invalid_voice_action")))
            embed = success_embed(self.bot.t(lang, "moderation.voice_title"), self.bot.t(lang, "moderation.voice_done", user=user.mention, action=a))
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @voice.autocomplete("action")
    async def voice_ac(self, interaction: discord.Interaction, current: str):
        opts = ["mute", "unmute", "deafen", "undeafen", "move", "disconnect"]
        return [app_commands.Choice(name=o, value=o) for o in opts if current.lower() in o.lower()]

    @app_commands.command(name="clean", description="Limpiar mensajes del bot en este canal")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(cantidad="Cuántos mensajes revisar")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True)
    async def clean(self, interaction: discord.Interaction, cantidad: int = 50):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            def check(m):
                return m.author == interaction.guild.me or m.author.bot
            deleted = await interaction.channel.purge(limit=min(cantidad, 500), check=check, bulk=True)
            embed = success_embed(self.bot.t(lang, "moderation.purged_title"), self.bot.t(lang, "moderation.cleaned_desc", count=len(deleted)))
            await interaction.followup.send(embed=embed, delete_after=5)
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="case", description="Ver detalles de un caso")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(case_id="ID del caso")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def case(self, interaction: discord.Interaction, case_id: int):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        case = await self.bot.db.get_case(case_id, interaction.guild.id)
        if not case:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.case_not_found")))
        user = interaction.guild.get_member(case["user_id"]) or (await self.bot.fetch_user(case["user_id"]))
        mod = interaction.guild.get_member(case["moderator_id"]) or (await self.bot.fetch_user(case["moderator_id"]))
        embed = GuildEmbed(title=self.bot.t(lang, "moderation.case_title", case=case_id), color=config.EMBED_COLOR)
        embed.add_field(name=self.bot.t(lang, "moderation.user_field"), value=user.mention if hasattr(user, 'mention') else f"`{case['user_id']}`", inline=True)
        embed.add_field(name=self.bot.t(lang, "moderation.type"), value=case["type"].capitalize(), inline=True)
        embed.add_field(name=self.bot.t(lang, "moderation.reason"), value=case["reason"], inline=False)
        embed.add_field(name=self.bot.t(lang, "moderation.moderator_field"), value=mod.mention if hasattr(mod, 'mention') else f"`{case['moderator_id']}`", inline=True)
        embed.add_field(name=self.bot.t(lang, "moderation.date"), value=f"<t:{int(case['created_at'])}:f>", inline=True)
        embed.add_field(name=self.bot.t(lang, "moderation.status"), value=case.get("status", "active").capitalize(), inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="massban", description="Banear múltiples IDs de usuario")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(ids="IDs separados por espacio/coma", reason="Razón")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def massban(self, interaction: discord.Interaction, ids: str, reason: str = None):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if not reason:
            reason = self.bot.t(lang, "moderation.default_reason")
        split_ids = []
        for p in ids.replace(",", " ").split():
            try:
                split_ids.append(int(p.strip()))
            except:
                pass
        if not split_ids:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "moderation.no_valid_ids")))
        ok, fail = 0, 0
        for uid in split_ids:
            try:
                await interaction.guild.ban(discord.Object(id=uid), reason=reason)
                ok += 1
            except:
                fail += 1
        embed = success_embed(self.bot.t(lang, "moderation.massban_title"), self.bot.t(lang, "moderation.massban_desc", ok=ok, fail=fail))
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
