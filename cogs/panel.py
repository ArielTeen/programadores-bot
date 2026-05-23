import discord
from discord.ext import commands
from discord import app_commands
import time
import config
from utils.embeds import PremiumEmbed, panel_embed, send_ephemeral
from utils.paginator import ButtonPaginator


class Panel(commands.Cog):
    """Panel de control interactivo del servidor."""

    def __init__(self, bot):
        self.bot = bot
        self._panel_lock = {}

    @app_commands.command(name="panel", description="Abrir panel de control interactivo del servidor")
    async def panel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        config_data = await self.bot.db.get_guild(guild.id)

        pages = await self._build_pages(interaction, config_data)
        pag = ButtonPaginator(pages, interaction, timeout=120, only_author=True)
        await pag.start()

    async def _build_pages(self, interaction, config_data):
        guild = interaction.guild
        bot = self.bot
        pages = []

        overview = PremiumEmbed(
            title=f"Panel de Control - {guild.name}",
            description=(
                f"\u2500" * 30 + "\n\n"
                f"**Servidor**\n"
                f"`{guild.name}` (`{guild.id}`)\n"
                f"**{guild.member_count:,}** miembros  |  Propietario: {guild.owner.mention if guild.owner else 'N/A'}\n"
                f"Creado <t:{int(guild.created_at.timestamp())}:R>\n\n"
                f"**Bot**\n"
                f"Ping: **{round(bot.latency * 1000)}ms**\n"
                f"Modulos cargados: **{len(bot.loaded_cogs) if hasattr(bot, 'loaded_cogs') else 'N/A'}**\n"
                f"Online desde: <t:{int(time.time())}:R>\n\n"
                f"**Base de datos**\n"
                f"Conectada  SQLite"
            ),
            color=config.EMBED_COLOR,
        )
        overview.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        overview.set_thumbnail(url=guild.icon.url if guild.icon else None)
        pages.append(overview)

        modules_info = PremiumEmbed(
            title=f"Modulos del Servidor",
            description="Estado actual de cada modulo. Usa `/config view` para cambiar su estado.\n" + "\u2500" * 30,
            color=config.EMBED_COLOR,
        )

        module_list = [
            ("Niveles", "level_system", "XP, niveles y roles automaticos"),
            ("Economia", "economy_system", "Monedas, tienda y apuestas"),
            ("Reputacion", "rep_system", "Sistema de reputacion entre usuarios"),
            ("Bienvenidas", "welcome_system", "Mensajes al entrar y salir"),
            ("Tickets", "ticket_system", "Sistema de soporte con tickets"),
            ("Automod", "automod_enabled", "Anti-spam, links y palabras prohibidas"),
            ("Anti-Nuke", "antinuke_enabled", "Proteccion contra acciones masivas"),
            ("Verificacion", "verify_enabled", "Verificacion con boton o captcha"),
        ]

        lines = []
        for name, key, desc in module_list:
            s = "`[ON]`" if config_data.get(key, 1) else "`[OFF]`"
            lines.append(f"{s} **{name}**\n  {desc}")

        modules_info.description += "\n\n" + "\n\n".join(lines)
        pages.append(modules_info)

        eco = PremiumEmbed(
            title=f"Resumen Economico",
            description="Cargando estadisticas...",
            color=config.COLORS["gold"],
        )

        try:
            top_bal = await self.bot.db.get_leaderboard(guild.id, "balance", 5)
            eco_lines = [f"**Top 5 Economico**\n"]
            medals = ["#1", "#2", "#3", "#4", "#5"]
            for i, r in enumerate(top_bal or []):
                m = guild.get_member(r["user_id"])
                name = m.display_name if m else f"`{r['user_id']}`"
                eco_lines.append(f"{medals[i]} **{name}**  {r['balance']:,} monedas")

            total_members = await self.bot.db.fetchall(
                "SELECT COUNT(*) as c FROM members WHERE guild_id = ?", guild.id
            )
            total_warnings = await self.bot.db.fetchall(
                "SELECT COUNT(*) as c FROM warnings WHERE guild_id = ? AND active = 1", guild.id
            )

            eco_lines.extend([
                "",
                f"**Estadisticas**",
                f"Miembros registrados: `{total_members[0]['c'] if total_members else 0}`",
                f"Warns activos: `{total_warnings[0]['c'] if total_warnings else 0}`",
            ])
            eco.description = "\n".join(eco_lines)
        except Exception as e:
            eco.description = f"Error al cargar: {e}"

        pages.append(eco)

        mod_stats = PremiumEmbed(
            title=f"Moderacion",
            description="Estadisticas de moderacion del servidor.\n" + "\u2500" * 30,
            color=config.EMBED_COLOR,
        )

        try:
            recent_cases = await self.bot.db.fetchall(
                "SELECT * FROM cases WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 5",
                guild.id,
            )
            total_cases = await self.bot.db.fetchall(
                "SELECT COUNT(*) as c FROM cases WHERE guild_id = ?", guild.id
            )

            mod_lines = [
                f"Casos totales: `{total_cases[0]['c'] if total_cases else 0}`",
                "",
                "**Ultimas acciones**",
            ]

            for r in recent_cases or []:
                mod_lines.append(
                    f"  `#{r['case_number']}`  {r['action_type']}  <t:{int(r['timestamp'])}:R>"
                )

            mod_stats.description = "\n".join(mod_lines)
        except Exception as e:
            mod_stats.description = f"Error: {e}"

        pages.append(mod_stats)

        cfg = PremiumEmbed(
            title=f"Configuracion",
            color=config.EMBED_COLOR,
        )

        welcome_ch = guild.get_channel(config_data.get("welcome_channel") or 0)
        ticket_cat = guild.get_channel(config_data.get("ticket_category") or 0)
        mod_log = guild.get_channel(config_data.get("mod_log_channel") or 0)

        cfg.description = (
            f"**Prefijo:** `{config_data.get('prefix', '!')}`\n"
            f"**Idioma:** `{config_data.get('language', 'es')}`\n"
            f"**Bienvenidas:** {welcome_ch.mention if welcome_ch else 'No configurado'}\n"
            f"**Tickets:** {ticket_cat.mention if ticket_cat else 'No configurado'}\n"
            f"**Logs Mod:** {mod_log.mention if mod_log else 'No configurado'}\n\n"
            f"**Sugerencias:** {'Configurado' if config_data.get('suggested_channel') else 'No configurado'}\n"
            f"**Reportes:** {'Configurado' if config_data.get('report_channel') else 'No configurado'}\n"
            f"**Verificacion:** {'Configurado' if config_data.get('verify_channel') else 'No configurado'}\n\n"
            f"Usa `/config view` para ver toda la configuracion.\n"
            f"Gestiona todo desde el **Dashboard Web**."
        )
        pages.append(cfg)

        help_page = PremiumEmbed(
            title=f"Comandos Rapidos",
            description=(
                "\u2500" * 30 + "\n\n"
                "**Moderacion**\n"
                "  `/ban`, `/kick`, `/mute`, `/warn`, `/purge`, `/lock`\n\n"
                "**Economia**\n"
                "  `/balance`, `/daily`, `/work`, `/shop`, `/slots`\n\n"
                "**Niveles**\n"
                "  `/rank`, `/leaderboard`\n\n"
                "**Tickets**\n"
                "  `/ticket` Abrir, cerrar, reclamar\n\n"
                "**Configuracion**\n"
                "  `/config view`, `/config prefix`, `/config modules`\n\n"
                "**Diversion**\n"
                "  `/avatar`, `/serverinfo`, `/userinfo`\n\n"
                f"Panel interactivo: Usa los botones para navegar"
            ),
            color=config.EMBED_COLOR,
        )
        pages.append(help_page)

        return pages

    @panel.error
    async def panel_error(self, interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Espera {error.retry_after:.0f}s antes de usar el panel otra vez.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(Panel(bot))
