import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.embeds import GuildEmbed, info_embed
from utils.paginator import ReactionPaginator
import math


class Panel(commands.Cog):
    """📋 Panel del servidor — módulos, roles, economía, moderación."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="panel", description="Panel de administración del servidor")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def panel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)

        g = await self.bot.db.get_guild(interaction.guild.id)

        pages = []
        colors = {
            "economy": config.COLORS["green"],
            "moderation": config.COLORS["red"],
            "levels": config.COLORS["purple"],
            "tickets": config.COLORS["blue"],
            "reaction_roles": config.COLORS["pink"],
            "logging": config.COLORS["gray"],
        }

        # Page 1: Overview
        embed = GuildEmbed(
            title=f"📋 {self.bot.t(lang, 'panel.overview_title')}",
            description=interaction.guild.name,
            color=config.EMBED_COLOR,
            guild=interaction.guild,
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.add_field(name=self.bot.t(lang, "panel.total_members"), value=str(interaction.guild.member_count), inline=True)
        embed.add_field(name=self.bot.t(lang, "panel.total_channels"), value=str(len(interaction.guild.channels)), inline=True)
        embed.add_field(name=self.bot.t(lang, "panel.total_roles"), value=str(len(interaction.guild.roles)), inline=True)
        pages.append(embed)

        # Page 2: Modules
        embed = GuildEmbed(
            title=f"⚙️ {self.bot.t(lang, 'panel.modules_title')}",
            color=config.COLORS["blue"],
            guild=interaction.guild,
        )
        mods = [
            ("economy", self.bot.t(lang, "panel.economy_desc")),
            ("levels", self.bot.t(lang, "panel.levels_desc")),
            ("tickets", self.bot.t(lang, "panel.tickets_desc")),
            ("logging", self.bot.t(lang, "panel.logging_desc")),
            ("reaction_roles", self.bot.t(lang, "panel.reaction_roles_desc")),
            ("welcome", self.bot.t(lang, "panel.welcome_desc")),
            ("suggestions", self.bot.t(lang, "panel.suggestions_desc")),
            ("reports", self.bot.t(lang, "panel.reports_desc")),
            ("automod", self.bot.t(lang, "panel.automod_desc")),
            ("antinuke", self.bot.t(lang, "panel.antinuke_desc")),
            ("verification", self.bot.t(lang, "panel.verification_desc")),
        ]
        for key, desc in mods:
            status = g.get(f"{key}_enabled", 1 if key in ("economy", "levels", "tickets", "welcome") else 0)
            emoji = "✅" if status else "❌"
            embed.add_field(name=f"{emoji} {key.capitalize()}", value=desc, inline=True)
        pages.append(embed)

        # Page 3: Economy
        embed = GuildEmbed(
            title=f"💰 {self.bot.t(lang, 'panel.economy_section')}",
            color=colors["economy"],
            guild=interaction.guild,
        )
        eco_enabled = g.get("economy_enabled", 1)
        embed.add_field(name=self.bot.t(lang, "panel.status"), value="✅" if eco_enabled else "❌", inline=True)
        embed.add_field(name=self.bot.t(lang, "panel.economy_start_bal"), value=f"{g.get('economy_start_balance', 100):,} 🪙", inline=True)
        embed.add_field(name=self.bot.t(lang, "panel.economy_work_pay"), value=f"{g.get('economy_work_pay', 50):,} 🪙", inline=True)
        embed.add_field(name=self.bot.t(lang, "panel.economy_daily_amount"), value=f"{g.get('economy_daily_amount', 100):,} 🪙", inline=True)
        pages.append(embed)

        # Page 4: Moderation
        embed = GuildEmbed(
            title=f"🛡️ {self.bot.t(lang, 'panel.moderation_section')}",
            color=colors["moderation"],
            guild=interaction.guild,
        )
        mod_log = g.get("log_channel_all")
        embed.add_field(name=self.bot.t(lang, "panel.mod_log_channel"), value=f"<#{mod_log}>" if mod_log else self.bot.t(lang, "common.not_configured"), inline=False)
        muted_role = discord.utils.get(interaction.guild.roles, name="Silenciado")
        embed.add_field(name=self.bot.t(lang, "panel.muted_role"), value=muted_role.mention if muted_role else self.bot.t(lang, "common.not_configured"), inline=True)
        pages.append(embed)

        # Page 5: Config values
        embed = GuildEmbed(
            title=f"🔧 {self.bot.t(lang, 'panel.config_section')}",
            color=colors["levels"],
            guild=interaction.guild,
        )
        prefix = "/"
        embed.add_field(name=self.bot.t(lang, "panel.prefix"), value=f"`{prefix}`", inline=True)
        embed.add_field(name=self.bot.t(lang, "panel.language"), value=g.get("lang", "es"), inline=True)
        embed.add_field(name=self.bot.t(lang, "panel.level_channel"), value=f"<#{g.get('level_channel')}>" if g.get("level_channel") else self.bot.t(lang, "common.dm"), inline=True)
        pages.append(embed)

        # Page 6: Help info
        embed = GuildEmbed(
            title=f"❓ {self.bot.t(lang, 'panel.help_section')}",
            description=self.bot.t(lang, "panel.help_desc"),
            color=config.COLORS["yellow"],
            guild=interaction.guild,
        )
        embed.add_field(name=self.bot.t(lang, "panel.commands_list"), value=self.bot.t(lang, "panel.commands_help"), inline=False)
        embed.add_field(name=self.bot.t(lang, "panel.config_commands"), value=self.bot.t(lang, "panel.config_help"), inline=False)
        pages.append(embed)

        pag = ReactionPaginator(interaction, pages, timeout=120)
        await pag.start()


async def setup(bot):
    await bot.add_cog(Panel(bot))
