from nextcord import ui, ButtonStyle, Interaction, Colour, Embed
from utils.constants import *


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
        embed = Embed(title=self.confirm_message, color=EMBED_COLOR)
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
