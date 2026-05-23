import discord
from discord.ext import commands
from discord import app_commands
import time
import asyncio
import platform
import config
from utils.embeds import GuildEmbed, success_embed, error_embed, info_embed
from utils.helpers import send_log


class HelpSelect(discord.ui.Select):
    def __init__(self, bot, lang):
        self.bot = bot
        self.lang = lang
        opts = [
            discord.SelectOption(label=self.bot.t(lang, "help.moderation"), emoji="🛡️", value="moderation", description=self.bot.t(lang, "help.moderation_desc")),
            discord.SelectOption(label=self.bot.t(lang, "help.economy"), emoji="💰", value="economy", description=self.bot.t(lang, "help.economy_desc")),
            discord.SelectOption(label=self.bot.t(lang, "help.fun"), emoji="🎮", value="fun", description=self.bot.t(lang, "help.fun_desc")),
            discord.SelectOption(label=self.bot.t(lang, "help.utility"), emoji="🔧", value="utility", description=self.bot.t(lang, "help.utility_desc")),
            discord.SelectOption(label=self.bot.t(lang, "help.levels"), emoji="📊", value="levels", description=self.bot.t(lang, "help.levels_desc")),
            discord.SelectOption(label=self.bot.t(lang, "help.tickets"), emoji="🎫", value="tickets", description=self.bot.t(lang, "help.tickets_desc")),
            discord.SelectOption(label=self.bot.t(lang, "help.giveaways"), emoji="🎉", value="giveaways", description=self.bot.t(lang, "help.giveaways_desc")),
            discord.SelectOption(label=self.bot.t(lang, "help.reputation"), emoji="⭐", value="reputation", description=self.bot.t(lang, "help.reputation_desc")),
        ]
        super().__init__(placeholder=self.bot.t(lang, "help.select_category"), options=opts)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        category = interaction.data["values"][0]
        help_data = {
            "moderation": ("🛡️ " + self.bot.t(lang, "help.moderation"), [
                "/ban", "/kick", "/mute", "/unmute", "/warn", "/warnings",
                "/clearwarn", "/purge", "/purgeall", "/slowmode", "/lock",
                "/unlock", "/nick", "/role", "/voice", "/clean", "/case",
                "/massban",
            ]),
            "economy": ("💰 " + self.bot.t(lang, "help.economy"), [
                "/balance", "/daily", "/weekly", "/work", "/pay", "/shop",
                "/buy", "/rob", "/gamble", "/slots", "/inventory", "/give",
                "/economy give", "/economy remove", "/economy set",
                "/economy reset",
            ]),
            "fun": ("🎮 " + self.bot.t(lang, "help.fun"), [
                "/8ball", "/meme", "/cat", "/dog", "/hug", "/kiss", "/slap",
                "/pat", "/coinflip", "/dice", "/reverse", "/say", "/mock",
                "/randomnumber", "/github", "/urban",
            ]),
            "utility": ("🔧 " + self.bot.t(lang, "help.utility"), [
                "/help", "/ping", "/botinfo", "/serverinfo", "/userinfo",
                "/roleinfo", "/avatar", "/banner", "/poll", "/timestamp",
                "/remind", "/afk", "/membercount", "/roles", "/channels",
                "/boosters", "/servericon", "/serverbanner",
            ]),
            "levels": ("📊 " + self.bot.t(lang, "help.levels"), [
                "/rank", "/leaderboard", "/xp add", "/xp remove", "/xp set",
                "/xp reset", "/levelroles add", "/levelroles remove",
                "/levelroles list", "/levelconfig", "/levelmessage",
            ]),
            "tickets": ("🎫 " + self.bot.t(lang, "help.tickets"), [
                "/ticket", "/ticketpanel", "/ticketconfig", "/add", "/remove",
                "/rename", "/close", "/ticketstats",
            ]),
            "giveaways": ("🎉 " + self.bot.t(lang, "help.giveaways"), [
                "/giveaway start", "/giveaway end", "/giveaway reroll",
                "/giveaway list",
            ]),
            "reputation": ("⭐ " + self.bot.t(lang, "help.reputation"), [
                "/rep give", "/rep remove", "/rep set", "/rep profile",
                "/rep top", "/reprewards add", "/reprewards remove",
                "/reprewards list", "/rep config",
            ]),
        }
        title, cmds = help_data.get(category, ("❓ " + self.bot.t(lang, "help.unknown"), []))
        embed = GuildEmbed(title=title, color=config.EMBED_COLOR, guild=interaction.guild)
        for c in cmds:
            embed.add_field(name=c, value="", inline=True)
        await interaction.edit_original_response(embed=embed)


