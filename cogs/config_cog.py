import discord
from discord.ext import commands
from discord import app_commands
import json
import config
from utils.embeds import success_embed, error_embed, info_embed, GuildEmbed


class ConfigCog(commands.Cog):
    """⚙️ Configuración general del servidor."""

    def __init__(self, bot):
        self.bot = bot

    config_group = app_commands.Group(name="config", description="Configuración del servidor", default_permissions=discord.Permissions(administrator=True))

    @config_group.command(name="view", description="Ver configuración actual")
    async def config_view(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        g = await self.bot.db.get_guild(interaction.guild.id)
        embed = GuildEmbed(title=self.bot.t(lang, "config.title", guild=interaction.guild.name), color=config.EMBED_COLOR)
        log = interaction.guild.get_channel(g.get("mod_log_channel") or 0)
        welcome = interaction.guild.get_channel(g.get("welcome_channel") or 0)
        sug = interaction.guild.get_channel(g.get("suggested_channel") or 0)
        rep = interaction.guild.get_channel(g.get("report_channel") or 0)
        cat = interaction.guild.get_channel(g.get("ticket_category") or 0)
        embed.add_field(name=self.bot.t(lang, "config.prefix"), value=f"`{g.get('prefix', '!')}`f", inline=True)
        embed.add_field(name=self.bot.t(lang, "config.language"), value=g.get("language", "es"), inline=True)
        embed.add_field(name=self.bot.t(lang, "config.logs"), value=log.mention if log else "❌", inline=True)
        embed.add_field(name=self.bot.t(lang, "config.welcome"), value=welcome.mention if welcome else "❌", inline=True)
        embed.add_field(name=self.bot.t(lang, "config.suggestions"), value=sug.mention if sug else "❌", inline=True)
        embed.add_field(name=self.bot.t(lang, "config.reports"), value=rep.mention if rep else "❌", inline=True)
        embed.add_field(name=self.bot.t(lang, "config.tickets"), value=cat.mention if cat else "❌", inline=True)
        systems = [("level_system", "config.levels"), ("economy_system", "config.economy"), ("rep_system", "config.reputation"),
                   ("welcome_system", "config.welcome"), ("ticket_system", "config.tickets"),
                   ("automod_enabled", "config.automod"), ("antinuke_enabled", "config.antinuke")]
        for key, name_key in systems:
            embed.add_field(name=self.bot.t(lang, name_key), value="" if g.get(key, 1) else "❌", inline=True)
        await interaction.followup.send(embed=embed)

    @config_group.command(name="prefix", description="Cambiar prefijo")
    @app_commands.describe(prefix="Nuevo prefijo")
    async def config_prefix(self, interaction: discord.Interaction, prefix: str):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.update_guild(interaction.guild.id, prefix=prefix)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "config.prefix_changed"), f"`{prefix}`"))

    @config_group.command(name="language", description="Cambiar idioma / Change language / Mudar idioma")
    @app_commands.describe(language="Idioma (es/en/pt)")
    async def config_language(self, interaction: discord.Interaction, language: str):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if language not in ("es", "en", "pt"):
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "config.available_langs")))
        await self.bot.db.update_guild(interaction.guild.id, language=language)
        names = {"es": "Español", "en": "English", "pt": "Português"}
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "config.language_changed"), names.get(language, language)))

    @config_group.command(name="reset", description="Resetear configuración del servidor")
    async def config_reset(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.execute("DELETE FROM guild_config WHERE guild_id = ?", interaction.guild.id)
        await self.bot.db.execute("INSERT INTO guild_config (guild_id) VALUES (?)", interaction.guild.id)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "config.config_reset")))

    @config_group.command(name="modules", description="Ver módulos disponibles")
    async def config_modules(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        g = await self.bot.db.get_guild(interaction.guild.id)
        embed = GuildEmbed(title=self.bot.t(lang, "config.modules"), color=config.EMBED_COLOR)
        modules = [
            ("level_system", "config.levels", "panel.level_desc"),
            ("economy_system", "config.economy", "panel.economy_desc"),
            ("rep_system", "config.reputation", "panel.rep_desc"),
            ("welcome_system", "config.welcome", "panel.welcome_desc"),
            ("ticket_system", "config.tickets", "panel.ticket_desc"),
            ("automod_enabled", "config.automod", "panel.automod_desc"),
            ("antinuke_enabled", "config.antinuke", "panel.antinuke_desc"),
            ("verify_enabled", "config.verification", "panel.verify_desc"),
        ]
        for key, name_key, desc_key in modules:
            status = "✅" if g.get(key, 1) else "❌"
            embed.add_field(name=f"{status} {self.bot.t(lang, name_key)}f", value=self.bot.t(lang, desc_key), inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
