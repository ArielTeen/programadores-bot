import discord
from discord.ext import commands
from discord import app_commands
import time
import config
from utils.embeds import PremiumEmbed, success_embed, error_embed, info_embed
from utils.helpers import send_log


class Suggestions(commands.Cog):
    """💡 Sistema de sugerencias con votos."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="suggest", description="💡 Enviar una sugerencia")
    @app_commands.describe(sugerencia="Tu sugerencia")
    async def suggest(self, interaction: discord.Interaction, sugerencia: str):
        await interaction.response.defer(ephemeral=True)
        g = await self.bot.db.get_guild(interaction.guild.id)
        ch_id = g.get("suggested_channel")
        if not ch_id:
            return await interaction.followup.send(embed=error_embed("❌", "No hay canal de sugerencias configurado."), ephemeral=True)
        ch = interaction.guild.get_channel(ch_id)
        if not ch:
            return await interaction.followup.send(embed=error_embed("❌", "Canal no encontrado."), ephemeral=True)
        e = PremiumEmbed(title="💡 Sugerencia", description=sugerencia, color=config.COLORS["blue"])
        e.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        e.add_field(name="Estado", value="⏳ Pendiente")
        e.set_footer(text=f"ID: {interaction.user.id}")
        msg = await ch.send(embed=e)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await self.bot.db.create_suggestion(interaction.guild.id, msg.id, interaction.user.id, sugerencia)
        await interaction.followup.send(embed=success_embed("✅ Sugerencia enviada", f"{ch.mention}"), ephemeral=True)

    suggestions = app_commands.Group(name="suggestions", description="💡 Configurar sugerencias (staff)")

    @suggestions.command(name="setup", description="⚙️ Configurar canal de sugerencias")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal")
    @app_commands.checks.has_permissions(administrator=True)
    async def sug_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, suggested_channel=channel.id)
        await interaction.followup.send(embed=success_embed("💡 Canal de sugerencias", channel.mention))

    @suggestions.command(name="accept", description="✅ Aceptar sugerencia")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(message_id="ID del mensaje", comment="Comentario")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def sug_accept(self, interaction: discord.Interaction, message_id: str, comment: str = ""):
        await interaction.response.defer()
        try:
            mid = int(message_id)
            sug = await self.bot.db.get_suggestion(mid)
            if sug:
                ch = interaction.guild.get_channel(sug["guild_id"] and interaction.channel.id)
                try:
                    msg = await interaction.channel.fetch_message(mid)
                    e = msg.embeds[0]
                    e.color = config.SUCCESS_COLOR
                    e.set_field_at(0, name="Estado", value="✅ Aceptada")
                    if comment:
                        e.add_field(name="💬 Comentario", value=comment, inline=False)
                    await msg.edit(embed=e)
                except:
                    pass
                await self.bot.db.update_suggestion_status(mid, "accepted", comment)
            await interaction.followup.send(embed=success_embed("✅ Sugerencia aceptada"))
        except:
            await interaction.followup.send(embed=error_embed("❌", "Error."))

    @suggestions.command(name="deny", description="❌ Rechazar sugerencia")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(message_id="ID del mensaje", comment="Comentario")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def sug_deny(self, interaction: discord.Interaction, message_id: str, comment: str = ""):
        await interaction.response.defer()
        try:
            mid = int(message_id)
            sug = await self.bot.db.get_suggestion(mid)
            if sug:
                try:
                    msg = await interaction.channel.fetch_message(mid)
                    e = msg.embeds[0]
                    e.color = config.ERROR_COLOR
                    e.set_field_at(0, name="Estado", value="❌ Rechazada")
                    if comment:
                        e.add_field(name="💬 Comentario", value=comment, inline=False)
                    await msg.edit(embed=e)
                except:
                    pass
                await self.bot.db.update_suggestion_status(mid, "denied", comment)
            await interaction.followup.send(embed=success_embed("❌ Sugerencia rechazada"))
        except:
            await interaction.followup.send(embed=error_embed("❌", "Error."))

    @suggestions.command(name="comment", description="💬 Comentar sugerencia")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(message_id="ID del mensaje", comment="Comentario")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def sug_comment(self, interaction: discord.Interaction, message_id: str, comment: str):
        await interaction.response.defer()
        try:
            mid = int(message_id)
            sug = await self.bot.db.get_suggestion(mid)
            if sug:
                try:
                    msg = await interaction.channel.fetch_message(mid)
                    e = msg.embeds[0]
                    e.add_field(name="💬 Comentario del staff", value=comment, inline=False)
                    await msg.edit(embed=e)
                except:
                    pass
                await self.bot.db.update_suggestion_status(mid, sug["status"], comment)
            await interaction.followup.send(embed=success_embed("💬 Comentario añadido"))
        except:
            await interaction.followup.send(embed=error_embed("❌", "Error."))


async def setup(bot):
    await bot.add_cog(Suggestions(bot))
