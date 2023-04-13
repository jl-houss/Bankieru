from nextcord.ext.commands import Bot, Cog

from utils.utils import DB
from utils.views import Confirm
from utils.constants import *

from datetime import datetime
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
    Message,
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
                "user_id"	                INTEGER NOT NULL UNIQUE,
                "bank_id"	                INTEGER NOT NULL,
                "balance"	                REAL NOT NULL,
                "creation_date"	            TEXT NOT NULL,
                "panel_channel_id"          INTEGER NOT NULL UNIQUE,
                "help_channel_id"           INTEGER UNIQUE,
                "transactions_channel_id"   INTEGER NOT NULL UNIQUE,
                PRIMARY KEY("user_id")
            );"""
        )

    @Cog.listener()
    async def on_message(self, message: Message):
        channel = message.channel
        is_account_channel = (
            await self.db.get_fetchone(
                "SELECT * FROM accounts WHERE panel_channel_id = ?", (channel.id,)
            )
        ) is not None
        is_transactions_channel = (
            await self.db.get_fetchone(
                "SELECT * FROM accounts WHERE transactions_channel_id = ?",
                (channel.id,),
            )
        ) is not None
        is_help_channel = (
            await self.db.get_fetchone(
                "SELECT * FROM accounts WHERE help_channel_id = ?", (channel.id,)
            )
        ) is not None

        if is_help_channel:
            return

        if message.author.id == self.client.user.id:
            if is_transactions_channel:
                (
                    user_id,
                    bank_id,
                    balance,
                    created_at,
                    account_channel_id,
                ) = await self.db.get_fetchone(
                    "SELECT user_id, bank_id, balance, creation_date, panel_channel_id FROM accounts WHERE transactions_channel_id = ?",
                    (channel.id,),
                )

                account_owner = self.client.get_user(user_id)
                creation_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f")
                account_channel = self.client.get_channel(account_channel_id)
                currency = (
                    await self.db.get_fetchone(
                        "SELECT currency_code FROM banks WHERE bank_id = ?", (bank_id,)
                    )
                )[0]

                panel_message = (
                    await account_channel.history(oldest_first=True, limit=1).flatten()
                )[0]

                panel_embed = Embed(
                    title=f"Account of `{account_owner.name}`",
                    description=f"Created {creation_date.strftime('%A %d %B %Y')}",
                    color=EMBED_COLOR,
                )
                panel_embed.add_field(name="Balance:", value=f"`{balance}`{currency}")
                panel_embed.set_thumbnail(url=account_owner.avatar)

                await panel_message.edit(embed=panel_embed)
                return
            else:
                return

        if is_account_channel or is_transactions_channel:
            await message.delete()

    @slash_command(name="account")
    async def account(self, interaction: Interaction):
        return

    @slash_command(name="send")
    async def send(
        self,
        interaction: Interaction,
        receiver: Member = SlashOption(
            name="to", description="To who'm do you want to send money", required=True
        ),
        amount: float = SlashOption(
            name="amount", description="The amount to send", required=True
        ),
        note: str = SlashOption(
            name="note", description="Leave a note to the receiver", required=False
        ),
    ):
        sender = interaction.user

        (
            bank_id,
            bank_name,
            bank_logs_channel_id,
            currency_code,
        ) = await self.db.get_fetchone(
            "SELECT bank_id, name, logs_channel_id, currency_code FROM banks WHERE guild_id = ?",
            (interaction.guild.id,),
        )

        if not bank_id:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        sender_account = await self.db.get_fetchone(
            "SELECT user_id, balance, panel_channel_id, transactions_channel_id FROM accounts WHERE user_id = ? AND bank_id = ?",
            (sender.id, bank_id),
        )

        if not sender_account:
            embed = Embed(
                title="You do not have an account at this bank !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        (
            sender_id,
            sender_balance,
            sender_panel_channel_id,
            sender_transactions_channel_id,
        ) = sender_account

        receiver_account = await self.db.get_fetchone(
            "SELECT user_id, balance, transactions_channel_id FROM accounts WHERE user_id = ? AND bank_id = ?",
            (receiver.id, bank_id),
        )

        if not receiver_account:
            embed = Embed(
                title="The receiver does not have an account at this bank !",
                color=Colour.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        (
            receiver_id,
            receiver_balance,
            receiver_transactions_channel_id,
        ) = receiver_account

        if sender_id == receiver_id:
            embed = Embed(
                title="You can't send money to yourself !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if sender_balance < amount:
            embed = Embed(
                title="You do not have enough money !",
                description=f"You only have ``{sender_balance}{currency_code}`` In your account",
                color=Colour.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if interaction.channel.id != sender_panel_channel_id:
            channel = self.client.get_channel(sender_panel_channel_id)
            embed = Embed(
                title="You can't use this command here!",
                description=f"You can only use this command in your account's channel: {channel.mention}.",
                color=Colour.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        confirmEmbed = Embed(
            title="Confirmation",
            description=f"Are you sure about sending {amount}{currency_code} to {receiver.name} ?",
            color=Colour.yellow(),
        )
        confirmView = Confirm(
            confirm_text=f"{amount}{currency_code} have been transfered to `{receiver.name}` !",
            cancel_message="Transfer canceled !",
        )
        confirm_message = await interaction.response.send_message(
            embed=confirmEmbed, view=confirmView, ephemeral=True
        )

        await confirmView.wait()

        await confirm_message.delete()

        if confirmView.value:
            await self.db.request(
                "UPDATE accounts SET balance = ? WHERE user_id = ? AND bank_id = ?",
                (sender_balance - amount, sender.id, bank_id),
            )
            await self.db.request(
                "UPDATE accounts SET balance = ? WHERE user_id = ? AND bank_id = ?",
                (receiver_balance + amount, receiver.id, bank_id),
            )

            sender_alert = Embed(
                title=f"-{amount}{currency_code}",
                description=f"Note: {note}" if note else None,
                color=EMBED_COLOR,
            )
            sender_alert.set_footer(icon_url=receiver.avatar, text=f"To: {receiver}")
            receiver_alert = Embed(
                title=f"+{amount}{currency_code}",
                description=f"Note: {note}" if note else None,
                color=EMBED_COLOR,
            )
            receiver_alert.set_footer(icon_url=sender.avatar, text=f"From: {sender}")
            bank_log = Embed(
                title=f"**{sender}** sent `{amount}{currency_code}` **to {receiver}**",
                description=f"Note: {note}" if note else None,
                color=EMBED_COLOR,
            )
            wef_banks_log = Embed(
                title=f"**{sender}** sent `{amount}{currency_code}` **to {receiver}**",
                description=f"Note: {note}" if note else None,
                color=EMBED_COLOR,
            )
            wef_banks_log.add_field(name="Bank Name:", value=bank_name)
            wef_banks_log.set_footer(text=f"BANK ID: {bank_id}")

            await self.client.get_channel(sender_transactions_channel_id).send(
                embed=sender_alert
            )
            await self.client.get_channel(receiver_transactions_channel_id).send(
                embed=receiver_alert
            )
            await self.client.get_channel(bank_logs_channel_id).send(embed=bank_log)
            await self.client.get_channel(BANKS_LOGS).send(embed=wef_banks_log)


def setup(client: Bot):
    client.add_cog(Accounts(client))
