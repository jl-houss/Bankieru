
from utils.constants import *
from utils.utils import DB

from nextcord import ui, ButtonStyle, Interaction, Colour, Embed, Message, errors, PermissionOverwrite, utils
from nextcord.ext.commands import Bot
from datetime import datetime
from asyncio import TimeoutError, sleep


# Define a simple View that gives us a confirmation menu
class Confirm(ui.View):
    def __init__(self, confirm_text: str, cancel_message: str):
        super().__init__()
        self.confirm_text = confirm_text
        self.cancel_message = cancel_message
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    @ui.button(label="Confirm", style=ButtonStyle.green)
    async def confirm(self, button: ui.Button, interaction: Interaction):
        embed = Embed(title=self.confirm_text, color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=2)
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @ui.button(label="Cancel", style=ButtonStyle.grey)
    async def cancel(self, button: ui.Button, interaction: Interaction):
        embed = Embed(title=self.cancel_message, color=Colour.red())
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=2)
        self.value = False
        self.stop()
        

class AccountOpenView(ui.View):
    def __init__(self, client: Bot) -> None:
        super().__init__(timeout=None)
        self.client = client
        self.db: DB = client.db
        
    @ui.button(label="Open account", style=ButtonStyle.blurple, custom_id="open_account_button")
    async def open_account(self, button: ui.Button, interaction: Interaction):
        bank_id, bank_name, currency_code, bank_category_id, bank_logs_channel_id = await self.db.get_fetchone("SELECT bank_id, name, currency_code, bank_category_id, logs_channel_id FROM banks WHERE guild_id = ?", (interaction.guild.id,))

        if await self.db.get_fetchone("SELECT * FROM accounts WHERE user_id = ? AND bank_id = ?", (interaction.user.id, bank_id)):
            embed = Embed(title="You already have an account at this bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about opening an account ?",
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_text="Account created !", cancel_message="Creation canceled !")
        confirm_message = await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)

        await confirmView.wait()

        await confirm_message.delete()

        if confirmView.value:
            perms = {
                interaction.guild.default_role : PermissionOverwrite(view_channel=False),
                interaction.user : PermissionOverwrite(view_channel=True)
            }
        
            bank_category = utils.get(self.client.get_guild(interaction.guild.id).categories, id=bank_category_id)

            account_channel = await interaction.guild.create_text_channel(name=f"{interaction.user.name}-account", category=bank_category, overwrites=perms)
            transactions_channel = await account_channel.create_thread(name="Transactions")
            
            creation_date = datetime.now()

            panel_embed = Embed(
                title=f"Account of `{interaction.user.name}`",
                description=f"Created {creation_date.strftime('%A %d %B %Y')}",
                color=EMBED_COLOR,
            )
            panel_embed.add_field(name="Balance:", value=f"`0.0`{currency_code}")
            panel_embed.set_thumbnail(url=interaction.user.avatar)
            await account_channel.send(embed=panel_embed, view=AccountPanel(self.client))

            tc_embed = Embed(title=f"Transactions Logs", description="These are the logs of all your transactions.", color=EMBED_COLOR)
            tc_embed.set_thumbnail(url=interaction.user.avatar)
            await transactions_channel.send(embed=tc_embed)
            
            mention = await account_channel.send(interaction.user.mention)
            await mention.delete()
            mention = await transactions_channel.send(interaction.user.mention)
            await mention.delete()
            
            await self.db.request("INSERT INTO accounts VALUES (?,?,?,?,?,?,?)", (interaction.user.id, bank_id, 0.00, creation_date, account_channel.id, None, transactions_channel.id))
            
            logEmbed = Embed(title=f"Account created at `{bank_name}` Bank !", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank_id}")
            await self.client.get_channel(ACCOUNTS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank_logs_channel_id).send(embed=logEmbed)
            

