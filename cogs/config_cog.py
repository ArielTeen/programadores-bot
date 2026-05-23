import discord
from discord.ext import commands
from discord import app_commands
import json
import config
from utils.embeds import success_embed, error_embed, info_embed, PremiumEmbed


class ConfigCog(commands.Cog):
    """⚙️ Configuración general del servidor."""

    def __init__(self, bot):
        self.bot = bot

    config_group = app_commands.Group(name="config", description="⚙️ Configuración del servidor", default_permissions=discord.Permissions(administrator=True))

    @config_group.command(name="view", description="📋 Ver configuración actual")
    async def config_view(self, interaction: discord.Interaction):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        embed = PremiumEmbed(title=f"⚙️ Configuración de {interaction.guild.name}", color=config.EMBED_COLOR)
        log = interaction.guild.get_channel(g.get("mod_log_channel") or 0)
        welcome = interaction.guild.get_channel(g.get("welcome_channel") or 0)
        sug = interaction.guild.get_channel(g.get("suggested_channel") or 0)
        rep = interaction.guild.get_channel(g.get("report_channel") or 0)
        cat = interaction.guild.get_channel(g.get("ticket_category") or 0)
        embed.add_field(name="🔤 Prefijo", value=f"`{g.get('prefix', '!')}`", inline=True)
        embed.add_field(name="🌐 Idioma", value=g.get("language", "es"), inline=True)
        embed.add_field(name="📝 Logs", value=log.mention if log else "❌", inline=True)
        embed.add_field(name="👋 Bienvenidas", value=welcome.mention if welcome else "❌", inline=True)
        embed.add_field(name="💡 Sugerencias", value=sug.mention if sug else "❌", inline=True)
        embed.add_field(name="📢 Reportes", value=rep.mention if rep else "❌", inline=True)
        embed.add_field(name="🎫 Tickets", value=cat.mention if cat else "❌", inline=True)
        systems = [("level_system", "📊 Niveles"), ("economy_system", "💰 Economía"), ("rep_system", "⭐ Rep"),
                   ("welcome_system", "👋 Bienvenidas"), ("ticket_system", "🎫 Tickets"),
                   ("automod_enabled", "🤖 Automod"), ("antinuke_enabled", "☢️ Anti-Nuke")]
        for key, name in systems:
            embed.add_field(name=name, value="✅" if g.get(key, 1) else "❌", inline=True)
        await interaction.followup.send(embed=embed)

    @config_group.command(name="prefix", description="🔤 Cambiar prefijo")
    @app_commands.describe(prefix="Nuevo prefijo")
    async def config_prefix(self, interaction: discord.Interaction, prefix: str):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, prefix=prefix)
        await interaction.followup.send(embed=success_embed("🔤 Prefijo cambiado", f"`{prefix}`"))

    @config_group.command(name="language", description="🌐 Cambiar idioma")
    @app_commands.describe(language="Idioma (es/en)")
    async def config_language(self, interaction: discord.Interaction, language: str):
        await interaction.response.defer()
        if language not in ("es", "en"):
            return await interaction.followup.send(embed=error_embed("❌", "Idiomas: es, en"))
        await self.bot.db.update_guild(interaction.guild.id, language=language)
        await interaction.followup.send(embed=success_embed("🌐 Idioma", language))

    @config_group.command(name="reset", description="🔄 Resetear configuración del servidor")
    async def config_reset(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot.db.execute("DELETE FROM guild_config WHERE guild_id = ?", interaction.guild.id)
        await self.bot.db.execute("INSERT INTO guild_config (guild_id) VALUES (?)", interaction.guild.id)
        await interaction.followup.send(embed=success_embed("🔄 Configuración reseteada"))

    @config_group.command(name="modules", description="📋 Ver módulos disponibles")
    async def config_modules(self, interaction: discord.Interaction):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        embed = PremiumEmbed(title="📋 Módulos", color=config.EMBED_COLOR)
        modules = [
            ("level_system", "📊 Niveles", "Sistema de XP y niveles"),
            ("economy_system", "💰 Economía", "Monedas, tienda, apuestas"),
            ("rep_system", "⭐ Reputación", "Sistema de reputación"),
            ("welcome_system", "👋 Bienvenidas", "Mensajes de bienvenida/despedida"),
            ("ticket_system", "🎫 Tickets", "Sistema de tickets"),
            ("automod_enabled", "🤖 Automod", "Anti-spam, anti-link, etc."),
            ("antinuke_enabled", "☢️ Anti-Nuke", "Protección contra nuke"),
            ("verify_enabled", "🛂 Verificación", "Verificación de usuarios"),
        ]
        for key, name, desc in modules:
            status = "✅" if g.get(key, 1) else "❌"
            embed.add_field(name=f"{status} {name}", value=desc, inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
