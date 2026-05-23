import asyncio
import discord
import logging
from discord.ext import commands
from database import Database
from utils.i18n import I18n
import config


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            help_command=None,
            owner_id=config.OWNER_ID,
            chunk_guilds_at_startup=False,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"/help | {config.PREFIX}help",
            ),
        )
        self.db = Database()
        self.i18n = I18n()
        self.uptime = None
        self.logger = logging.getLogger("Bot")

    async def get_lang(self, guild_id: int) -> str:
        g = await self.db.get_guild(guild_id)
        return g.get("language", "es")

    def t(self, lang: str, key: str, **kwargs) -> str:
        return self.i18n.t(lang, key, **kwargs)

    async def _get_prefix(self, msg: discord.Message):
        if not msg.guild:
            return config.PREFIX
        g = await self.db.get_guild(msg.guild.id)
        return g.get("prefix", config.PREFIX)

    async def setup_hook(self):
        await self.db.connect()
        self.loaded_cogs = []
        cogs = [
            "cogs.moderation", "cogs.automod", "cogs.antinuke",
            "cogs.reputation", "cogs.levels", "cogs.economy",
            "cogs.tickets", "cogs.welcome", "cogs.logs",
            "cogs.utility", "cogs.fun", "cogs.suggestions",
            "cogs.reports", "cogs.verification", "cogs.reaction_roles",
            "cogs.giveaways", "cogs.config_cog", "cogs.events", "cogs.panel",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                self.loaded_cogs.append(cog)
            except Exception as e:
                self.logger.error(f"Error loading {cog}: {e}")

    async def _update_status(self):
        lang = await self.get_lang(self.guilds[0].id) if self.guilds else "es"
        if not self.guilds:
            name = self.t(lang, "status.no_servers")
        else:
            guild = self.guilds[0]
            name = self.t(lang, "status.watching", guild=guild.name, members=str(guild.member_count))
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=name,
            )
        )

    async def on_ready(self):
        import datetime
        self.uptime = datetime.datetime.utcnow()
        self.logger.info(f"── {self.user} listo ──")
        self.logger.info(f"Servidores: {len(self.guilds)}")
        self.logger.info(f"Usuarios: {len(self.users)}")
        self.logger.info(f"Cogs cargados: {len(self.loaded_cogs)}")
        self.logger.info("Sincronizando comandos por servidor...")
        for guild in self.guilds:
            try:
                await self.tree.sync(guild=guild)
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.warning(f"Error syncing {guild.name}: {e}")
        self.logger.info("Sincronizacion completada.")
        await self._update_status()

    async def on_guild_join(self, guild):
        try:
            await self.tree.sync(guild=guild)
            self.logger.info(f"Comandos sincronizados en nuevo servidor: {guild.name}")
        except Exception as e:
            self.logger.warning(f"Error syncing new guild {guild.name}: {e}")
        await self._update_status()

    async def on_guild_remove(self, guild):
        await self._update_status()

    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await self._update_status()
