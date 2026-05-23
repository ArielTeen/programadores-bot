import discord
from discord.ext import commands
from discord import app_commands
import time
import config
from utils.embeds import PremiumEmbed, success_embed, error_embed, info_embed


class Reports(commands.Cog):
    """📢 Sistema de reportes de usuarios."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="report", description="📢 Reportar un usuario")
    @app_commands.describe(user="Usuario", reason="Motivo")
    async def report(self, interaction: discord.Interaction, user: discord.User, reason: str):
        await interaction.response.defer(ephemeral=True)
        g = await self.bot.db.get_guild(interaction.guild.id)
        ch_id = g.get("report_channel")
        if not ch_id:
            return await interaction.followup.send(embed=error_embed("❌", "No hay canal de reportes."), ephemeral=True)
        ch = interaction.guild.get_channel(ch_id)
        if not ch:
            return await interaction.followup.send(embed=error_embed("❌", "Canal no encontrado."), ephemeral=True)
        e = PremiumEmbed(title="📢 Reporte", color=config.ERROR_COLOR)
        e.add_field(name="👤 Reportado", value=user.mention, inline=True)
        e.add_field(name="🆔 ID", value=str(user.id), inline=True)
        e.add_field(name="📝 Razón", value=reason, inline=False)
        e.add_field(name="👮 Reportó", value=interaction.user.mention, inline=True)
        e.set_footer(text=f"ID: {interaction.user.id}")
        msg = await ch.send(embed=e)
        await self.bot.db.create_report(interaction.guild.id, msg.id, interaction.user.id, user.id, reason)
        await interaction.followup.send(embed=success_embed("✅ Reporte enviado", "El staff revisará tu reporte."), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Reports(bot))
