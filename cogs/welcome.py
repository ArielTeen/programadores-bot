import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.embeds import GuildEmbed, success_embed, error_embed, info_embed
from utils.helpers import send_log


class Welcome(commands.Cog):
    """👋 Bienvenidas, despedidas y autorol."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        g = await self.bot.db.get_guild(guild.id)
        lang = await self.bot.get_lang(guild.id)

        # Autorol
        ar_ids = g.get("auto_roles", [])
        if ar_ids:
            for rid in ar_ids:
                role = guild.get_role(rid)
                if role and role < guild.me.top_role:
                    try:
                        await member.add_roles(role, reason="Autorol")
                    except:
                        pass

        # Bienvenida
        wc_id = g.get("welcome_channel")
        if wc_id:
            wc = guild.get_channel(wc_id)
            if wc:
                msg = g.get("welcome_message", self.bot.t(lang, "welcome.default_welcome", user=member.mention, guild=guild.name))
                msg = msg.replace("{user}", member.mention).replace("{guild}", guild.name).replace("{members}", str(len(guild.members)))
                embed = GuildEmbed(
                    title=self.bot.t(lang, "welcome.welcome_title"),
                    description=msg,
                    color=config.COLORS["green"],
                    guild=guild,
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                try:
                    await wc.send(embed=embed)
                except:
                    pass

        # Bienvenida DM
        wdm = g.get("welcome_dm", 0)
        if wdm:
            try:
                e = GuildEmbed(
                    title=self.bot.t(lang, "welcome.dm_title", guild=guild.name),
                    description=self.bot.t(lang, "welcome.dm_desc", guild=guild.name),
                    color=config.COLORS["green"],
                    guild=guild,
                )
                await member.send(embed=e)
            except:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        g = await self.bot.db.get_guild(guild.id)
        lang = await self.bot.get_lang(guild.id)
        gc_id = g.get("goodbye_channel")
        if not gc_id:
            return
        gc = guild.get_channel(gc_id)
        if not gc:
            return
        msg = g.get("goodbye_message", self.bot.t(lang, "welcome.default_goodbye", user=member.name, guild=guild.name))
        msg = msg.replace("{user}", member.name).replace("{guild}", guild.name)
        embed = GuildEmbed(
            title=self.bot.t(lang, "welcome.goodbye_title"),
            description=msg,
            color=config.COLORS["red"],
            guild=guild,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await gc.send(embed=embed)
        except:
            pass

    welcome = app_commands.Group(name="welcome", description="Configurar bienvenidas")

    @welcome.command(name="channel", description="Establecer canal de bienvenidas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.update_guild(interaction.guild.id, welcome_channel=channel.id)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "welcome.channel_set"), self.bot.t(lang, "welcome.channel_set_desc", channel=channel.mention)))

    @welcome.command(name="message", description="Establecer mensaje de bienvenida")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message="Mensaje ({user}, {guild}, {members})")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.update_guild(interaction.guild.id, welcome_message=message)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "welcome.message_set"), self.bot.t(lang, "welcome.message_set_desc")))

    @welcome.command(name="dm", description="Activar/desactivar DM de bienvenida")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(enabled="True o False")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_dm(self, interaction: discord.Interaction, enabled: bool):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.update_guild(interaction.guild.id, welcome_dm=1 if enabled else 0)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "welcome.dm_set"), self.bot.t(lang, "welcome.dm_set_desc", state=self.bot.t(lang, "common.yes") if enabled else self.bot.t(lang, "common.no"))))

    goodbye = app_commands.Group(name="goodbye", description="Configurar despedidas")

    @goodbye.command(name="channel", description="Establecer canal de despedidas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal")
    @app_commands.checks.has_permissions(administrator=True)
    async def goodbye_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.update_guild(interaction.guild.id, goodbye_channel=channel.id)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "welcome.goodbye_channel_set"), self.bot.t(lang, "welcome.goodbye_channel_set_desc", channel=channel.mention)))

    @goodbye.command(name="message", description="Establecer mensaje de despedida")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message="Mensaje ({user}, {guild})")
    @app_commands.checks.has_permissions(administrator=True)
    async def goodbye_message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.update_guild(interaction.guild.id, goodbye_message=message)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "welcome.goodbye_message_set"), self.bot.t(lang, "welcome.goodbye_message_set_desc")))

    autorol = app_commands.Group(name="autorol", description="Configurar autorol")

    @autorol.command(name="add", description="Añadir rol al autorol")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="Rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorol_add(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if role >= interaction.guild.me.top_role:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "welcome.role_too_high")))
        g = await self.bot.db.get_guild(interaction.guild.id)
        ar = g.get("auto_roles", []) or []
        if role.id in ar:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "welcome.role_already_set")))
        ar.append(role.id)
        await self.bot.db.update_guild(interaction.guild.id, auto_roles=ar)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "welcome.autorol_added"), self.bot.t(lang, "welcome.autorol_added_desc", role=role.mention)))

    @autorol.command(name="remove", description="Quitar rol del autorol")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="Rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorol_remove(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        g = await self.bot.db.get_guild(interaction.guild.id)
        ar = g.get("auto_roles", []) or []
        if role.id not in ar:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "welcome.role_not_in_autorol")))
        ar.remove(role.id)
        await self.bot.db.update_guild(interaction.guild.id, auto_roles=ar)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "welcome.autorol_removed"), self.bot.t(lang, "welcome.autorol_removed_desc", role=role.mention)))

    @autorol.command(name="list", description="Listar autoroles")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def autorol_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        g = await self.bot.db.get_guild(interaction.guild.id)
        ar = g.get("auto_roles", []) or []
        if not ar:
            return await interaction.followup.send(embed=info_embed(self.bot.t(lang, "welcome.autorol_title"), self.bot.t(lang, "welcome.no_autorol")))
        lines = []
        for rid in ar:
            role = interaction.guild.get_role(rid)
            lines.append(role.mention if role else f"`{rid}`")
        embed = GuildEmbed(title=self.bot.t(lang, "welcome.autorol_title"), color=config.EMBED_COLOR, guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "welcome.autorol_roles"), value="\n".join(lines), inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
