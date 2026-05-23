import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
import asyncio
import config
from utils.embeds import GuildEmbed, success_embed, error_embed
from utils.helpers import send_log


class Fun(commands.Cog):
    """🎮 Comandos de diversión — 8ball, memes, imágenes, interacciones."""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    async def _fetch_reddit(self, subreddit: str):
        try:
            async with self.session.get(f"https://www.reddit.com/r/{subreddit}/random.json", headers={"User-Agent": "Mozilla/5.0"}) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                if isinstance(data, list):
                    post = data[0]["data"]["children"][0]["data"]
                    return post.get("url") or post.get("url_overridden_by_dest") or None
                return None
        except:
            return None

    @app_commands.command(name="8ball", description="Pregúntale algo a la bola mágica")
    @app_commands.describe(pregunta="Tu pregunta")
    async def eightball(self, interaction: discord.Interaction, pregunta: str):
        lang = await self.bot.get_lang(interaction.guild.id)
        responses = [
            self.bot.t(lang, "fun.eightball_yes"),
            self.bot.t(lang, "fun.eightball_no"),
            self.bot.t(lang, "fun.eightball_maybe"),
            self.bot.t(lang, "fun.eightball_ask_again"),
            self.bot.t(lang, "fun.eightball_certainly"),
            self.bot.t(lang, "fun.eightball_unlikely"),
            self.bot.t(lang, "fun.eightball_definitely"),
            self.bot.t(lang, "fun.eightball_doubtful"),
            self.bot.t(lang, "fun.eightball_absolutely"),
            self.bot.t(lang, "fun.eightball_no_chance"),
            self.bot.t(lang, "fun.eightball_outlook_good"),
            self.bot.t(lang, "fun.eightball_better_not"),
        ]
        ans = random.choice(responses)
        embed = GuildEmbed(title=f"🎱 {self.bot.t(lang, 'fun.eightball_title')}", color=config.COLORS["purple"], guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "fun.eightball_question"), value=pregunta, inline=False)
        embed.add_field(name=self.bot.t(lang, "fun.eightball_answer"), value=f"**{ans}**", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="meme", description="Meme aleatorio de Reddit")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        url = await self._fetch_reddit("memes")
        if url:
            embed = GuildEmbed(title=self.bot.t(lang, "fun.meme_title"), color=config.EMBED_COLOR, guild=interaction.guild)
            embed.set_image(url=url)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.meme_error")))

    @app_commands.command(name="cat", description="Gato aleatorio")
    async def cat(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            async with self.session.get("https://api.thecatapi.com/v1/images/search") as r:
                if r.status == 200:
                    data = await r.json()
                    url = data[0]["url"]
                    embed = GuildEmbed(title=self.bot.t(lang, "fun.cat_title"), color=config.COLORS["orange"], guild=interaction.guild)
                    embed.set_image(url=url)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.cat_error")))
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.cat_error")))

    @app_commands.command(name="dog", description="Perro aleatorio")
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            async with self.session.get("https://dog.ceo/api/breeds/image/random") as r:
                if r.status == 200:
                    data = await r.json()
                    embed = GuildEmbed(title=self.bot.t(lang, "fun.dog_title"), color=config.COLORS["brown"], guild=interaction.guild)
                    embed.set_image(url=data["message"])
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.dog_error")))
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.dog_error")))

    @app_commands.command(name="hug", description="Abrázate con alguien")
    @app_commands.describe(user="Usuario")
    async def hug(self, interaction: discord.Interaction, user: discord.Member):
        lang = await self.bot.get_lang(interaction.guild.id)
        gifs = [x.strip() for x in self.bot.t(lang, "fun.hug_gifs").split(",") if x.strip()]
        url = random.choice(gifs) if gifs else "https://example.com/hug.gif"
        embed = GuildEmbed(title=self.bot.t(lang, "fun.hug_title"), color=config.COLORS["pink"], guild=interaction.guild)
        embed.set_image(url=url)
        embed.set_footer(text=self.bot.t(lang, "fun.hug_footer", user=interaction.user.display_name, target=user.display_name))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="kiss", description="Besa a alguien")
    @app_commands.describe(user="Usuario")
    async def kiss(self, interaction: discord.Interaction, user: discord.Member):
        lang = await self.bot.get_lang(interaction.guild.id)
        gifs = [x.strip() for x in self.bot.t(lang, "fun.kiss_gifs").split(",") if x.strip()]
        url = random.choice(gifs) if gifs else "https://example.com/kiss.gif"
        embed = GuildEmbed(title=self.bot.t(lang, "fun.kiss_title"), color=config.COLORS["pink"], guild=interaction.guild)
        embed.set_image(url=url)
        embed.set_footer(text=self.bot.t(lang, "fun.kiss_footer", user=interaction.user.display_name, target=user.display_name))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slap", description="Abofetea a alguien")
    @app_commands.describe(user="Usuario")
    async def slap(self, interaction: discord.Interaction, user: discord.Member):
        lang = await self.bot.get_lang(interaction.guild.id)
        gifs = [x.strip() for x in self.bot.t(lang, "fun.slap_gifs").split(",") if x.strip()]
        url = random.choice(gifs) if gifs else "https://example.com/slap.gif"
        embed = GuildEmbed(title=self.bot.t(lang, "fun.slap_title"), color=config.COLORS["red"], guild=interaction.guild)
        embed.set_image(url=url)
        embed.set_footer(text=self.bot.t(lang, "fun.slap_footer", user=interaction.user.display_name, target=user.display_name))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pat", description="Acaricia a alguien")
    @app_commands.describe(user="Usuario")
    async def pat(self, interaction: discord.Interaction, user: discord.Member):
        lang = await self.bot.get_lang(interaction.guild.id)
        gifs = [x.strip() for x in self.bot.t(lang, "fun.pat_gifs").split(",") if x.strip()]
        url = random.choice(gifs) if gifs else "https://example.com/pat.gif"
        embed = GuildEmbed(title=self.bot.t(lang, "fun.pat_title"), color=config.COLORS["green"], guild=interaction.guild)
        embed.set_image(url=url)
        embed.set_footer(text=self.bot.t(lang, "fun.pat_footer", user=interaction.user.display_name, target=user.display_name))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Cara o cruz")
    async def coinflip(self, interaction: discord.Interaction):
        lang = await self.bot.get_lang(interaction.guild.id)
        result = random.choice(["heads", "tails"])
        embed = GuildEmbed(title="🪙 " + self.bot.t(lang, "fun.coinflip_title"), color=config.COLORS["gold"], guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "fun.coinflip_result"), value=self.bot.t(lang, f"fun.coinflip_{result}"), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice", description="Lanzar dados")
    @app_commands.describe(sides="Número de caras")
    async def dice(self, interaction: discord.Interaction, sides: int = 6):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if sides < 2 or sides > 100:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.dice_error")))
        result = random.randint(1, sides)
        embed = GuildEmbed(title="🎲 " + self.bot.t(lang, "fun.dice_title"), color=config.EMBED_COLOR, guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "fun.dice_result"), value=self.bot.t(lang, "fun.dice_rolled", result=result, sides=sides), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="reverse", description="Invertir un texto")
    @app_commands.describe(text="Texto a invertir")
    async def reverse(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        reversed_text = text[::-1]
        embed = GuildEmbed(title=self.bot.t(lang, "fun.reverse_title"), color=config.EMBED_COLOR, guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "fun.reverse_original"), value=text[:1024], inline=False)
        embed.add_field(name=self.bot.t(lang, "fun.reverse_reversed"), value=reversed_text[:1024], inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="say", description="Haz que el bot diga algo")
    @app_commands.describe(text="Texto", ephemeral="Mensaje efímero")
    async def say(self, interaction: discord.Interaction, text: str, ephemeral: bool = False):
        await interaction.response.defer(ephemeral=ephemeral)
        await interaction.followup.send(content=text)

    @app_commands.command(name="mock", description="Convierte texto en esPOngEbOB")
    @app_commands.describe(text="Texto")
    async def mock(self, interaction: discord.Interaction, text: str):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        result = "".join(c.upper() if random.random() > 0.5 else c.lower() for c in text)
        embed = GuildEmbed(title=self.bot.t(lang, "fun.mock_title"), description=result, color=config.COLORS["yellow"], guild=interaction.guild)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="randomnumber", description="Número aleatorio en un rango")
    @app_commands.describe(min="Valor mínimo", max="Valor máximo")
    async def randomnumber(self, interaction: discord.Interaction, min: int = 1, max: int = 100):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        if min >= max:
            return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.rng_error")))
        result = random.randint(min, max)
        embed = GuildEmbed(title=self.bot.t(lang, "fun.rng_title"), color=config.COLORS["blue"], guild=interaction.guild)
        embed.add_field(name=self.bot.t(lang, "fun.rng_range", min=min, max=max), value=str(result), inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="github", description="Buscar un repo en GitHub")
    @app_commands.describe(repo="Nombre del repo (user/repo)")
    async def github(self, interaction: discord.Interaction, repo: str):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            async with self.session.get(f"https://api.github.com/repos/{repo}") as r:
                if r.status != 200:
                    return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.github_error")))
                data = await r.json()
                embed = GuildEmbed(title=data["full_name"], url=data["html_url"], description=data.get("description", self.bot.t(lang, "common.no_description")), color=config.COLORS["gray"], guild=interaction.guild)
                embed.set_thumbnail(url=data["owner"]["avatar_url"])
                embed.add_field(name=self.bot.t(lang, "fun.github_stars"), value=f"⭐ {data['stargazers_count']}", inline=True)
                embed.add_field(name=self.bot.t(lang, "fun.github_forks"), value=f"🍴 {data['forks_count']}", inline=True)
                embed.add_field(name=self.bot.t(lang, "fun.github_language"), value=data.get("language", self.bot.t(lang, "common.na")), inline=True)
                embed.add_field(name=self.bot.t(lang, "fun.github_open_issues"), value=str(data["open_issues_count"]), inline=True)
                embed.add_field(name=self.bot.t(lang, "fun.github_license"), value=data.get("license", {}).get("spdx_id", self.bot.t(lang, "common.na")) if data.get("license") else self.bot.t(lang, "common.na"), inline=True)
                await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.github_error")))

    @app_commands.command(name="urban", description="Buscar en Urban Dictionary")
    @app_commands.describe(term="Término")
    async def urban(self, interaction: discord.Interaction, term: str):
        await interaction.response.defer()
        lang = await self.bot.get_lang(interaction.guild.id)
        try:
            async with self.session.get(f"https://api.urbandictionary.com/v0/define", params={"term": term}) as r:
                if r.status != 200:
                    return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.urban_error")))
                data = await r.json()
                if not data.get("list"):
                    return await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.urban_not_found")))
                entry = data["list"][0]
                embed = GuildEmbed(title=self.bot.t(lang, "fun.urban_title", term=entry["word"]), url=entry["permalink"], description=entry["definition"][:1024], color=config.COLORS["blue"], guild=interaction.guild)
                embed.add_field(name=self.bot.t(lang, "fun.urban_example"), value=entry.get("example", self.bot.t(lang, "common.na"))[:1024] or self.bot.t(lang, "common.na"), inline=False)
                embed.set_footer(text=f"👍 {entry['thumbs_up']} 👎 {entry['thumbs_down']} — {self.bot.t(lang, 'fun.urban_author')}: {entry['author']}")
                await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(embed=error_embed(self.bot.t(lang, "errors.title"), self.bot.t(lang, "fun.urban_error")))


async def setup(bot):
    await bot.add_cog(Fun(bot))
