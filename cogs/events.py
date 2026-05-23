import discord
from discord.ext import commands
import logging
import config


class Events(commands.Cog):
    """📡 Manejador global de eventos y errores."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("Events")

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error):
        from utils.embeds import error_embed, warning_embed

        if isinstance(error, discord.app_commands.CommandOnCooldown):
            return await interaction.response.send_message(
                embed=warning_embed("⏳ Cooldown", f"Espera {error.retry_after:.1f}s."), ephemeral=True
            )
        if isinstance(error, discord.app_commands.MissingPermissions):
            return await interaction.response.send_message(
                embed=warning_embed("🚫 Permisos", "No tienes permisos."), ephemeral=True
            )
        if isinstance(error, discord.app_commands.BotMissingPermissions):
            return await interaction.response.send_message(
                embed=warning_embed("🚫", f"No tengo permisos: {', '.join(error.missing_permissions)}"), ephemeral=True
            )
        if isinstance(error, discord.app_commands.CommandNotFound):
            return

        self.logger.error(f"Slash error: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=error_embed("❌ Error", str(error)[:500]), ephemeral=True
                )
        except:
            pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        from utils.embeds import warning_embed
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(embed=warning_embed("⏳", f"Espera {error.retry_after:.1f}s."), delete_after=5)
        if isinstance(error, commands.MissingPermissions):
            return await ctx.send(embed=warning_embed("🚫", "No tienes permisos."), delete_after=5)
        if isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(embed=warning_embed("🚫", f"No tengo permisos."), delete_after=5)
        if isinstance(error, commands.CommandNotFound):
            return

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"── {self.bot.user} listo ──")
        self.logger.info(f"Servidores: {len(self.bot.guilds)}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.logger.info(f"📥 Nuevo servidor: {guild.name} ({guild.id}) - {guild.member_count} miembros")
        await self.bot.db.get_guild(guild.id)
        # Log to owner
        owner = self.bot.get_user(config.OWNER_ID)
        if owner:
            from utils.embeds import info_embed
            await owner.send(embed=info_embed("📥 Nuevo servidor", f"{guild.name} (`{guild.id}`)\n{guild.member_count} miembros"))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.logger.info(f"📤 Salí de: {guild.name} ({guild.id})")


async def setup(bot):
    await bot.add_cog(Events(bot))
