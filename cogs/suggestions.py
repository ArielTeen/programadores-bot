import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.embeds import success_embed, error_embed, info_embed, GuildEmbed
from utils.helpers import send_log


class Suggestions(commands.Cog):
    """💡 Sistema de sugerencias — crear, aprobar, rechazar."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="suggest", description="Enviar una sugerencia")
    @app_commands.describe(suggestion="Tu sugerencia")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        g = await self.bot.db.get_guild(interaction.guild.id)
        ch_id = g.get("suggestion_channel")
        if not ch_id:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "suggestions.not_configured")))
        ch = interaction.guild.get_channel(ch_id)
        if not ch:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "suggestions.channel_not_found")))

        sid = await self.bot.db.create_suggestion(interaction.guild.id, interaction.user.id, suggestion)
        embed = GuildEmbed(
            title=self.bot.t(lang, "suggestions.new_suggestion", user=interaction.user.display_name),
            description=suggestion,
            color=config.COLORS["blue"],
            guild=interaction.guild,
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        view = discord.ui.View()
        up = discord.ui.Button(emoji="✅", label=self.bot.t(lang, "suggestions.approve"), custom_id=f"sug_up_{sid}", style=discord.ButtonStyle.success)
        down = discord.ui.Button(emoji="❌", label=self.bot.t(lang, "suggestions.reject"), custom_id=f"sug_down_{sid}", style=discord.ButtonStyle.danger)

        async def up_cb(inter: discord.Interaction):
            await inter.response.defer()
            sug = await self.bot.db.get_suggestion(sid, inter.guild.id)
            if not sug or sug["status"] != "pending":
                return await inter.followup.send(self.bot.t(await self.bot.get_lang(inter.guild.id), "suggestions.already_processed"), ephemeral=True)
            await self.bot.db.approve_suggestion(sid, inter.guild.id, inter.user.id)
            e = inter.message.embeds[0]
            e.color = config.COLORS["green"]
            e.add_field(name=self.bot.t(await self.bot.get_lang(inter.guild.id), "suggestions.approved_by"), value=inter.user.mention, inline=False)
            await inter.message.edit(embed=e, view=None)

        async def down_cb(inter: discord.Interaction):
            await inter.response.defer()
            sug = await self.bot.db.get_suggestion(sid, inter.guild.id)
            if not sug or sug["status"] != "pending":
                return await inter.followup.send(self.bot.t(await self.bot.get_lang(inter.guild.id), "suggestions.already_processed"), ephemeral=True)
            await self.bot.db.reject_suggestion(sid, inter.guild.id, inter.user.id)
            e = inter.message.embeds[0]
            e.color = config.COLORS["red"]
            e.add_field(name=self.bot.t(await self.bot.get_lang(inter.guild.id), "suggestions.rejected_by"), value=inter.user.mention, inline=False)
            await inter.message.edit(embed=e, view=None)

        up.callback = up_cb
        down.callback = down_cb
        view.add_item(up)
        view.add_item(down)
        msg = await ch.send(embed=embed, view=view)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "suggestions.created"), self.bot.t(lang, "suggestions.created_desc", channel=ch.mention)))

    @app_commands.command(name="suggestions", description="Listar sugerencias")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(status="Estado (pending, approved, rejected)")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def suggestions_list(self, interaction: discord.Interaction, status: str = "pending"):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        status_map = {"pending": "pending", "pendiente": "pending", "approved": "approved", "aprobada": "approved", "aprobado": "approved", "rejected": "rejected", "rechazada": "rejected", "rechazado": "rejected", "all": "all", "todas": "all", "todos": "all"}
        key = status_map.get(status.lower(), "pending")
        rows = await self.bot.db.get_suggestions(interaction.guild.id, key)
        if not rows:
            return await interaction.followup.send(embed=info_embed(self.bot.t(lang, "suggestions.title"), self.bot.t(lang, "suggestions.no_suggestions")))
        embed = GuildEmbed(title=self.bot.t(lang, "suggestions.list_title", status=key.capitalize(), guild=interaction.guild.name), color=config.EMBED_COLOR, guild=interaction.guild)
        for r in rows[:15]:
            author = interaction.guild.get_member(r["user_id"])
            embed.add_field(name=f"#{r['id']} — {author.display_name if author else r['user_id']}", value=r["suggestion"][:100], inline=False)
        await interaction.followup.send(embed=embed)

    @suggestions_list.autocomplete("status")
    async def sl_ac(self, interaction: discord.Interaction, current: str):
        opts = ["pending", "approved", "rejected", "all"]
        return [app_commands.Choice(name=o, value=o) for o in opts if current.lower() in o.lower()]


async def setup(bot):
    await bot.add_cog(Suggestions(bot))
