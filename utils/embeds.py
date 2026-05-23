import discord
import config


class GuildEmbed(discord.Embed):
    def __init__(self, title="", description="", color=config.EMBED_COLOR, guild=None, **kwargs):
        super().__init__(title=title, description=description, color=color, **kwargs)
        self.timestamp = discord.utils.utcnow()
        if guild:
            name = guild.name if hasattr(guild, "name") else str(guild)
            self.set_footer(text=name)

    def set_standard_footer(self, bot=None, guild=None):
        name = guild.name if guild and hasattr(guild, "name") else str(guild) if guild else ""
        if bot and bot.user:
            parts = [p for p in [name, bot.user.name] if p]
            self.set_footer(
                text="  ·  ".join(parts),
                icon_url=bot.user.display_avatar.url,
            )
        elif name:
            self.set_footer(text=name)
        return self


def success_embed(title, desc=""):
    e = GuildEmbed(title=title, description=desc, color=config.SUCCESS_COLOR)
    return e


def error_embed(title, desc=""):
    e = GuildEmbed(title=title, description=desc, color=config.ERROR_COLOR)
    return e


def warning_embed(title, desc=""):
    e = GuildEmbed(title=title, description=desc, color=config.WARNING_COLOR)
    return e


def info_embed(title, desc=""):
    e = GuildEmbed(title=title, description=desc, color=config.EMBED_COLOR)
    return e


def mod_embed(action, user, mod, reason, color=config.EMBED_COLOR):
    e = GuildEmbed(
        title=action,
        description=f"**Usuario:** {user.mention} (`{user.id}`)\n**Moderador:** {mod.mention}\n**Motivo:** {reason}",
        color=color,
    )
    e.set_thumbnail(url=user.display_avatar.url)
    return e


def stat_embed(title, fields_data, color=config.EMBED_COLOR):
    desc_lines = []
    for label, value in fields_data:
        desc_lines.append(f"**{label}**\n```{value}```")
    e = GuildEmbed(title=title, description="\n".join(desc_lines), color=color)
    return e


def panel_embed(title, description, color=config.EMBED_COLOR):
    e = GuildEmbed(
        title=f"\u2500" * 24 + f"\n{title}\n" + "\u2500" * 24,
        description=description,
        color=color,
    )
    return e


async def send_ephemeral(interaction, embed=None, content=None, view=None):
    kwargs = {"ephemeral": True}
    if embed:
        kwargs["embed"] = embed
    if content:
        kwargs["content"] = content
    if view:
        kwargs["view"] = view
    return await interaction.followup.send(**kwargs)
