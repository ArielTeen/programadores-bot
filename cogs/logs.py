import discord
from discord.ext import commands
import datetime
import config
from utils.embeds import GuildEmbed
from utils.helpers import send_log


class Logs(commands.Cog):
    """📝 Logs del servidor — mensajes, miembros, canales, moderación."""

    def __init__(self, bot):
        self.bot = bot

    def format_time(self, dt=None):
        return (dt or discord.utils.utcnow()).strftime("%Y-%m-%d %H:%M:%S UTC")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        guild = message.guild
        lang = await self.bot.get_lang(guild.id)
        await self._log_event(guild, "message_delete", message.channel, desc=(
            f"**{self.bot.t(lang, 'logs.author_field')}:** {message.author} (`{message.author.id}`)\n"
            f"**{self.bot.t(lang, 'logs.channel_field')}:** {message.channel.mention}\n"
            f"**{self.bot.t(lang, 'logs.content_field')}:** {message.content or f'*{self.bot.t(lang, "logs.no_content")}*'}\n"
            f"**{self.bot.t(lang, 'panel.created')}:** {self.format_time(message.created_at)}"
        ), color=config.COLORS["red"], author=message.author)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return
        guild = before.guild
        lang = await self.bot.get_lang(guild.id)
        await self._log_event(guild, "message_edit", before.channel, desc=(
            f"**{self.bot.t(lang, 'logs.author_field')}:** {before.author} (`{before.author.id}`)\n"
            f"**{self.bot.t(lang, 'logs.channel_field')}:** {before.channel.mention}\n"
            f"**{self.bot.t(lang, 'logs.before_field')}:** {before.content or f'*{self.bot.t(lang, "logs.no_content")}*'}\n"
            f"**{self.bot.t(lang, 'logs.after_field')}:** {after.content or f'*{self.bot.t(lang, "logs.no_content")}*'}\n"
            f"[{self.bot.t(lang, 'reports.jump_to_msg')}]({after.jump_url})"
        ), color=config.COLORS["yellow"], author=before.author)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        lang = await self.bot.get_lang(guild.id)
        created = (discord.utils.utcnow() - member.created_at).days
        desc = (
            f"**{self.bot.t(lang, 'logs.user_field')}:** {member} (`{member.id}`)\n"
            f"**{self.bot.t(lang, 'welcome.account_created')}:** {self.format_time(member.created_at)} ({created} {self.bot.t(lang, 'common_time.days')})\n"
            f"**{self.bot.t(lang, 'welcome.members_field')}:** {len(guild.members)}"
        )
        await self._log_event(guild, "member_join", None, desc=desc, color=config.COLORS["green"], author=member)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        lang = await self.bot.get_lang(guild.id)
        joined = self.format_time(member.joined_at) if member.joined_at else self.bot.t(lang, "common.na")
        roles = ", ".join(r.mention for r in member.roles if r.name != "@everyone") or self.bot.t(lang, "common.none")
        desc = (
            f"**{self.bot.t(lang, 'logs.user_field')}:** {member} (`{member.id}`)\n"
            f"**{self.bot.t(lang, 'welcome.members_now')}:** {joined}\n"
            f"**{self.bot.t(lang, 'panel.roles')}:** {roles}"
        )
        await self._log_event(guild, "member_remove", None, desc=desc, color=config.COLORS["orange"], author=member)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        lang = await self.bot.get_lang(guild.id)
        desc = f"**{self.bot.t(lang, 'logs.user_field')}:** {user} (`{user.id}`)"
        await self._log_event(guild, "member_ban", None, desc=desc, color=config.COLORS["dark_red"], author=user)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        lang = await self.bot.get_lang(guild.id)
        desc = f"**{self.bot.t(lang, 'logs.user_field')}:** {user} (`{user.id}`)"
        await self._log_event(guild, "member_unban", None, desc=desc, color=config.COLORS["green"], author=user)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        guild = channel.guild
        lang = await self.bot.get_lang(guild.id)
        desc = f"**{self.bot.t(lang, 'logs.channel_field')}:** {channel.mention} (`{channel.id}`)\n**{self.bot.t(lang, 'logs.type_field')}:** {str(channel.type)}"
        await self._log_event(guild, "channel_create", None, desc=desc, color=config.COLORS["green"])

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        lang = await self.bot.get_lang(guild.id)
        desc = f"**{self.bot.t(lang, 'logs.channel_field')}:** #{channel.name} (`{channel.id}`)\n**{self.bot.t(lang, 'logs.type_field')}:** {str(channel.type)}"
        await self._log_event(guild, "channel_delete", None, desc=desc, color=config.COLORS["red"])

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        guild = role.guild
        lang = await self.bot.get_lang(guild.id)
        desc = f"**{self.bot.t(lang, 'logs.name_field')}:** {role.mention} (`{role.id}`)\n**{self.bot.t(lang, 'logs.color_field')}:** {role.color}"
        await self._log_event(guild, "role_create", None, desc=desc, color=config.COLORS["green"])

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        lang = await self.bot.get_lang(guild.id)
        desc = f"**{self.bot.t(lang, 'logs.name_field')}:** @{role.name} (`{role.id}`)"
        await self._log_event(guild, "role_delete", None, desc=desc, color=config.COLORS["red"])

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        guild = member.guild
        lang = await self.bot.get_lang(guild.id)
        action = []
        if before.channel != after.channel:
            if after.channel:
                action.append(f"**{self.bot.t(lang, 'logs.voice_connected')}** → {after.channel.mention}")
            if before.channel:
                action.append(f"**{self.bot.t(lang, 'logs.voice_disconnected')}** → {before.channel.mention}")
        if before.mute != after.mute and after.mute:
            action.append("🔇 **Server mute**")
        if before.deaf != after.deaf and after.deaf:
            action.append("🔇 **Server deaf**")
        if before.self_mute != after.self_mute and after.self_mute:
            action.append("🎤 **Self-mute**")
        if before.self_deaf != after.self_deaf and after.self_deaf:
            action.append("🎤 **Self-deaf**")
        if before.self_stream != after.self_stream and after.self_stream:
            action.append("🖥️ Streaming")
        if before.self_video != after.self_video and after.self_video:
            action.append("📷 Camera")
        if not action:
            return
        desc = f"**{self.bot.t(lang, 'logs.user_field')}:** {member} (`{member.id}`)\n" + "\n".join(action)
        await self._log_event(guild, "voice_state", None, desc=desc, color=config.COLORS["blue"], author=member)

    async def _log_event(self, guild, event_type, channel=None, desc="", color=None, author=None):
        log_channels = await self.bot.db.get_log_channels(guild.id)
        log_ch_id = log_channels.get(event_type)
        if not log_ch_id:
            log_ch_id = log_channels.get("all")
            if not log_ch_id:
                return
        log_ch = guild.get_channel(log_ch_id)
        if not log_ch:
            return
        lang = await self.bot.get_lang(guild.id)
        titles = {
            "message_delete": self.bot.t(lang, "logs.message_delete"),
            "message_edit": self.bot.t(lang, "logs.message_edit"),
            "member_join": self.bot.t(lang, "logs.member_join"),
            "member_remove": self.bot.t(lang, "logs.member_remove"),
            "member_ban": self.bot.t(lang, "logs.member_ban"),
            "member_unban": self.bot.t(lang, "logs.member_unban"),
            "channel_create": self.bot.t(lang, "logs.channel_create"),
            "channel_delete": self.bot.t(lang, "logs.channel_delete"),
            "role_create": self.bot.t(lang, "logs.role_create"),
            "role_delete": self.bot.t(lang, "logs.role_delete"),
            "voice_state": self.bot.t(lang, "logs.voice_state"),
        }
        embed = GuildEmbed(title=titles.get(event_type, "#️ Log"), description=desc, color=color or config.EMBED_COLOR, guild=guild)
        if channel:
            embed.add_field(name=self.bot.t(lang, "logs.channel"), value=channel.mention, inline=False)
        if author:
            embed.set_author(name=self.bot.t(lang, "logs.user") if author else "", icon_url=author.display_avatar.url)
        await log_ch.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Logs(bot))
