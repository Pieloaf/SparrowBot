import discord
from discord.ext import commands
from const import *
import trello
import steam
import sparrow
from importlib import reload
from tournaments import Tournament


class Prep(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def init_server(self):
        server = discord.utils.get(self.client.guilds, id=ServerId)
        if not server:
            raise self.client.MissingSomething('ServerId')
        self.client.server = server

        self.client.tourneyServer = server

    async def init_channels(self):
        for (var, chanName) in UsefulChannelNames:
            channel = discord.utils.get(
                self.client.server.channels, name=chanName)
            if not channel:
                raise self.client.MissingSomething(
                    f"{chanName} channel is missing")
            self.client.usefulChannels[var] = channel

    async def init_roles(self):
        for (var, roleName) in UsefulRoles:
            role = discord.utils.get(self.client.server.roles, name=roleName)
            if not role:
                raise self.client.MissingSomething(
                    f"{roleName} role is missing")
            self.client.usefulRoles[var] = role

    async def init_cogs(self):
        for (var, cogName) in UsefulCogs:
            cog = self.client.get_cog(cogName)
            if not cog:
                raise self.client.MissingSomething(
                    f"{cogName} cog is missing")
            self.client.usefulCogs[var] = cog

    async def init_emotes(self):
        for (var, emote) in UsefulEmotes:
            self.client.usefulEmotes[var] = emote

    async def init_api(self):
        self.client.trello = trello.Trello(self.client)
        self.client.steam = steam.Steam(self.client)
        self.client.sparrow = sparrow.SparrowAPI(self.client)

    async def init_tournaments(self):
        tCog = self.client.get_cog('Tourney')
        db = self.client.get_cog('dbCog')

        tourneys = await db.getDocuments('tournaments', {})
        for t in tourneys:
            if t['state']['inprogress'] == 'ended':
                continue
            evt = discord.utils.get(
                self.client.server.scheduled_events, id=t['event'])
            tObj = Tournament(self.client, evt)
            await tObj.create(t['teamCount'], t['teamSize'],
                              t['region'], t['groups'], t['_id'], t['role'])

            tCog.tournaments.append(tObj)

        # schedule checkins
        # self.client.loop.create_task(tCog.signup_or_checkin())

    async def prep(self):
        try:
            await self.init_server()
            await self.init_channels()
            await self.init_cogs()
            await self.init_emotes()
            await self.init_roles()
            await self.init_api()
            await self.init_tournaments()
        except self.client.MissingSomething as e:
            await self.client.log(e)
            await self.client.log('Exiting...')
            await self.client.close()
            exit()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def runPrep(self, ctx):
        await self.prep()
        await ctx.send('Done!')
        await self.client.log('Prep complete')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reloadAPI(self, ctx, api):
        if api == 'trello':
            reload(trello)
            self.client.trello = trello.Trello(self.client)
        elif api == 'steam':
            reload(steam)
            self.client.steam = steam.Steam(self.client)
        elif api == 'sparrow':
            reload(sparrow)
            self.client.sparrow = sparrow.SparrowAPI(self.client)
        await ctx.send(f'Reloaded {api} API functions')


async def setup(client):
    await client.add_cog(Prep(client))