class AccountPanel(ui.View):
    def __init__(self, client: Bot) -> None:
        super().__init__(timeout=None)
        self.client = client
        self.db: DB = client.db
        
    @ui.button(label="Close account", style=ButtonStyle.red, custom_id="close_account_button")
    async def close_account(self, button: ui.Button, interaction: Interaction):
        bank_id, bank_name, bank_logs_channel_id = await self.db.get_fetchone("SELECT bank_id, name, logs_channel_id FROM banks WHERE guild_id = ?", (interaction.guild.id,))
        panel_id, = await self.db.get_fetchone("SELECT panel_channel_id FROM accounts WHERE panel_channel_id = ?", (interaction.channel.id,))

        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about closing your account ?",
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_text="Account closed !", cancel_message="Closing canceled !")
        confirm_message = await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)

        await confirmView.wait()

        await confirm_message.delete()

        if confirmView.value:
            await sleep(2.5)
            account_channel = self.client.get_channel(panel_id)
            await account_channel.delete()
            await self.db.request("DELETE FROM accounts WHERE panel_channel_id = ?", (panel_id,))
            
            logEmbed = Embed(title=f"Account closed at `{bank_name}` Bank", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank_id}")
            await self.client.get_channel(ACCOUNTS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank_logs_channel_id).send(embed=logEmbed)


    @ui.button(label="Help", style=ButtonStyle.blurple, custom_id="request_help_button")
    async def account_help(self, button: ui.Button, interaction: Interaction):
        user_id, help_channel_id  = await self.db.get_fetchone("SELECT user_id, help_channel_id from accounts WHERE panel_channel_id = ?", (interaction.channel.id,))
        
        if user_id != interaction.user.id:
            alert_embed = Embed(
                title="You are not the owner of this account !",
                description=f"Only {self.client.get_user(user_id).mention} can use this.",
                color=EMBED_COLOR
            )
            await interaction.response.send_message(embed=alert_embed, ephemeral=True)
            return

        if help_channel_id:
            help_channel = self.client.get_channel(help_channel_id)
            alert_embed = Embed(
                title="You already have a help thread !", 
                description=f"This is your help thread {help_channel.mention}.", 
                color=EMBED_COLOR
            )
            await interaction.response.send_message(embed=alert_embed, ephemeral=True)
            await help_channel.send(interaction.user.mention)
            return
        
        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about opening a help thread ?",
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_text="Help thread created !", cancel_message="Help thread creation canceled.")
        confirm_message = await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)

        await confirmView.wait()

        await confirm_message.delete()

        if confirmView.value:
            new_help_channel = await interaction.channel.create_thread(name="Help")

            await self.db.request("UPDATE accounts SET help_channel_id = ? WHERE user_id = ?", (new_help_channel.id, interaction.user.id))

            help_embed = Embed(
                title=f"Account Help", 
                description=f"{interaction.user.mention} this is your help thread.\nPlease explain in detail your problem, the admins will help you.", 
                color=EMBED_COLOR
            )
            help_embed.set_thumbnail(url=interaction.user.avatar)
            await new_help_channel.send(embed=help_embed, view=HelpPanel(self.client))
            await new_help_channel.send(interaction.user.mention, delete_after=1)

            def is_allowed(message: Message):
                return message.author.id == interaction.user.id and message.channel.id == new_help_channel.id

            try:
                await self.client.wait_for("message", timeout=1800, check=is_allowed)
            except TimeoutError:                
                await self.db.request("UPDATE accounts SET help_channel_id = ? WHERE help_channel_id = ?", (None, new_help_channel.id,))
                
                await new_help_channel.delete()
                return
            else:
                await new_help_channel.send(f"<@&{TOPG_ROLE}>", delete_after=1)

class HelpPanel(ui.View):
    def __init__(self, client: Bot) -> None:
        super().__init__(timeout=None)
        self.client = client
        self.db: DB = client.db

    @ui.button(label="Close", style=ButtonStyle.red, custom_id="close_help_channel")
    async def close_help_channel(self, button: ui.Button, interaction: Interaction):
        help_channel_id, = await self.db.get_fetchone("SELECT help_channel_id from accounts WHERE help_channel_id = ?", (interaction.channel.id,))
        help_channel = self.client.get_channel(help_channel_id)

        if not help_channel_id:
            await interaction.response.send_message("This is not a help channel anymore, You can delete it")
            return
        
        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about closing your help thread ?",
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_text="Help thread closed !", cancel_message="Help thread closing canceled.")
        confirm_message = await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)

        await confirmView.wait()

        await confirm_message.delete()

        if confirmView.value:
            await self.db.request("UPDATE accounts SET help_channel_id = ? WHERE help_channel_id = ?", (None, help_channel_id,))
            await sleep(2.5)
            await help_channel.delete()