from aiosqlite import Connection, Cursor
from nextcord.ext.commands import Bot, Cog

from utils.utils import DB
from utils.views import Confirm
from utils.constants import *

from datetime import datetime

from nextcord.ext import application_checks
from nextcord import (
    slash_command,
    Embed,
    Colour,
    Interaction,
    SlashOption,
    TextChannel,
    ui,
    ButtonStyle,
    Member,
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
                PRIMARY KEY("userId")
            );"""
        )

    @slash_command(name="account")
    async def account(self, interaction: Interaction):
        return

    @account.subcommand(name="open")
    async def open(self, interaction: Interaction):
        bank = await self.db.get_fetchone(
            "SELECT * FROM banks WHERE guildId = ?", (interaction.guild.id,)
        )

        if not bank:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        account = await self.db.get_fetchone(
            "SELECT * FROM accounts WHERE userId = ? AND bankId = ?", (interaction.user.id, bank[0])
        )

        if account:
            embed = Embed(
                title="You already have an account at this bank !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about opening a new account ?",
            color=Colour.yellow(),
        )
        confirmView = Confirm(confirm_message="Account created !", cancel_message="Creation canceled !")
        await interaction.response.send_message(
            embed=confirmEmbed, view=confirmView, ephemeral=True
        )

        await confirmView.wait()

        if confirmView.value:
            await self.db.request(
                "INSERT INTO accounts VALUES (?,?,?,?)",
                (interaction.user.id, bank[0], 0.00, datetime.now()),
            )
            
            logEmbed = Embed(title=f"Account created at `{bank[4]}` Bank !", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank[0]}")
            await self.client.get_channel(ACCOUNTS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank[3]).send(embed=logEmbed)
            

    @account.subcommand(name="close")
    async def close(self, interaction: Interaction):
        bank = await self.db.get_fetchone(
            "SELECT * FROM banks WHERE guildId = ?", (interaction.guild.id,)
        )
        if not bank:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        account = await self.db.get_fetchone(
            "SELECT * FROM accounts WHERE userId = ? AND bankId = ?", (interaction.user.id, bank[0])
        )

        if not account:
            embed = Embed(
                title="You do not have an account at this bank !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about closing your account ?",
            color=Colour.yellow(),
        )
        confirmView = Confirm(confirm_message="Account closed !", cancel_message="Closing canceled !")
        await interaction.response.send_message(
            embed=confirmEmbed, view=confirmView, ephemeral=True
        )

        await confirmView.wait()

        if confirmView.value:
            await self.db.request(
                "DELETE FROM accounts WHERE userId = ?", (interaction.user.id,)
            )
            
            logEmbed = Embed(title=f"Account closed at `{bank[4]}` Bank", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank[0]}")
            await self.client.get_channel(ACCOUNTS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank[3]).send(embed=logEmbed)

    @account.subcommand(name="info")
    async def info(self, interaction: Interaction):
        bank = await self.db.get_fetchone(
            "SELECT * FROM banks WHERE guildId = ?", (interaction.guild.id,)
        )
        if not bank:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        account = await self.db.get_fetchone(
            "SELECT * FROM accounts WHERE userId = ? AND bankId = ?", (interaction.user.id, bank[0])
        )
        if not account:
            embed = Embed(
                title="You do not have an account at this bank !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        creation_date = datetime.strptime(account[3], "%Y-%m-%d %H:%M:%S.%f")

        embed = Embed(
            title=f"Account of `{interaction.user.name}`",
            description=f"Created {creation_date.strftime('%A %d %B %Y')}",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Balance:", value=f"{account[2]}{bank[6]}")
        embed.set_thumbnail(url=interaction.user.avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @slash_command(name="send")
    async def send(
        self,
        interaction: Interaction,
        receiver: Member = SlashOption(
            name="receiver",
            description="To who'm do you want to send money",
            required=True,
        ),
        amount: float = SlashOption(
            name="amount", description="The amount to send", required=True
        ),
    ):
        bank = await self.db.get_fetchone(
            "SELECT * FROM banks WHERE guildId = ?", (interaction.guild.id,)
        )
        if not bank:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_account = await self.db.get_fetchone(
            "SELECT * FROM accounts WHERE userId = ?", (interaction.user.id,)
        )
        receiver_account = await self.db.get_fetchone(
            "SELECT * FROM accounts WHERE userId = ?", (receiver.id,)
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
            embed = Embed(title="You do not have enough money !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return 
    
        confirmEmbed = Embed(
            title="Confirmation",
            description=f"Are you sure about sending {amount}{bank[6]} to {receiver.name} ?",
            color=Colour.yellow(),
        )
        confirmView = Confirm(
            confirm_message=f"{amount}{bank[6]} have been transfered to `{receiver.name}` !",
            cancel_message="Transfer canceled !",
        )
        await interaction.response.send_message(
            embed=confirmEmbed, view=confirmView, ephemeral=True
        )

        await confirmView.wait()

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
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank[0]}")
            await self.client.get_channel(TRANSACTIONS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank[3]).send(embed=logEmbed)


def setup(client: Bot):
    client.add_cog(Accounts(client))
