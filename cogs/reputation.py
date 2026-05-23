import discord
from discord.ext import commands
from discord import app_commands
import time
import config
from utils.embeds import PremiumEmbed, success_embed, error_embed, warning_embed, info_embed, send_ephemeral
from utils.helpers import send_log


class Reputation(commands.Cog):
    """Sistema de reputacion avanzado con proteccion anti-spam, historial, niveles y configuracion completa."""

    def __init__(self, bot):
        self.bot = bot
        self._cooldown_cache = {}

    rep = app_commands.Group(name="rep", description="Gestionar reputacion")

    # ─── Ayudas para verificacion ───────────────────────────────────────

    async def _check_channel(self, interaction: discord.Interaction, guild_data: dict) -> bool:
        ch = guild_data.get("rep_channel", 0)
        if ch and interaction.channel_id != ch:
            channel = interaction.guild.get_channel(ch)
            name = channel.mention if channel else f"<#{ch}>"
            await interaction.followup.send(
                embed=warning_embed("Canal restringido", f"La reputacion solo puede usarse en {name}"),
                ephemeral=True
            )
            return False
        return True

    async def _check_staff(self, interaction: discord.Interaction, guild_data: dict) -> bool:
        if not guild_data.get("rep_staff_only", 0):
            return True
        staff_roles = guild_data.get("staff_roles", [])
        if isinstance(staff_roles, str):
            import json
            staff_roles = json.loads(staff_roles) if staff_roles else []
        user_roles = [r.id for r in interaction.user.roles]
        if any(s in user_roles for s in staff_roles):
            return True
        if interaction.user.guild_permissions.kick_members:
            return True
        await interaction.followup.send(
            embed=warning_embed("Acceso restringido", "Solo el staff puede dar reputacion en este servidor."),
            ephemeral=True
        )
        return False

    async def _log_rep_action(self, guild_id: int, action: str, data: dict):
        g = await self.bot.db.get_guild(guild_id)
        log_ch = g.get("rep_log_channel", 0)
        if not log_ch:
            return
        channel = self.bot.get_channel(log_ch)
        if not channel:
            return
        e = PremiumEmbed(title=f"Reputacion - {action}", color=config.COLORS["blue"])
        for k, v in data.items():
            e.add_field(name=k, value=str(v), inline=True)
        e.timestamp = discord.utils.utcnow()
        try:
            await channel.send(embed=e)
        except:
            pass

    # ─── Comando: give ──────────────────────────────────────────────────

    @rep.command(name="give", description="Dar reputacion a un usuario")
    @app_commands.describe(usuario="Usuario a recomendar", razon="Motivo (opcional)")
    async def rep_give(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = None):
        await interaction.response.defer(ephemeral=True)

        if usuario.id == interaction.user.id:
            return await interaction.followup.send(embed=error_embed("Operacion invalida", "No puedes darte reputacion a ti mismo."))
        if usuario.bot:
            return await interaction.followup.send(embed=error_embed("Operacion invalida", "No puedes dar reputacion a bots."))

        g = await self.bot.db.get_guild(interaction.guild.id)
        if not g.get("rep_enabled", 1):
            return await interaction.followup.send(embed=warning_embed("Sistema desactivado", "La reputacion esta deshabilitada en este servidor."))

        if not await self._check_channel(interaction, g):
            return
        if not await self._check_staff(interaction, g):
            return

        md = await self.bot.db.get_member(interaction.user.id, interaction.guild.id)
        now = time.time()
        cd = g.get("rep_cooldown", config.REP_COOLDOWN)

        if now - md.get("last_rep_time", 0) < cd:
            rem = cd - (now - md.get("last_rep_time", 0))
            hrs = int(rem // 3600)
            mins = int((rem % 3600) // 60)
            return await interaction.followup.send(
                embed=warning_embed("Cooldown activo", f"Espera **{hrs}h {mins}m** antes de volver a recomendar."),
                ephemeral=True
            )

        min_level = g.get("rep_min_level", config.REP_MIN_LEVEL)
        if min_level > 0 and md.get("level", 0) < min_level:
            return await interaction.followup.send(
                embed=warning_embed("Nivel insuficiente", f"Necesitas nivel **{min_level}** para dar reputacion. Tu nivel: **{md.get('level', 0)}**"),
                ephemeral=True
            )

        td = await self.bot.db.get_member(usuario.id, interaction.guild.id)
        max_rep = g.get("rep_max_per_user", config.REP_MAX_PER_USER)
        current_rep = td.get("reputation", 0)
        if current_rep >= max_rep:
            return await interaction.followup.send(
                embed=warning_embed("Limite alcanzado", f"{usuario.mention} ya tiene el maximo de reputacion permitido (**{max_rep}**)."),
                ephemeral=True
            )

        new_rep = current_rep + 1
        await self.bot.db.update_member(usuario.id, interaction.guild.id, reputation=new_rep)
        await self.bot.db.update_member(interaction.user.id, interaction.guild.id, last_rep_time=now, rep_given=md.get("rep_given", 0) + 1)
        await self.bot.db.add_rep_history(interaction.guild.id, interaction.user.id, usuario.id, razon or "")

        embed = PremiumEmbed(
            title="Reputacion asignada",
            description=f"{usuario.mention} ha recibido **+1** punto de reputacion.",
            color=config.COLORS["blue"]
        )
        if razon:
            embed.add_field(name="Motivo", value=razon, inline=False)
        embed.add_field(name="Total actual", value=f"**{new_rep}** puntos", inline=True)
        embed.add_field(name="Recomendaciones dadas", value=f"**{md.get('rep_given', 0) + 1}**", inline=True)
        await interaction.followup.send(embed=embed)

        await self._log_rep_action(interaction.guild.id, "Recomendacion", {
            "De": f"{interaction.user} (`{interaction.user.id}`)",
            "Para": f"{usuario} (`{usuario.id}`)",
            "Total": str(new_rep),
            "Razon": razon or "Sin motivo",
        })

        rep_role = await self.bot.db.check_rep_roles(interaction.guild.id, new_rep)
        if rep_role:
            role = interaction.guild.get_role(rep_role["role_id"])
            if role and role not in usuario.roles:
                try:
                    await usuario.add_roles(role, reason="Recompensa por reputacion")
                except:
                    pass

    # ─── Comando: remove ────────────────────────────────────────────────

    @rep.command(name="remove", description="Quitar reputacion a un usuario (staff)")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(usuario="Usuario", cantidad="Cantidad a quitar")
    @app_commands.checks.has_permissions(kick_members=True)
    async def rep_remove(self, interaction: discord.Interaction, usuario: discord.Member, cantidad: int = 1):
        await interaction.response.defer(ephemeral=True)
        td = await self.bot.db.get_member(usuario.id, interaction.guild.id)
        new = max(0, td.get("reputation", 0) - cantidad)
        await self.bot.db.update_member(usuario.id, interaction.guild.id, reputation=new)
        await interaction.followup.send(embed=success_embed("Reputacion removida", f"{usuario.mention}: **-{cantidad}** puntos (ahora: **{new}**)"))
        await self._log_rep_action(interaction.guild.id, "Remocion", {
            "Staff": f"{interaction.user} (`{interaction.user.id}`)",
            "Usuario": f"{usuario} (`{usuario.id}`)",
            "Quitado": str(cantidad),
            "Nuevo total": str(new),
        })

    # ─── Comando: set ───────────────────────────────────────────────────

    @rep.command(name="set", description="Establecer reputacion de un usuario (admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(usuario="Usuario", cantidad="Nuevo valor")
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_set(self, interaction: discord.Interaction, usuario: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        val = max(0, cantidad)
        await self.bot.db.update_member(usuario.id, interaction.guild.id, reputation=val)
        await interaction.followup.send(embed=success_embed("Reputacion establecida", f"{usuario.mention}: **{val}** puntos"))
        await self._log_rep_action(interaction.guild.id, "Asignacion manual", {
            "Staff": f"{interaction.user} (`{interaction.user.id}`)",
            "Usuario": f"{usuario} (`{usuario.id}`)",
            "Valor asignado": str(val),
        })

    # ─── Comando: profile ───────────────────────────────────────────────

    @rep.command(name="profile", description="Ver perfil de reputacion de un usuario")
    @app_commands.describe(usuario="Usuario (opcional, por defecto tu perfil)")
    async def rep_profile(self, interaction: discord.Interaction, usuario: discord.Member = None):
        usuario = usuario or interaction.user
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(usuario.id, interaction.guild.id)
        rank, _ = await self.bot.db.get_rank(usuario.id, interaction.guild.id, "reputation")

        history = await self.bot.db.get_rep_history(interaction.guild.id, usuario.id, 5)
        received = sum(1 for h in history if h["to_user_id"] == usuario.id) if history else 0
        given = sum(1 for h in history if h["from_user_id"] == usuario.id) if history else 0

        rep = md.get("reputation", 0)
        level = md.get("level", 0)

        next_rep_role = await self.bot.db.check_rep_roles(interaction.guild.id, rep + 1)

        embed = PremiumEmbed(
            title=f"Perfil de reputacion - {usuario.display_name}",
            color=config.COLORS["blue"]
        )
        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.add_field(name="Puntos", value=f"**{rep}**", inline=True)
        embed.add_field(name="Ranking", value=f"**#{rank}**" if rank else "**N/A**", inline=True)
        embed.add_field(name="Nivel", value=f"**{level}**", inline=True)
        embed.add_field(name="Recibidos (recientes)", value=f"**{received}**", inline=True)
        embed.add_field(name="Dados (recientes)", value=f"**{given}**", inline=True)
        embed.add_field(name="Recomendaciones totales", value=f"**{md.get('rep_given', 0)}**", inline=True)

        if next_rep_role:
            role = interaction.guild.get_role(next_rep_role["role_id"])
            if role:
                remaining = next_rep_role["rep"] - rep
                embed.add_field(name="Siguiente recompensa", value=f"{role.mention} en **{remaining}** puntos", inline=False)

        if history:
            lines = []
            for h in list(history)[:3]:
                who = interaction.guild.get_member(h["from_user_id"] if h["to_user_id"] == usuario.id else h["to_user_id"])
                wname = who.mention if who else f"`{h['from_user_id']}`"
                ts = f"<t:{int(h['timestamp'])}:R>"
                action = "de" if h["to_user_id"] == usuario.id else "para"
                lines.append(f"{action} {wname} - {ts}")
            if lines:
                embed.add_field(name="Actividad reciente", value="\n".join(lines), inline=False)

        await interaction.followup.send(embed=embed)

    # ─── Comando: leaderboard ───────────────────────────────────────────

    @rep.command(name="leaderboard", description="Ranking global de reputacion del servidor")
    async def rep_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows = await self.bot.db.get_leaderboard(interaction.guild.id, "reputation", 20)
        if not rows:
            return await interaction.followup.send(embed=info_embed("Ranking de reputacion", "Aun no hay datos en este servidor."))

        embed = PremiumEmbed(
            title=f"Ranking de reputacion - {interaction.guild.name}",
            color=config.COLORS["blue"]
        )
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        desc_lines = []
        for i, r in enumerate(rows):
            m = interaction.guild.get_member(r["user_id"])
            if not m:
                continue
            val = r["reputation"]
            pos = f"#{i+1}" if i >= 3 else ["\U0001f947", "\U0001f948", "\U0001f949"][i]
            bar = "\u2588" * min(int(val / 3), 15) + "\u2591" * max(15 - min(int(val / 3), 15), 0)
            desc_lines.append(f"**{pos}** {m.display_name}  `{val}`\n`{bar}`")

        embed.description = "\n".join(desc_lines[:15])
        await interaction.followup.send(embed=embed)

    # ─── Comando: history ───────────────────────────────────────────────

    @rep.command(name="history", description="Ver historial completo de reputacion (staff)")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(usuario="Usuario para ver historial")
    @app_commands.checks.has_permissions(kick_members=True)
    async def rep_history(self, interaction: discord.Interaction, usuario: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        user_id = usuario.id if usuario else None
        rows = await self.bot.db.get_rep_history(interaction.guild.id, user_id, 25)
        if not rows:
            return await interaction.followup.send(embed=info_embed("Historial", "No hay registros de reputacion."))

        embed = PremiumEmbed(
            title=f"Historial de reputacion" + (f" - {usuario.display_name}" if usuario else ""),
            color=config.COLORS["blue"]
        )
        lines = []
        for r in rows[:20]:
            from_u = interaction.guild.get_member(r["from_user_id"])
            to_u = interaction.guild.get_member(r["to_user_id"])
            fname = from_u.display_name if from_u else f"`{r['from_user_id']}`"
            tname = to_u.display_name if to_u else f"`{r['to_user_id']}`"
            ts = f"<t:{int(r['timestamp'])}:R>"
            reason = f" - {r['reason']}" if r.get("reason") else ""
            lines.append(f"`+1` {fname} \u2192 {tname} {ts}{reason}")

        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Mostrando {min(len(rows), 20)} de {len(rows)} registros")
        await interaction.followup.send(embed=embed)

    # ─── Comando: reset ─────────────────────────────────────────────────

    @rep.command(name="reset", description="Resetear reputacion de un usuario (admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(usuario="Usuario")
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_reset(self, interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.update_member(usuario.id, interaction.guild.id, reputation=0)
        await interaction.followup.send(embed=success_embed("Reputacion reseteada", f"{usuario.mention} ahora tiene **0** puntos."))
        await self._log_rep_action(interaction.guild.id, "Reseteo", {
            "Staff": f"{interaction.user} (`{interaction.user.id}`)",
            "Usuario": f"{usuario} (`{usuario.id}`)",
        })

    # ─── Comando: config ────────────────────────────────────────────────

    rep_config = app_commands.Group(name="config", description="Configurar sistema de reputacion", parent=rep)

    @rep_config.command(name="view", description="Ver configuracion actual de reputacion")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config_view(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        g = await self.bot.db.get_guild(interaction.guild.id)
        embed = PremiumEmbed(
            title="Configuracion de reputacion",
            color=config.COLORS["blue"]
        )
        embed.add_field(name="Sistema activo", value="**Si**" if g.get("rep_enabled", 1) else "**No**", inline=True)
        embed.add_field(name="Staff solo", value="**Si**" if g.get("rep_staff_only", 0) else "**No**", inline=True)
        embed.add_field(name="Cooldown", value=f"**{g.get('rep_cooldown', config.REP_COOLDOWN) // 3600}h**", inline=True)
        embed.add_field(name="Maximo por usuario", value=f"**{g.get('rep_max_per_user', config.REP_MAX_PER_USER)}**", inline=True)
        embed.add_field(name="Nivel minimo", value=f"**{g.get('rep_min_level', config.REP_MIN_LEVEL)}**", inline=True)

        ch = g.get("rep_channel", 0)
        channel = interaction.guild.get_channel(ch) if ch else None
        embed.add_field(name="Canal especifico", value=channel.mention if channel else "**Cualquier canal**", inline=True)

        log_ch = g.get("rep_log_channel", 0)
        lch = interaction.guild.get_channel(log_ch) if log_ch else None
        embed.add_field(name="Canal de logs", value=lch.mention if lch else "**No configurado**", inline=True)

        await interaction.followup.send(embed=embed)

    @rep_config.command(name="channel", description="Establecer canal especifico para reputacion")
    @app_commands.describe(canal="Canal (dejar vacio para quitar restriccion)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config_channel(self, interaction: discord.Interaction, canal: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        ch_id = canal.id if canal else 0
        await self.bot.db.update_guild(interaction.guild.id, rep_channel=ch_id)
        await interaction.followup.send(
            embed=success_embed("Canal actualizado", f"Reputacion restringida a: {canal.mention}" if canal else "Reputacion permitida en cualquier canal.")
        )

    @rep_config.command(name="cooldown", description="Establecer cooldown entre recomendaciones")
    @app_commands.describe(horas="Horas de cooldown")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config_cooldown(self, interaction: discord.Interaction, horas: int):
        await interaction.response.defer(ephemeral=True)
        cd = max(1, horas) * 3600
        await self.bot.db.update_guild(interaction.guild.id, rep_cooldown=cd)
        await interaction.followup.send(embed=success_embed("Cooldown actualizado", f"**{horas}h** entre recomendaciones."))

    @rep_config.command(name="max", description="Establecer maximo de reputacion por usuario")
    @app_commands.describe(cantidad="Maximo de puntos")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config_max(self, interaction: discord.Interaction, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        val = max(1, cantidad)
        await self.bot.db.update_guild(interaction.guild.id, rep_max_per_user=val)
        await interaction.followup.send(embed=success_embed("Limite actualizado", f"Maximo **{val}** puntos de reputacion por usuario."))

    @rep_config.command(name="minlevel", description="Nivel minimo para poder dar reputacion")
    @app_commands.describe(nivel="Nivel requerido")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config_minlevel(self, interaction: discord.Interaction, nivel: int):
        await interaction.response.defer(ephemeral=True)
        val = max(0, nivel)
        await self.bot.db.update_guild(interaction.guild.id, rep_min_level=val)
        await interaction.followup.send(embed=success_embed("Nivel minimo actualizado", f"Se requiere nivel **{val}** para dar reputacion."))

    @rep_config.command(name="logs", description="Configurar canal de logs de reputacion")
    @app_commands.describe(canal="Canal para logs")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config_logs(self, interaction: discord.Interaction, canal: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        ch_id = canal.id if canal else 0
        await self.bot.db.update_guild(interaction.guild.id, rep_log_channel=ch_id)
        await interaction.followup.send(
            embed=success_embed("Canal de logs actualizado", f"Logs de reputacion: {canal.mention}" if canal else "Logs de reputacion desactivados.")
        )

    @rep_config.command(name="staffonly", description="Restringir reputacion solo a staff")
    @app_commands.describe(activado="True para staff only, False para todos")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config_staffonly(self, interaction: discord.Interaction, activado: bool):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.update_guild(interaction.guild.id, rep_staff_only=1 if activado else 0)
        await interaction.followup.send(embed=success_embed("Staff only actualizado", f"Reputacion **{'solo staff' if activado else 'para todos'}**."))

    @rep_config.command(name="toggle", description="Activar o desactivar el sistema de reputacion")
    @app_commands.describe(activado="True para activar, False para desactivar")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config_toggle(self, interaction: discord.Interaction, activado: bool):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.update_guild(interaction.guild.id, rep_enabled=1 if activado else 0)
        await interaction.followup.send(embed=success_embed("Sistema actualizado", f"Reputacion **{'activada' if activado else 'desactivada'}**."))

    # ─── Comando: roles (recompensas) ───────────────────────────────────

    rep_roles_group = app_commands.Group(name="roles", description="Gestionar recompensas por reputacion", parent=rep)

    @rep_roles_group.command(name="add", description="Anadir recompensa por reputacion")
    @app_commands.describe(reputacion="Puntos necesarios", rol="Rol a otorgar")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_roles_add(self, interaction: discord.Interaction, reputacion: int, rol: discord.Role):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.add_rep_role(interaction.guild.id, reputacion, rol.id)
        await interaction.followup.send(embed=success_embed("Recompensa anadida", f"**{reputacion}** pts \u2192 {rol.mention}"))

    @rep_roles_group.command(name="remove", description="Quitar recompensa por reputacion")
    @app_commands.describe(reputacion="Puntos necesarios")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_roles_remove(self, interaction: discord.Interaction, reputacion: int):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.remove_rep_role(interaction.guild.id, reputacion)
        await interaction.followup.send(embed=success_embed("Recompensa removida", f"Recompensa de **{reputacion}** pts eliminada."))

    @rep_roles_group.command(name="list", description="Listar recompensas por reputacion")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_roles_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows = await self.bot.db.get_rep_roles(interaction.guild.id)
        if not rows:
            return await interaction.followup.send(embed=info_embed("Recompensas", "No hay recompensas configuradas."))
        embed = PremiumEmbed(title="Recompensas por reputacion", color=config.COLORS["blue"])
        for r in rows:
            role = interaction.guild.get_role(r["role_id"])
            embed.add_field(name=f"{r['rep']} puntos", value=role.mention if role else f"`{r['role_id']}`", inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Reputation(bot))
