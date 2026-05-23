import discord
from discord.ext import commands
from discord import app_commands
import random
import config
from utils.embeds import success_embed, error_embed, GuildEmbed
from utils.helpers import send_log


class Verification(commands.Cog):
    """✅ Sistema de verificación por botón."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setupverify", description="Configurar verificación en un canal")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Canal donde estará el mensaje",
        role="Rol a dar al verificar",
        message="Mensaje del embed (opcional)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_verify(self, interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role, message: str = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if role >= interaction.guild.me.top_role:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "verification.role_too_high")))
        await self.bot.db.update_guild(interaction.guild.id, verify_role=role.id, verify_channel=channel.id)
        embed = GuildEmbed(
            title=self.bot.t(lang, "verification.title"),
            description=message or self.bot.t(lang, "verification.default_message"),
            color=config.COLORS["green"],
            guild=interaction.guild,
        )
        view = discord.ui.View()
        btn = discord.ui.Button(emoji="✅", label=self.bot.t(lang, "verification.verify_button"), style=discord.ButtonStyle.success, custom_id="verify_btn")

        async def btn_cb(inter: discord.Interaction):
            await inter.response.defer(ephemeral=True)
            lang2 = await self.bot.get_lang(inter.guild.id)
            g = await self.bot.db.get_guild(inter.guild.id)
            rid = g.get("verify_role")
            if rid:
                role_obj = inter.guild.get_role(rid)
                if role_obj and role_obj not in inter.user.roles:
                    await inter.user.add_roles(role_obj, reason="Verificación")
                    await inter.followup.send(embed=success_embed(self.bot.t(lang2, "verification.verified_title"), self.bot.t(lang2, "verification.verified_desc")))
                else:
                    await inter.followup.send(embed=error_embed(self.bot.t(lang2, "errors.title"), self.bot.t(lang2, "verification.already_verified")))
            else:
                await inter.followup.send(embed=error_embed(self.bot.t(lang2, "errors.title"), self.bot.t(lang2, "verification.not_configured")))

        btn.callback = btn_cb
        view.add_item(btn)
        await channel.send(embed=embed, view=view)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "verification.setup_done"), self.bot.t(lang, "verification.setup_done_desc", channel=channel.mention)))

    @app_commands.command(name="verifyconfig", description="Ver configuración de verificación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_config(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        g = await self.bot.db.get_guild(interaction.guild.id)
        rid = g.get("verify_role")
        chid = g.get("verify_channel")
        embed = GuildEmbed(title=self.bot.t(lang, "verification.config_title"), color=config.EMBED_COLOR, guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "verification.verify_role"), value=f"<@&{rid}>" if rid else self.bot.t(lang, "common.not_configured"), inline=True)
        embed.add_field(name=self.bot.t(lang, "verification.verify_channel"), value=f"<#{chid}>" if chid else self.bot.t(lang, "common.not_configured"), inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Verification(bot))
