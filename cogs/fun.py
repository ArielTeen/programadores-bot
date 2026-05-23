import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import config
from utils.embeds import PremiumEmbed, success_embed, info_embed


class Fun(commands.Cog):
    """🎮 Comandos de diversión — 8ball, meme, hug, ship, etc."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="8ball", description="🔮 Pregúntale a la bola mágica")
    @app_commands.describe(pregunta="Tu pregunta")
    async def eightball(self, interaction: discord.Interaction, pregunta: str):
        respuestas = [
            "Sí", "No", "Tal vez", "Claramente", "Ni lo sueñes", "Por supuesto",
            "No cuentes con ello", "Absolutamente", "Mejor no te digo", "Sin duda",
            "Las señales apuntan a que sí", "Muy dudoso", "Concéntrate y pregunta otra vez",
            "Definitivamente sí", "No puedo predecirlo ahora", "Pregunta más tarde",
        ]
        await interaction.response.send_message(
            embed=PremiumEmbed(title="🔮 8Ball", description=f"**Pregunta:** {pregunta}\n**Respuesta:** {random.choice(respuestas)}", color=config.COLORS["purple"])
        )

    @app_commands.command(name="meme", description="😂 Ver un meme aleatorio")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://meme-api.com/gimme") as r:
                    if r.status == 200:
                        data = await r.json()
                        e = PremiumEmbed(title=data.get("title", "😂 Meme"), color=config.EMBED_COLOR)
                        e.set_image(url=data.get("url", ""))
                        e.set_footer(text=f"👍 {data.get('ups', 0)} | r/{data.get('subreddit', '')}")
                        await interaction.followup.send(embed=e)
                        return
            await interaction.followup.send(embed=info_embed("😂", "No pude obtener un meme."))
        except:
            await interaction.followup.send(embed=info_embed("😂", "Error."))

    @app_commands.command(name="joke", description="😂 Contar un chiste")
    async def joke(self, interaction: discord.Interaction):
        await interaction.response.defer()
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://v2.jokeapi.dev/joke/Any?lang=es") as r:
                    if r.status == 200:
                        data = await r.json()
                        if data.get("type") == "single":
                            desc = data.get("joke", "")
                        else:
                            desc = f"{data.get('setup', '')}\n\n**{data.get('delivery', '')}**"
                        await interaction.followup.send(embed=info_embed("😂 Chiste", desc))
                        return
            await interaction.followup.send(embed=info_embed("😂", "No encontré chiste."))
        except:
            await interaction.followup.send(embed=info_embed("😂", "Error."))

    @app_commands.command(name="cat", description="🐱 Ver un gato")
    async def cat(self, interaction: discord.Interaction):
        await interaction.response.defer()
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.thecatapi.com/v1/images/search") as r:
                    if r.status == 200:
                        data = await r.json()
                        await interaction.followup.send(embed=PremiumEmbed(title="🐱 Gato", color=config.EMBED_COLOR).set_image(url=data[0]["url"]))
                        return
            await interaction.followup.send(embed=info_embed("🐱", "Error."))
        except:
            await interaction.followup.send(embed=info_embed("🐱", "Error."))

    @app_commands.command(name="dog", description="🐶 Ver un perro")
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.defer()
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://dog.ceo/api/breeds/image/random") as r:
                    if r.status == 200:
                        data = await r.json()
                        await interaction.followup.send(embed=PremiumEmbed(title="🐶 Perro", color=config.EMBED_COLOR).set_image(url=data["message"]))
                        return
            await interaction.followup.send(embed=info_embed("🐶", "Error."))
        except:
            await interaction.followup.send(embed=info_embed("🐶", "Error."))

    @app_commands.command(name="hug", description="🤗 Abrazar a alguien")
    @app_commands.describe(user="Usuario")
    async def hug(self, interaction: discord.Interaction, user: discord.Member):
        gifs = ["https://media.tenor.com/2SXmGp_fB1YAAAAC/hug-anime.gif", "https://media.tenor.com/QG9YVFh6c4MAAAAC/hug-anime.gif"]
        e = PremiumEmbed(title="🤗 Abrazo!", description=f"{interaction.user.mention} abrazó a {user.mention}", color=config.COLORS["pink"])
        e.set_image(url=random.choice(gifs))
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="kiss", description="😘 Besar a alguien")
    @app_commands.describe(user="Usuario")
    async def kiss(self, interaction: discord.Interaction, user: discord.Member):
        gifs = ["https://media.tenor.com/CvaBWw3BoFYAAAAC/anime-kiss.gif"]
        e = PremiumEmbed(title="😘 Beso!", description=f"{interaction.user.mention} besó a {user.mention}", color=config.COLORS["pink"])
        e.set_image(url=random.choice(gifs))
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="pat", description="👋 Acariciar a alguien")
    @app_commands.describe(user="Usuario")
    async def pat(self, interaction: discord.Interaction, user: discord.Member):
        gifs = ["https://media.tenor.com/BjA5I6uVq1MAAAAC/pat-cat.gif"]
        e = PremiumEmbed(title="👋 Caricia!", description=f"{interaction.user.mention} acarició a {user.mention}", color=config.COLORS["pink"])
        e.set_image(url=random.choice(gifs))
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="slap", description="🖐️ Abofetear a alguien")
    @app_commands.describe(user="Usuario")
    async def slap(self, interaction: discord.Interaction, user: discord.Member):
        gifs = ["https://media.tenor.com/LVgSxZk7wpgAAAAC/anime-slap.gif"]
        e = PremiumEmbed(title="🖐️ Bofetada!", description=f"{interaction.user.mention} abofeteó a {user.mention}", color=config.COLORS["red"])
        e.set_image(url=random.choice(gifs))
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="ship", description="💕 Medir compatibilidad entre dos usuarios")
    @app_commands.describe(user1="Usuario 1", user2="Usuario 2")
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member = None):
        user2 = user2 or interaction.user
        ship_value = (user1.id + user2.id) % 101
        hearts = "❤️" * (ship_value // 10) + "🖤" * (10 - ship_value // 10)
        e = PremiumEmbed(title="💕 Ship", color=config.COLORS["pink"])
        e.add_field(name="Compatibilidad", value=f"{user1.mention} x {user2.mention}\n**{ship_value}%**\n{hearts}", inline=False)
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="rate", description="⭐ Calificar algo")
    @app_commands.describe(algo="Algo a calificar")
    async def rate(self, interaction: discord.Interaction, algo: str):
        rating = (hash(algo) % 101)
        stars = "⭐" * (rating // 10) + "☆" * (10 - rating // 10)
        await interaction.response.send_message(embed=info_embed("⭐ Rating", f"**{algo}**\n{rating}%\n{stars}"))

    @app_commands.command(name="reverse", description="🔄 Invertir texto")
    @app_commands.describe(texto="Texto a invertir")
    async def reverse(self, interaction: discord.Interaction, texto: str):
        await interaction.response.send_message(embed=info_embed("🔄 Invertido", texto[::-1]))

    @app_commands.command(name="choose", description="🤔 Elegir entre opciones")
    @app_commands.describe(opciones="Opciones separadas por |")
    async def choose(self, interaction: discord.Interaction, opciones: str):
        opts = [o.strip() for o in opciones.split("|")]
        choice = random.choice(opts)
        await interaction.response.send_message(embed=info_embed("🤔 Elegido", f"Entre: `{'`, `'.join(opts)}`\n→ **{choice}**"))

    @app_commands.command(name="rps", description="✊ Piedra, papel o tijera")
    @app_commands.describe(eleccion="piedra, papel o tijera")
    async def rps(self, interaction: discord.Interaction, eleccion: str):
        choices = {"piedra": "🪨", "papel": "📄", "tijera": "✂️"}
        if eleccion.lower() not in choices:
            return await interaction.response.send_message("Elige: piedra, papel o tijera", ephemeral=True)
        bot = random.choice(list(choices.keys()))
        result = {("piedra", "tijera"): "Ganaste!", ("tijera", "papel"): "Ganaste!", ("papel", "piedra"): "Ganaste!"}
        outcome = result.get((eleccion.lower(), bot), result.get((bot, eleccion.lower()), "Empate!"))
        e = info_embed("✊ RPS", f"Tú: {choices[eleccion.lower()]} {eleccion}\nBot: {choices[bot]} {bot}\n**{outcome}**")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="trivia", description="🧠 Pregunta de trivia")
    async def trivia(self, interaction: discord.Interaction):
        await interaction.response.defer()
        import aiohttp
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://opentdb.com/api.php?amount=1&type=multiple&lang=es") as r:
                    if r.status == 200:
                        data = await r.json()
                        q = data["results"][0]
                        import html
                        e = PremiumEmbed(title="🧠 Trivia", description=f"**{html.unescape(q['question'])}**\nCategoría: {q['category']} | Dificultad: {q['difficulty']}", color=config.EMBED_COLOR)
                        await interaction.followup.send(embed=e)
                        return
            await interaction.followup.send(embed=info_embed("🧠", "Error."))
        except:
            await interaction.followup.send(embed=info_embed("🧠", "Error."))


async def setup(bot):
    await bot.add_cog(Fun(bot))
