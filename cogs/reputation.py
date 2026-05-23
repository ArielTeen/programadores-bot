import discord
from discord.ext import commands
from discord import app_commands
import config
from utils.embeds import success_embed, error_embed, info_embed, GuildEmbed
from utils.helpers import send_log, get_level_from_xp
from utils.paginator import ReactionPaginator


class Reputation(commands.Cog):
    """⭐ Sistema de reputación — dar, quitar, perfil, top, recompensas."""

    def __init__(self, bot):
        self.bot = bot

    rep = app_commands.Group(name="rep", description="Gestionar reputación")

    @rep.command(name="give", description="Dar reputación a un usuario")
    @app_commands.describe(user="Usuario", reason="Razón (opcional)")
    async def rep_give(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if user == interaction.user:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reputation.self_rep")))
        if user.bot:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reputation.bot_rep")))
        cd = await self.bot.db.get_rep_cooldown(interaction.user.id, interaction.guild.id)
        if cd:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reputation.cooldown", time=f"<t:{cd}:R>")))
        new_bal = await self.bot.db.add_reputation(user.id, interaction.guild.id, 1)
        await self.bot.db.set_rep_cooldown(interaction.user.id, interaction.guild.id, int(time.time()) + config.REP_COOLDOWN)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reputation.given"), self.bot.t(lang, "reputation.given_desc", user=user.mention, reason=reason or "")))
        await self._check_rep_rewards(user, new_bal, interaction.guild)

    @rep.command(name="remove", description="Quitar reputación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario", cantidad="Cantidad")
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_remove(self, interaction: discord.Interaction, user: discord.Member, cantidad: int = 1):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        bal = await self.bot.db.add_reputation(user.id, interaction.guild.id, -cantidad)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reputation.removed"), self.bot.t(lang, "reputation.removed_desc", user=user.mention, amount=cantidad)))

    @rep.command(name="set", description="Establecer reputación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario", cantidad="Nuevo valor")
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_set(self, interaction: discord.Interaction, user: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        md = await self.bot.db.get_member(user.id, interaction.guild.id)
        md["reputation"] = max(0, cantidad)
        await self.bot.db.update_member(user.id, interaction.guild.id, reputation=md["reputation"])
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reputation.set"), self.bot.t(lang, "reputation.set_desc", user=user.mention, amount=cantidad)))

    @rep.command(name="profile", description="Ver perfil de reputación")
    @app_commands.describe(user="Usuario (opcional)")
    async def rep_profile(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        md = await self.bot.db.get_member(user.id, interaction.guild.id)
        rep = md.get("reputation", 0)
        rep_given = md.get("rep_given", 0)
        rank, _ = await self.bot.db.get_rank(user.id, interaction.guild.id, "reputation")
        embed = GuildEmbed(title=self.bot.t(lang, "reputation.profile_title", user=user.display_name), color=user.color or config.EMBED_COLOR, guild=interaction.guild)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name=self.bot.t(lang, "reputation.reputation"), value=f"⭐ {rep}", inline=True)
        embed.add_field(name="#⃣ " + self.bot.t(lang, "levels.rank"), value=f"#{rank}" if rank else self.bot.t(lang, "common.na"), inline=True)
        embed.add_field(name=self.bot.t(lang, "reputation.total_given"), value=str(rep_given), inline=True)
        await interaction.followup.send(embed=embed)

    @rep.command(name="top", description="Top de reputación")
    async def rep_top(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        rows = await self.bot.db.get_leaderboard(interaction.guild.id, "reputation", 50)
        if not rows:
            return await interaction.followup.send(embed=info_embed(self.bot.t(lang, "reputation.top_title"), self.bot.t(lang, "reputation.no_top")))
        per_page = 10
        chunks = [rows[i:i+per_page] for i in range(0, len(rows), per_page)]
        pages = []
        medals = ["🥇", "🥈", "🥉"]
        for ci, chunk in enumerate(chunks):
            embed = GuildEmbed(title=self.bot.t(lang, "reputation.top_ranking", guild=interaction.guild.name), color=config.COLORS["gold"], guild=interaction.guild)
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            for i, r in enumerate(chunk):
                m = interaction.guild.get_member(r["user_id"])
                name = m.display_name if m else f"`{r['user_id']}`"
                rank = ci * 10 + i + 1
                prefix = medals[i] if i < 3 else f"`#{rank}`"
                embed.add_field(name=f"{prefix} {name}", value=f"⭐ {r.get('reputation', 0)}", inline=False)
            pages.append(embed)
        if len(pages) <= 1:
            return await interaction.followup.send(embed=pages[0])
        pag = ReactionPaginator(interaction, pages, timeout=60)
        await pag.start()

    rep_rewards = app_commands.Group(name="reprewards", description="Recompensas por reputación")

    @rep_rewards.command(name="add", description="Añadir recompensa por reputación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(reputation="Reputación requerida", role="Rol")
    @app_commands.checks.has_permissions(administrator=True)
    async def repr_add(self, interaction: discord.Interaction, reputation: int, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.add_rep_reward(interaction.guild.id, reputation, role.id)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reputation.reward_added"), self.bot.t(lang, "reputation.reward_added_desc", rep=reputation, role=role.mention)))

    @rep_rewards.command(name="remove", description="Quitar recompensa por reputación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(reputation="Reputación")
    @app_commands.checks.has_permissions(administrator=True)
    async def repr_remove(self, interaction: discord.Interaction, reputation: int):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        await self.bot.db.remove_rep_reward(interaction.guild.id, reputation)
        await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reputation.reward_removed"), self.bot.t(lang, "reputation.reward_removed_desc", rep=reputation)))

    @rep_rewards.command(name="list", description="Listar recompensas")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def repr_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        rows = await self.bot.db.get_rep_rewards(interaction.guild.id)
        if not rows:
            return await interaction.followup.send(embed=info_embed(self.bot.t(lang, "reputation.rewards_title"), self.bot.t(lang, "reputation.no_rewards")))
        embed = GuildEmbed(title=self.bot.t(lang, "reputation.rewards_title"), color=config.COLORS["gold"], guild=interaction.guild)
        for r in rows:
            role = interaction.guild.get_role(r["role_id"])
            embed.add_field(name=f"⭐ {r['reputation']}", value=role.mention if role else self.bot.t(lang, "common.deleted_role"), inline=False)
        await interaction.followup.send(embed=embed)

    async def _check_rep_rewards(self, member, new_rep, guild):
        rows = await self.bot.db.get_rep_rewards(guild.id)
        for r in rows:
            if new_rep >= r["reputation"]:
                role = guild.get_role(r["role_id"])
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Recompensa de reputación")
                    except:
                        pass

    @rep.command(name="config", description="Configurar reputación")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(cooldown_hours="Cooldown en horas")
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_config(self, interaction: discord.Interaction, cooldown_hours: int = None):
        await interaction.response.defer(ephemeral=True)
        lang = await self.bot.get_lang(interaction.guild.id)
        if cooldown_hours is not None:
            if cooldown_hours < 0 or cooldown_hours > 168:
                return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "reputation.invalid_cooldown")))
            global config
            config.REP_COOLDOWN = cooldown_hours * 3600
            await interaction.followup.send(embed=success_embed(self.bot.t(lang, "reputation.config_updated"), self.bot.t(lang, "reputation.config_updated_desc", hours=cooldown_hours)))
        else:
            cd_hours = config.REP_COOLDOWN // 3600 if hasattr(config, 'REP_COOLDOWN') else 12
            embed = info_embed(self.bot.t(lang, "reputation.config_title"), self.bot.t(lang, "reputation.config_info", cooldown=cd_hours))
            await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Reputation(bot))
