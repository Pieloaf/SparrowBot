import discord
from sparrowBot import SparrowBot
import os
import json

with open("steam.json", "r") as f:
    steam = json.load(f)

game = discord.Activity(
    name=f"{steam['peakPlayers']} Peak Players! 🎉", type=discord.ActivityType.playing)

intents = discord.Intents.all()
client = SparrowBot(command_prefix=',', intents=intents,
                    status=discord.Status.dnd, activity=game, help_command=None)

# client.run(os.environ['SPARROWBOT_API_KEY'])
client.run(os.environ['TESTBOT_API_KEY'])
