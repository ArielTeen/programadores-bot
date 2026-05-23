import discord
from discord.ext import commands
from discord import app_commands
import datetime
import platform
import time
import math
import asyncio
import config
from utils.embeds import PremiumEmbed, info_embed, error_embed, success_embed, send_ephemeral
from utils.paginator import ButtonPaginator


class HelpSelect(discord.ui.Select):
    def __init__(self, categories, bot):
        self.categories = categories
        self.bot = bot
        options = []
        for name, cog_name, desc in categories:
            cog = bot.get_cog(cog_name)
            cmd_count = len(list(cog.walk_app_commands())) if cog else 0
            options.append(discord.SelectOption(
                label=name,
                description=f"{cmd_count} comandos",
                value=cog_name
            ))
        super().__init__(
            placeholder="Selecciona una categoria...",
            min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction):
        cog_name = self.values[0]
        cog = self.bot.get_cog(cog_name)
        if not cog:
            return await interaction.response.send_message(
                "Categoria no encontrada.", ephemeral=True
            )
        cmds = list(cog.walk_app_commands())
        label = cog_name
        cat_desc = ""
        for name, cn, desc in self.categories:
            if cn == cog_name:
                label = name
                cat_desc = desc
                break
        embed = PremiumEmbed(
            title=label,
            description=cat_desc,
            color=config.COLORS["purple"]
        )
        if cmds:
            lines = []
            for cmd in cmds:
                lines.append(f"`/{cmd.name}`  —  {cmd.description or 'Sin descripcion'}")
            embed.add_field(
                name=f"Comandos ({len(cmds)})",
                value="\n".join(lines),
                inline=False
            )
        else:
            embed.add_field(name="Comandos", value="Ninguno", inline=False)
        embed.set_footer(text="Comunidad de Programadores")
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, categories, bot):
        super().__init__(timeout=120)
        self.add_item(HelpSelect(categories, bot))
        self.main_embed = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.main_embed:
            try:
                await self.message.edit(view=self)
            except:
                pass


