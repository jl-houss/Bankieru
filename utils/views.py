from nextcord import ui, ButtonStyle, Interaction, Colour, Embed
from nextcord.ext.commands import Bot
from nextcord import PermissionOverwrite, utils
from datetime import datetime
from utils.constants import *
from utils.utils import DB


# Define a simple View that gives us a confirmation menu
class Confirm(ui.View):
    def __init__(self, confirm_message: str, cancel_message: str):
        super().__init__()
        self.confirm_message = confirm_message
        self.cancel_message = cancel_message
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    @ui.button(label="Confirm", style=ButtonStyle.green)
    async def confirm(self, button: ui.Button, interaction: Interaction):
        embed = Embed(title=self.confirm_message, color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @ui.button(label="Cancel", style=ButtonStyle.grey)
    async def cancel(self, button: ui.Button, interaction: Interaction):
        embed = Embed(title=self.cancel_message, color=Colour.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.value = False
        self.stop()

class AccountOpenView(ui.View):
    def __init__(self, client: Bot) -> None:
        super().__init__(timeout=None)
        self.client = client
        self.db: DB = client.db
        
    @ui.button(label="Open account", style=ButtonStyle.blurple, custom_id="open_account_button")
    async def open_account(self, button: ui.Button, interaction: Interaction):
        bank = await self.db.get_fetchone("SELECT * FROM banks WHERE guildId = ?", (interaction.guild.id,))
        account = await self.db.get_fetchone("SELECT * FROM accounts WHERE userId = ? AND bankId = ?", (interaction.user.id, bank[0]))

        if account:
            embed = Embed(title="You already have an account at this bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about opening a new account ?",
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_message="Account created !", cancel_message="Creation canceled !")
        await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)

        await confirmView.wait()

        if confirmView.value:
            perms = {
                interaction.guild.default_role : PermissionOverwrite(view_channel=False),
                interaction.user : PermissionOverwrite(view_channel=True)
            }
        
            bank_category = utils.get(self.client.get_guild(bank[1]).categories, id=bank[2])

            account_channel = await interaction.guild.create_text_channel(name=f"{interaction.user.name}-account", category=bank_category, overwrites=perms)

            mention_message = await account_channel.send(interaction.user.mention)
            await mention_message.delete()
            
            creation_date = datetime.now()

            account_channel_embed = Embed(
                title=f"Account of `{interaction.user.name}`",
                description=f"Created {creation_date.strftime('%A %d %B %Y')}",
                color=EMBED_COLOR,
            )
            account_channel_embed.add_field(name="Balance:", value=f"0.0{bank[6]}")
            account_channel_embed.set_thumbnail(url=interaction.user.avatar)
            panel_message = await account_channel.send(embed=account_channel_embed, view=AccountCloseView(self.client))
            
            await self.db.request("INSERT INTO accounts VALUES (?,?,?,?,?,?)", (interaction.user.id, bank[0], 0.00, creation_date, account_channel.id, panel_message.id),)
            
            logEmbed = Embed(title=f"Account created at `{bank[4]}` Bank !", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank[0]}")
            await self.client.get_channel(ACCOUNTS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank[3]).send(embed=logEmbed)
            
class AccountCloseView(ui.View):
    def __init__(self, client: Bot) -> None:
        super().__init__(timeout=None)
        self.client = client
        self.db: DB = client.db
        
    @ui.button(label="Close account", style=ButtonStyle.red, custom_id="close_account_button")
    async def close_account(self, button: ui.Button, interaction: Interaction):
        bank = await self.db.get_fetchone("SELECT * FROM banks WHERE guildId = ?", (interaction.guild.id,))
        account = await self.db.get_fetchone("SELECT * FROM accounts WHERE userId = ? AND bankId = ?", (interaction.user.id, bank[0]))

        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about closing your account ?",
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_message="Account closed !", cancel_message="Closing canceled !")
        await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)

        await confirmView.wait()

        if confirmView.value:
            account_channel = self.client.get_channel(account[4])
            await account_channel.delete()
            await self.db.request("DELETE FROM accounts WHERE userId = ?", (interaction.user.id,))
            
            logEmbed = Embed(title=f"Account closed at `{bank[4]}` Bank", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank[0]}")
            await self.client.get_channel(ACCOUNTS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank[3]).send(embed=logEmbed)