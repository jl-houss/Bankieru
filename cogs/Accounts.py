from aiosqlite import Connection, Cursor
from nextcord.ext.commands import Bot, Cog

from utils.utils import DB
from utils.views import Confirm, AccountMessageView
from utils.constants import *

from datetime import datetime

from nextcord.ext import application_checks
from nextcord import (
    slash_command,
    Embed,
    Colour,
    Interaction,
    SlashOption,
    Message,
    TextChannel,
    ui,
    ButtonStyle,
    Member,
    PermissionOverwrite,
    utils,
    Message

)

class Accounts(Cog):
    def __init__(self, client: Bot) -> None:
        self.client = client
        self.db: DB = self.client.db

    @Cog.listener()
    async def on_ready(self):
        await self.db.request(
            """
            CREATE TABLE IF NOT EXISTS "accounts" (
                "userId"	    INTEGER NOT NULL UNIQUE,
                "bankId"	    INTEGER NOT NULL,
                "balance"	    REAL NOT NULL,
                "created_at"	TEXT NOT NULL,
                "accountChannelId" INTEGER NOT NULL UNIQUE,
                "accountMessageId" INTEGER NOT NULL UNIQUE,
                "helpChannelId" INTEGER UNIQUE,
                "transactionsChannelId" INTEGER NOT NULL UNIQUE,
                PRIMARY KEY("userId")
            );"""
        )
        
    @Cog.listener()
    async def on_message(self, message: Message):    
        account = await self.db.get_fetchone("SELECT * FROM accounts WHERE accountChannelId = ?", (message.channel.id,))
        
        if not account:
            return
        
        if message.embeds and message.embeds[0].title.startswith("Account of"):
            return
        
        if message.flags.ephemeral:
            return
        
        member = self.client.get_user(account[0])
        account_channel: TextChannel = self.client.get_channel(account[4])
        bank = await self.db.get_fetchone("SELECT * FROM banks WHERE bankId = ?", (account[1],))
        
        await account_channel.get_partial_message(account[5]).delete()
        
        creation_date = datetime.strptime(account[3], "%Y-%m-%d %H:%M:%S.%f")

        account_channel_embed = Embed(
            title=f"Account of `{member.name}`",
            description=f"Created {creation_date.strftime('%A %d %B %Y')}",
            color=EMBED_COLOR,
        )
        account_channel_embed.add_field(name="Balance:", value=f"{account[2]}{bank[6]}")
        account_channel_embed.set_thumbnail(url=member.avatar)
        panel_message = await account_channel.send(embed=account_channel_embed, view=AccountMessageView(self.client))
        
        await self.db.request("UPDATE accounts SET accountMessageId = ? WHERE accountChannelId = ?", (panel_message.id, account_channel.id))
    
    # @Cog.listener() #On_message to automatically delete normal messages in account channel
    # async def on_message(self, message : Message):
    #     bank_category_id = await self.db.get_fetchone("SELECT bankCategoryId FROM banks WHERE guildId=?", (message.guild.id,))
    #     bank_category_id = bank_category_id if bank_category_id else ["suii"]
    #     helpChannelId = await self.db.get_fetchone("SELECT helpChannelId FROM accounts WHERE userId = ?", (message.author.id,))

    #     if not message.guild:
    #         return
    #     if message.channel.category.id == bank_category_id[0] and not message.content.startswith("/") and message.author.id!=self.client.user.id:
    #         message_count = 0
    #         async for _ in message.channel.history(limit=None):
    #             message_count += 1

    #         if not "help" in message.channel.name:
    #             await message.delete()
            
    #         elif message_count==2 and message.channel.id==helpChannelId[0]:
    #             topg_role = [role for role in message.guild.roles if role.id==TOPG_ROLE][0]
    #             await message.channel.edit(name=f"{message.author.name} help🟡")
    #             await message.channel.send(topg_role.mention)
        

    @slash_command(name="account")
    async def account(self, interaction: Interaction):
        return

    @slash_command(name="send")
    async def send(
        self,
        interaction: Interaction,
        receiver: Member = SlashOption(
            name="to",
            description="To who'm do you want to send money",
            required=True),
        amount: float = SlashOption(name="amount", description="The amount to send", required=True),
    ):
        bank = await self.db.get_fetchone("SELECT * FROM banks WHERE guildId = ?", (interaction.guild.id,))
        if not bank:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_account = await self.db.get_fetchone(
            "SELECT * FROM accounts WHERE userId = ? AND bankId=?", (interaction.user.id, bank[0])
        )
        receiver_account = await self.db.get_fetchone(
            "SELECT * FROM accounts WHERE userId = ? AND bankId=?", (receiver.id, bank[0])
        )

        if not user_account:
            embed = Embed(
                title="You do not have an account at this bank !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not receiver_account:
            embed = Embed(
                title="The receiver does not have an account at this bank !",
                color=Colour.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if interaction.user == receiver:
            embed = Embed(
                title="You can't send money to yourself !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user_account[2] < amount:
            embed = Embed(title="You do not have enough money !", description=f"You only have ``{user_account[1]}{bank[6]}`` In your account", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user_account[4]!=interaction.channel.id:
            channel = self.client.get_channel(user_account[4])
            embed = Embed(title="You Cannot use this command here!", description=f"You can only use This command in Your account's channel : {channel.mention} .", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return 
    
        confirmEmbed = Embed(
            title="Confirmation",
            description=f"Are you sure about sending {amount}{bank[6]} to {receiver.name} ?",
            color=Colour.yellow(),
        )
        confirmView = Confirm(
            confirm_text=f"{amount}{bank[6]} have been transfered to `{receiver.name}` !",
            cancel_message="Transfer canceled !",
        )
        confirm_message = await interaction.response.send_message(
            embed=confirmEmbed, view=confirmView
        )

        await confirmView.wait()

        await confirm_message.delete()
        
        if confirmView.value:
            await self.db.request(
                "UPDATE accounts SET balance = ? WHERE userId = ? AND bankId = ?",
                (user_account[2] - amount, interaction.user.id, bank[0]),
            )
            await self.db.request(
                "UPDATE accounts SET balance = ? WHERE userId = ? AND bankId = ?",
                (receiver_account[2] + amount, receiver.id, bank[0]),
            )
            
            logEmbed = Embed(title=f"{interaction.user} sent `{amount}{bank[6]}` to {receiver} at `{bank[4]}` Bank", color=EMBED_COLOR)
            logEmbed_2 = Embed(title=f"You have received `{amount}{bank[6]}` from {interaction.user} at `{bank[4]}`", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank[0]}")
            await self.client.get_channel(TRANSACTIONS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank[3]).send(embed=logEmbed)
            await self.client.get_channel(receiver_account[7]).send(embed=logEmbed_2)
            

def setup(client: Bot):
    client.add_cog(Accounts(client))
