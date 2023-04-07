from aiosqlite import Connection, Cursor
from nextcord.ext.commands import Bot, Cog

from utils import DB

from datetime import datetime

from nextcord.ext import application_checks
from nextcord import slash_command, Embed, Colour, Interaction, SlashOption, TextChannel, ui, ButtonStyle, Member

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
        embed = Embed(title=self.confirm_message, color=Colour.green())
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

class Bank(Cog):
    def __init__(self, client: Bot) -> None:
        self.client = client
        self.db: DB = self.client.db

    @Cog.listener()
    async def on_ready(self):
        await self.db.request("""
            CREATE TABLE IF NOT EXISTS "accounts" (
                "userId"	INTEGER NOT NULL UNIQUE,
                "balance"	REAL NOT NULL,
                "created_at"	TEXT NOT NULL,
                PRIMARY KEY("userId")
            );
        """)
        
    @slash_command(name="account")
    async def account(self, interaction: Interaction):
        return

    @account.subcommand(name="open")
    async def open(self, interaction: Interaction):
        res = await self.db.request("SELECT * FROM accounts WHERE userId = ?", (interaction.user.id,))
        
        if await res.fetchone():
            embed = Embed(title="You already have an account at this bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await self.db.request("INSERT INTO accounts VALUES (?,?,?)", (interaction.user.id, 0.00, datetime.now()))
        
        embed = Embed(title="Account created !", color=Colour.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @account.subcommand(name="close")
    async def close(self, interaction: Interaction):
        res = await self.db.request("SELECT * FROM accounts WHERE userId = ?", (interaction.user.id,))
        
        if not await res.fetchone():
            embed = Embed(title="You do not have an account at this bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        confirmEmbed = Embed(title="Confirmation", description="Are you sure about closing your account ?", color=Colour.yellow())
        
        confirmView = Confirm("Account closed !", "Closing canceled !")
        await interaction.response.send_message(embed=confirmEmbed, view=confirmView, ephemeral=True)
        
        await confirmView.wait()
        
        if confirmView.value:
            await self.db.request("DELETE FROM accounts WHERE userId = ?", (interaction.user.id,))
            
    
    @account.subcommand(name="info")
    async def info(self, interaction: Interaction):
        res = await self.db.request("SELECT * FROM accounts WHERE userId = ?", (interaction.user.id,))
        account = await res.fetchone()
        if not account:
            embed = Embed(title="You do not have an account at this bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        creation_date = datetime.strptime(account[2], "%Y-%m-%d %H:%M:%S.%f")
        
        embed = Embed(title=f"Account of `{interaction.user.name}`", description=f"Created {creation_date.strftime('%A %d %B %Y')}", color=Colour.blue())
        embed.add_field(name="Balance:", value=f"{account[1]}€")
        embed.set_thumbnail(url=interaction.user.avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @slash_command(name="send")
    async def send(self, interaction: Interaction, receiver: Member = SlashOption(name="receiver", description="To who'm do you want to send money", required=True), amount: float = SlashOption(name="amount", description="The amount to send", required=True)):
        res = await self.db.request("SELECT * FROM accounts WHERE userId = ?", (interaction.user.id,))
        user_account = await res.fetchone()
        
        res = await self.db.request("SELECT * FROM accounts WHERE userId = ?", (receiver.id,))
        receiver_account = await res.fetchone()
        
        if not user_account:
            embed = Embed(title="You do not have an account at this bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif not receiver_account:
            embed = Embed(title="That member does not have an account at this bank !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif interaction.user == receiver:
            embed = Embed(title="You can't send money to yourself !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True) 
                   
        elif user_account[1] < amount:
            embed = Embed(title="You do not have enough money !", color=Colour.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        else:
            await self.db.request("UPDATE accounts SET balance = ? WHERE userId = ?", (user_account[1] - amount, interaction.user.id))
            await self.db.request("UPDATE accounts SET balance = ? WHERE userId = ?", (receiver_account[1] + amount, receiver.id))
            
            embed = Embed(title=f"{amount}€ ont été transféré a `{receiver.name}` !", color=Colour.green())
            await interaction.response.send_message(embed=embed, ephemeral=True)

def setup(client: Bot):
    client.add_cog(Bank(client))
