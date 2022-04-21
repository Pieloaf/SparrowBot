import discord
from discord import app_commands
from discord.ext import commands
import json
from sparrow import *
from const import appId, EmbedColor, ServerId


class SparrowStats(app_commands.Group):
    """Manage Steam Account Linking"""

    def __init__(self, client: commands.Bot) -> None:
        super().__init__(name="sparrow", description="Sparrow Project Commands")
        self.client = client

        with open('constData.json', 'r') as f:
            data = json.load(f)
            self.regions = data['regions']

    @app_commands.command()
    async def current_players(self, interaction: discord.Interaction) -> None:
        """Get the current players in game"""
        players = await self.client.steam.getCurrentPlayers(appId)
        await interaction.response.send_message(
            f"There are currently **{players}** players in game", ephemeral=True)

    @app_commands.command()
    @app_commands.describe(player="@mention the player")
    async def stats(self, interaction: discord.Interaction, player: discord.User = None) -> None:
        """Get player rank"""
        uId = player.id if player else interaction.user.id
        user = await self.client.usefulCogs['db'].getDocument('users', {'_id': str(uId)})
        if not user or 'steamID' not in user:
            await interaction.response.send_message(
                f"{player.mention + 'has ' if player else 'You have'} not yet linked their steam account.\n"
                "See the pinned message in <#958874746177597483>", ephemeral=True)
            return

        steamId = user['steamID']
        player = await self.client.sparrow.getPlayer(steamId)
        steamUser = await self.client.steam.getUser(player['playerId'])

        url = await self.client.sparrow.makeProfileUrl(player['playerId'])
        rating = player['rating']
        region = self.regions[player['region']]['abbr']
        rank = await self.client.sparrow.getRank(player['playerId'])
        victories = player['wins']
        defeats = player['losses']
        avatar = steamUser['avatarmedium']
        level = await self.client.sparrow.getLevel(player['XP'])

        await interaction.response.send_message(
            embed=discord.Embed.from_dict({
                "color": EmbedColor,
                "title": f"{player['name']}",
                "thumbnail": {"url": avatar},
                "url": url,
                "fields": [{"name": "Rating", "value": rating, "inline": True},
                           {"name": "Region", "value": region, "inline": True},
                           {"name": "Rank", "value": rank, "inline": True},
                           {"name": "Level", "value": level, "inline": True},
                           {"name": "Victories", "value": victories, "inline": True},
                           {"name": "Defeats", "value": defeats, "inline": True}]
            }))


async def setup(client: commands.Bot) -> None:
    client.tree.add_command(SparrowStats(client=client),
                            guild=discord.Object(id=ServerId))
