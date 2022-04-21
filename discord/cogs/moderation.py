from re import A
from discord.ext import commands
from datetime import datetime, timedelta


class Moderation(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.purgeCount = 0

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int, *args):
        author = None
        message = None
        limit = 100

        if ctx.message.mentions:
            author = ctx.message.mentions[0]

        if ctx.message.channel_mentions:
            channel = ctx.message.channel_mentions[0]
        else:
            channel = ctx.message.channel

        for arg in args:
            if arg.startswith('a.'):
                author = self.client.get_user(int(arg[2:]))
                if not author:
                    await ctx.send(f"An error occured: see {self.client.usefulChannels['logs'].mention} for more info.")
                    await self.client.log(f"Invalid author id: {arg[2:]}")
                    return

            if arg.startswith('m.'):
                try:
                    message = await channel.fetch_message(int(arg[2:]))
                except Exception as e:
                    await ctx.send(f"An error occured: see {self.client.usefulChannels['logs'].mention} for more info.")
                    await self.client.log(f"Error fetching message: {e}")
                    return

            if arg.startswith('l.'):
                limit = int(arg[2:])

        def check_author(m):
            if m.author == author and self.purgeCount < amount:
                self.purgeCount += 1
                return True

        def check_message(m):
            if m.id == message.id:
                self.purgeCount += 1
                return True
            elif self.purgeCount > 0 and self.purgeCount < amount:
                self.purgeCount += 1
                return True

        def check_author_message(m):
            if m.id == message.id:
                self.purgeCount += 1
                return True
            elif self.purgeCount > 0 and self.purgeCount < amount and m.author == author:
                self.purgeCount += 1
                return True

        try:
            if not author and not message:
                await channel.purge(limit=amount)
            elif author and not message:
                await channel.purge(limit=limit, check=check_author)
            elif message and not author:
                await channel.purge(limit=limit, check=check_message, after=(message.created_at-timedelta(hours=1)), oldest_first=True)
            elif author and message:
                await channel.purge(limit=limit, check=check_author_message, after=(message.created_at-timedelta(hours=1)), oldest_first=True)
        except Exception as e:
            await ctx.send(f"An error occured: see #{self.client.usefulChannels['logs'].name} for more info.")
            await self.client.log(f"Error purging messages: {e}")
            self.purgeCount = 0
            return

        self.purgeCount = 0
        await self.client.log(f"{ctx.message.author} purged {amount} messages in {channel.mention}")
        return

    @commands.command()
    @commands.has_any_role('Moderator', 'Developer', 'Administrator')
    async def revokeSteam(self, ctx, user_id, *, reason=None):
        await self.client.usefulCogs['db'].updateDocument('users', {'_id': user_id}, {'$unset': {'steamID': ''}})
        await ctx.send(f"{ctx.message.author.mention} has revoked <@{user_id}>'s linked steam account\nReason: {reason if reason else 'No reason provided'}")

    @commands.Cog.listener()
    async def on_join(self, member):
        if member.created_at < datetime.now() - datetime.timedelta(days=1):
            await self.client.usefulChannels['mod-general'].send(f"{member.mention} has joined the server.\nTheir account is {(datetime.now() - member.created_at).days} days old.\nKinda Sussy Wussy.")


async def setup(client: commands.Bot):
    await client.add_cog(Moderation(client))
