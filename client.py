import os
import traceback
import sys
import nextcord

from utils import DB

from os import environ as env

from nextcord import Intents, Interaction, Embed, Colour
from nextcord.ext.commands import Bot, errors, Context
from nextcord.ext.application_checks import errors as application_errors

class Client(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop.create_task(self.get_ready())

    async def get_ready(self):
        self.db = DB()
        await self.db.load_db("main.db")
        self.load_extensions()

    def load_extensions(self) -> None:
        print("---------[Loading]---------")
        loaded = []
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                self.load_extension(f"cogs.{filename[:-3]}")
                print(f"[System]: {filename[:-3]} cog loaded.")
                loaded.append(filename[:-3])
        print("---------------------------")
        return loaded

    def unload_extensions(self) -> None:
        print("--------[Unloading]--------")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                self.unload_extension(f"cogs.{filename[:-3]}")
                print(f"[System]: {filename[:-3]} cog unloaded.")
        print("---------------------------")

    async def on_ready(self):
        print("Ready !")

    async def on_command_error(self, ctx: Context, error):
        description = None
        if isinstance(error, errors.CommandNotFound):
            return
        elif isinstance(error, errors.TooManyArguments):
            title = "You are giving too many arguments !"
        elif isinstance(error, errors.BadArgument):
            title = "The library ran into an error attempting to parse your argument !"
        elif isinstance(error, errors.MissingRequiredArgument):
            title = "You're missing a required argument !"

        # kinda annoying and useless error.
        elif isinstance(error, nextcord.NotFound) and "Unknown interaction" in str(error):
            return
        elif isinstance(error, errors.MissingRole):
            role = ctx.guild.get_role(int(error.missing_role))
            await ctx.send(f'"{role.name}" is required to use this command.')
        elif isinstance(error, errors.MissingAnyRole):
            roles = [ctx.guild.get_role(int(role)) for role in error.missing_roles]
            title = "Missing role !"
            description = f"Atleast one of these roles: {', '.join([role.mention for role in roles])} is required to use this command."
        elif isinstance(error, errors.MissingPermissions):
            permissions = error.missing_permissions
            title = f"Missing permission{'s' if len(permissions) > 1 else ''} !"
            description = f"The permission{'s' if len(permissions) > 1 else ''}: **{', '.join(permissions)}**. {'are' if len(permissions) > 1 else 'is'} required to use this command."
        elif isinstance(error, errors.NotOwner):
            title = f"Only the bot's owner can use this command."
        else:
            await ctx.send(
                f"This command raised an exception: `{type(error)}:{str(error)}`"
            )
            
        embed = Embed(title=title, description=description, color=Colour.red())
        await ctx.send(embed=embed, ephemeral=True)

    async def on_application_command_error(self, interaction: Interaction, error: Exception) -> None:
        description = None
        if isinstance(error, application_errors.ApplicationMissingRole):
            role = interaction.guild.get_role(int(error.missing_role))
            title = "Missing role !"
            description = f"The role {role.mention} is required to use this command."
        
        elif isinstance(error, application_errors.ApplicationMissingAnyRole):
            roles = [interaction.guild.get_role(int(role)) for role in error.missing_roles]
            title = "Missing role !"
            description = f"Any of these roles: {', '.join([role.mention for role in roles])} are required to use this command."
        
        elif isinstance(error, application_errors.ApplicationNotOwner):
            title = f"Only the bot's owner can use this command."

        elif isinstance(error, application_errors.ApplicationMissingPermissions):
            permissions = error.missing_permissions
            title = f"Missing permission{'s' if len(permissions) > 1 else ''} !"
            description = f"The permission{'s' if len(permissions) > 1 else ''}: **{', '.join(permissions)}**. {'are' if len(permissions) > 1 else 'is'} required to use this command."

        else:
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            title = f"The command has encountred an error: `{type(error)}:`"
            description = f"{str(error)}\n\nCheck the console for more details"
            
        embed = Embed(title=title, description=description, color=Colour.red())
        await interaction.send(embed=embed, ephemeral=True)


client = Client(
    "=", intents=Intents(messages=True, guilds=True, members=True, message_content=True, invites=True)
)

if __name__ == "__main__":
    client.run(env["TOKEN"])
