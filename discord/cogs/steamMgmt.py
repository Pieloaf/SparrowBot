import discord
from discord import app_commands, ui
from discord.ext import commands
import re
from const import ServerId
from interactionTemplates import YesNoView


class SteamMgmt(app_commands.Group):
    """Manage Steam Account Linking"""

    def __init__(self, client: commands.Bot) -> None:
        super().__init__(name="steam", description="Steam Account Commands")
        self.client = client

    @app_commands.command()
    @app_commands.describe(steam_url='Your Steam Profile URL')
    async def link(self, interaction: discord.Interaction, steam_url: str) -> None:
        """Link your Steam account"""
        userExists = await self.client.usefulCogs['db'].getDocument('users', {
            '_id': str(interaction.user.id)
        })
        if userExists is not None and 'steamID' in userExists:
            await interaction.response.send_message(
                "There is already a Steam account linked to this Discord account. You can remove it by using `/steam unlink`", ephemeral=True)
            return

        parsedURL = re.match(
            r'https:\/\/steamcommunity\.com\/(profiles|id)\/([^/]*|.*)', steam_url)

        if not parsedURL:
            await interaction.response.send_message('Invalid Steam Profile URL', ephemeral=True)
            return

        if parsedURL.group(1) == 'id':
            steamID = await self.client.steam.resolveVanityUrl(parsedURL.group(2))

        user = await self.client.steam.getUser(steamID)
        taken = await self.client.usefulCogs['db'].getDocument('users', {
            'steamID': str(steamID)})

        if taken:
            await interaction.response.send_message(
                "This Steam account is already linked to another Discord account\nIf this is your account please report it to a moderator", ephemeral=True)
            return

        async def yesBtnCB(interaction):
            """Do some DB shit here"""
            # getting user again here due to a bug when peope double click the button
            user = await self.client.usefulCogs['db'].getDocument('users', {
                '_id': str(interaction.user.id)
            })
            await interaction.response.defer()
            if user:
                newData = {'$set': {'steamID': steamID}}
                res = await self.client.usefulCogs['db'].updateDocument('users', user, newData)
            else:
                res = await self.client.usefulCogs['db'].addDocument('users', {
                    '_id': str(interaction.user.id),
                    'steamID': steamID,
                })
            if not res:
                await interaction.edit_original_message(content=f'An error occured while trying to link your Steam account. Please let <@439364864763363363> know', view=None)
                return
            await interaction.edit_original_message(content='Successfully linked your Steam account!', view=None)
            await self.client.log(f'User {interaction.user.id} has linked their Steam account: {steam_url}')

        async def noBtnCB(interaction):
            await interaction.response.defer()
            await interaction.edit_original_message(content='Cancelled', view=None)

        view = YesNoView(timeout=60, yes_callback=yesBtnCB,
                         no_callback=noBtnCB)

        await interaction.response.send_message(
            f"Are you sure you want to link steam account: \"**{user['personaname']}**{ ' - '+user['realname'] if 'realname' in user else ''}\" with this discord account?\n", ephemeral=True, view=view)

    @ app_commands.command()
    async def unlink(self, interaction: discord.Interaction) -> None:
        """Unlink your Steam account"""

        if not await self.client.usefulCogs['db'].getDocument('users', {
            '_id': str(interaction.user.id)
        }):
            await interaction.response.send_message(
                "There is no Steam account linked to this Discord account. You can link one by using `/steam link`", ephemeral=True)
            return

        async def yesBtnCB(interaction):
            """Do some DB shit here"""
            await interaction.response.defer()
            res = await self.client.usefulCogs['db'].updateDocument('users', {
                '_id': str(interaction.user.id)
            }, {'$unset': {'steamID': ''}})
            if not res:
                await interaction.edit_original_message(content=f'An error occured while trying to unlink your Steam account. Please let <@439364864763363363> know', view=None)
                return
            await interaction.edit_original_message(
                content='Successfully unlinked your Steam account!', view=None)
            await self.client.log(f'User {interaction.user.id} has unlinked their Steam account')

        async def noBtnCB(interaction):
            await interaction.response.defer()
            await interaction.edit_original_message(content='Cancelled', view=None)

        view = YesNoView(timeout=60, yes_callback=yesBtnCB,
                         no_callback=noBtnCB)

        await interaction.response.send_message(
            f"Are you sure you want to unlink your steam account?\n", ephemeral=True, view=view)


async def setup(client: commands.Bot) -> None:
    client.tree.add_command(SteamMgmt(client=client),
                            guild=discord.Object(id=ServerId))
