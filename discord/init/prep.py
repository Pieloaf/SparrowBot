from datetime import datetime, timedelta
import discord
from discord.ext import commands
from const import *
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
        self.client.steam = steam.Steam(self.client)
        self.client.sparrow = sparrow.SparrowAPI(self.client)

    async def init_tournaments(self):
        tCog = self.client.get_cog('Tourney')
        db = self.client.get_cog('dbCog')

        tCog.tCategory = discord.utils.get(
            self.client.tourneyServer.categories, name="Participants")

        tourneys = await db.getDocuments('tournaments', {})
        for t in tourneys:
            if t['state']['inprogress'] == 'ended':
                continue

            evt = discord.utils.get(
                self.client.server.scheduled_events, id=t['event'])

            if not evt:
                await db.deleteDocument('tournaments', {'_id': t['_id']})
                continue

            if t['event'] in [t.event.id for t in tCog.tournaments]:
                continue

            tObj = Tournament(self.client, evt)
            try:
                await tObj.create(t['teamSize'], t['region'], t['_id'], t['role'])
            except Exception as e:
                await self.client.log(f"Error loading tournament {t['_id']}: {e}\nRemoving tournament from database")
                await db.deleteDocument('tournaments', {'_id': t['_id']})

            tCog.tournaments.append(tObj)

            # schedule checkins
            if evt.start_time > discord.utils.utcnow():
                self.client.loop.create_task(self.client.call_this_in(
                    tCog.signup_or_checkin,
                    ((evt.start_time -
                     timedelta(minutes=(checkinTime-checkinBuffer))-discord.utils.utcnow())).total_seconds(),
                    t['_id'], checkinTime, False))

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
        if api == 'steam':
            reload(steam)
            self.client.steam = steam.Steam(self.client)
        elif api == 'sparrow':
            reload(sparrow)
            self.client.sparrow = sparrow.SparrowAPI(self.client)
        await ctx.send(f'Reloaded {api} API functions')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def loadTournaments(self, ctx):
        await self.init_tournaments()
        await ctx.send('Done!')


async def setup(client):
    await client.add_cog(Prep(client))
