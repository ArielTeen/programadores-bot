import discord
from discord.ext import commands
from discord import app_commands
import random
import string
import asyncio
import config
from utils.embeds import PremiumEmbed, success_embed, error_embed, info_embed


class Verification(commands.Cog):
    """🛂 Sistema de verificación con botón y captcha opcional."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if cid == "verify_btn":
            await self._verify(interaction)

    async def _verify(self, interaction: discord.Interaction):
        g = await self.bot.db.get_guild(interaction.guild.id)
        if not g.get("verify_enabled", 0):
            return await interaction.response.send_message("Verificación desactivada.", ephemeral=True)
        if await self.bot.db.is_verified(interaction.user.id, interaction.guild.id):
            return await interaction.response.send_message("Ya estás verificado.", ephemeral=True)

        role_id = g.get("verify_role")
        if not role_id:
            return await interaction.response.send_message("Rol de verificación no configurado.", ephemeral=True)
        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("Rol no encontrado.", ephemeral=True)

        if g.get("verify_captcha", 0):
            captcha = "".join(random.choices(string.ascii_uppercase + string.digits, k=config.VERIFY_CAPTCHA_LENGTH))
            await self.bot.db.set_verified(interaction.user.id, interaction.guild.id, captcha)
            await interaction.response.send_message(
                embed=info_embed("🛂 Verificación", f"Escribe este código para verificar: **{captcha}**\nTienes {config.VERIFY_TIMEOUT}s."),
                ephemeral=True,
            )

            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id

            try:
                msg = await self.bot.wait_for("message", timeout=config.VERIFY_TIMEOUT, check=check)
                if msg.content.strip() == captcha:
                    await interaction.user.add_roles(role, reason="Verificado")
                    await msg.reply(embed=success_embed("✅ Verificado!", f"{role.mention} asignado."), delete_after=10)
                else:
                    await msg.reply(embed=error_embed("❌", "Código incorrecto."), delete_after=10)
            except asyncio.TimeoutError:
                await interaction.followup.send(embed=error_embed("⏰", "Tiempo agotado."), ephemeral=True)
        else:
            await interaction.user.add_roles(role, reason="Verificado")
            await self.bot.db.set_verified(interaction.user.id, interaction.guild.id)
            await interaction.response.send_message(embed=success_embed("✅ Verificado!", f"{role.mention} asignado."), ephemeral=True)

    verify = app_commands.Group(name="verify", description="Configurar verificación")

    @verify.command(name="panel", description="Enviar panel de verificación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_panel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        channel = channel or interaction.channel
        await interaction.response.defer(ephemeral=True)
        e = PremiumEmbed(title="Verificación", description="Presiona el botón para verificar tu identidad.", color=config.COLORS["green"])
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="✅ Verificar", style=discord.ButtonStyle.success, custom_id="verify_btn", emoji="✅"))
        await channel.send(embed=e, view=view)
        await interaction.followup.send(f"✅ Panel enviado a {channel.mention}", ephemeral=True)

    @verify.command(name="setup", description="Configurar verificación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="Rol a asignar", captcha="Usar captcha")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_setup(self, interaction: discord.Interaction, role: discord.Role, captcha: bool = False):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, verify_role=role.id, verify_captcha=1 if captcha else 0)
        await interaction.followup.send(embed=success_embed("🛂 Verificación configurada", f"Rol: {role.mention} | Captcha: {'✅' if captcha else '❌'}"))

    @verify.command(name="enable", description="Activar verificación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_enable(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, verify_enabled=1)
        await interaction.followup.send(embed=success_embed("✅ Verificación activada"))

    @verify.command(name="disable", description="Desactivar verificación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_disable(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, verify_enabled=0)
        await interaction.followup.send(embed=success_embed("❌ Verificación desactivada"))

    @verify.command(name="role", description="Configurar rol de verificación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="Rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_role(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, verify_role=role.id)
        await interaction.followup.send(embed=success_embed("🎭 Rol de verificación", role.mention))


async def setup(bot):
    await bot.add_cog(Verification(bot))
