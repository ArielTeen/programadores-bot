import discord
from discord.ext import commands
from discord import app_commands
import time
import asyncio
import config
from utils.embeds import GuildEmbed, success_embed, error_embed, info_embed
from utils.helpers import send_log


class TicketSelect(discord.ui.Select):
    def __init__(self, bot, lang):
        self.bot = bot
        self.lang = lang
        opts = [
            discord.SelectOption(label=self.bot.t(lang, "tickets.general"), emoji="❓", value="general", description=self.bot.t(lang, "tickets.general_desc")),
            discord.SelectOption(label=self.bot.t(lang, "tickets.support"), emoji="🛠️", value="support", description=self.bot.t(lang, "tickets.support_desc")),
            discord.SelectOption(label=self.bot.t(lang, "tickets.billing"), emoji="💰", value="billing", description=self.bot.t(lang, "tickets.billing_desc")),
            discord.SelectOption(label=self.bot.t(lang, "tickets.report"), emoji="🚨", value="report", description=self.bot.t(lang, "tickets.report_desc")),
            discord.SelectOption(label=self.bot.t(lang, "tickets.other"), emoji="📝", value="other", description=self.bot.t(lang, "tickets.other_desc")),
        ]
        super().__init__(placeholder=self.bot.t(lang, "tickets.placeholder"), max_values=1, options=opts)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        g = await self.bot.db.get_guild(interaction.guild.id)
        cat_id = g.get("ticket_category")
        category = None
        if cat_id:
            category = interaction.guild.get_channel(cat_id)
        name = f"ticket-{interaction.user.name.lower().replace(' ', '-')[:20]}"
        existing = discord.utils.get(interaction.guild.text_channels, name=name)
        if existing:
            lang2 = await self.bot.get_lang(interaction.guild.id)
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang2, "errors.title"), self.bot.t(lang2, "tickets.already_open", channel=existing.mention)))
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_permissions=True),
        }
        sup_role_id = g.get("ticket_support_role")
        if sup_role_id:
            sup_role = interaction.guild.get_role(sup_role_id)
            if sup_role:
                overwrites[sup_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        try:
            channel = await interaction.guild.create_text_channel(name=name, category=category, overwrites=overwrites, reason=f"Ticket de {interaction.user}")
            lang2 = await self.bot.get_lang(interaction.guild.id)
            e = GuildEmbed(title=self.bot.t(lang2, "tickets.ticket_created"), description=self.bot.t(lang2, "tickets.ticket_desc", user=interaction.user.mention, reason=interaction.data["values"][0] if interaction.data.get("values") else "general"), color=config.COLORS["green"], guild=interaction.guild)
            close_btn = discord.ui.Button(emoji="🔒", label=self.bot.t(lang2, "tickets.close"), style=discord.ButtonStyle.danger, custom_id="ticket_close")
            claim_btn = discord.ui.Button(emoji="👋", label=self.bot.t(lang2, "tickets.claim"), style=discord.ButtonStyle.primary, custom_id="ticket_claim")

            async def close_cb(inter: discord.Interaction):
                await inter.response.defer()
                lang3 = await self.bot.get_lang(inter.guild.id)
                await inter.channel.delete(reason=f"Ticket cerrado por {inter.user}")
                try:
                    await inter.user.send(embed=info_embed(self.bot.t(lang3, "tickets.closed_title"), self.bot.t(lang3, "tickets.closed_desc", channel=inter.channel.name)))
                except:
                    pass

            async def claim_cb(inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                lang4 = await self.bot.get_lang(inter.guild.id)
                e2 = inter.message.embeds[0]
                e2.add_field(name=self.bot.t(lang4, "tickets.claimed_by"), value=inter.user.mention, inline=False)
                await inter.message.edit(embed=e2)
                await inter.followup.send(self.bot.t(lang4, "tickets.claimed_desc", user=inter.user.mention))

            close_btn.callback = close_cb
            claim_btn.callback = claim_cb
            view = discord.ui.View()
            view.add_item(close_btn)
            view.add_item(claim_btn)
            await channel.send(embed=e, view=view)
            await interaction.followup.send(embed=success_embed(self.bot.t(lang2, "tickets.created"), self.bot.t(lang2, "tickets.created_desc", channel=channel.mention)))
        except Exception as ex:
            lang2 = await self.bot.get_lang(interaction.guild.id)
            await interaction.followup.send(embed=error_embed(self.bot.t(lang2, "errors.title"), str(ex)))


class Tickets(commands.Cog):
    """🎫 Sistema de tickets con selección de categoría."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket", description="Crear un ticket")
    async def ticket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        g = await self.bot.db.get_guild(interaction.guild.id)
        cat_id = g.get("ticket_category")
        category = None
        if cat_id:
            category = interaction.guild.get_channel(cat_id)
        name = f"ticket-{interaction.user.name.lower().replace(' ', '-')[:20]}"
        existing = discord.utils.get(interaction.guild.text_channels, name=name)
        if existing:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "tickets.already_open", channel=existing.mention)))
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_permissions=True),
        }
        sup_role_id = g.get("ticket_support_role")
        if sup_role_id:
            sup_role = interaction.guild.get_role(sup_role_id)
            if sup_role:
                overwrites[sup_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        try:
            channel = await interaction.guild.create_text_channel(name=name, category=category, overwrites=overwrites, reason=f"Ticket de {interaction.user}")
            e = GuildEmbed(title=self.bot.t(lang, "tickets.ticket_created"), description=self.bot.t(lang, "tickets.ticket_desc", user=interaction.user.mention, reason="general"), color=config.COLORS["green"], guild=interaction.guild)
            close_btn = discord.ui.Button(emoji="🔒", label=self.bot.t(lang, "tickets.close"), style=discord.ButtonStyle.danger, custom_id="ticket_close")
            claim_btn = discord.ui.Button(emoji="👋", label=self.bot.t(lang, "tickets.claim"), style=discord.ButtonStyle.primary, custom_id="ticket_claim")

            async def close_cb(inter: discord.Interaction):
                await inter.response.defer()
                lang2 = await self.bot.get_lang(inter.guild.id)
                await inter.channel.delete(reason=f"Ticket cerrado por {inter.user}")
                try:
                    await inter.user.send(embed=info_embed(self.bot.t(lang2, "tickets.closed_title"), self.bot.t(lang2, "tickets.closed_desc", channel=inter.channel.name)))
                except:
                    pass

            async def claim_cb(inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                lang2 = await self.bot.get_lang(inter.guild.id)
                e2 = inter.message.embeds[0]
                e2.add_field(name=self.bot.t(lang2, "tickets.claimed_by"), value=inter.user.mention, inline=False)
                await inter.message.edit(embed=e2)
                await inter.followup.send(self.bot.t(lang2, "tickets.claimed_desc", user=inter.user.mention))

            close_btn.callback = close_cb
            claim_btn.callback = claim_cb
            view = discord.ui.View()
            view.add_item(close_btn)
            view.add_item(claim_btn)
            await channel.send(embed=e, view=view)
            await interaction.followup.send(embed=success_embed(self.bot.t(lang, "tickets.created"), self.bot.t(lang, "tickets.created_desc", channel=channel.mention)))
        except Exception as ex:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), str(ex)))

    @app_commands.command(name="ticketpanel", description="Crear panel de tickets con selector")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal", title="Título (opcional)", description="Descripción (opcional)")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str = None, description: str = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        embed = GuildEmbed(
            title=title or self.bot.t(lang, "tickets.panel_title"),
            description=description or self.bot.t(lang, "tickets.panel_desc"),
            color=config.COLORS["blue"],
            guild=interaction.guild,
        )
        view = discord.ui.View()
        view.add_item(TicketSelect(self.bot, lang))
        await channel.send(embed=embed, view=view)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "tickets.panel_created"), self.bot.t(lang, "tickets.panel_created_desc", channel=channel.mention)))

    @app_commands.command(name="ticketconfig", description="Configurar tickets")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(category="Categoría para tickets", support_role="Rol de soporte")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_config(self, interaction: discord.Interaction, category: discord.CategoryChannel = None, support_role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if category:
            await self.bot.db.update_guild(interaction.guild.id, ticket_category=category.id)
        if support_role:
            await self.bot.db.update_guild(interaction.guild.id, ticket_support_role=support_role.id)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "tickets.config_updated")))

    @app_commands.command(name="add", description="Añadir usuario a un ticket")
    @app_commands.describe(user="Usuario")
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if "ticket-" not in interaction.channel.name:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "tickets.not_ticket_channel")))
        await interaction.channel.set_permissions(user, view_channel=True, send_messages=True)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "tickets.user_added"), self.bot.t(lang, "tickets.user_added_desc", user=user.mention)))

    @app_commands.command(name="remove", description="Quitar usuario de un ticket")
    @app_commands.describe(user="Usuario")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if "ticket-" not in interaction.channel.name:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "tickets.not_ticket_channel")))
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "tickets.user_removed"), self.bot.t(lang, "tickets.user_removed_desc", user=user.mention)))

    @app_commands.command(name="rename", description="Renombrar ticket")
    @app_commands.describe(name="Nuevo nombre")
    async def rename(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if "ticket-" not in interaction.channel.name:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "tickets.not_ticket_channel")))
        await interaction.channel.edit(name=name[:32].lower().replace(" ", "-"))
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "tickets.renamed"), self.bot.t(lang, "tickets.renamed_desc", name=name)))

    @app_commands.command(name="close", description="Cerrar ticket actual")
    async def close(self, interaction: discord.Interaction):
        lang = await self.bot.get_lang(interaction.guild.id)
        if "ticket-" not in interaction.channel.name:
            return await interaction.response.send_message(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "tickets.not_ticket_channel")), ephemeral=True)
        await interaction.response.send_message(embed=info_embed(self.bot.t(lang, "tickets.closing"), self.bot.t(lang, "tickets.closing_desc")))
        await asyncio.sleep(3)
        await interaction.channel.delete(reason=f"Ticket cerrado por {interaction.user}")

    @app_commands.command(name="ticketstats", description="Estadísticas de tickets")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        ticket_channels = [ch for ch in interaction.guild.text_channels if ch.name.startswith("ticket-")]
        embed = GuildEmbed(title=self.bot.t(lang, "tickets.stats_title"), color=config.COLORS["blue"], guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "tickets.open_tickets"), value=str(len(ticket_channels)), inline=True)
        embed.add_field(name=self.bot.t(lang, "tickets.total_tickets"), value=str(0), inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
