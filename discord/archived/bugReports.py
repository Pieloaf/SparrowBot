from discord.ext import commands
import json


class BugReport(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.priority = {
            "✅": "low",
            "⚠": "medium",
            "❗": "high"
        }
        self.update = None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id not in [self.client.usefulChannels["bugs"].id,
                                      self.client.usefulChannels["feedback"].id]:
            return
        channel = self.client.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        member = self.client.server.get_member(payload.user_id)

        if self.client.usefulRoles['dev'] in member.roles or member.id == self.client.owner_id:

            with open("trello.json", "r") as f:
                data = json.load(f)
                bugTracking = data["bugTracking"] if "bugTracking" in data else {
                }

            description = f"**{message.author.name}#{message.author.discriminator}:** {message.content}"

            if payload.emoji.name == self.client.usefulEmotes['append']:
                if not self.update:
                    cardId = bugTracking['bugs'][-1]['card']
                else:
                    cardId = self.update

                if not len(message.content) == 0:
                    resp = await self.client.trello.getElement('card', cardId, {"fields": "desc"})
                    desc = resp['desc']
                    desc += f"\n\n{description}"
                    await self.client.trello.updateElement('card', cardId, {"desc": desc})

                if message.attachments:
                    for attachment in message.attachments:
                        await self.client.trello.addAttachment(cardId, attachment.url, attachment.filename)

            elif payload.emoji.name == self.client.usefulEmotes['update']:
                # remove old update
                if self.update:
                    for bug in bugTracking['bugs']:
                        if bug['card'] == self.update:
                            msg = await channel.fetch_message(bug['message'])
                            await msg.remove_reaction(payload.emoji, payload.member)

                # set new update
                for bug in bugTracking['bugs']:
                    if bug['message'] == payload.message_id:
                        self.update = bug['card']
                        break

                # if message not registerd bug
                if not self.update:
                    await self.client.log(f'Message {payload.message_id} not found in bugTracking')
                    await message.remove_reaction(payload.emoji, payload.member)
                    return

            elif payload.emoji.name in self.priority.keys():
                priority = self.priority[payload.emoji.name]
                if 'bugs' in bugTracking:
                    for bug in bugTracking['bugs']:
                        if bug['message'] == payload.message_id:
                            await self.client.log(f'Bug {bug["card"]} already exists')
                            await message.remove_reaction(payload.emoji, payload.member)
                            msg = await channel.fetch_message(bug['message'])
                            await msg.remove_reaction(payload.emoji, payload.member)
                            return

                card = await self.client.trello.createElement(
                    'card',
                    {
                        "name": f"Bug #{len(bugTracking['bugs']) if 'bugs' in bugTracking else 0}",
                        "desc": description+f"\n\n{message.jump_url}",
                        "idList": bugTracking['lists'][priority],
                        "idLabels": [bugTracking['labels'][priority]]
                    })
                if not card:
                    await self.client.usefulChannels['logs'].send(self.client.usefulRoles['dev'].mention)
                    return
                cardId = card['id']
                bug = {
                    'card': cardId,
                    'message': message.id
                }

                with open("trello.json", "w") as f:
                    bugTracking['bugs'] = [
                        bug] if 'bugs' not in bugTracking else bugTracking['bugs'] + [bug]
                    data['bugTracking'] = bugTracking
                    json.dump(data, f)

                if message.attachments:
                    for attachment in message.attachments:
                        await self.client.trello.addAttachment(cardId, attachment.url, attachment.filename)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id not in [self.client.usefulChannels["bugs"].id,
                                      self.client.usefulChannels["feedback"].id]:
            return

        if payload.emoji.name != self.client.usefulEmotes['update']:
            return

        if self.client.usefulRoles['dev'] in self.client.server.get_member(payload.user_id).roles:
            with open("trello.json", "r") as f:
                data = json.load(f)
                if not "bugTracking" in data or not "bugs" in data["bugTracking"]:
                    return

                for bug in data['bugTracking']['bugs']:
                    if self.update == bug['card'] and bug['message'] == payload.message_id:
                        self.update = None
                        break

    @ commands.command()
    @ commands.has_role('developer')
    async def trelloAuth(self, ctx):
        await self.client.log("Setting up Trello...")
        await ctx.send("Trello Login:\nhttps://sparrow.pieloaf.com/trello/login")
        auth = await self.client.trello.auth()
        if not auth:
            await ctx.send("Error connecting to Trello, see {} for more info".format(self.client.usefulChannels['logs'].mention))
            return
        await ctx.send("Trello Auth Complete\n")

    @ commands.command()
    @ commands.has_role('developer')
    async def CreateBugBoard(self, ctx, orgName=None):
        with open("trello.json", "r") as f:
            data = json.load(f)
            bugTracking = data["bugTracking"] if "bugTracking" in data else {
            }
        # check if board exists
        if 'board' in bugTracking:
            await ctx.send("Bug Board already exists")
            return

        await self.client.log(f"Creating Bug Board")

        if orgName:
            org = await self.client.trello.createOrg(orgName)
            if not org:
                await ctx.send(f"Error creating org\nSee {self.client.usefulChannels['logs'].mention} for more info")
                return
            data['org'] = org['id']

        # create board
        board = await self.client.trello.createElement(
            'board',
            {
                "name": "Bugs",
                "defaultLabels": False,
                "defaultLists": False,
                "prefs_background": "purple",
                "idOrganization": org['id'] if orgName else "",
                "prefs_permissionLevel": "org" if orgName else "private"
            }
        )
        # if board is created
        if board:
            await ctx.send(f"Bug Board Created: {board['url']}")
            bugTracking['board'] = board['id']

        else:
            await ctx.send(f"Error creating board\nSee {self.client.usefulChannels['logs'].mention} for more info")
            return

        # create pending list
        lists = ['Fixed for next patch', 'Working on', 'High', 'Medium', 'Low']
        bugTracking['lists'] = {}
        for listName in lists:
            list = await self.client.trello.createElement(
                'list',
                {
                    "name": listName,
                    "idBoard": board['id']
                }
            )
            if list:
                bugTracking['lists'][listName.lower().replace(
                    " ", "-")] = list['id']
            else:
                await ctx.send(f"Error creating list\nSee {self.client.usefulChannels['logs'].mention} for more info")
                return

        # create labels
        lables = [
            {"name": "low", "color": "green"},
            {"name": "medium", "color": "orange"},
            {"name": "high", "color": "red"}
        ]
        bugTracking['labels'] = {}
        for labelDetails in lables:
            labelDetails['idBoard'] = board['id']
            label = await self.client.trello.createElement('label', labelDetails)
            if label:
                bugTracking['labels'][label['name']] = label['id']
            else:
                await ctx.send(f"Error creating label\nSee {self.client.usefulChannels['logs'].mention} for more info")
                return

        with open("trello.json", "w") as f:
            data['bugTracking'] = bugTracking
            json.dump(data, f)

        await self.client.log("Bug Board Created")


async def setup(client: commands.Bot):
    await client.add_cog(BugReport(client))
