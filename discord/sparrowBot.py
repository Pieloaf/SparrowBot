import os
from discord.ext import commands
import challonge
from dotenv import load_dotenv
import asyncio
import inspect


class SparrowBot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        load_dotenv()
        self.server = None
        self.usefulChannels = {}
        self.usefulEmotes = {}
        self.usefulRoles = {}
        self.usefulChannels = {}
        self.usefulCogs = {}
        self.trello = None
        self.steam = None
        self.sparrow = None
        self.challonge = None

    async def setup_hook(self):
        for file in os.listdir('./init'):
            if file.endswith('.py'):
                await self.load_extension(f'init.{file[:-3]}')

        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                await self.load_extension(f'cogs.{file[:-3]}')

        self.challonge = challonge.User(
            os.environ['CHALLONGE_USER'], os.environ['CHALLONGE_API_KEY'])

    async def log(self, *args):
        msg = ' '.join(str(x) for x in args)
        if 'logs' in self.usefulChannels:
            await self.usefulChannels['logs'].send(f"```{msg}```")
        print(msg, flush=True)

    @staticmethod
    async def call_this_in(func, time, *args):
        await asyncio.sleep(time)
        if inspect.iscoroutinefunction(func):
            if args:
                return await func(*args)
            return await func()
        if args:
            return func(*args)
        return func()

    # on command error

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You are missing a required argument.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
        else:
            await ctx.send(f"An error occurred: {error}")
            await self.log(error)

    class MissingSomething(Exception):
        def __init__(self, *args):
            if args:
                self.message = args[0]
            else:
                self.message = None

        def __str__(self):
            if self.message:
                return 'MissingSomething, {0} '.format(self.message)
            else:
                return 'MissingSomething has been raised'