class Utility(commands.Cog):
    """🔧 Comandos de utilidad — info, help, ping, etc."""

    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    @app_commands.command(name="help", description="Menú de ayuda")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        embed = GuildEmbed(
            title=f"❓ {self.bot.t(lang, 'help.title')}",
            description=self.bot.t(lang, "help.desc", prefix="/"),
            color=config.EMBED_COLOR,
            guild=interaction.guild,
        )
        embed.set_footer(text=self.bot.t(lang, "help.select_category"))
        view = discord.ui.View()
        view.add_item(HelpSelect(self.bot, lang))
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="ping", description="Latencia del bot")
    async def ping(self, interaction: discord.Interaction):
        lang = await self.bot.get_lang(interaction.guild.id)
        start = time.monotonic()
        await interaction.response.send_message("🏓")
        end = time.monotonic()
        api_latency = round((end - start) * 1000)
        embed = GuildEmbed(title="🏓 " + self.bot.t(lang, "ping.title"), color=config.COLORS["green"], guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "ping.bot_latency"), value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name=self.bot.t(lang, "ping.api_latency"), value=f"{api_latency}ms", inline=True)
        embed.add_field(name=self.bot.t(lang, "ping.uptime"), value=f"<t:{int(self.start_time)}:R>", inline=False)
        await interaction.edit_original_response(content=None, embed=embed)

    @app_commands.command(name="botinfo", description="Información del bot")
    async def botinfo(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        uptime_seconds = int(time.time() - self.start_time)
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        minutes = (uptime_seconds % 3600) // 60
        uptime_str = f"{days}d {hours}h {minutes}m"
        total_users = sum(len(g.members) for g in self.bot.guilds)
        embed = GuildEmbed(title=self.bot.t(lang, "botinfo.title"), color=config.COLORS["blue"], guild=interaction.guild)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name=self.bot.t(lang, "botinfo.name"), value=self.bot.user.name, inline=True)
        embed.add_field(name=self.bot.t(lang, "botinfo.id"), value=f"`{self.bot.user.id}`", inline=True)
        embed.add_field(name=self.bot.t(lang, "botinfo.servers"), value=f"{len(self.bot.guilds):,}", inline=True)
        embed.add_field(name=self.bot.t(lang, "botinfo.users"), value=f"{total_users:,}", inline=True)
        embed.add_field(name=self.bot.t(lang, "botinfo.uptime"), value=uptime_str, inline=True)
        embed.add_field(name=self.bot.t(lang, "botinfo.latency"), value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name=self.bot.t(lang, "botinfo.python"), value=platform.python_version(), inline=True)
        embed.add_field(name=self.bot.t(lang, "botinfo.discord_py"), value=discord.__version__, inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="serverinfo", description="Información del servidor")
    async def serverinfo(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        g = interaction.guild
        embed = GuildEmbed(title=self.bot.t(lang, "serverinfo.title", guild=g.name), color=g.me.color or config.EMBED_COLOR, guild=g)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name=self.bot.t(lang, "serverinfo.name"), value=g.name, inline=True)
        embed.add_field(name=self.bot.t(lang, "serverinfo.id"), value=f"`{g.id}`", inline=True)
        embed.add_field(name=self.bot.t(lang, "serverinfo.owner"), value=g.owner.mention if g.owner else self.bot.t(lang, "common.na"), inline=True)
        embed.add_field(name=self.bot.t(lang, "serverinfo.members"), value=str(g.member_count), inline=True)
        embed.add_field(name=self.bot.t(lang, "serverinfo.channels"), value=str(len(g.channels)), inline=True)
        embed.add_field(name=self.bot.t(lang, "serverinfo.roles"), value=str(len(g.roles)), inline=True)
        embed.add_field(name=self.bot.t(lang, "serverinfo.created"), value=f"<t:{int(g.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name=self.bot.t(lang, "serverinfo.boost_level"), value=str(g.premium_tier), inline=True)
        embed.add_field(name=self.bot.t(lang, "serverinfo.boosts"), value=str(g.premium_subscription_count), inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="userinfo", description="Información de un usuario")
    @app_commands.describe(user="Usuario (opcional)")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        embed = GuildEmbed(title=self.bot.t(lang, "userinfo.title", user=user.display_name), color=user.color or config.EMBED_COLOR, guild=interaction.guild)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name=self.bot.t(lang, "userinfo.name"), value=str(user), inline=True)
        embed.add_field(name=self.bot.t(lang, "userinfo.id"), value=f"`{user.id}`", inline=True)
        embed.add_field(name=self.bot.t(lang, "userinfo.nickname"), value=user.nick or self.bot.t(lang, "common.na"), inline=True)
        embed.add_field(name=self.bot.t(lang, "userinfo.joined"), value=f"<t:{int(user.joined_at.timestamp())}:D>" if user.joined_at else self.bot.t(lang, "common.na"), inline=True)
        embed.add_field(name=self.bot.t(lang, "userinfo.registered"), value=f"<t:{int(user.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name=self.bot.t(lang, "userinfo.roles"), value=", ".join(r.mention for r in user.roles[1:6]) or self.bot.t(lang, "common.none"), inline=True)
        embed.add_field(name=self.bot.t(lang, "userinfo.top_role"), value=user.top_role.mention if user.top_role.name != "@everyone" else self.bot.t(lang, "common.none"), inline=True)
        embed.add_field(name=self.bot.t(lang, "userinfo.avatar"), value=f"[{self.bot.t(lang, 'common.link')}]({user.display_avatar.url})", inline=True)
        embed.add_field(name=self.bot.t(lang, "userinfo.bot"), value=self.bot.t(lang, "common.yes") if user.bot else self.bot.t(lang, "common.no"), inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="roleinfo", description="Información de un rol")
    @app_commands.describe(role="Rol")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        embed = GuildEmbed(title=self.bot.t(lang, "roleinfo.title", role=role.name), color=role.color or config.EMBED_COLOR, guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "roleinfo.name"), value=role.name, inline=True)
        embed.add_field(name=self.bot.t(lang, "roleinfo.id"), value=f"`{role.id}`", inline=True)
        embed.add_field(name=self.bot.t(lang, "roleinfo.color"), value=str(role.color), inline=True)
        embed.add_field(name=self.bot.t(lang, "roleinfo.members"), value=str(len(role.members)), inline=True)
        embed.add_field(name=self.bot.t(lang, "roleinfo.position"), value=str(role.position), inline=True)
        embed.add_field(name=self.bot.t(lang, "roleinfo.mentionable"), value=self.bot.t(lang, "common.yes") if role.mentionable else self.bot.t(lang, "common.no"), inline=True)
        embed.add_field(name=self.bot.t(lang, "roleinfo.created"), value=f"<t:{int(role.created_at.timestamp())}:D>", inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="avatar", description="Ver avatar de un usuario")
    @app_commands.describe(user="Usuario (opcional)")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        embed = GuildEmbed(title=self.bot.t(lang, "avatar.title", user=user.display_name), url=user.display_avatar.url, color=user.color or config.EMBED_COLOR, guild=interaction.guild)
        embed.set_image(url=user.display_avatar.url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="banner", description="Ver banner de un usuario")
    @app_commands.describe(user="Usuario (opcional)")
    async def banner(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            usr = await self.bot.fetch_user(user.id)
            if usr.banner:
                embed = GuildEmbed(title=self.bot.t(lang, "banner.title", user=user.display_name), url=usr.banner.url, color=user.color or config.EMBED_COLOR, guild=interaction.guild)
                embed.set_image(url=usr.banner.url)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "banner.not_found")))
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "errors.generic")))

    @app_commands.command(name="poll", description="Crear una encuesta")
    @app_commands.describe(pregunta="Pregunta", opciones="Opciones separadas por comas (2-10)")
    async def poll(self, interaction: discord.Interaction, pregunta: str, opciones: str):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        opts = [o.strip() for o in opciones.split(",") if o.strip()]
        if len(opts) < 2 or len(opts) > 10:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "utility.poll_error_range")))
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        desc = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(opts))
        embed = GuildEmbed(title=f"📊 {pregunta}", description=desc, color=config.COLORS["blue"], guild=interaction.guild)
        msg = await interaction.followup.send(embed=embed)
        for i in range(len(opts)):
            await msg.add_reaction(emojis[i])

    @app_commands.command(name="timestamp", description="Generar timestamp de Discord")
    @app_commands.describe(ano="Año", mes="Mes (1-12)", dia="Día", hora="Hora (0-23)", minuto="Minuto (0-59)", format="Formato: t, T, d, D, f, F, R")
    async def timestamp(self, interaction: discord.Interaction, ano: int, mes: int, dia: int, hora: int = 0, minuto: int = 0, format: str = "f"):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        import datetime
        try:
            dt = datetime.datetime(ano, mes, dia, hora, minuto, tzinfo=datetime.timezone.utc)
            ts = int(dt.timestamp())
            embed = GuildEmbed(title=self.bot.t(lang, "utility.timestamp_title"), color=config.EMBED_COLOR, guild=interaction.guild)
            embed.add_field(name=self.bot.t(lang, "utility.timestamp_input"), value=f"{ano}-{mes:02d}-{dia:02d} {hora:02d}:{minuto:02d}", inline=False)
            embed.add_field(name=self.bot.t(lang, "utility.timestamp_result"), value=f"`<t:{ts}:{format}>` → <t:{ts}:{format}>", inline=False)
            await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "utility.timestamp_invalid")))

    @timestamp.autocomplete("format")
    async def ts_ac(self, interaction: discord.Interaction, current: str):
        opts = {"t": "Hora corta", "T": "Hora larga", "d": "Fecha corta", "D": "Fecha larga", "f": "Fecha y hora", "F": "Fecha y hora larga", "R": "Relativo"}
        return [app_commands.Choice(name=f"{k} — {v}", value=k) for k, v in opts.items() if current.lower() in k.lower() or current.lower() in v.lower()]

    @app_commands.command(name="remind", description="Crear un recordatorio")
    @app_commands.describe(duration="Duración (ej: 10m, 1h, 2d)", text="Texto del recordatorio")
    async def remind(self, interaction: discord.Interaction, duration: str, text: str):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        from utils.helpers import parse_duration
        secs = parse_duration(duration)
        if secs is None or secs <= 0 or secs > config.REMINDER_MAX_DURATION:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "utility.remind_invalid")))
        await self.bot.db.create_reminder(interaction.user.id, interaction.guild.id, interaction.channel.id, text, time.time() + secs)
        embed = success_embed(self.bot.t(lang, "utility.remind_created"), self.bot.t(lang, "utility.remind_created_desc", duration=parse_duration(secs, readable=True) if not isinstance(secs, int) else duration))
        await interaction.followup.send(embed=embed)

    async def check_reminders(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(15)
            try:
                rows = await self.bot.db.get_due_reminders()
                for r in rows:
                    guild = self.bot.get_guild(r["guild_id"])
                    if guild:
                        ch = guild.get_channel(r["channel_id"])
                        if ch:
                            try:
                                await ch.send(embed=info_embed("⏰ " + self.bot.t(await self.bot.get_lang(guild.id), "utility.reminder"), r["text"]), content=f"<@{r['user_id']}>")
                            except:
                                pass
                    await self.bot.db.delete_reminder(r["id"])
            except:
                pass

    @app_commands.command(name="afk", description="Establecer estado AFK")
    @app_commands.describe(reason="Razón (opcional)")
    async def afk(self, interaction: discord.Interaction, reason: str = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        reason = reason or self.bot.t(lang, "utility.afk_default_reason")
        await self.bot.db.set_afk(interaction.user.id, interaction.guild.id, reason, time.time())
        try:
            await interaction.user.edit(nick=f"[AFK] {interaction.user.display_name}", reason="AFK")
        except:
            pass
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "utility.afk_set"), self.bot.t(lang, "utility.afk_set_desc", reason=reason)))

    async def check_afk(self, message):
        if message.author.bot or not message.guild:
            return
        # Remove AFK on message
        md = await self.bot.db.get_member(message.author.id, message.guild.id)
        if md.get("afk"):
            await self.bot.db.clear_afk(message.author.id, message.guild.id)
            try:
                nick = message.author.display_name
                if nick.startswith("[AFK] "):
                    await message.author.edit(nick=nick[6:], reason="AFK removido")
            except:
                pass
            lang = await self.bot.get_lang(message.guild.id)
            await message.channel.send(embed=success_embed(self.bot.t(lang, "utility.afk_removed"), self.bot.t(lang, "utility.afk_removed_desc", user=message.author.mention)))
        # Check mentions
        if message.mentions:
            lang = await self.bot.get_lang(message.guild.id)
            for u in message.mentions:
                md2 = await self.bot.db.get_member(u.id, message.guild.id)
                if md2.get("afk"):
                    since = int(time.time() - md2["afk_since"]) if md2.get("afk_since") else 0
                    await message.channel.send(embed=info_embed(self.bot.t(lang, "utility.afk_notice"), self.bot.t(lang, "utility.afk_notice_desc", user=u.display_name, reason=md2['afk_reason'], time=f"<t:{int(md2['afk_since'])}:R>" if md2.get('afk_since') else "")))

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.check_afk(message)

    @app_commands.command(name="membercount", description="Contar miembros del servidor")
    async def membercount(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        g = interaction.guild
        online = len([m for m in g.members if m.status != discord.Status.offline])
        bots = len([m for m in g.members if m.bot])
        humans = g.member_count - bots
        embed = GuildEmbed(title=self.bot.t(lang, "utility.membercount_title", guild=g.name), color=config.EMBED_COLOR, guild=g)
        embed.add_field(name=self.bot.t(lang, "utility.membercount_total"), value=str(g.member_count), inline=True)
        embed.add_field(name=self.bot.t(lang, "utility.membercount_humans"), value=str(humans), inline=True)
        embed.add_field(name=self.bot.t(lang, "utility.membercount_bots"), value=str(bots), inline=True)
        embed.add_field(name=self.bot.t(lang, "utility.membercount_online"), value=str(online), inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="roles", description="Listar roles del servidor")
    async def roles(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        roles_list = [r.mention for r in interaction.guild.roles if r.name != "@everyone"][:30]
        if not roles_list:
            return await interaction.followup.send(embed=info_embed(self.bot.t(lang, "utility.roles_title"), self.bot.t(lang, "utility.no_roles")))
        embed = GuildEmbed(title=self.bot.t(lang, "utility.roles_title", guild=interaction.guild.name), description=", ".join(roles_list), color=config.EMBED_COLOR, guild=interaction.guild)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="channels", description="Listar canales del servidor")
    async def channels(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        cats = {}
        for ch in interaction.guild.channels:
            cat_name = ch.category.name if ch.category else self.bot.t(lang, "utility.no_category")
            if cat_name not in cats:
                cats[cat_name] = []
            cats[cat_name].append(ch.mention)
        embed = GuildEmbed(title=self.bot.t(lang, "utility.channels_title", guild=interaction.guild.name), color=config.EMBED_COLOR, guild=interaction.guild)
        for cat, chs in list(cats.items())[:10]:
            embed.add_field(name=cat, value=", ".join(chs), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="boosters", description="Listar boosters del servidor")
    async def boosters(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        boosters = interaction.guild.premium_subscribers
        if not boosters:
            return await interaction.followup.send(embed=info_embed(self.bot.t(lang, "utility.boosters_title"), self.bot.t(lang, "utility.no_boosters")))
        embed = GuildEmbed(title=self.bot.t(lang, "utility.boosters_title", guild=interaction.guild.name), description="\n".join(m.mention for m in boosters[:30]), color=config.COLORS["pink"], guild=interaction.guild)
        embed.set_footer(text=self.bot.t(lang, "utility.boosters_count", count=len(boosters)))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="servericon", description="Ver ícono del servidor")
    async def servericon(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if not interaction.guild.icon:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "utility.no_icon")))
        embed = GuildEmbed(title=self.bot.t(lang, "utility.servericon_title", guild=interaction.guild.name), url=interaction.guild.icon.url, color=config.EMBED_COLOR, guild=interaction.guild)
        embed.set_image(url=interaction.guild.icon.url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="serverbanner", description="Ver banner del servidor")
    async def serverbanner(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if not interaction.guild.banner:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "utility.no_banner")))
        embed = GuildEmbed(title=self.bot.t(lang, "utility.serverbanner_title", guild=interaction.guild.name), url=interaction.guild.banner.url, color=config.EMBED_COLOR, guild=interaction.guild)
        embed.set_image(url=interaction.guild.banner.url)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    cog = Utility(bot)
    await bot.add_cog(cog)
    asyncio.create_task(cog.check_reminders())
