import discord
from discord.ext import commands
import logging
import config


class Events(commands.Cog):
    """📡 Manejador global de eventos y errores."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("Events")

    async def _get_lang_for(self, interaction):
        if interaction.guild:
            return await self.bot.get_lang(interaction.guild.id)
        return "es"

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error):
        from utils.embeds import error_embed, warning_embed
        lang = await self._get_lang_for(interaction)

        if isinstance(error, discord.app_commands.CommandOnCooldown):
            return await interaction.response.send_message(
                embed=warning_embed(self.bot.t(lang, "common.warning"), self.bot.t(lang, "events.cooldown", time=f"{error.retry_after:.1f}")), ephemeral=True
            )
        if isinstance(error, discord.app_commands.MissingPermissions):
            return await interaction.response.send_message(
                embed=warning_embed(self.bot.t(lang, "common.warning"), self.bot.t(lang, "events.missing_perms")), ephemeral=True
            )
        if isinstance(error, discord.app_commands.BotMissingPermissions):
            return await interaction.response.send_message(
                embed=warning_embed(self.bot.t(lang, "common.warning"), self.bot.t(lang, "events.bot_missing_perms", perms=", ".join(error.missing_permissions))), ephemeral=True
            )
        if isinstance(error, discord.app_commands.CommandNotFound):
            return

        self.logger.error(f"Slash error: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=error_embed(self.bot.t(lang, "errors.title"), str(error)[:500]), ephemeral=True
                )
        except:
            pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        from utils.embeds import warning_embed
        lang = "es"
        if ctx.guild:
            lang = await self.bot.get_lang(ctx.guild.id)
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(embed=warning_embed(self.bot.t(lang, "common.warning"), self.bot.t(lang, "events.cooldown", time=f"{error.retry_after:.1f}")), delete_after=5)
        if isinstance(error, commands.MissingPermissions):
            return await ctx.send(embed=warning_embed(self.bot.t(lang, "common.warning"), self.bot.t(lang, "events.missing_perms")), delete_after=5)
        if isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(embed=warning_embed(self.bot.t(lang, "common.warning"), self.bot.t(lang, "events.bot_missing_perms", perms="")), delete_after=5)
        if isinstance(error, commands.CommandNotFound):
            return

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"── {self.bot.user} listo ──")
        self.logger.info(f"Servidores: {len(self.bot.guilds)}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.logger.info(f"📥 Nuevo servidor: {guild.name} ({guild.id}) - {guild.member_count} miembros")
        lang = "es"
        try:
            lang = await self.bot.get_lang(guild.id)
        except:
            pass
        await self.bot.db.get_guild(guild.id)
        # Log to owner
        owner = self.bot.get_user(config.OWNER_ID)
        if owner:
            from utils.embeds import info_embed
            await owner.send(embed=info_embed(self.bot.t(lang, "events.new_server"), self.bot.t(lang, "events.new_server_desc", name=guild.name, id=guild.id, members=guild.member_count)))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.logger.info(f"📤 Salí de: {guild.name} ({guild.id})")


async def setup(bot):
    await bot.add_cog(Events(bot))
