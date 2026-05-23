import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.embeds import success_embed, error_embed, info_embed, PremiumEmbed


class Logs(commands.Cog):
    """📝 Sistema de logs — mensajes, miembros, moderación, etc."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        embed = PremiumEmbed(title="Mensaje eliminado", color=config.ERROR_COLOR)
        embed.add_field(name="Autor", value=message.author.mention, inline=True)
        embed.add_field(name="Canal", value=message.channel.mention, inline=True)
        embed.add_field(name="Contenido", value=message.content[:1000] or "Sin contenido", inline=False)
        await self._send(message.guild.id, "messages", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = PremiumEmbed(title="Mensaje editado", color=config.WARNING_COLOR)
        embed.add_field(name="Autor", value=before.author.mention, inline=True)
        embed.add_field(name="Canal", value=before.channel.mention, inline=True)
        embed.add_field(name="Antes", value=before.content[:500] or "N/A", inline=False)
        embed.add_field(name="Después", value=after.content[:500] or "N/A", inline=False)
        await self._send(before.guild.id, "messages", embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        embed = PremiumEmbed(title="Canal creado", color=config.SUCCESS_COLOR)
        embed.add_field(name="Nombre", value=channel.mention, inline=True)
        embed.add_field(name="Tipo", value=str(channel.type), inline=True)
        await self._send(channel.guild.id, "channels", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = PremiumEmbed(title="Canal eliminado", color=config.ERROR_COLOR)
        embed.add_field(name="Nombre", value=channel.name, inline=True)
        embed.add_field(name="Tipo", value=str(channel.type), inline=True)
        await self._send(channel.guild.id, "channels", embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        embed = PremiumEmbed(title="Rol creado", color=config.SUCCESS_COLOR)
        embed.add_field(name="Nombre", value=role.mention, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        await self._send(role.guild.id, "roles", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        embed = PremiumEmbed(title="Rol eliminado", color=config.ERROR_COLOR)
        embed.add_field(name="Nombre", value=role.name, inline=True)
        await self._send(role.guild.id, "roles", embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        if before.channel != after.channel:
            if after.channel and not before.channel:
                embed = PremiumEmbed(title="Conectado a voz", color=config.SUCCESS_COLOR)
                embed.add_field(name="Usuario", value=member.mention, inline=True)
                embed.add_field(name="Canal", value=after.channel.mention, inline=True)
                await self._send(member.guild.id, "voice", embed)
            elif before.channel and not after.channel:
                embed = PremiumEmbed(title="Desconectado de voz", color=config.ERROR_COLOR)
                embed.add_field(name="Usuario", value=member.mention, inline=True)
                embed.add_field(name="Canal", value=before.channel.mention, inline=True)
                await self._send(member.guild.id, "voice", embed)

    async def _send(self, guild_id, module, embed):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        channels = await self.bot.db.get_log_channels(guild_id)
        ch_id = channels.get(module)
        if ch_id:
            ch = guild.get_channel(ch_id)
            if ch and ch.permissions_for(guild.me).send_messages:
                try:
                    await ch.send(embed=embed)
                except:
                    pass

    # ── Comandos ─────────────────────────────────────────────────────────────
    logs = app_commands.Group(name="logs", description="Configurar logs")

    @logs.command(name="setup", description="Configurar canal de logs")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(module="Módulo", channel="Canal")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_setup(self, interaction: discord.Interaction, module: str, channel: discord.TextChannel):
        await interaction.response.defer()
        await self.bot.db.set_log_channel(interaction.guild.id, module, channel.id)
        await interaction.followup.send(embed=success_embed("📝 Log configurado", f"{module} → {channel.mention}"))

    @logs_setup.autocomplete("module")
    async def logs_module_ac(self, interaction: discord.Interaction, current: str):
        opts = ["messages", "members", "moderation", "channels", "roles", "voice", "invites", "automod", "antinuke", "commands", "tickets", "reputation"]
        return [app_commands.Choice(name=m, value=m) for m in opts if current.lower() in m.lower()]

    @logs.command(name="enable", description="Activar módulo de logs")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(module="Módulo")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_enable(self, interaction: discord.Interaction, module: str):
        await interaction.response.defer()
        await self.bot.db.toggle_log_module(interaction.guild.id, module, True)
        await interaction.followup.send(embed=success_embed("✅ Log activado", module))

    @logs.command(name="disable", description="Desactivar módulo de logs")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(module="Módulo")
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_disable(self, interaction: discord.Interaction, module: str):
        await interaction.response.defer()
        await self.bot.db.toggle_log_module(interaction.guild.id, module, False)
        await interaction.followup.send(embed=success_embed("❌ Log desactivado", module))

    @logs.command(name="test", description="Probar logs")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_test(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = PremiumEmbed(title="Test de logs", description="Si ves esto, los logs funcionan.", color=config.SUCCESS_COLOR)
        await self._send(interaction.guild.id, "messages", embed)
        await interaction.followup.send(embed=success_embed("🧪 Test enviado"))

    @logs.command(name="modules", description="Ver módulos de logs activos")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def logs_modules(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channels = await self.bot.db.get_log_channels(interaction.guild.id)
        if not channels:
            return await interaction.followup.send(embed=info_embed("📝", "No hay logs configurados."))
        embed = PremiumEmbed(title="Módulos de logs", color=config.EMBED_COLOR)
        for mod, ch_id in channels.items():
            ch = interaction.guild.get_channel(ch_id)
            embed.add_field(name=mod, value=ch.mention if ch else "❌", inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Logs(bot))
