import discord
from discord.ext import commands
from discord import app_commands
import time
import random
import asyncio
import config
from utils.embeds import PremiumEmbed, success_embed, error_embed, info_embed
from utils.helpers import send_log


class Giveaways(commands.Cog):
    """🎉 Sistema de giveaways con botones."""

    def __init__(self, bot):
        self.bot = bot

    async def check_giveaways(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(10)
            try:
                active = await self.bot.db.get_active_giveaways()
                for gw in active:
                    await self._end_giveaway(gw)
            except:
                pass

    async def _end_giveaway(self, gw):
        guild = self.bot.get_guild(gw["guild_id"])
        if not guild:
            await self.bot.db.end_giveaway(gw["message_id"])
            return
        ch = guild.get_channel(gw["channel_id"])
        if not ch:
            await self.bot.db.end_giveaway(gw["message_id"])
            return
        entries = await self.bot.db.get_giveaway_entries(gw["id"])
        if not entries:
            try:
                msg = await ch.fetch_message(gw["message_id"])
                e = msg.embeds[0]
                e.color = config.ERROR_COLOR
                e.add_field(name="Resultado", value="Sin participantes.", inline=False)
                await msg.edit(embed=e)
            except:
                pass
            await self.bot.db.end_giveaway(gw["message_id"])
            return

        winners_count = min(gw["winners"], len(entries))
        winners = random.sample(entries, winners_count)
        winner_mentions = []
        for w in winners:
            member = guild.get_member(w["user_id"])
            if member:
                winner_mentions.append(member.mention)

        try:
            msg = await ch.fetch_message(gw["message_id"])
            e = msg.embeds[0]
            e.color = config.SUCCESS_COLOR
            e.add_field(name="Ganadores", value="".join(winner_mentions) or "Nadie", inline=False)
            await msg.edit(embed=e)
            await ch.send(f"🎉 **{gw['prize']}**\nGanadores: {', '.join(winner_mentions)}\n{', '.join(w.mention for w in winners if guild.get_member(w['user_id']))}")
        except:
            pass
        await self.bot.db.end_giveaway(gw["message_id"])

    giveaway = app_commands.Group(name="giveaway", description="Gestionar giveaways")

    @giveaway.command(name="start", description="Iniciar un giveaway")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(premio="Premio", duracion="Duración (ej: 1h, 1d)", ganadores="Número de ganadores", canal="Canal")
    @app_commands.checks.has_permissions(administrator=True)
    async def gw_start(self, interaction: discord.Interaction, premio: str, duracion: str, ganadores: int = 1, canal: discord.TextChannel = None):
        await interaction.response.defer()
        canal = canal or interaction.channel
        from utils.helpers import parse_duration
        secs = parse_duration(duracion)
        if secs <= 0 or secs > config.GIVEAWAY_MAX_DURATION:
            return await interaction.followup.send(embed=error_embed("❌", "Duración inválida (máx 7 días)."))
        if ganadores < 1 or ganadores > config.GIVEAWAY_MAX_WINNERS:
            return await interaction.followup.send(embed=error_embed("❌", f"Ganadores entre 1 y {config.GIVEAWAY_MAX_WINNERS}."))
        end_time = time.time() + secs
        e = PremiumEmbed(title=f"🎉 {premio}", color=config.COLORS["gold"])
        e.add_field(name="Premio", value=premio, inline=True)
        e.add_field(name="Ganadores", value=str(ganadores), inline=True)
        e.add_field(name="Termina", value=f"<t:{int(end_time)}:R>f", inline=False)
        e.add_field(name="Hosted por", value=interaction.user.mention, inline=False)
        e.set_footer(text="Presiona 🎉 para participar!")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🎉 Participar", style=discord.ButtonStyle.primary, custom_id=f"gw_join_{int(end_time)}", emoji="🎉"))
        msg = await canal.send(embed=e, view=view)
        await self.bot.db.create_giveaway(interaction.guild.id, canal.id, msg.id, premio, ganadores, end_time, interaction.user.id)
        await interaction.followup.send(embed=success_embed("🎉 Giveaway iniciado", canal.mention))

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if cid.startswith("gw_join_"):
            try:
                gw = await self.bot.db.fetchone(
                    "SELECT * FROM giveaways WHERE message_id = ? AND finished = 0",
                    interaction.message.id,
                )
                if gw:
                    await self.bot.db.add_giveaway_entry(gw["id"], interaction.user.id)
                    await interaction.response.send_message("🎉 Participación registrada!", ephemeral=True)
                else:
                    await interaction.response.send_message("Este giveaway ya terminó.", ephemeral=True)
            except:
                await interaction.response.send_message("Error.", ephemeral=True)

    @giveaway.command(name="end", description="Terminar giveaway antes de tiempo")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message_id="ID del mensaje")
    @app_commands.checks.has_permissions(administrator=True)
    async def gw_end(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer()
        try:
            gw = await self.bot.db.fetchone(
                "SELECT * FROM giveaways WHERE message_id = ? AND guild_id = ? AND finished = 0",
                int(message_id), interaction.guild.id,
            )
            if gw:
                await self._end_giveaway(dict(gw))
                await interaction.followup.send(embed=success_embed("⏹️ Giveaway terminado"))
            else:
                await interaction.followup.send(embed=error_embed("❌", "No encontrado o ya terminado."))
        except:
            await interaction.followup.send(embed=error_embed("❌", "Error."))

    @giveaway.command(name="reroll", description="Re-elegir ganador")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(message_id="ID del mensaje")
    @app_commands.checks.has_permissions(administrator=True)
    async def gw_reroll(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer()
        try:
            gw = await self.bot.db.fetchone(
                "SELECT * FROM giveaways WHERE message_id = ? AND guild_id = ?",
                int(message_id), interaction.guild.id,
            )
            if gw:
                entries = await self.bot.db.get_giveaway_entries(gw["id"])
                if entries:
                    winner = random.choice(entries)
                    member = interaction.guild.get_member(winner["user_id"])
                    if member:
                        await interaction.followup.send(f"🎉 Nuevo ganador: {member.mention}")
                    else:
                        await interaction.followup.send("Ganador ya no está en el servidor.")
                else:
                    await interaction.followup.send("Sin participantes.")
            else:
                await interaction.followup.send(embed=error_embed("❌", "No encontrado."))
        except:
            await interaction.followup.send(embed=error_embed("❌", "Error."))

    @giveaway.command(name="list", description="Listar giveaways activos")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def gw_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rows = await self.bot.db.get_guild_giveaways(interaction.guild.id)
        active = [r for r in rows if not r["finished"]]
        if not active:
            return await interaction.followup.send(embed=info_embed("🎉", "Sin giveaways activos."))
        embed = PremiumEmbed(title="Giveaways activos", color=config.COLORS["gold"])
        for gw in active[:10]:
            embed.add_field(
                name=gw["prize"],
                value=f"ID: `{gw['message_id']}` · Termina: <t:{int(gw['end_time'])}:R> · Ganadores: {gw['winners']}f",
                inline=False,
            )
        await interaction.followup.send(embed=embed)


async def setup(bot):
    cog = Giveaways(bot)
    await bot.add_cog(cog)
    asyncio.create_task(cog.check_giveaways())
