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
    PermissionOverwrite,
    utils

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
                "account_channel" INTEGER NOT NULL UNIQUE,
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
            "SELECT * FROM accounts WHERE userId = ?", (interaction.user.id,)
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
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_message="Account created !", cancel_message="Creation canceled !")
        await interaction.response.send_message(
            embed=confirmEmbed, view=confirmView, ephemeral=True
        )

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

            account_channel_embed = Embed(title=f"Account of {interaction.user}", description=f"{interaction.user.mention} this is your account channel.\nAny action on your account will be made \nfrom here using the panel below.", color=EMBED_COLOR)
            await account_channel.send(embed=account_channel_embed)
            await self.db.request(
                "INSERT INTO accounts VALUES (?,?,?,?,?)",
                (interaction.user.id, bank[0], 0.00, datetime.now(), account_channel.id),
            )

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
            "SELECT * FROM accounts WHERE userId = ?", (interaction.user.id,)
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
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_message="Account closed !", cancel_message="Closing canceled !")
        await interaction.response.send_message(
            embed=confirmEmbed, view=confirmView, ephemeral=True
        )

        await confirmView.wait()

        if confirmView.value:
            account_channel = utils.get(self.client.get_all_channels(), id=account[4])
            await account_channel.delete()
            await self.db.request(
                "DELETE FROM accounts WHERE userId = ?", (interaction.user.id,)
            )

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
            "SELECT * FROM accounts WHERE userId = ?", (interaction.user.id,)
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
        embed.add_field(name="Balance:", value=f"{account[2]}€")
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

        elif not receiver_account:
            embed = Embed(
                title="The receiver does not have an account at this bank !",
                color=Colour.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif interaction.user == receiver:
            embed = Embed(
                title="You can't send money to yourself !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif user_account[2] < amount:
            embed = Embed(title="You do not have enough money !", description=f"You only have ``{user_account[1]}{bank[6]}`` In your account", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif user_account[4]!=interaction.channel.id:
            channel = self.client.get_channel(user_account[4])
            embed = Embed(title="You Cannot use this command here!", description=f"You can only use This command in Your account's channel : {channel.mention} .", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            confirmEmbed = Embed(
                title="Confirmation",
                description=f"Are you sure about sending {amount}€ to {receiver.name} ?",
                color=EMBED_COLOR,
            )
            confirmView = Confirm(
                confirm_message=f"{amount}€ have been transfered to `{receiver.name}` !",
                cancel_message="Transfer canceled !",
            )
            await interaction.response.send_message(
                embed=confirmEmbed, view=confirmView, ephemeral=True
            )

            await confirmView.wait()

            if confirmView.value:
                await self.db.request(
                    "UPDATE accounts SET balance = ? WHERE userId = ?",
                    (user_account[1] - amount, interaction.user.id),
                )
                await self.db.request(
                    "UPDATE accounts SET balance = ? WHERE userId = ?",
                    (receiver_account[1] + amount, receiver.id),
                )


def setup(client: Bot):
    client.add_cog(Accounts(client))
