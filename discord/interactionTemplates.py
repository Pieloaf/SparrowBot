import discord


class YesNoView(discord.ui.View):

    def __init__(self, timeout: int, yes_callback, no_callback):
        super().__init__()
        self.timeout = timeout
        self.yes_button.callback = yes_callback
        self.no_button.callback = no_callback
        self.add_item(self.yes_button)
        self.add_item(self.no_button)

    yes_button = discord.ui.Button(
        label='Yes', style=discord.ButtonStyle.success)
    no_button = discord.ui.Button(label='No', style=discord.ButtonStyle.danger)


class TwoButtonView(discord.ui.View):
    def __init__(self, timeout: int, opt1: str, opt2: str, callback1, callback2, customId1: str = None, customId2: str = None):
        super().__init__()
        self.timeout = timeout

        self.opt1_button.label = opt1
        self.opt1_button.callback = callback1
        self.opt1_button.custom_id = customId1

        self.opt2_button.label = opt2
        self.opt2_button.callback = callback2
        self.opt2_button.custom_id = customId2

        self.add_item(self.opt1_button)
        self.add_item(self.opt2_button)

    opt1_button = discord.ui.Button(
        label='', style=discord.ButtonStyle.secondary)
    opt2_button = discord.ui.Button(
        label='', style=discord.ButtonStyle.secondary)
