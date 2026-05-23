import discord
from discord.ext import commands
from discord import app_commands
import time
import config
from utils.embeds import GuildEmbed, success_embed, error_embed, info_embed
from utils.helpers import send_log
from utils.paginator import ReactionPaginator


class Reports(commands.Cog):
    """📮 Sistema de reportes de usuarios."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="report", description="Reportar a un usuario del servidor")
    @app_commands.describe(user="Usuario a reportar", reason="Razón del reporte")
    async def report(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)

        if user == interaction.user:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reports.self_report")))
        if user.bot:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reports.bot_report")))

        report_id = await self.bot.db.create_report(interaction.guild.id, interaction.user.id, user.id, reason)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reports.created_title"), self.bot.t(lang, "reports.created_desc", report=report_id)))

        g = await self.bot.db.get_guild(interaction.guild.id)
        ch_id = g.get("report_channel")
        if ch_id:
            ch = interaction.guild.get_channel(ch_id)
            if ch:
                e = GuildEmbed(title=self.bot.t(lang, "reports.new_report", report=report_id), color=config.COLORS["red"], guild=interaction.guild)
                e.add_field(name=self.bot.t(lang, "reports.reported_user"), value=user.mention, inline=True)
                e.add_field(name=self.bot.t(lang, "reports.reported_by"), value=interaction.user.mention, inline=True)
                e.add_field(name=self.bot.t(lang, "moderation.reason"), value=reason, inline=False)
                await ch.send(embed=e)

    @app_commands.command(name="reports", description="Ver reportes de un usuario")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(user="Usuario (opcional)")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def reports_list(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        rows = await self.bot.db.get_reports(interaction.guild.id, user.id if user else None)
        if not rows:
            return await interaction.followup.send(embed=info_embed(self.bot.t(lang, "reports.list_title"), self.bot.t(lang, "reports.no_reports", user=user.mention) if user else self.bot.t(lang, "reports.no_reports_all")))
        per_page = 5
        chunks = [rows[i:i+per_page] for i in range(0, len(rows), per_page)]
        pages = []
        for chunk in chunks:
            embed = GuildEmbed(
                title=self.bot.t(lang, "reports.list_user", user=user.display_name) if user else self.bot.t(lang, "reports.list_all"),
                color=config.COLORS["orange"],
                guild=interaction.guild,
            )
            for r in chunk:
                reporter = interaction.guild.get_member(r["reporter_id"])
                embed.add_field(
                    name=f"#{r['id']} — {self.bot.t(lang, 'reports.status_' + (r.get('status', 'open')))}",
                    value=self.bot.t(lang, "reports.entry", user=f"<@{r['user_id']}>", reason=r['reason'], reporter=reporter.mention if reporter else f"`{r['reporter_id']}`"),
                    inline=False,
                )
            pages.append(embed)
        if len(pages) <= 1:
            return await interaction.followup.send(embed=pages[0])
        pag = ReactionPaginator(interaction, pages, timeout=60)
        await pag.start()

    @app_commands.command(name="reportresolve", description="Resolver un reporte")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(report_id="ID del reporte", note="Nota opcional")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def reportresolve(self, interaction: discord.Interaction, report_id: int, note: str = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            await self.bot.db.update_report(report_id, interaction.guild.id, status="resolved", resolved_by=interaction.user.id)
            embed = success_embed(self.bot.t(lang, "reports.resolved_title"), self.bot.t(lang, "reports.resolved_desc", report=report_id))
            if note:
                embed.add_field(name=self.bot.t(lang, "reports.note"), value=note, inline=False)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), f"{e}"))


async def setup(bot):
    await bot.add_cog(Reports(bot))
