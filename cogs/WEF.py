from aiosqlite import Connection, Cursor
from nextcord.ext.commands import Bot, Cog
from utils import DB
from nextcord.ext import application_checks

from nextcord import slash_command, Embed, Colour, Interaction, SlashOption, TextChannel
from uuid import uuid1, UUID

class WEF(Cog):
    def __init__(self, client: Bot) -> None:
        self.client = client
        self.db: DB = self.client.db        

    @Cog.listener()
    async def on_ready(self):
        await self.db.request("""
            CREATE TABLE IF NOT EXISTS "banks" (
                "bankId"	TEXT NOT NULL UNIQUE,
                "Name"	TEXT NOT NULL UNIQUE,
                "currencyName"	TEXT NOT NULL UNIQUE,
                "currencyCode"	TEXT NOT NULL UNIQUE,
                "balance"	REAL NOT NULL,
                PRIMARY KEY("bankId")
            );""")
    
    async def create_id(self) -> UUID:
        res = await self.db.request("SELECT bankId FROM banks")
        bankIds = [i[0] for i in await res.fetchall()]
        
        id = uuid1()
        while id in bankIds:
            id = uuid1()
            
        return id
            
    @slash_command(name="bank")
    async def bank(self, interaction: Interaction):
        return
    
    @application_checks.has_role(1093908602424668250)
    @bank.subcommand(name="open")
    async def open(
        self, 
        interaction: Interaction, 
        name: str = SlashOption(name="name", description="The bank's name", required=True), 
        currency_name: str = SlashOption(name="currency-name", description="The bank's currency", required=True), 
        currency_code: str = SlashOption(name="currency-code", description="The bank's currency's code", required=True), 
        balance: float = SlashOption(name="balance", description="The bank's balance", required=True)
    ):
        res = await self.db.request("SELECT * FROM banks WHERE name = ?", (name,))
        if await res.fetchone():
            embed = Embed(title="This name is already taken !", color=Colour.red())
            await interaction.response.send_message(embed=embed)
            return

        res = await self.db.request("SELECT * FROM banks WHERE currencyName = ?", (currency_name,))
        if await res.fetchone():
            embed = Embed(title="This currency name is already taken !", color=Colour.red())
            await interaction.response.send_message(embed=embed)
            return
        
        res = await self.db.request("SELECT * FROM banks WHERE currencyCode = ?", (currency_code,))
        if await res.fetchone():
            embed = Embed(title="This currency code is already taken !", color=Colour.red())
            await interaction.response.send_message(embed=embed)
            return
        
        id = str(await self.create_id())
        
        await self.db.request("INSERT INTO banks VALUES (?,?,?,?,?)", (id, name, currency_name, currency_code, balance))
        
        embed = Embed(title="Bank opened !", color=Colour.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        

    @application_checks.has_role(1093908602424668250)
    @bank.subcommand(name="close")
    async def close(self, interaction: Interaction):
        return
    
    @application_checks.has_role(1093908602424668250)
    @bank.subcommand(name="list")
    async def list(self, interaction: Interaction):
        return


def setup(client: Bot):
    client.add_cog(WEF(client))
