import discord
from discord.ext import commands
from discord import app_commands
import time
import asyncio
import config
from utils.embeds import success_embed, error_embed, info_embed, PremiumEmbed
from utils.helpers import send_log


class Tickets(commands.Cog):
    """🎫 Sistema de tickets con botones, categorías, transcript y más."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if cid == "ticket_open":
            await self._open_ticket(interaction)
        elif cid == "ticket_close":
            await self._close_ticket(interaction)
        elif cid == "ticket_claim":
            await self._claim_ticket(interaction)
        elif cid == "ticket_delete":
            await self._delete_ticket(interaction)

    async def _open_ticket(self, interaction: discord.Interaction):
        g = await self.bot.db.get_guild(interaction.guild.id)
        if not g.get("ticket_enabled", 1):
            return await interaction.response.send_message("Tickets desactivados.", ephemeral=True)
        existing = await self.bot.db.get_user_open_ticket(interaction.user.id, interaction.guild.id)
        if existing:
            ch = interaction.guild.get_channel(existing["channel_id"])
            if ch:
                return await interaction.response.send_message(f"Ya tienes un ticket: {ch.mention}", ephemeral=True)
        cat_id = g.get("ticket_category")
        cat = interaction.guild.get_channel(cat_id) if cat_id else None
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        try:
            ch = await interaction.guild.create_text_channel(
                f"ticket-{interaction.user.name.lower()[:20]}",
                category=cat,
                overwrites=overwrites,
                reason=f"Ticket de {interaction.user}",
            )
            await self.bot.db.create_ticket(interaction.guild.id, ch.id, interaction.user.id)
            embed = PremiumEmbed(title="🎫 Nuevo Ticket", description="Un miembro del staff te atenderá pronto.", color=config.COLORS["green"])
            embed.add_field(name="👤 Creado por", value=interaction.user.mention)
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="🔒 Cerrar", style=discord.ButtonStyle.danger, custom_id="ticket_close", emoji="🔒"))
            view.add_item(discord.ui.Button(label="📋 Reclamar", style=discord.ButtonStyle.secondary, custom_id="ticket_claim", emoji="📋"))
            await ch.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Ticket creado: {ch.mention}", ephemeral=True)
            await send_log(self.bot, interaction.guild.id, "tickets", embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    async def _close_ticket(self, interaction: discord.Interaction):
        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("Este canal no es un ticket.", ephemeral=True)
        if ticket["status"] == "closed":
            return await interaction.response.send_message("Ya está cerrado.", ephemeral=True)
        await self.bot.db.close_ticket(interaction.channel.id, interaction.user.id)
        await interaction.response.send_message(embed=success_embed("🔒 Ticket cerrado", f"Por {interaction.user.mention}"))
        await interaction.channel.edit(name=f"closed-{interaction.channel.name}")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🗑️ Eliminar", style=discord.ButtonStyle.danger, custom_id="ticket_delete", emoji="🗑️"))
        await interaction.channel.send(embed=info_embed("🗑️", "Presiona para eliminar el canal."), view=view)

    async def _claim_ticket(self, interaction: discord.Interaction):
        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.response.send_message("No es un ticket.", ephemeral=True)
        if ticket["claimer_id"]:
            claimer = interaction.guild.get_member(ticket["claimer_id"])
            return await interaction.response.send_message(f"Reclamado por {claimer.mention}", ephemeral=True)
        await self.bot.db.claim_ticket(interaction.channel.id, interaction.user.id)
        await interaction.response.send_message(embed=success_embed("📋 Ticket reclamado", interaction.user.mention))

    async def _delete_ticket(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_channels and not interaction.channel.name.startswith("closed-"):
            return await interaction.response.send_message("No puedes eliminar.", ephemeral=True)
        await interaction.response.defer()
        await interaction.channel.delete(reason=f"Eliminado por {interaction.user}")

    # ── Comandos ─────────────────────────────────────────────────────────────
    ticket = app_commands.Group(name="ticket", description="🎫 Sistema de tickets")

    @ticket.command(name="panel", description="🎫 Enviar panel de tickets")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(canal="Canal (opcional)")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction, canal: discord.TextChannel = None):
        canal = canal or interaction.channel
        await interaction.response.defer(ephemeral=True)
        embed = PremiumEmbed(title="🎫 Sistema de Tickets", description="Presiona el botón para abrir un ticket.", color=config.COLORS["blue"])
        embed.add_field(name="📋 ¿Cómo funciona?", value="1. Presiona 🎫\n2. Se crea un canal privado\n3. Un staff te atenderá", inline=False)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🎫 Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="ticket_open", emoji="🎫"))
        await canal.send(embed=embed, view=view)
        await interaction.followup.send(f"✅ Panel enviado a {canal.mention}", ephemeral=True)

    @ticket.command(name="create", description="🎫 Crear ticket manualmente")
    async def ticket_create(self, interaction: discord.Interaction):
        await self._open_ticket(interaction)

    @ticket.command(name="close", description="🔒 Cerrar ticket actual")
    async def ticket_close(self, interaction: discord.Interaction):
        await self._close_ticket(interaction)

    @ticket.command(name="reopen", description="🔓 Reabrir ticket")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticket_reopen(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.followup.send("No es un ticket.", ephemeral=True)
        await self.bot.db.reopen_ticket(interaction.channel.id)
        await interaction.channel.edit(name=interaction.channel.name.replace("closed-", ""))
        await interaction.followup.send(embed=success_embed("🔓 Ticket reabierto"))

    @ticket.command(name="claim", description="📋 Reclamar ticket")
    async def ticket_claim(self, interaction: discord.Interaction):
        await self._claim_ticket(interaction)

    @ticket.command(name="unclaim", description="📋 Liberar ticket")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticket_unclaim(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ticket = await self.bot.db.get_ticket(interaction.channel.id)
        if not ticket:
            return await interaction.followup.send("No es un ticket.", ephemeral=True)
        await self.bot.db.unclaim_ticket(interaction.channel.id)
        await interaction.followup.send(embed=success_embed("📋 Ticket liberado"))

    @ticket.command(name="adduser", description="➕ Añadir usuario al ticket")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticket_adduser(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
        await interaction.followup.send(embed=success_embed("➕ Usuario añadido", user.mention))

    @ticket.command(name="removeuser", description="➖ Quitar usuario del ticket")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticket_removeuser(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        await interaction.channel.set_permissions(user, overwrite=None)
        await interaction.followup.send(embed=success_embed("➖ Usuario quitado", user.mention))

    @ticket.command(name="rename", description="✏️ Renombrar ticket")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.describe(name="Nuevo nombre")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticket_rename(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        await interaction.channel.edit(name=name[:32])
        await interaction.followup.send(embed=success_embed("✏️ Renombrado", name))

    @ticket.command(name="setup", description="⚙️ Configurar tickets")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(categoria="Categoría para tickets", logs="Canal de logs")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_setup(self, interaction: discord.Interaction, categoria: discord.CategoryChannel, logs: discord.TextChannel = None):
        await interaction.response.defer()
        await self.bot.db.update_guild(interaction.guild.id, ticket_category=categoria.id)
        if logs:
            await self.bot.db.update_guild(interaction.guild.id, ticket_log_channel=logs.id)
        await interaction.followup.send(embed=success_embed("⚙️ Tickets configurados", f"Categoría: {categoria.mention}"))

    @ticket.command(name="config", description="📋 Ver configuración de tickets")
    async def ticket_config(self, interaction: discord.Interaction):
        await interaction.response.defer()
        g = await self.bot.db.get_guild(interaction.guild.id)
        embed = info_embed("🎫 Configuración de Tickets", f"Estado: {'✅' if g.get('ticket_enabled', 1) else '❌'}")
        cat = interaction.guild.get_channel(g.get("ticket_category") or 0)
        log = interaction.guild.get_channel(g.get("ticket_log_channel") or 0)
        embed.add_field(name="📁 Categoría", value=cat.mention if cat else "❌", inline=True)
        embed.add_field(name="📝 Logs", value=log.mention if log else "❌", inline=True)
        embed.add_field(name="🔢 Límite abiertos", value=str(g.get("ticket_open_limit", 3)), inline=True)
        await interaction.followup.send(embed=embed)

    @ticket.command(name="stats", description="📊 Estadísticas de tickets")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_stats(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rows = await self.bot.db.get_guild_tickets(interaction.guild.id)
        total = len(rows)
        open_t = sum(1 for r in rows if r["status"] == "open")
        claimed = sum(1 for r in rows if r["status"] == "claimed")
        closed = sum(1 for r in rows if r["status"] == "closed")
        embed = PremiumEmbed(title="📊 Estadísticas de Tickets", color=config.EMBED_COLOR)
        embed.add_field(name="📋 Total", value=str(total), inline=True)
        embed.add_field(name="🟢 Abiertos", value=str(open_t), inline=True)
        embed.add_field(name="📋 Reclamados", value=str(claimed), inline=True)
        embed.add_field(name="🔒 Cerrados", value=str(closed), inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
