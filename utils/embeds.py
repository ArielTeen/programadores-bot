import discord
import config


class PremiumEmbed(discord.Embed):
    def __init__(self, title="", description="", color=config.EMBED_COLOR, **kwargs):
        super().__init__(title=title, description=description, color=color, **kwargs)
        self.timestamp = discord.utils.utcnow()

    def set_standard_footer(self, bot=None):
        if bot and bot.user:
            self.set_footer(
                text=f"Teen Bot Premium  {bot.user.name}",
                icon_url=bot.user.display_avatar.url,
            )
        else:
            self.set_footer(text="Teen Bot Premium")
        return self


def success_embed(title, desc=""):
    e = PremiumEmbed(title=title, description=desc, color=config.SUCCESS_COLOR)
    return e


def error_embed(title, desc=""):
    e = PremiumEmbed(title=title, description=desc, color=config.ERROR_COLOR)
    return e


def warning_embed(title, desc=""):
    e = PremiumEmbed(title=title, description=desc, color=config.WARNING_COLOR)
    return e


def info_embed(title, desc=""):
    e = PremiumEmbed(title=title, description=desc, color=config.EMBED_COLOR)
    return e


def mod_embed(action, user, mod, reason, color=config.EMBED_COLOR):
    e = PremiumEmbed(
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
    e = PremiumEmbed(title=title, description="\n".join(desc_lines), color=color)
    return e


def panel_embed(title, description, color=config.EMBED_COLOR):
    e = PremiumEmbed(
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
