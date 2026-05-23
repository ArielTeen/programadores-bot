import discord
from discord.ext import commands
from discord import app_commands
import time
import random
import math
import config
from utils.embeds import success_embed, error_embed, warning_embed, info_embed, PremiumEmbed, send_ephemeral
from utils.helpers import send_log
from utils.paginator import ReactionPaginator


class Economy(commands.Cog):
    """💰 Economía — balance, daily, work, crime, shop, slots, etc."""

    def __init__(self, bot):
        self.bot = bot

    async def _get_bal(self, uid, gid):
        md = await self.bot.db.get_member(uid, gid)
        return md.get("balance", 0), md.get("bank", 0)

    async def _set_bal(self, uid, gid, bal, bank=None):
        kwargs = {"balance": bal}
        if bank is not None:
            kwargs["bank"] = bank
        await self.bot.db.update_member(uid, gid, **kwargs)

    @app_commands.command(name="balance", description="Ver tu saldo")
    @app_commands.describe(user="Usuario (opcional)")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer(ephemeral=True)
        bal, bank = await self._get_bal(user.id, interaction.guild.id)
        embed = PremiumEmbed(title=f"💰 Saldo de {user.display_name}", color=config.COLORS["green"])
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Efectivo", value=f"```{bal:,} ```f", inline=True)
        embed.add_field(name="Banco", value=f"```{bank:,} ```f", inline=True)
        embed.add_field(name="Total", value=f"```{bal + bank:,} ```f", inline=True)
        await send_ephemeral(interaction, embed=embed)

    @app_commands.command(name="daily", description="Recompensa diaria")
    async def daily(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(interaction.user.id, interaction.guild.id)
        now = time.time()
        if now - md.get("last_daily_time", 0) < 86400:
            rem = 86400 - (now - md.get("last_daily_time", 0))
            return await send_ephemeral(interaction, embed=warning_embed("⏳", f"Espera {int(rem//3600)}h {int((rem%3600)//60)}m."))
        bal = md.get("balance", 0) + config.DAILY_REWARD
        await self.bot.db.update_member(interaction.user.id, interaction.guild.id, balance=bal, last_daily_time=now)
        await send_ephemeral(interaction, embed=success_embed("🎁 Daily", f"+{config.DAILY_REWARD} 🪙 · Total: {bal:,} 🪙"))

    @app_commands.command(name="weekly", description="Recompensa semanal")
    async def weekly(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(interaction.user.id, interaction.guild.id)
        now = time.time()
        if now - md.get("last_weekly_time", 0) < 604800:
            return await send_ephemeral(interaction, embed=warning_embed("⏳", "Ya reclamaste tu weekly."))
        bal = md.get("balance", 0) + config.WEEKLY_REWARD
        await self.bot.db.update_member(interaction.user.id, interaction.guild.id, balance=bal, last_weekly_time=now)
        await send_ephemeral(interaction, embed=success_embed("🎁 Weekly", f"+{config.WEEKLY_REWARD} 🪙 · Total: {bal:,} 🪙"))

    @app_commands.command(name="work", description="Trabajar para ganar monedas")
    async def work(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(interaction.user.id, interaction.guild.id)
        now = time.time()
        if now - md.get("last_work_time", 0) < 3600:
            return await send_ephemeral(interaction, embed=warning_embed("⏳", "Espera 1h para volver a trabajar."))
        earned = random.randint(config.WORK_MIN, config.WORK_MAX)
        bal = md.get("balance", 0) + earned
        await self.bot.db.update_member(interaction.user.id, interaction.guild.id, balance=bal, last_work_time=now, total_earned=md.get("total_earned", 0) + earned)
        await send_ephemeral(interaction, embed=success_embed("💼 Trabajo", f"Has ganado {earned} 🪙\nSaldo: {bal:,} 🪙"))

    @app_commands.command(name="crime", description="Cometer un crimen (arriesgado)")
    async def crime(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        md = await self.bot.db.get_member(interaction.user.id, interaction.guild.id)
        now = time.time()
        if now - md.get("last_crime_time", 0) < 3600:
            return await send_ephemeral(interaction, embed=warning_embed("⏳", "Espera 1h."))
        if random.random() < config.CRIME_FAIL_CHANCE:
            fine = random.randint(10, 50)
            bal = max(0, md.get("balance", 0) - fine)
            await self.bot.db.update_member(interaction.user.id, interaction.guild.id, balance=bal, last_crime_time=now)
            await send_ephemeral(interaction, embed=error_embed("🚔 Fallaste", f"Te atraparon. Multa: {fine} 🪙\nSaldo: {bal:,} 🪙"))
        else:
            earned = random.randint(config.CRIME_MIN, config.CRIME_MAX)
            bal = md.get("balance", 0) + earned
            await self.bot.db.update_member(interaction.user.id, interaction.guild.id, balance=bal, last_crime_time=now, total_earned=md.get("total_earned", 0) + earned)
            await send_ephemeral(interaction, embed=success_embed("💰 Crimen exitoso", f"Ganaste {earned} 🪙\nSaldo: {bal:,} 🪙"))

    @app_commands.command(name="pay", description="Transferir monedas a un usuario")
    @app_commands.describe(user="Usuario", cantidad="Cantidad")
    async def pay(self, interaction: discord.Interaction, user: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        if user.id == interaction.user.id:
            return await send_ephemeral(interaction, embed=error_embed("❌", "No puedes pagarte a ti mismo."))
        if cantidad <= 0:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Cantidad inválida."))
        bal, _ = await self._get_bal(interaction.user.id, interaction.guild.id)
        if bal < cantidad:
            return await send_ephemeral(interaction, embed=error_embed("❌", f"No tienes suficiente. Tienes {bal:,} 🪙."))
        r_bal, _ = await self._get_bal(user.id, interaction.guild.id)
        await self._set_bal(interaction.user.id, interaction.guild.id, bal - cantidad)
        await self._set_bal(user.id, interaction.guild.id, r_bal + cantidad)
        await send_ephemeral(interaction, embed=success_embed("💸 Pago", f"Pagaste {cantidad:,} 🪙 a {user.mention}"))

    @app_commands.command(name="rob", description="Robar a un usuario")
    @app_commands.describe(user="Usuario")
    async def rob(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        if user.id == interaction.user.id:
            return await send_ephemeral(interaction, embed=error_embed("❌", "No puedes robarte a ti mismo."))
        bal, _ = await self._get_bal(user.id, interaction.guild.id)
        if bal < 50:
            return await send_ephemeral(interaction, embed=warning_embed("⚠️", f"{user.mention} es muy pobre para robar."))
        if random.random() < config.ROB_FAIL_CHANCE:
            fine = random.randint(5, 20)
            my_bal, _ = await self._get_bal(interaction.user.id, interaction.guild.id)
            await self._set_bal(interaction.user.id, interaction.guild.id, max(0, my_bal - fine))
            await send_ephemeral(interaction, embed=error_embed("🚔 Fallaste", f"Te atraparon. Multa: {fine} 🪙"))
        else:
            stolen = random.randint(config.ROB_MIN, config.ROB_MAX)
            my_bal, _ = await self._get_bal(interaction.user.id, interaction.guild.id)
            await self._set_bal(interaction.user.id, interaction.guild.id, my_bal + stolen)
            await self._set_bal(user.id, interaction.guild.id, bal - stolen)
            await send_ephemeral(interaction, embed=success_embed("🔫 Robo", f"Robaste {stolen} 🪙 a {user.mention}"))

    @app_commands.command(name="deposit", description="Depositar dinero al banco")
    @app_commands.describe(cantidad="Cantidad (o 'all')")
    async def deposit(self, interaction: discord.Interaction, cantidad: str):
        await interaction.response.defer(ephemeral=True)
        bal, bank = await self._get_bal(interaction.user.id, interaction.guild.id)
        if cantidad.lower() == "all":
            amount = bal
        else:
            try:
                amount = int(cantidad)
            except:
                return await send_ephemeral(interaction, embed=error_embed("❌", "Cantidad inválida."))
        if amount <= 0 or amount > bal:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Cantidad inválida."))
        await self._set_bal(interaction.user.id, interaction.guild.id, bal - amount, bank + amount)
        await send_ephemeral(interaction, embed=success_embed("🏦 Depositado", f"{amount} 🪙 → Banco ({bank+amount:,} 🪙)"))

    @app_commands.command(name="withdraw", description="Retirar dinero del banco")
    @app_commands.describe(cantidad="Cantidad (o 'all')")
    async def withdraw(self, interaction: discord.Interaction, cantidad: str):
        await interaction.response.defer(ephemeral=True)
        bal, bank = await self._get_bal(interaction.user.id, interaction.guild.id)
        if cantidad.lower() == "all":
            amount = bank
        else:
            try:
                amount = int(cantidad)
            except:
                return await send_ephemeral(interaction, embed=error_embed("❌", "Cantidad inválida."))
        if amount <= 0 or amount > bank:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Cantidad inválida."))
        await self._set_bal(interaction.user.id, interaction.guild.id, bal + amount, bank - amount)
        await send_ephemeral(interaction, embed=success_embed("🏦 Retirado", f"{amount} 🪙 → Efectivo ({bal+amount:,} 🪙)"))

    @app_commands.command(name="slots", description="Jugar a las tragamonedas")
    @app_commands.describe(apuesta="Cantidad a apostar")
    async def slots(self, interaction: discord.Interaction, apuesta: int):
        await interaction.response.defer(ephemeral=True)
        if apuesta < 1:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Apuesta mínima: 1"))
        bal, _ = await self._get_bal(interaction.user.id, interaction.guild.id)
        if bal < apuesta:
            return await send_ephemeral(interaction, embed=error_embed("❌", f"No tienes suficiente. Tienes {bal:,} 🪙"))
        symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "⭐", "🔔"]
        r1, r2, r3 = random.choices(symbols, k=3)
        matches = len({r1, r2, r3})
        multiplier = config.SLOTS_MULTIPLIERS.get(matches, 0)
        won = int(apuesta * multiplier)
        new_bal = bal - apuesta + won
        await self._set_bal(interaction.user.id, interaction.guild.id, new_bal)
        embed = PremiumEmbed(title="Slots", color=config.COLORS["gold"])
        embed.add_field(name="Resultado", value=f"`{r1}` `{r2}` `{r3}`f", inline=False)
        if won > 0:
            embed.add_field(name="Ganaste", value=f"+{won} (x{multiplier})f", inline=False)
        else:
            embed.add_field(name="Perdiste", value=f"-{apuesta}f", inline=False)
        embed.add_field(name="Saldo", value=f"{new_bal:,}f", inline=False)
        await send_ephemeral(interaction, embed=embed)

    @app_commands.command(name="roulette", description="Ruleta simple")
    @app_commands.describe(apuesta="Cantidad", tipo="red, black, odd, even, o número 1-10")
    async def roulette(self, interaction: discord.Interaction, apuesta: int, tipo: str):
        await interaction.response.defer(ephemeral=True)
        if apuesta < 1 or apuesta > config.ROULETTE_MAX:
            return await send_ephemeral(interaction, embed=error_embed("❌", f"Apuesta entre 1 y {config.ROULETTE_MAX}"))
        bal, _ = await self._get_bal(interaction.user.id, interaction.guild.id)
        if bal < apuesta:
            return await send_ephemeral(interaction, embed=error_embed("❌", "No tienes suficiente."))
        number = random.randint(0, 10)
        color = "red" if number % 2 == 0 else "black"
        odd_even = "even" if number % 2 == 0 else "odd"
        won = False
        multiplier = 0
        if tipo.lower() == "red" and color == "red":
            won, multiplier = True, 2
        elif tipo.lower() == "black" and color == "black":
            won, multiplier = True, 2
        elif tipo.lower() == "odd" and odd_even == "odd":
            won, multiplier = True, 2
        elif tipo.lower() == "even" and odd_even == "even":
            won, multiplier = True, 2
        elif tipo.isdigit() and int(tipo) == number:
            won, multiplier = True, 5
        amount = apuesta * multiplier if won else -apuesta
        new_bal = bal + amount
        await self._set_bal(interaction.user.id, interaction.guild.id, new_bal)
        embed = PremiumEmbed(title="Ruleta", color=config.COLORS["gold"])
        embed.add_field(name="Número", value=str(number), inline=True)
        embed.add_field(name="Color", value=color.capitalize(), inline=True)
        embed.add_field(name="Resultado", value=f"{' Ganaste' if won else ' Perdiste'} {amount:+}f", inline=False)
        embed.add_field(name="Saldo", value=f"{new_bal:,}f")
        await send_ephemeral(interaction, embed=embed)

    # ── Shop ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="shop", description="Ver tienda del servidor")
    async def shop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        items = await self.bot.db.get_shop_items(interaction.guild.id)
        if not items:
            return await send_ephemeral(interaction, embed=info_embed("🛒 Tienda vacía", "Usa `/shop_add` para agregar artículos."))
        embed = PremiumEmbed(title=f"🛒 Tienda · {interaction.guild.name}", color=config.COLORS["gold"])
        for item in items:
            embed.add_field(
                name=f"{item['emoji']} {item['name']}f",
                value=f"{item['description']}\n {item['price']:,} · `ID: {item['id']}`f",
                inline=False,
            )
        await send_ephemeral(interaction, embed=embed)

    @app_commands.command(name="buy", description="Comprar un artículo")
    @app_commands.describe(item_id="ID del artículo")
    async def buy(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)
        item = await self.bot.db.get_shop_item(item_id)
        if not item or item["guild_id"] != interaction.guild.id:
            return await send_ephemeral(interaction, embed=error_embed("❌", "Artículo no encontrado."))
        bal, _ = await self._get_bal(interaction.user.id, interaction.guild.id)
        if bal < item["price"]:
            return await send_ephemeral(interaction, embed=error_embed("❌", f"Necesitas {item['price']:,} 🪙, tienes {bal:,}."))
        if await self.bot.db.has_item(interaction.user.id, interaction.guild.id, item_id):
            return await send_ephemeral(interaction, embed=warning_embed("⚠️", "Ya tienes este artículo."))
        role = interaction.guild.get_role(item["role_id"])
        if not role:
            return await send_ephemeral(interaction, embed=error_embed("❌", "El rol ya no existe."))
        try:
            await interaction.user.add_roles(role, reason="Compra en tienda")
        except:
            return await send_ephemeral(interaction, embed=error_embed("❌", "No pude asignar el rol."))
        await self._set_bal(interaction.user.id, interaction.guild.id, bal - item["price"])
        await self.bot.db.buy_item(interaction.user.id, interaction.guild.id, item_id)
        await self.bot.db.update_member(interaction.user.id, interaction.guild.id, total_spent=(await self.bot.db.get_member(interaction.user.id, interaction.guild.id)).get("total_spent", 0) + item["price"])
        await send_ephemeral(interaction, embed=success_embed("🛍️ Comprado", f"{item['emoji']} {item['name']} por {item['price']:,} 🪙"))

    @app_commands.command(name="sell", description="Vender un artículo de tu inventario")
    @app_commands.describe(item_id="ID del artículo")
    async def sell(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)
        refund = await self.bot.db.sell_item(interaction.user.id, interaction.guild.id, item_id)
        if not refund:
            return await send_ephemeral(interaction, embed=error_embed("❌", "No tienes ese artículo."))
        bal, _ = await self._get_bal(interaction.user.id, interaction.guild.id)
        await self._set_bal(interaction.user.id, interaction.guild.id, bal + refund)
        await send_ephemeral(interaction, embed=success_embed("💰 Vendido", f"Recibiste {refund} 🪙 (50% del precio original)."))

    @app_commands.command(name="inventory", description="Ver tu inventario")
    @app_commands.describe(user="Usuario (opcional)")
    async def inventory(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.defer(ephemeral=True)
        items = await self.bot.db.get_inventory(user.id, interaction.guild.id)
        if not items:
            return await send_ephemeral(interaction, embed=info_embed("🎒", f"{user.mention} no tiene artículos."))
        embed = PremiumEmbed(title=f"🎒 Inventario de {user.display_name}", color=config.COLORS["purple"])
        for item in items:
            role = interaction.guild.get_role(item["role_id"])
            embed.add_field(
                name=f"{item['emoji']} {item['name']}f",
                value=f"Precio: {item['price']:,} \n{role.mention if role else ''}\n <t:{int(item['purchased_at'])}:R>f",
                inline=False,
            )
        await send_ephemeral(interaction, embed=embed)

    # ── Economy Admin ────────────────────────────────────────────────────────
    economy = app_commands.Group(name="economy", description="Admin economía")

    @economy.command(name="leaderboard", description="Ranking de economía")
    async def eco_lb(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows = await self.bot.db.get_leaderboard(interaction.guild.id, "balance", 50)
        if not rows:
            return await send_ephemeral(interaction, embed=info_embed("🏆", "Sin datos."))
        per_page = 10
        pages = []
        medals = ["🥇", "🥈", "🥉"]
        chunks = [rows[i:i+per_page] for i in range(0, len(rows), per_page)]
        for chunk_idx, chunk in enumerate(chunks):
            embed = PremiumEmbed(
                title=f"🏆 Ranking Económico · {interaction.guild.name}",
                color=config.COLORS["gold"],
            )
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            start_rank = chunk_idx * per_page + 1
            for i, r in enumerate(chunk):
                m = interaction.guild.get_member(r["user_id"])
                name = m.display_name if m else f"`{r['user_id']}`"
                rank = start_rank + i
                prefix = medals[i] if i < 3 else f"`#{rank}`"
                embed.add_field(
                    name=f"{prefix} {name}f",
                    value=f"`{r['balance']:,}` • `{r['bank']:,}`f",
                    inline=False,
                )
            total = await self.bot.db.fetchall(
                "SELECT COUNT(*) as c FROM members WHERE guild_id = ?", interaction.guild.id
            )
            embed.add_field(
                name="Totales",
                value=f"`{total[0]['c'] if total else 0}` miembros en el rankingf",
                inline=False,
            )
            pages.append(embed)
        if len(pages) <= 1:
            return await send_ephemeral(interaction, embed=pages[0])
        pag = ReactionPaginator(interaction, pages, timeout=60)
        await pag.start()

    @economy.command(name="add", description="Añadir monedas (admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario", cantidad="Cantidad")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_add(self, interaction: discord.Interaction, user: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        bal, _ = await self._get_bal(user.id, interaction.guild.id)
        await self._set_bal(user.id, interaction.guild.id, bal + cantidad)
        await send_ephemeral(interaction, embed=success_embed("➕ Monedas", f"{user.mention}: +{cantidad} 🪙"))

    @economy.command(name="remove", description="Quitar monedas (admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario", cantidad="Cantidad")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_remove(self, interaction: discord.Interaction, user: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        bal, _ = await self._get_bal(user.id, interaction.guild.id)
        await self._set_bal(user.id, interaction.guild.id, max(0, bal - cantidad))
        await send_ephemeral(interaction, embed=success_embed("➖ Monedas", f"{user.mention}: -{cantidad} 🪙"))

    @economy.command(name="set", description="Establecer monedas (admin)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario", cantidad="Nuevo balance")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_set(self, interaction: discord.Interaction, user: discord.Member, cantidad: int):
        await interaction.response.defer(ephemeral=True)
        await self._set_bal(user.id, interaction.guild.id, max(0, cantidad))
        await send_ephemeral(interaction, embed=success_embed("🔧 Balance", f"{user.mention}: {cantidad} 🪙"))

    @economy.command(name="reset", description="Resetear economía de un usuario")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user="Usuario")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_reset(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.update_member(user.id, interaction.guild.id, balance=config.STARTING_BALANCE, bank=0, total_earned=0, total_spent=0)
        await send_ephemeral(interaction, embed=success_embed("🔄 Economía reseteada", user.mention))

    @economy.command(name="shop_add", description="Añadir artículo a la tienda")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(name="Nombre", description="Descripción", role="Rol", price="Precio", emoji="Emoji")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_shop_add(self, interaction: discord.Interaction, name: str, description: str, role: discord.Role, price: int, emoji: str = "🎁"):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.add_shop_item(interaction.guild.id, name, description, role.id, price, emoji)
        await send_ephemeral(interaction, embed=success_embed("➕ Artículo", f"{emoji} {name} · {price} 🪙"))

    @economy.command(name="shop_remove", description="Quitar artículo de la tienda")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(item_id="ID del artículo")
    @app_commands.checks.has_permissions(administrator=True)
    async def eco_shop_remove(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)
        await self.bot.db.remove_shop_item(item_id, interaction.guild.id)
        await send_ephemeral(interaction, embed=success_embed("➖ Artículo quitado"))


async def setup(bot):
    await bot.add_cog(Economy(bot))
