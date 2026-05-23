import discord


class ButtonPaginator(discord.ui.View):

    def __init__(self, pages, interaction, timeout=60, only_author=True):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.interaction = interaction
        self.only_author = only_author
        self.current = 0
        self.message = None

    async def start(self):
        if not self.pages:
            return
        self._update_buttons()
        embed = self._build_embed()
        await self.interaction.followup.send(embed=embed, view=self)
        self.message = await self.interaction.original_response()

    def _build_embed(self):
        embed = self.pages[self.current].copy()
        if len(self.pages) > 1:
            embed.set_footer(
            guild_name = self.interaction.guild.name if self.interaction.guild else ""
            footer = f"Pagina {self.current + 1}/{len(self.pages)}"
            if guild_name:
                footer += f"  ·  {guild_name}"
            embed.set_footer(
                text=footer,
                icon_url=(
                    self.interaction.client.user.display_avatar.url
                    if self.interaction.client and self.interaction.client.user
                    else None
                ),
            )
        return embed

    def _update_buttons(self):
        self.first_page.disabled = self.current == 0
        self.prev_page.disabled = self.current == 0
        self.next_page.disabled = self.current == len(self.pages) - 1
        self.last_page.disabled = self.current == len(self.pages) - 1

    @discord.ui.button(label="\u23ee", style=discord.ButtonStyle.secondary, row=0)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.only_author and interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("Solo quien uso el comando puede navegar.", ephemeral=True)
        self.current = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="\u25c0", style=discord.ButtonStyle.secondary, row=0)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.only_author and interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("Solo quien uso el comando puede navegar.", ephemeral=True)
        self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="\u25a0", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.only_author and interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("Solo quien uso el comando puede navegar.", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="\u25b6", style=discord.ButtonStyle.secondary, row=0)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.only_author and interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("Solo quien uso el comando puede navegar.", ephemeral=True)
        self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    @discord.ui.button(label="\u23ed", style=discord.ButtonStyle.secondary, row=0)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.only_author and interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("Solo quien uso el comando puede navegar.", ephemeral=True)
        self.current = len(self.pages) - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self._build_embed(), view=self)

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass


class ReactionPaginator:

    def __init__(self, interaction, pages, timeout=60, only_author=True):
        self.interaction = interaction
        self.pages = pages
        self.timeout = timeout
        self.only_author = only_author
        self.current = 0
        self.message = None
        self.running = False
        self._controls = {
            "\u23ee": self._first,
            "\u25c0": self._prev,
            "\u25a0": self._stop,
            "\u25b6": self._next,
            "\u23ed": self._last,
        }

    async def start(self):
        if not self.pages:
            return
        embed = self.pages[0].copy()
        if len(self.pages) > 1:
            guild_name = self.interaction.guild.name if self.interaction.guild else ""
            footer = f"Pagina 1/{len(self.pages)}"
            if guild_name:
                footer += f"  ·  {guild_name}"
            embed.set_footer(
                text=footer,
                icon_url=(
                    self.interaction.client.user.display_avatar.url
                    if self.interaction.client and self.interaction.client.user
                    else None
                ),
            )
        await self.interaction.followup.send(embed=embed)
        msg = await self.interaction.original_response()
        self.message = msg
        self.running = True
        if len(self.pages) <= 1:
            return
        for reaction in self._controls:
            await msg.add_reaction(reaction)

        def check(reaction, user):
            if user.bot:
                return False
            if reaction.message.id != msg.id:
                return False
            if self.only_author and user.id != self.interaction.user.id:
                return False
            return str(reaction.emoji) in self._controls

        import asyncio
        while self.running:
            try:
                reaction, user = await self.interaction.client.wait_for(
                    "reaction_add", timeout=self.timeout, check=check
                )
            except asyncio.TimeoutError:
                await self._cleanup()
                return
            handler = self._controls.get(str(reaction.emoji))
            if handler:
                await handler()
            try:
                await reaction.remove(user)
            except (discord.Forbidden, discord.HTTPException):
                pass
        await self._cleanup()

    async def _first(self):
        if self.current != 0:
            self.current = 0
            await self._update()

    async def _prev(self):
        if self.current > 0:
            self.current -= 1
            await self._update()

    async def _next(self):
        if self.current < len(self.pages) - 1:
            self.current += 1
            await self._update()

    async def _last(self):
        if self.current != len(self.pages) - 1:
            self.current = len(self.pages) - 1
            await self._update()

    async def _stop(self):
        self.running = False
        await self._cleanup()

    async def _update(self):
        embed = self.pages[self.current].copy()
        guild_name = self.interaction.guild.name if self.interaction.guild else ""
        footer = f"Pagina {self.current + 1}/{len(self.pages)}"
        if guild_name:
            footer += f"  ·  {guild_name}"
        embed.set_footer(
            text=footer,
            icon_url=(
                self.interaction.client.user.display_avatar.url
                if self.interaction.client and self.interaction.client.user
                else None
            ),
        )
        try:
            await self.message.edit(embed=embed)
        except (discord.NotFound, discord.HTTPException):
            self.running = False

    async def _cleanup(self):
        if self.message:
            try:
                await self.message.clear_reactions()
            except (discord.Forbidden, discord.HTTPException):
                try:
                    await self.message.delete()
                except:
                    pass