class Utility(commands.Cog):
    """Utilidad e informacion del bot."""

    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}

    tools = app_commands.Group(name="tools", description="Herramientas adicionales")

    CATEGORIES = [
        ("Moderacion", "Moderation", "Gestion de sanciones, warns y proteccion del servidor"),
        ("Automod", "AutoMod", "Filtro automatico de spam, links y menciones"),
        ("Anti-Nuke", "AntiNuke", "Proteccion contra acciones destructivas masivas"),
        ("Reputacion", "Reputation", "Sistema de reputacion, ranking y recompensas"),
        ("Niveles", "Levels", "Sistema de XP, niveles y roles automaticos"),
        ("Economia", "Economy", "Monedas, tienda y economia virtual"),
        ("Tickets", "Tickets", "Sistema de soporte con tickets interactivos"),
        ("Bienvenidas", "Welcome", "Mensajes de bienvenida, despedida y autorol"),
        ("Logs", "Logs", "Registro de eventos y auditoria del servidor"),
        ("Utilidad", "Utility", "Informacion, herramientas y comandos de ayuda"),
        ("Diversion", "Fun", "Comandos entretenidos y minijuegos"),
        ("Sugerencias", "Suggestions", "Sistema de sugerencias con votacion"),
        ("Reportes", "Reports", "Sistema de reportes de usuarios"),
        ("Verificacion", "Verification", "Sistema de verificacion con botones"),
        ("Reaction Roles", "ReactionRoles", "Roles por reacciones y botones"),
        ("Giveaways", "Giveaways", "Sorteos y premios automaticos"),
        ("Configuracion", "ConfigCog", "Ajustes generales del bot en el servidor"),
        ("Panel", "Panel", "Panel de control interactivo del servidor"),
    ]

    # ─── HELP ───────────────────────────────────────────────────────────

    @app_commands.command(name="help", description="Explorar todos los comandos del bot")
    @app_commands.describe(comando="Comando especifico para ver detalles")
    async def help(self, interaction: discord.Interaction, comando: str = None):
        await interaction.response.defer(ephemeral=True)

        if comando:
            for cog in self.bot.cogs.values():
                for cmd in cog.walk_app_commands():
                    if cmd.name == comando:
                        e = PremiumEmbed(
                            title=f"/{cmd.name}",
                            description=cmd.description or "Sin descripcion",
                            color=config.COLORS["purple"]
                        )
                        e.set_footer(text="Comunidad de Programadores")
                        await send_ephemeral(interaction, embed=e)
                        return
            return await send_ephemeral(
                interaction,
                embed=error_embed("Comando no encontrado", f"No existe el comando `/{comando}`.")
            )

        embed = PremiumEmbed(
            title="Centro de Comandos",
            description=(
                f"Selecciona una categoria del menu desplegable para ver sus comandos.\n"
                f"Usa `/help <comando>` para ver detalles de un comando especifico."
            ),
            color=config.COLORS["purple"]
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="Comunidad de Programadores")

        total_cmds = sum(
            len(list(cog.walk_app_commands()))
            for cog in self.bot.cogs.values()
        )
        embed.add_field(
            name="Resumen",
            value=(
                f"**{len(self.bot.cogs)}** modulos  ·  **{total_cmds}** comandos\n"
                f"[Dashboard]({config.DASHBOARD_URL})"
            ),
            inline=False
        )

        view = HelpView(self.CATEGORIES, self.bot)
        view.main_embed = embed
        await interaction.followup.send(embed=embed, view=view)
        view.message = await interaction.original_response()

    # ─── PING ──────────────────────────────────────────────────────────

    @app_commands.command(name="ping", description="Ver latencia del bot")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        start = time.time()
        await self.bot.db.execute("SELECT 1")
        db_ms = (time.time() - start) * 1000
        e = PremiumEmbed(title="Ping", color=config.COLORS["green"])
        e.add_field(name="API", value=f"**{round(self.bot.latency * 1000)}ms**", inline=True)
        e.add_field(name="Base de datos", value=f"**{db_ms:.1f}ms**", inline=True)
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e)

    # ─── BOTINFO ──────────────────────────────────────────────────────

    @app_commands.command(name="botinfo", description="Informacion del bot")
    async def botinfo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uptime = datetime.datetime.utcnow() - (self.bot.uptime or datetime.datetime.utcnow())
        h, rem = divmod(int(uptime.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        e = PremiumEmbed(title=f"{self.bot.user.name}  ·  Informacion", color=config.EMBED_COLOR)
        e.set_thumbnail(url=self.bot.user.display_avatar.url)
        e.add_field(name="Version", value="**3.0.0**", inline=True)
        e.add_field(name="Python", value=f"**{platform.python_version()}**", inline=True)
        e.add_field(name="discord.py", value=f"**{discord.__version__}**", inline=True)
        e.add_field(name="Tiempo activo", value=f"**{h}h {m}m {s}s**", inline=True)
        e.add_field(name="Servidores", value=f"**{len(self.bot.guilds)}**", inline=True)
        e.add_field(name="Usuarios", value=f"**{len(self.bot.users)}**", inline=True)
        e.add_field(name="Latencia", value=f"**{round(self.bot.latency * 1000)}ms**", inline=True)
        e.add_field(name="Modulos", value=f"**{len(self.bot.loaded_cogs)}**", inline=True)
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e)

    # ─── SERVERINFO ───────────────────────────────────────────────────

    @app_commands.command(name="serverinfo", description="Informacion del servidor")
    async def serverinfo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        g = interaction.guild
        e = PremiumEmbed(title=g.name, color=g.me.color or config.EMBED_COLOR)
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        e.add_field(name="Propietario", value=g.owner.mention if g.owner else "N/A", inline=True)
        e.add_field(name="ID", value=f"**{g.id}**", inline=True)
        e.add_field(name="Creacion", value=f"<t:{int(g.created_at.timestamp())}:D>", inline=True)
        e.add_field(name="Miembros", value=f"**{g.member_count}**", inline=True)
        e.add_field(name="Canales", value=f"**{len(g.channels)}**", inline=True)
        e.add_field(name="Roles", value=f"**{len(g.roles)}**", inline=True)
        e.add_field(name="Boost", value=f"Nivel **{g.premium_tier}** ({g.premium_subscription_count})", inline=True)
        e.add_field(name="Verificacion", value=str(g.verification_level).capitalize(), inline=True)
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e)

    # ─── USERINFO ─────────────────────────────────────────────────────

    @app_commands.command(name="userinfo", description="Informacion de un usuario")
    @app_commands.describe(user="Usuario")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(user.id, interaction.guild.id)
        e = PremiumEmbed(title=user.display_name, color=user.color or config.EMBED_COLOR)
        e.set_thumbnail(url=user.display_avatar.url)
        e.add_field(name="ID", value=f"**{user.id}**", inline=True)
        e.add_field(name="Tag", value=f"**{user}**", inline=True)
        e.add_field(name="Bot", value="**Si**" if user.bot else "**No**", inline=True)
        e.add_field(name="Creacion", value=f"<t:{int(user.created_at.timestamp())}:D>", inline=True)
        e.add_field(name="Ingreso", value=f"<t:{int(user.joined_at.timestamp())}:D>" if user.joined_at else "N/A", inline=True)
        e.add_field(name="Nivel", value=f"**{md.get('level', 0)}**", inline=True)
        e.add_field(name="Reputacion", value=f"**{md.get('reputation', 0)}**", inline=True)
        e.add_field(name="Balance", value=f"**{md.get('balance', 0):,}**", inline=True)
        roles = [r.mention for r in user.roles if r != interaction.guild.default_role]
        if roles:
            e.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles[:5]) + ("..." if len(roles) > 5 else ""), inline=False)
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e)

    # ─── AVATAR ────────────────────────────────────────────────────────

    @app_commands.command(name="avatar", description="Ver avatar de un usuario")
    @app_commands.describe(user="Usuario")
    async def avatar(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        await interaction.response.defer(ephemeral=True)
        e = PremiumEmbed(title=f"Avatar de {user.display_name}", color=config.EMBED_COLOR)
        e.set_image(url=user.display_avatar.url)
        v = discord.ui.View()
        v.add_item(discord.ui.Button(label="Descargar", url=user.display_avatar.url.replace("size=", "size=4096")))
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e, view=v)

    # ─── BANNER ────────────────────────────────────────────────────────

    @app_commands.command(name="banner", description="Ver banner de un usuario")
    @app_commands.describe(user="Usuario")
    async def banner(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        await interaction.response.defer(ephemeral=True)
        u = await self.bot.fetch_user(user.id)
        if u.banner:
            e = PremiumEmbed(title=f"Banner de {u.display_name}", color=config.EMBED_COLOR)
            e.set_image(url=u.banner.url)
            e.set_footer(text="Comunidad de Programadores")
            await send_ephemeral(interaction, embed=e)
        else:
            await send_ephemeral(interaction, embed=info_embed("Sin banner", "Este usuario no tiene banner."))

    # ─── ROLEINFO ──────────────────────────────────────────────────────

    @app_commands.command(name="roleinfo", description="Informacion de un rol")
    @app_commands.describe(rol="Rol")
    async def roleinfo(self, interaction: discord.Interaction, rol: discord.Role):
        await interaction.response.defer(ephemeral=True)
        e = PremiumEmbed(title=rol.name, color=rol.color or config.EMBED_COLOR)
        e.add_field(name="ID", value=f"**{rol.id}**", inline=True)
        e.add_field(name="Color", value=str(rol.color), inline=True)
        e.add_field(name="Miembros", value=f"**{len(rol.members)}**", inline=True)
        e.add_field(name="Creacion", value=f"<t:{int(rol.created_at.timestamp())}:D>", inline=True)
        e.add_field(name="Mencionable", value="**Si**" if rol.mentionable else "**No**", inline=True)
        e.add_field(name="Separado", value="**Si**" if rol.hoist else "**No**", inline=True)
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e)

    # ─── CHANNELINFO ──────────────────────────────────────────────────

    @app_commands.command(name="channelinfo", description="Informacion de un canal")
    @app_commands.describe(canal="Canal")
    async def channelinfo(self, interaction: discord.Interaction, canal: discord.TextChannel = None):
        canal = canal or interaction.channel
        await interaction.response.defer(ephemeral=True)
        e = PremiumEmbed(title=f"#{canal.name}", color=config.EMBED_COLOR)
        e.add_field(name="ID", value=f"**{canal.id}**", inline=True)
        e.add_field(name="Tipo", value=str(canal.type).capitalize(), inline=True)
        e.add_field(name="Creacion", value=f"<t:{int(canal.created_at.timestamp())}:D>", inline=True)
        if hasattr(canal, "slowmode_delay"):
            e.add_field(name="Slowmode", value=f"**{canal.slowmode_delay}s**" if canal.slowmode_delay else "**No**", inline=True)
        if hasattr(canal, "category") and canal.category:
            e.add_field(name="Categoria", value=canal.category.name, inline=True)
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e)

    # ─── MEMBERCOUNT ──────────────────────────────────────────────────

    @app_commands.command(name="membercount", description="Contar miembros del servidor")
    async def membercount(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        g = interaction.guild
        humans = sum(1 for m in g.members if not m.bot)
        bots = g.member_count - humans
        online = sum(1 for m in g.members if m.status != discord.Status.offline)
        e = PremiumEmbed(title=f"Miembros de {g.name}", color=config.EMBED_COLOR)
        e.add_field(name="Humanos", value=f"**{humans}**", inline=True)
        e.add_field(name="Bots", value=f"**{bots}**", inline=True)
        e.add_field(name="En linea", value=f"**{online}**", inline=True)
        e.add_field(name="Total", value=f"**{g.member_count}**", inline=True)
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e)

    # ─── SERVER ICON ──────────────────────────────────────────────────

    @app_commands.command(name="servericon", description="Ver icono del servidor")
    async def servericon(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild.icon:
            e = PremiumEmbed(title=f"Icono de {interaction.guild.name}", color=config.EMBED_COLOR)
            e.set_image(url=interaction.guild.icon.url)
            e.set_footer(text="Comunidad de Programadores")
            await send_ephemeral(interaction, embed=e)
        else:
            await send_ephemeral(interaction, embed=info_embed("Sin icono", "Este servidor no tiene icono."))

    # ─── SERVER BANNER ────────────────────────────────────────────────

    @app_commands.command(name="serverbanner", description="Ver banner del servidor")
    async def serverbanner(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.guild.banner:
            e = PremiumEmbed(title=f"Banner de {interaction.guild.name}", color=config.EMBED_COLOR)
            e.set_image(url=interaction.guild.banner.url)
            e.set_footer(text="Comunidad de Programadores")
            await send_ephemeral(interaction, embed=e)
        else:
            await send_ephemeral(interaction, embed=info_embed("Sin banner", "Este servidor no tiene banner."))

    # ─── POLL ─────────────────────────────────────────────────────────

    @tools.command(name="poll", description="Crear una encuesta")
    @app_commands.describe(pregunta="Pregunta", opciones="Opciones separadas por |")
    async def poll(self, interaction: discord.Interaction, pregunta: str, opciones: str = "Si | No"):
        await interaction.response.defer(ephemeral=False)
        opts = [o.strip() for o in opciones.split("|")]
        if len(opts) < 2 or len(opts) > 10:
            return await send_ephemeral(interaction, embed=error_embed("Error", "Entre 2 y 10 opciones separadas por |"))
        numbers = ["1\u20e3", "2\u20e3", "3\u20e3", "4\u20e3", "5\u20e3", "6\u20e3", "7\u20e3", "8\u20e3", "9\u20e3", "\U0001f51f"]
        desc = "\n".join(f"{numbers[i]} {o}" for i, o in enumerate(opts))
        e = PremiumEmbed(title=pregunta, description=desc, color=config.EMBED_COLOR)
        e.set_footer(text=f"Por {interaction.user.display_name}")
        msg = await interaction.followup.send(embed=e)
        for i in range(len(opts)):
            await msg.add_reaction(numbers[i])

    # ─── AFK ──────────────────────────────────────────────────────────

    @tools.command(name="afk", description="Establecer estado AFK")
    @app_commands.describe(mensaje="Mensaje AFK")
    async def afk(self, interaction: discord.Interaction, mensaje: str = "AFK"):
        await interaction.response.defer(ephemeral=True)
        self.afk_users[interaction.user.id] = {"message": mensaje, "since": time.time()}
        await send_ephemeral(interaction, embed=success_embed("AFK activado", mensaje))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.author.id in self.afk_users:
            del self.afk_users[message.author.id]
            await message.channel.send(embed=success_embed("Bienvenido de vuelta", f"{message.author.mention} ya no estas AFK."), delete_after=5)
        for user in message.mentions:
            if user.id in self.afk_users:
                data = self.afk_users[user.id]
                dur = int(time.time() - data["since"])
                await message.channel.send(embed=info_embed("AFK", f"{user.mention} esta AFK: {data['message']} ({dur}s)"), delete_after=10)

    # ─── REMIND ───────────────────────────────────────────────────────

    @tools.command(name="remind", description="Crear un recordatorio")
    @app_commands.describe(tiempo="Tiempo (ej: 10m, 1h, 1d)", mensaje="Mensaje")
    async def remind(self, interaction: discord.Interaction, tiempo: str, mensaje: str):
        await interaction.response.defer(ephemeral=True)
        from utils.helpers import parse_duration
        secs = parse_duration(tiempo)
        if secs <= 0:
            return await send_ephemeral(interaction, embed=error_embed("Error", "Tiempo invalido."))
        if secs > 86400 * 7:
            return await send_ephemeral(interaction, embed=error_embed("Error", "Maximo 7 dias."))
        await send_ephemeral(interaction, embed=success_embed("Recordatorio", f"Te recordare en **{tiempo}**: {mensaje}"))
        await asyncio.sleep(secs)
        try:
            await interaction.user.send(embed=info_embed("Recordatorio", mensaje))
        except:
            await interaction.channel.send(f"{interaction.user.mention} Recordatorio: {mensaje}")

    # ─── TIMESTAMP ────────────────────────────────────────────────────

    @tools.command(name="timestamp", description="Convertir fecha a timestamp de Discord")
    @app_commands.describe(fecha="Formato: YYYY-MM-DD HH:MM")
    async def timestamp(self, interaction: discord.Interaction, fecha: str):
        await interaction.response.defer(ephemeral=True)
        import dateutil.parser
        try:
            dt = dateutil.parser.parse(fecha)
            ts = int(dt.timestamp())
            e = info_embed("Timestamp", f"`{ts}`\n<t:{ts}:F>\n<t:{ts}:R>\n`<t:{ts}:F>`")
            await send_ephemeral(interaction, embed=e)
        except:
            await send_ephemeral(interaction, embed=error_embed("Error", "Formato invalido. Usa: 2024-12-25 15:00"))

    # ─── SHORTEN ──────────────────────────────────────────────────────

    @tools.command(name="shorten", description="Acortar URL")
    @app_commands.describe(url="URL")
    async def shorten(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(ephemeral=True)
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://tinyurl.com/api-create.php?url={url}") as r:
                    short = await r.text()
                    await send_ephemeral(interaction, embed=success_embed("URL acortada", short.strip()))
        except:
            await send_ephemeral(interaction, embed=error_embed("Error", "Error al acortar."))

    # ─── QR ───────────────────────────────────────────────────────────

    @tools.command(name="qr", description="Generar codigo QR")
    @app_commands.describe(texto="Texto o URL")
    async def qr(self, interaction: discord.Interaction, texto: str):
        await interaction.response.defer(ephemeral=True)
        e = PremiumEmbed(title="QR Code", color=config.EMBED_COLOR)
        e.set_image(url=f"https://api.qrserver.com/v1/create-qr-code/?size=256x256&data={texto}")
        e.set_footer(text="Comunidad de Programadores")
        await send_ephemeral(interaction, embed=e)

    # ─── COLOR ────────────────────────────────────────────────────────

    @tools.command(name="color", description="Ver un color")
    @app_commands.describe(hex_color="Color en hex (ej: #5865F2)")
    async def color(self, interaction: discord.Interaction, hex_color: str):
        await interaction.response.defer(ephemeral=True)
        hex_color = hex_color.lstrip("#")
        try:
            r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            e = PremiumEmbed(title=f"#{hex_color.upper()}", color=int(hex_color, 16))
            e.add_field(name="RGB", value=f"({r}, {g}, {b})", inline=True)
            e.add_field(name="HEX", value=f"#{hex_color.upper()}", inline=True)
            e.set_image(url=f"https://singlecolorimage.com/get/{hex_color}/256x256")
            e.set_footer(text="Comunidad de Programadores")
            await send_ephemeral(interaction, embed=e)
        except:
            await send_ephemeral(interaction, embed=error_embed("Error", "Color invalido. Usa: #5865F2"))

    # ─── DEFINE ───────────────────────────────────────────────────────

    @tools.command(name="define", description="Definir una palabra")
    @app_commands.describe(palabra="Palabra")
    async def define(self, interaction: discord.Interaction, palabra: str):
        await interaction.response.defer(ephemeral=True)
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{palabra}") as r:
                    if r.status == 200:
                        data = await r.json()
                        meanings = data[0].get("meanings", [])
                        if meanings:
                            defs = meanings[0].get("definitions", [])
                            if defs:
                                e = info_embed(palabra.capitalize(), defs[0].get("definition", "N/A"))
                                await send_ephemeral(interaction, embed=e)
                                return
            await send_ephemeral(interaction, embed=error_embed("Error", "Palabra no encontrada."))
        except:
            await send_ephemeral(interaction, embed=error_embed("Error", "Error en la consulta."))


async def setup(bot):
    await bot.add_cog(Utility(bot))
