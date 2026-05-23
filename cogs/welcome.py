import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.embeds import PremiumEmbed, success_embed, info_embed
from utils.helpers import send_log


class Welcome(commands.Cog):
    """👋 Bienvenidas, despedidas y autoroles."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        g = await self.bot.db.get_guild(member.guild.id)
        if not g.get("welcome_enabled", 1):
            return

        # Welcome message
        ch_id = g.get("welcome_channel")
        if ch_id:
            ch = member.guild.get_channel(ch_id)
            if ch:
                msg = g.get("welcome_message", "¡Bienvenido {user} a **{guild}**!").format(
                    user=member.mention, guild=member.guild.name, name=member.name
                )
                embed = PremiumEmbed(
                    title=f"👋 ¡Bienvenido a {member.guild.name}!",
                    description=msg,
                    color=config.COLORS["green"],
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="Miembros", value=str(member.guild.member_count), inline=True)
                embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
                try:
                    await ch.send(embed=embed)
                except:
                    pass

        # Autorole
        autoroles = await self.bot.db.get_automod_whitelist(member.guild.id, "autorole")
        for rid in autoroles:
            role = member.guild.get_role(rid)
            if role:
                try:
                    await member.add_roles(role, reason="Autorol")
                except:
                    pass

        # Log
        log_embed = PremiumEmbed(title="Miembro Unido", color=config.COLORS["green"])
        log_embed.add_field(name="Usuario", value=member.mention, inline=True)
        log_embed.add_field(name="ID", value=str(member.id), inline=True)
        log_embed.add_field(name="Cuenta creada", value=f"<t:{int(member.created_at.timestamp())}:R>f", inline=False)
        await send_log(self.bot, member.guild.id, "members", log_embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        g = await self.bot.db.get_guild(member.guild.id)
        if not g.get("goodbye_enabled", 1):
            return
        ch_id = g.get("goodbye_channel") or g.get("welcome_channel")
        if ch_id:
            ch = member.guild.get_channel(ch_id)
            if ch:
                msg = g.get("goodbye_message", "{user} ha abandonado el servidor.").format(
                    user=member.name, guild=member.guild.name, name=member.name
                )
                embed = PremiumEmbed(
                    title=f"👋 {member.name} ha salido",
                    description=msg,
                    color=config.COLORS["orange"],
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(name="Miembros ahora", value=str(member.guild.member_count))
                try:
                    await ch.send(embed=embed)
                except:
                    pass

        log_embed = PremiumEmbed(title="Miembro Salió", color=config.COLORS["orange"])
        log_embed.add_field(name="Usuario", value=str(member), inline=True)
        log_embed.add_field(name="ID", value=str(member.id), inline=True)
        await send_log(self.bot, member.guild.id, "members", log_embed)

    @commands.Cog.listener()
    async def on_member_boost(self, member: discord.Member):
        log_embed = PremiumEmbed(title="Boost!", description=f"{member.mention} boosteó el servidor!f", color=config.COLORS["purple"])
        await send_log(self.bot, member.guild.id, "members", log_embed)

    # ── Comandos ─────────────────────────────────────────────────────────────
    welcome = app_commands.Group(name="welcome", description="Configurar bienvenidas")

    @welcome.command(name="setup", description="Configurar bienvenidas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal", message="Mensaje ({user}, {guild}, {name})")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_setup(self, interaction, channel: discord.TextChannel, message: str = None):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, welcome_channel=channel.id)
        if message:
            await self.bot.db.update_guild(interaction.guild.id, welcome_message=message)
        await interaction.followup.send(embed=success_embed("👋 Bienvenidas configuradas", channel.mention))

    @welcome.command(name="enable", description="Activar bienvenidas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_enable(self, interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, welcome_enabled=1)
        await interaction.followup.send(embed=success_embed("✅ Bienvenidas activadas"))

    @welcome.command(name="disable", description="Desactivar bienvenidas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_disable(self, interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, welcome_enabled=0)
        await interaction.followup.send(embed=success_embed("❌ Bienvenidas desactivadas"))

    @welcome.command(name="test", description="Probar mensaje de bienvenida")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_test(self, interaction):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        msg = g.get("welcome_message", "¡Bienvenido {user} a **{guild}**!").format(
            user=interaction.user.mention, guild=interaction.guild.name, name=interaction.user.name
        )
        embed = PremiumEmbed(title="Bienvenida (test)", description=msg, color=config.COLORS["green"])
        await interaction.followup.send(embed=embed)

    @welcome.command(name="channel", description="Cambiar canal de bienvenidas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal")
    @app_commands.checks.has_permissions(administrator=True)
    async def welcome_channel(self, interaction, channel: discord.TextChannel):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, welcome_channel=channel.id)
        await interaction.followup.send(embed=success_embed("📝 Canal de bienvenidas", channel.mention))

    goodbye = app_commands.Group(name="goodbye", description="Configurar despedidas")

    @goodbye.command(name="enable", description="Activar despedidas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def goodbye_enable(self, interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, goodbye_enabled=1)
        await interaction.followup.send(embed=success_embed("✅ Despedidas activadas"))

    @goodbye.command(name="disable", description="Desactivar despedidas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def goodbye_disable(self, interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, goodbye_enabled=0)
        await interaction.followup.send(embed=success_embed("❌ Despedidas desactivadas"))

    @goodbye.command(name="test", description="Probar mensaje de despedida")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def goodbye_test(self, interaction):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        msg = g.get("goodbye_message", "{user} ha abandonado el servidor.").format(
            user=interaction.user.name, guild=interaction.guild.name
        )
        embed = PremiumEmbed(title="Despedida (test)", description=msg, color=config.COLORS["orange"])
        await interaction.followup.send(embed=embed)

    autorole = app_commands.Group(name="autorole", description="Roles automáticos")

    @autorole.command(name="add", description="Añadir autorol")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="Rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_add(self, interaction, role: discord.Role):
        await interaction.response.defer()
        await self.bot.db.add_automod_whitelist(interaction.guild.id, role.id, "autorole")
        await interaction.followup.send(embed=success_embed("🎭 Autorol añadido", role.mention))

    @autorole.command(name="remove", description="Quitar autorol")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="Rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_remove(self, interaction, role: discord.Role):
        await interaction.response.defer()
        await self.bot.db.remove_automod_whitelist(interaction.guild.id, role.id)
        await interaction.followup.send(embed=success_embed("🎭 Autorol quitado", role.mention))

    @autorole.command(name="list", description="Listar autoroles")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def autorole_list(self, interaction):
        await interaction.response.defer()
        roles = await self.bot.db.get_automod_whitelist(interaction.guild.id, "autorole")
        if not roles:
            return await interaction.followup.send(embed=info_embed("📋", "Sin autoroles."))
        lines = [f"• {interaction.guild.get_role(rid).mention}" for rid in roles if interaction.guild.get_role(rid)]
        embed = info_embed("🎭 Autoroles", "\n".join(lines))
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
