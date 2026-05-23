import discord
from discord.ext import commands


def has_staff():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        g = await ctx.bot.db.get_guild(ctx.guild.id)
        sr = g.get("staff_roles", [])
        for rid in sr:
            r = ctx.guild.get_role(rid)
            if r and r in ctx.author.roles:
                return True
        return False
    return commands.check(predicate)

def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def is_owner():
    async def predicate(ctx):
        return await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)

def bot_perms(**perms):
    async def predicate(ctx):
        missing = [p for p, v in perms.items() if not getattr(ctx.guild.me.guild_permissions, p, False)]
        if missing:
            emb = discord.Embed(
                title="❌ Permisos insuficientes",
                description=f"No tengo: `{'`, `'.join(missing)}`",
                color=0xED4245,
            )
            await ctx.send(embed=emb, ephemeral=True)
            return False
        return True
    return commands.check(predicate)

def user_perms(**perms):
    async def predicate(ctx):
        missing = [p for p, v in perms.items() if not getattr(ctx.author.guild_permissions, p, False)]
        if missing:
            emb = discord.Embed(
                title="❌ No tienes permisos",
                description=f"Necesitas: `{'`, `'.join(missing)}`",
                color=0xED4245,
            )
            await ctx.send(embed=emb, ephemeral=True)
            return False
        return True
    return commands.check(predicate)
