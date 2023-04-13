from utils.constants import *
from utils.utils import DB
from utils.views import Confirm

import os
import asyncio
from datetime import datetime

from nextcord.ext.commands import Cog, Bot
from nextcord.ext import application_checks
from nextcord.abc import GuildChannel
from nextcord import (
    slash_command,
    Embed,
    ui,
    ButtonStyle,
    Colour,
    Interaction,
    SlashOption,
    TextChannel,
    CategoryChannel,
    utils,
    PermissionOverwrite,
    Member
)

class Admin(Cog):
    def __init__(self, client) -> None:
        self.client = client
        self.db: DB = self.client.db

    @application_checks.has_role(TOPG_ROLE)
    @slash_command(name="account_info")
    async def account_info(self, interaction: Interaction, member: Member = SlashOption(name="member", description="The member to get his infos", required=True)):
        bank_id, currency_code = await self.db.get_fetchone("SELECT bank_id, currency_code FROM banks WHERE guild_id = ?", (interaction.guild.id,))
        if not bank_id:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        account_user_id, account_balance, creation_date = await self.db.get_fetchone("SELECT user_id, balance, creation_date FROM accounts WHERE user_id = ? AND bank_id = ?", (member.id, bank_id))
        if not account_user_id:
            embed = Embed(title="This member doesn't have an account at this bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S.%f")

        embed = Embed(
            title=f"Account of `{member.name}`",
            description=f"Created {creation_date.strftime('%A %d %B %Y')}",
            color=EMBED_COLOR,
        )
        embed.add_field(name="Balance:", value=f"{account_balance}{currency_code}")
        embed.set_thumbnail(url=member.avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @application_checks.has_role(TOPG_ROLE)
    @slash_command(name="give")
    async def give(
        self,
        interaction: Interaction,
        amount: float = SlashOption(name="amount", description="The amount to give", required=True),
        receiver: Member = SlashOption(
            name="to",
            description="To who'm do you want to give money",
            required=True
    )):
        bank_id, bank_name, currency_code, bank_logs_channel_id = await self.db.get_fetchone("SELECT bank_id, name, currency_code, logs_channel_id FROM banks WHERE guild_id = ?", (interaction.guild.id,))
        if not bank_id:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        receiver_account = await self.db.get_fetchone("SELECT * FROM accounts WHERE user_id = ? AND bank_id=?", (receiver.id, bank_id))
        
        if not receiver_account:
            embed = Embed(
                title="The receiver does not have an account at this bank !",
                color=Colour.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
        confirmEmbed = Embed(
            title="Confirmation",
            description=f"Are you sure about giving {amount}{currency_code} to {receiver.name} ?",
            color=EMBED_COLOR,
        )
        confirmView = Confirm(
            confirm_text=f"{amount}{currency_code} have been given to `{receiver.name}` !",
            cancel_message="Transfer canceled !",
        )
        confirm_message = await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)

        await confirmView.wait()
        
        await confirm_message.delete()

        if confirmView.value:
            await self.db.request("UPDATE accounts SET balance = ? WHERE user_id = ? AND bank_id = ?",(receiver_account[2] + amount, receiver.id, bank_id),)
            logEmbed_2 = Embed(title=f"{interaction.user} gave you `{amount}{currency_code}` at `{bank_name}`", color=EMBED_COLOR)
            logEmbed = Embed(title=f"{interaction.user} gave `{amount}{currency_code}` to {receiver} at `{bank_name}` Bank", color=EMBED_COLOR)

            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank_id}")
            
            await self.client.get_channel(TRANSACTIONS_LOGS).send(embed=logEmbed)
            await self.client.get_channel(bank_logs_channel_id).send(embed=logEmbed)
            await self.client.get_channel(receiver_account[6]).send(embed=logEmbed_2)
        
def setup(client : Bot):
    client.add_cog(Admin(client))