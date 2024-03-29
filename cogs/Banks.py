from aiosqlite import Connection, Cursor
from nextcord.ext.commands import Bot, Cog

from utils.utils import DB
from utils.views import Confirm, AccountOpenView, AccountPanel, HelpPanel
from utils.constants import *

from nextcord.ext import application_checks
from datetime import datetime
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
    PermissionOverwrite
)

class Banks(Cog):
    def __init__(self, client: Bot) -> None:
        self.client = client
        self.db: DB = self.client.db

    @Cog.listener()
    async def on_ready(self):
        self.client.add_view(AccountOpenView(self.client))
        self.client.add_view(AccountPanel(self.client))
        self.client.add_view(HelpPanel(self.client))
        
        await self.db.request("""
            CREATE TABLE IF NOT EXISTS "banks" (
                "bank_id"	        INTEGER NOT NULL UNIQUE,
                "guild_id"	        INTEGER NOT NULL UNIQUE,
                "name"	            TEXT NOT NULL UNIQUE,
                "balance"	        REAL NOT NULL,
                "currency_name"	    TEXT NOT NULL UNIQUE,
                "currency_code"	    TEXT NOT NULL UNIQUE,
                "creation_date"	    TEXT NOT NULL UNIQUE,
                "bank_category_id"	INTEGER NOT NULL UNIQUE,
                "logs_channel_id"	INTEGER NOT NULL UNIQUE,
                PRIMARY KEY("bank_id" AUTOINCREMENT)
            );""")

    @slash_command(name="bank")
    async def bank(self, interaction: Interaction):
        return

    @application_checks.has_role(TOPG_ROLE)
    @bank.subcommand(name="open")
    async def open(
        self,
        interaction: Interaction,
        name: str = SlashOption(name="name", description="The bank's name", required=True),
        currency_name: str = SlashOption(name="currency-name", description="The bank's currency", required=True),
        currency_code: str = SlashOption(name="currency-code",description="The bank's currency's code",required=True,),
        balance: float = SlashOption(name="balance", description="The bank's balance", required=True),
    ):
        name = " ".join([word[0].upper() + word[1:].lower() for word in name.split()])
        currency_name = " ".join([word[0].upper() + word[1:].lower() for word in currency_name.split()])
        currency_code = currency_code.upper()

        if await self.db.get_fetchone("SELECT * FROM banks WHERE guild_id = ?", (interaction.guild.id,)):
            embed = Embed(title="This server has already a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if await self.db.get_fetchone("SELECT * FROM banks WHERE name = ?", (name,)):
            embed = Embed(title="This name is already taken !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if await self.db.get_fetchone("SELECT * FROM banks WHERE currency_name = ?", (currency_name,)):
            embed = Embed(
                title="This currency name is already taken !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if await self.db.get_fetchone("SELECT * FROM banks WHERE currency_code = ?", (currency_code,)):
            embed = Embed(
                title="This currency code is already taken !", color=Colour.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        confirmEmbed = Embed(
            title="Confirmation",
            description="Are you sure about opening a bank with these informations ?",
            color=EMBED_COLOR,
        )
        confirmEmbed.add_field(
            name="Informations", 
            value=f"**Name** : ``{name}``\n**Currency name** : ``{currency_name}``\n**Currency code** : ``{currency_code}``\n**Balance** : ``{balance}{currency_code}``"
        )

        confirmView = Confirm(f"`{name}` Bank created !", "Creation canceled !")
        confirm_message = await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)

        await confirmView.wait()

        await confirm_message.delete()

        if confirmView.value: 
            bank_perms = {
                interaction.guild.default_role : PermissionOverwrite(view_channel=False)
            }   
            
            reception_perms = {
                interaction.guild.default_role : PermissionOverwrite(view_channel=True, send_messages=False)
            }
            
            bank_category: CategoryChannel = await interaction.guild.create_category(name=f"{name} bank", overwrites=bank_perms)
            
            bank_reception_channel: TextChannel = await interaction.guild.create_text_channel(name="reception", category=bank_category, overwrites=reception_perms)
            
            bank_logs_channel: TextChannel = await interaction.guild.create_text_channel(name="logs", category=bank_category)
            
            await self.db.request(
                "INSERT INTO banks (guild_id, name, balance, currency_name, currency_code, creation_date, bank_category_id, logs_channel_id) VALUES (?,?,?,?,?,?,?,?)",
                (
                    interaction.guild.id,
                    name,
                    balance,
                    currency_name,
                    currency_code,
                    datetime.now(),
                    bank_category.id,
                    bank_logs_channel.id,
                ),
            )
            
            bank_id = (await self.db.get_fetchone("SELECT bank_id FROM banks WHERE name = ?", (name,)))[0]
            
            logEmbed = Embed(title=f"`{name}` Bank created !", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank_id}")
            await self.client.get_channel(BANKS_LOGS).send(embed=logEmbed)
            
            reception_embed = Embed(title=f"Welcome to `{name}` Bank", description="Click on the button below to open your account.", color=EMBED_COLOR)
            await bank_reception_channel.send(embed=reception_embed, view=AccountOpenView(self.client))
            
        
    @application_checks.has_role(TOPG_ROLE)
    @bank.subcommand(name="close")
    async def close(
        self,
        interaction: Interaction,
        id: str = SlashOption(
            name="bank-id", description="The id of the bank to close", required=False
        ),
    ):
        if id:
            bank_id, bank_name, bank_guild_id, bank_category_id = await self.db.get_fetchone("SELECT bank_id, name, guild_id, bank_category_id FROM banks WHERE bank_id = ?", (id,))
            if not bank_id:
                embed = Embed(title="This id doesn't match any bank !", color=Colour.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        else:
            bank_id, bank_name, bank_guild_id, bank_category_id = await self.db.get_fetchone("SELECT bank_id, name, guild_id, bank_category_id FROM banks WHERE guild_id = ?", (interaction.guild.id,))
            if not bank_id:
                embed = Embed(
                    title="This server doesn't have a bank !", color=Colour.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        confirmEmbed = Embed(
            title="Confirmation",
            description=f"Are you sure about closing `{bank_name}` Bank ?",
            color=EMBED_COLOR,
        )
        confirmView = Confirm(confirm_text=f"`{bank_name}` Bank closed !", cancel_message="Closing canceled !")
        confirm_message = await interaction.response.send_message(
            embed=confirmEmbed, view=confirmView, ephemeral=True
        )

        await confirmView.wait()

        await confirm_message.delete()
        
        bank_category = utils.get(self.client.get_guild(bank_guild_id).categories, id=bank_category_id)

        if confirmView.value:
            for channel in bank_category.channels:
                await channel.delete()

            await bank_category.delete()

            await self.db.request("DELETE FROM banks WHERE bank_id = ?", (bank_id,))
            await self.db.request("DELETE FROM accounts WHERE bank_id = ?", (bank_id,))
            
            logEmbed = Embed(title=f"`{bank_name}` Bank closed !", color=EMBED_COLOR)
            logEmbed.set_author(name=interaction.user, icon_url=interaction.user.avatar)
            logEmbed.set_thumbnail(url=interaction.guild.icon)
            logEmbed.set_footer(text=f"BANK ID: {bank_id}")
            await self.client.get_channel(BANKS_LOGS).send(embed=logEmbed)

    @application_checks.has_permissions(administrator=True)
    @bank.subcommand(name="info")
    async def info(self, interaction: Interaction):
        bank_id, bank_name, balance, currency_name, currency_code, creation_date = await self.db.get_fetchone(
            "SELECT bank_id, name, balance, currency_name, currency_code, creation_date  FROM banks WHERE guild_id = ?", (interaction.guild.id,)
        )
        if not bank_id:
            embed = Embed(title="This server doesn't have a bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S.%f")
    
        embed = Embed(
            title=f"{bank_name} Bank",
            color=EMBED_COLOR,
            description=f"Created {creation_date.strftime('%A %d %B %Y')}",
        )
        accounts_number = len(await self.db.get_fetchall("SELECT * FROM accounts WHERE bank_id = ?", (bank_id,)))

        embed.add_field(name="Currency:", value=f"`{currency_name}`", inline=True)
        embed.add_field(name="Currency Code:", value=f"`{currency_code}`", inline=True)
        embed.add_field(name="Balance:", value=f"`{balance}{currency_code}`", inline=True)
        embed.add_field(name="Accounts number:", value=f"`{accounts_number}` account{'s' if accounts_number>1 else ''}", inline=True)

        embed.set_footer(text=f"ID: {bank_id}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @application_checks.has_role(TOPG_ROLE)
    @bank.subcommand(name="list")
    async def list(self, interaction: Interaction):
        banks = await self.db.get_fetchall("SELECT bank_id, name, currency_code, creation_date FROM banks")

        embed = Embed(title="Banks list", color=EMBED_COLOR, description="No bank at the moment" if not banks else None)
        for bank_id, name, currency_code, creation_date in banks:
            creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S.%f")
                
            embed.add_field(name=f"{name} Bank ({currency_code})", value=f"> Created {creation_date.strftime('%A %d %B %Y')}\n> ID: {bank_id}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

def setup(client: Bot):
    client.add_cog(Banks(client))
