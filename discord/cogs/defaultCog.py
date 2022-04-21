from ast import alias
from discord.ext import commands
import discord
import json
from const import UsefulCogs


class DefaultCog(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    def is_cool(self, member: discord.Member):
        for role in member.roles:
            if role.id in [role.id for role in self.client.usefulRoles.values()]:
                return True
        return False

    @commands.command()
    async def ping(self, ctx):
        if self.is_cool(ctx.author):
            await ctx.send(f"{ctx.author.mention} Pong!")
            return

        await ctx.send(f"You are not cool enough to use this command B(")

    @commands.command(aliases=['setStatus'])
    async def status(self, ctx, type, *, message):
        if self.is_cool(ctx.author):
            try:
                game = discord.Activity(
                    name=message, type=discord.ActivityType[type])
            except:
                await ctx.send(f"Invalid activity type '{type}'")
                return

            await self.client.change_presence(status=discord.Status.online, activity=game)
            await ctx.send(f"Status changed!")
            await self.client.log(f"Bot status changed to {type} {message} by {ctx.author}")
            return

        await ctx.send(f"You don't have permission to change the bot's status!")

    @commands.command(aliases=['addCmd'])
    async def createCmd(self, ctx, name, *, response):
        if self.is_cool(ctx.author):

            with open("./customCmd.json", "r") as f:
                cmds = json.load(f)

            cmds[name] = response

            with open("./customCmd.json", "w") as f:
                json.dump(cmds, f)

            await ctx.send(f"Command '{name}' created!")
            return

        await ctx.send(f"You don't have permission to create commands!")

    @commands.command(aliases=['removeCmd'])
    async def deleteCmd(self, ctx, name):
        if self.is_cool(ctx.author):
            with open("./customCmd.json", "r") as f:
                cmds = json.load(f)

            if name in cmds:
                del cmds[name]

                with open("./customCmd.json", "w") as f:
                    json.dump(cmds, f)
                await ctx.send(f"Command '{name}' deleted!")
            else:
                await ctx.send(f"Command '{name}' not found")
            return

        await ctx.send(f"You don't have permission to delete commands!")

    @commands.command(aliases=['editCmd'])
    async def updateCmd(self, ctx, name, *, response):
        if self.is_cool(ctx.author):
            with open("./customCmd.json", "r") as f:
                cmds = json.load(f)

            if name in cmds:
                cmds[name] = response

                with open("./customCmd.json", "w") as f:
                    json.dump(cmds, f)
                await ctx.send(f"Command '{name}' updated!")
            else:
                await ctx.send(f"Command '{name}' not found")
            return

        await ctx.send(f"You don't have permission to update commands!")

    @commands.command(aliases=['cmds', 'help'])
    async def listCmds(self, ctx):
        with open("./customCmd.json", "r") as f:
            cmds = json.load(f)

        msg = ""
        for idx, cmd in enumerate(cmds):
            msg += f"{idx + 1}. {cmd}\n"

        await ctx.send(f"```{msg}```")
        return

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            with open("./customCmd.json", "r") as f:
                cmds = json.load(f)
            if ctx.invoked_with.lower() in cmds:
                await ctx.send(cmds[ctx.invoked_with.lower()])
                return
        await self.client.log(error)


async def setup(client: commands.Bot):
    await client.add_cog(DefaultCog(client))
