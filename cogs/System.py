from nextcord.ext.commands import Cog, Bot

import os
import asyncio

from nextcord.ext import application_checks
from nextcord.abc import GuildChannel
from nextcord import (
	Color,
	SlashOption,
	Embed,
	Interaction,
	slash_command,
)


class System(Cog):
	def __init__(self, client: Bot) -> None:
		self.client = client

	@application_checks.is_owner()
	@slash_command(name="ping", description="Get bot's latency")
	async def ping(self, interaction: Interaction):
		ping = Embed(title=f"Bot's Ping", color=Color.blue())
		ping.add_field(
			name="My latency is:", value=f"{round(self.client.latency*1000)}ms"
		)
		ping.set_author(
			name=interaction.user.name, icon_url=interaction.user.avatar.url
		)
		await interaction.send(embed=ping)

	@slash_command(name="cogs", description="Cogs commands")
	async def cogs(self, interacton: Interaction):
		return

	@application_checks.is_owner()
	@cogs.subcommand(name="list", description="List bot cogs")
	async def list(self, interaction: Interaction):
		loaded = []
		unloaded = []

		[
			(
				loaded.append(filename[:-3])
				if filename[:-3] in self.client.cogs
				else unloaded.append(filename[:-3])
			)
			for filename in os.listdir("./cogs")
			if filename.endswith(".py")
		]

		cogs = Embed(title=f"Bot Cogs:", color=Color.blue())

		if loaded:
			cogs.add_field(name="Loaded:", value="\n".join(loaded), inline=False)

		if unloaded:
			cogs.add_field(name="Not loaded:", value="\n".join(unloaded), inline=False)

		cogs.set_author(
			name=interaction.user.name, icon_url=interaction.user.avatar.url
		)

		await interaction.send(embed=cogs)

	@application_checks.is_owner()
	@cogs.subcommand(name="load", description="Load bot cog")
	async def load(
		self,
		interaction: Interaction,
		cog: str = SlashOption(
			name="cog", description="The cog to load", required=True
		),
	):
		if cog in [
			filename[:-3]
			for filename in os.listdir("./cogs")
			if filename.endswith(".py")
		]:
			self.client.load_extension(name=f"cogs.{cog}")
			reloaded = Embed(
				title=f"Loaded!",
				description=f"**{cog}** cog loaded!",
				color=Color.green(),
			)
			reloaded.set_author(
				name=interaction.user.name, icon_url=interaction.user.avatar.url
			)

			await interaction.send(embed=reloaded)
			await self.client.sync_all_application_commands()
		else:
			no_cog = Embed(
				title=f"No Cog!",
				description=f"There is no cog named {cog}!",
				color=Color.red(),
			)
			no_cog.set_author(
				name=interaction.user.name, icon_url=interaction.user.avatar.url
			)

			await interaction.response.send_message(embed=no_cog, ephemeral=True)

	@application_checks.is_owner()
	@cogs.subcommand(name="unload", description="Load bot cog")
	async def unload(
		self,
		interaction: Interaction,
		cog: str = SlashOption(
			name="cog", description="The cog to unload", required=True
		),
	):
		if cog in [
			filename[:-3]
			for filename in os.listdir("./cogs")
			if filename.endswith(".py")
		]:
			self.client.unload_extension(name=f"cogs.{cog}")

			reloaded = Embed(
				title=f"Unloaded!",
				description=f"**{cog}** cog unloaded!",
				color=Color.green(),
			)
			reloaded.set_author(
				name=interaction.user.name, icon_url=interaction.user.avatar.url
			)

			await interaction.send(embed=reloaded)
			await self.client.sync_all_application_commands()
		else:
			no_cog = Embed(
				title=f"No Cog!",
				description=f"There is no cog named {cog}!",
				color=Color.red(),
			)
			no_cog.set_author(
				name=interaction.user.name, icon_url=interaction.user.avatar.url
			)

			await interaction.response.send_message(embed=no_cog, ephemeral=True)

	@application_checks.is_owner()
	@cogs.subcommand(name="reload", description="Reload bot cogs")
	async def reload(
		self,
		interaction: Interaction,
		cog: str = SlashOption(
			name="cog", description="The cog to reload", required=False
		),
	):
		if cog:
			if cog in [
				filename[:-3]
				for filename in os.listdir("./cogs")
				if filename.endswith(".py")
			]:
				self.client.unload_extension(name=f"cogs.{cog}")
				self.client.load_extension(name=f"cogs.{cog}")

				reloaded = Embed(
					title=f"Reloaded!",
					description=f"**{cog}** cog reloaded!",
					color=Color.green(),
				)
				reloaded.set_author(
					name=interaction.user.name, icon_url=interaction.user.avatar.url
				)

				await interaction.send(embed=reloaded)
				await self.client.sync_all_application_commands()
			else:
				no_cog = Embed(
					title=f"No Cog!",
					description=f"There is no cog named {cog}!",
					color=Color.red(),
				)
				no_cog.set_author(
					name=interaction.user.name, icon_url=interaction.user.avatar.url
				)

				await interaction.response.send_message(embed=no_cog, ephemeral=True)
		else:
			self.client.unload_extensions()
			cogs = self.client.load_extensions()

			reloaded = Embed(
				title=f"Reloaded!",
				description="Bot cogs reloaded!",
				color=Color.green(),
			)
			reloaded.add_field(name="Reloaded Cogs:", value="\n".join(cogs))
			reloaded.set_author(
				name=interaction.user.name, icon_url=interaction.user.avatar.url
			)

			await interaction.send(embed=reloaded)
			await self.client.sync_all_application_commands()
   
	@application_checks.has_permissions(manage_messages=True)
	@slash_command(name="clear", description="To clear a channel")
	async def clear_channel(
		self,
		interaction: Interaction,
		channel: GuildChannel = SlashOption(
			name="channel", description="The channel to clear", required=False
		),
		limit: int = SlashOption(
			name="limit", description="Number of messages to clear", required=False
		),
	):

		if not channel:
			channel = interaction.channel

		clearing = Embed(title="Clearing the channel...", color=Color.green())

		await interaction.send(embed=clearing)

		await channel.purge(limit=int(limit) if limit else None)

		cleared = Embed(title="The channel has been cleared", color=Color.green())
		cleared.set_author(
			icon_url=interaction.user.avatar.url,
			name=interaction.user.name,
		)

		response = await interaction.followup.send(embed=cleared)

		await asyncio.sleep(5)
		if channel != interaction.channel:
			await clearing.delete()
		await response.delete()


def setup(client: Bot):
	client.add_cog(System(client))
