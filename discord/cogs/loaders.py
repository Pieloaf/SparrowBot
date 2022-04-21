from discord.ext import commands
import os
from const import ServerId
from discord import Object


class Loaders(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @staticmethod
    async def parse_args(args):
        if not args:
            return ''
        if not args.endswith('.py'):
            args += '.py'
        return args

    async def for_each_cog(self, func, args=None):
        # accepting extensions from other dirs
        if len(args.split('/')) == 2:
            parts = args.split('/')
            extDir = parts[0]
            args = parts[1]
        else:
            extDir = 'cogs'

        for filename in os.listdir(f"./{extDir}"):
            # dont unload loader cog
            if filename == 'loaders.py':
                continue

            if filename.endswith('.py') and (args is None or args == filename):
                try:
                    if 'unload' in func:
                        await self.client.unload_extension(
                            f'{extDir}.{filename[:-3]}')
                        await self.client.log(f'unloaded {filename}')
                except Exception as e:
                    await self.client.log(e)
                try:
                    if 'load' in func:
                        await self.client.load_extension(
                            f'{extDir}.{filename[:-3]}')
                        await self.client.log(f'loaded {filename}')
                except Exception as e:
                    await self.client.log(e)
                try:
                    if 'reload' in func:
                        await self.client.reload_extension(
                            f'{extDir}.{filename[:-3]}')
                        await self.client.log(f'reloaded {filename}')
                except Exception as e:
                    await self.client.log(e)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, args):
        args = await self.parse_args(args)
        if not args:
            return
        await self.for_each_cog(['load'], args)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, args):
        args = await self.parse_args(args)
        if not args:
            return
        await self.for_each_cog(['unload'], args)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, args):
        args = await self.parse_args(args)
        if not args:
            return
        await self.for_each_cog(['reload'], args)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reloadAll(self, ctx):
        await self.for_each_cog(['unload', 'load'])

    @commands.command(hidden=True)
    @commands.is_owner()
    async def loadAll(self, ctx):
        await self.for_each_cog(['load'])

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unloadAll(self, ctx):
        await self.for_each_cog(['unload'])

    @commands.command(hidden=True)
    @commands.is_owner()
    async def syncTree(self, ctx):
        try:
            await self.client.tree.sync(guild=Object(id=ServerId))
            await ctx.send('Tree synced!')
            await self.client.log('Tree synced')
        except Exception as e:
            await ctx.send(f"Error syncing tree, see {self.client.usefulChannels['logs']} for more info.")
            await self.client.log(e)


async def setup(client):
    await client.add_cog(Loaders(client))
