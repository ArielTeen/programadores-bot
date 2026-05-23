import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.embeds import PremiumEmbed, success_embed, error_embed, info_embed


class ReactionRoles(commands.Cog):
    """🎭 Sistema de reaction roles y button roles."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        rrs = await self.bot.db.get_reaction_roles_for_message(payload.message_id)
        for rr in rrs:
            if str(payload.emoji) == rr["emoji"] and rr["type"] == "reaction":
                guild = self.bot.get_guild(payload.guild_id)
                if guild:
                    role = guild.get_role(rr["role_id"])
                    member = guild.get_member(payload.user_id)
                    if role and member and role not in member.roles:
                        try:
                            await member.add_roles(role, reason="Reaction Role")
                        except:
                            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.bot.user.id:
            return
        rrs = await self.bot.db.get_reaction_roles_for_message(payload.message_id)
        for rr in rrs:
            if str(payload.emoji) == rr["emoji"] and rr["type"] == "reaction":
                guild = self.bot.get_guild(payload.guild_id)
                if guild:
                    role = guild.get_role(rr["role_id"])
                    member = guild.get_member(payload.user_id)
                    if role and member and role in member.roles:
                        try:
                            await member.remove_roles(role, reason="Reaction Role")
                        except:
                            pass

    reactionrole = app_commands.Group(name="reactionrole", description="🎭 Configurar reaction roles")

    @reactionrole.command(name="create", description="➕ Crear reaction role")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal", message_id="ID del mensaje", role="Rol", emoji="Emoji")
    @app_commands.checks.has_permissions(administrator=True)
    async def rr_create(self, interaction: discord.Interaction, channel: discord.TextChannel, message_id: str, role: discord.Role, emoji: str):
        await interaction.response.defer()
        try:
            mid = int(message_id)
            msg = await channel.fetch_message(mid)
            await msg.add_reaction(emoji)
            await self.bot.db.add_reaction_role(interaction.guild.id, channel.id, mid, role.id, emoji, "reaction")
            await interaction.followup.send(embed=success_embed("🎭 Reaction role creado", f"{emoji} → {role.mention} en {channel.mention}"))
        except:
            await interaction.followup.send(embed=error_embed("❌", "Mensaje no encontrado o error."))

    @reactionrole.command(name="delete", description="➖ Eliminar reaction role")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(id="ID del reaction role")
    @app_commands.checks.has_permissions(administrator=True)
    async def rr_delete(self, interaction: discord.Interaction, id: int):
        await interaction.response.defer()
        await self.bot.db.remove_reaction_role(id, interaction.guild.id)
        await interaction.followup.send(embed=success_embed("➖ Reaction role eliminado"))

    @reactionrole.command(name="list", description="📋 Listar reaction roles")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rr_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rows = await self.bot.db.get_reaction_roles(interaction.guild.id)
        if not rows:
            return await interaction.followup.send(embed=info_embed("📋", "Sin reaction roles."))
        embed = PremiumEmbed(title="🎭 Reaction Roles", color=config.EMBED_COLOR)
        for r in rows:
            role = interaction.guild.get_role(r["role_id"])
            embed.add_field(
                name=f"{r['emoji']} · ID {r['id']}",
                value=f"Rol: {role.mention if role else '❌'}\nTipo: {r['type']}",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    buttonrole = app_commands.Group(name="buttonrole", description="🔘 Configurar button roles")

    @buttonrole.command(name="panel", description="🔘 Crear panel de button roles")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal", title="Título", roles_text="rol1:emoji1,rol2:emoji2...")
    @app_commands.checks.has_permissions(administrator=True)
    async def br_panel(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str, roles_text: str):
        await interaction.response.defer()
        pairs = [p.strip().split(":") for p in roles_text.split(",")]
        embed = PremiumEmbed(title=f"🔘 {title}", description="Presiona un botón para obtener el rol.", color=config.COLORS["blue"])
        view = discord.ui.View()
        for pair in pairs:
            if len(pair) >= 2:
                role_name, emoji = pair[0].strip(), pair[1].strip()
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    embed.add_field(name=f"{emoji} {role.name}", value=role.mention, inline=True)
                    btn = discord.ui.Button(label=role.name, emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=f"br_{role.id}")
                    view.add_item(btn)
        await channel.send(embed=embed, view=view)
        await interaction.followup.send(embed=success_embed("🔘 Panel de roles enviado", channel.mention))

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if cid.startswith("br_"):
            role_id = int(cid[3:])
            role = interaction.guild.get_role(role_id)
            if role:
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role, reason="Button Role")
                    await interaction.response.send_message(f"➖ {role.name} quitado.", ephemeral=True)
                else:
                    await interaction.user.add_roles(role, reason="Button Role")
                    await interaction.response.send_message(f"➕ {role.name} añadido.", ephemeral=True)
            else:
                await interaction.response.send_message("Rol no encontrado.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
