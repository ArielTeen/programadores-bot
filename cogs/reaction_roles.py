import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.embeds import success_embed, error_embed, GuildEmbed
from utils.helpers import create_pages


class ReactionRoles(commands.Cog):
    """🔘 Sistema de reacción-roles con botones y select menus."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reactionrole", description="Crear panel de reaction roles")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Canal del menú",
        title="Título del embed",
        description="Descripción",
        roles="Roles: 'rol1=emoji1, rol2=emoji2' o 'rol1=r1; rol1=r2'",
        style="button (botones) o select (menú desplegable)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def reactionrole(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str = None,
        roles: str = None,
        style: str = "button",
    ):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if not roles:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reaction_roles.no_roles")))

        parsed = []
        for part in roles.replace(";", ",").split(","):
            part = part.strip()
            if "=" in part:
                rname, emoji = part.split("=", 1)
                parsed.append((rname.strip(), emoji.strip()))
        if not parsed:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reaction_roles.parse_error")))

        resolved = []
        for rname, emoji in parsed:
            role = discord.utils.get(interaction.guild.roles, name=rname)
            if not role:
                try:
                    role = discord.utils.get(interaction.guild.roles, id=int(rname.strip("<@&>")))
                except:
                    pass
            if role:
                resolved.append((role, emoji))

        if not resolved:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reaction_roles.no_roles_found")))

        embed = GuildEmbed(title=title, description=description or "", color=config.EMBED_COLOR, guild=interaction.guild)
        for role, emoji in resolved:
            embed.add_field(name=role.name, value=f"{emoji} {self.bot.t(lang, 'reaction_roles.click_to_get')}", inline=True)

        if style == "select":
            opts = []
            for role, emoji in resolved:
                opts.append(discord.SelectOption(label=role.name, emoji=emoji, value=str(role.id), description=self.bot.t(lang, "reaction_roles.get_role", role=role.name)))
            select = discord.ui.Select(placeholder=self.bot.t(lang, "reaction_roles.placeholder"), min_values=0, max_values=len(opts), options=opts)

            async def select_cb(inter: discord.Interaction):
                await inter.response.defer(ephemeral=True)
                lang2 = await self.bot.get_lang(inter.guild.id)
                added, removed = 0, 0
                for opt in select.options:
                    rid = int(opt.value)
                    r = inter.guild.get_role(rid)
                    if r:
                        if str(rid) in inter.data["values"]:
                            if r not in inter.user.roles:
                                await inter.user.add_roles(r, reason="Reaction role")
                                added += 1
                        else:
                            if r in inter.user.roles:
                                await inter.user.remove_roles(r, reason="Reaction role")
                                removed += 1
                await inter.followup.send(embed=success_embed(self.bot.t(lang2, "reaction_roles.updated"), self.bot.t(lang2, "reaction_roles.updated_desc", add=added, remove=removed)))

            select.callback = select_cb
            view = discord.ui.View().add_item(select)
        else:
            view = discord.ui.View()
            for role, emoji in resolved:
                btn = discord.ui.Button(emoji=emoji, label=role.name[:75], style=discord.ButtonStyle.secondary, custom_id=f"rr_{role.id}")

                async def make_cb(rid):
                    async def cb(inter: discord.Interaction):
                        await inter.response.defer(ephemeral=True)
                        lang3 = await self.bot.get_lang(inter.guild.id)
                        r = inter.guild.get_role(rid)
                        if r:
                            if r in inter.user.roles:
                                await inter.user.remove_roles(r, reason="Reaction role")
                                await inter.followup.send(embed=success_embed(self.bot.t(lang3, "reaction_roles.role_removed"), self.bot.t(lang3, "reaction_roles.role_removed_desc", role=r.name)))
                            else:
                                await inter.user.add_roles(r, reason="Reaction role")
                                await inter.followup.send(embed=success_embed(self.bot.t(lang3, "reaction_roles.role_added"), self.bot.t(lang3, "reaction_roles.role_added_desc", role=r.name)))
                    return cb

                btn.callback = await make_cb(role.id)
                view.add_item(btn)

        msg = await channel.send(embed=embed, view=view)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reaction_roles.created_title"), self.bot.t(lang, "reaction_roles.created_desc", channel=channel.mention)))

    @app_commands.command(name="rrpanel", description="Crear panel de reaction roles con texto")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Canal", message="Texto del panel", roles="rol1=emoji1, rol2=emoji2")
    @app_commands.checks.has_permissions(administrator=True)
    async def rrpanel(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str, roles: str):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        parsed = []
        for part in roles.replace(";", ",").split(","):
            part = part.strip()
            if "=" in part:
                rname, emoji = part.split("=", 1)
                parsed.append((rname.strip(), emoji.strip()))
        if not parsed:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reaction_roles.no_roles")))
        resolved = []
        for rname, emoji in parsed:
            role = discord.utils.get(interaction.guild.roles, name=rname)
            if role:
                resolved.append((role, emoji))
        if not resolved:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reaction_roles.no_roles_found")))
        embed = GuildEmbed(description=message, color=config.EMBED_COLOR, guild=interaction.guild)
        view = discord.ui.View()
        for role, emoji in resolved:
            btn = discord.ui.Button(emoji=emoji, label=role.name[:75], style=discord.ButtonStyle.secondary, custom_id=f"rrp_{role.id}")

            async def make_cb(rid):
                async def cb(inter: discord.Interaction):
                    await inter.response.defer(ephemeral=True)
                    lang4 = await self.bot.get_lang(inter.guild.id)
                    r = inter.guild.get_role(rid)
                    if r:
                        if r in inter.user.roles:
                            await inter.user.remove_roles(r, reason="Rr panel")
                            await inter.followup.send(embed=success_embed(self.bot.t(lang4, "reaction_roles.role_removed"), self.bot.t(lang4, "reaction_roles.role_removed_desc", role=r.name)))
                        else:
                            await inter.user.add_roles(r, reason="Rr panel")
                            await inter.followup.send(embed=success_embed(self.bot.t(lang4, "reaction_roles.role_added"), self.bot.t(lang4, "reaction_roles.role_added_desc", role=r.name)))
                return cb

            btn.callback = await make_cb(role.id)
            view.add_item(btn)
        msg = await channel.send(embed=embed, view=view)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reaction_roles.created_title"), self.bot.t(lang, "reaction_roles.created_desc", channel=channel.mention)))


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
