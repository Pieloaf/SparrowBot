import discord
from discord.ext import commands
from discord import ui, app_commands, Interaction
from datetime import datetime, timedelta
from interactionTemplates import YesNoView
import json
import re
from const import EmbedColor, checkinBuffer, checkinTime

from tournaments import Tournament, Team
from const import ServerId


class SignUpModal(discord.ui.Modal, title="Tournament Sign Up"):
    def __init__(self, client: commands.Bot, tournament: Tournament) -> None:
        super().__init__()
        self.client = client
        self.tournament = tournament
        self.members: list = []
        self.team: Team = None
        # create inputs for each member
        for i in range(tournament.teamSize-1):
            self.add_item(discord.ui.TextInput(
                label=f"Team Member {i + 1}", placeholder="Name#1234", custom_id=f"user{i}"))

    async def on_submit(self, interaction: Interaction) -> None:
        """on submit modal"""
        teamID = self.tournament.event.id + interaction.user.id

        team = Team(client=self.client, teamId=teamID)
        await team.create(members=self.members)
        if team.name:
            self.team = team
            await self.tournament.addTeam(team)
            await interaction.response.send_message("Team Signup successful!", ephemeral=True)

    async def on_error(self, error, interaction: Interaction) -> None:
        await self.client.log(f"Error creating team: {error}")

    async def interaction_check(self, interaction: Interaction) -> bool:
        """check if interaction is valid"""

        # ensure user not already signed up
        signedup = [member["discord"]
                    for team in self.tournament.teams for member in team.members]
        print(signedup)

        if str(interaction.user.id) in signedup:
            await interaction.response.send_message(
                f"You are already signed up for this tournament.", ephemeral=True)

        # ensure user has linked steam account
        dbUser = await self.client.usefulCogs['db'].getDocument('users', {
            '_id': str(interaction.user.id)
        })
        if not dbUser or not dbUser['steamID']:
            await interaction.response.send_message(f"**Error:** You must link your steam account to the bot to sign up.\n"
                                                    "See the pinned message in <#958874746177597483> for details",
                                                    ephemeral=True)

        # init members list with sign up user
        members = [
            {"discord": str(interaction.user.id), "steam": dbUser['steamID']}]

        # get other members
        for comp in interaction.data['components']:
            nInput = comp['components'][0]['value']
            inputSplit = nInput.split('#')
            name = inputSplit[0]
            try:
                discriminator = inputSplit[1]
                userid = discord.utils.get(self.client.server.members,
                                           name=name, discriminator=discriminator).id

            # handle incorrect formatting/member not found
            except:
                await interaction.response.send_message(f"**Error:** User {nInput}#{discriminator} is not a valid member of this discord.", ephemeral=True)
                return False

            # ensure user not already signed up
            if interaction.user.id in signedup:
                await interaction.response.send_message(
                    f"**Error:** Member <@{userid}> is already signed up for this tournament.", ephemeral=True)
                return False

            # check if user has linked steam account
            dbUser = await self.client.usefulCogs['db'].getDocument('users', {
                '_id': str(userid)
            })
            if not dbUser or not dbUser['steamID']:
                await interaction.response.send_message(f"**Error:** User <@{userid}> has not yet linked their steam account.", ephemeral=True)
                return False

            # ensure unique user
            if userid in members:
                await interaction.response.send_message(
                    f"**Error:** Each team member must be unique.", ephemeral=True)
                return False

            members.append(
                {"discord": str(userid), "steam": dbUser['steamID']})

        self.members = members
        if self.tournament.teamCount == len(self.tournament.teams):
            await interaction.response.send_message(
                f"**Error:** Tournament is already full.", ephemeral=True)
            return False
        return True


class RegionSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Region...", custom_id="region")
        with open("constData.json", "r") as f:
            config = json.load(f)
            options = [discord.SelectOption(
                label=region["name"], value=region["abbr"], emoji=region["flag"]) for region in list(config["regions"].values())]
            options.append(discord.SelectOption(
                label="All Regions", value="all", emoji="🌎"))
            self.options = options

    async def callback(self, interaction: Interaction) -> None:
        self.view.region = str(interaction.data["values"][0])
        await self.view.recieveResp(self, interaction)


class TeamSize(discord.ui.Select):
    def __init__(self):
        with open("constData.json", "r") as f:
            config = json.load(f)
            emojis = ["1️⃣", "2️⃣", "3️⃣"]
            options = [discord.SelectOption(
                label=f"{size}v{size}", value=size, emoji=emojis[size-1]) for size in config["teamSize"]]

        super().__init__(placeholder="Game mode...", options=options, custom_id="teamSize")

    async def callback(self, interaction: Interaction) -> None:
        self.view.teamSize = int(interaction.data["values"][0])
        await self.view.recieveResp(self, interaction)


# class TeamCount(discord.ui.Select):
#     def __init__(self):
#         with open("constData.json", "r") as f:
#             config = json.load(f)
#             options = [discord.SelectOption(
#                 label=f"{count} teams", value=count) for count in config["teamCount"]]

#         super().__init__(placeholder="Team count...",
#                          options=options, custom_id="teamCount")

#     async def callback(self, interaction: Interaction) -> None:
#         self.view.teamCount = int(interaction.data["values"][0])
#         await self.view.recieveResp(self, interaction)


# class GroupStages(discord.ui.Select):
#     def __init__(self):
#         options = [discord.SelectOption(label="No", value=False, description="No group stages"),
#                    discord.SelectOption(label="Yes", value=True, description="Group stages")]

#         super().__init__(placeholder="Group stages...",
#                          options=options, custom_id="groupStages")

#     async def callback(self, interaction: Interaction) -> None:
#         self.view.groups = bool(interaction.data["values"][0])
#         await self.view.recieveResp(self, interaction)


class TourneyConfig(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()
        self.timeout = 120

        self.region = None
        self.teamSize = None
        # self.teamCount = None
        self.groups = None

        self.add_item(RegionSelect())
        self.add_item(TeamSize())
        # self.add_item(TeamCount())
        # self.add_item(GroupStages())

    async def recieveResp(self, comp, interaction):
        self.remove_item(comp)
        label = re.sub(r'(?<!^)(?=[A-Z])', ' ',
                       interaction.data['custom_id']).capitalize()

        data = [data.label for data in comp.options if str(data.value) ==
                interaction.data['values'][0]][0]
        content = f"{interaction.message.content}\n**{label}**: {data}"
        await interaction.response.edit_message(content=content, view=self)
        if self.region and self.teamSize:
            self.stop()


class Tourney(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        super().__init__()
        self.client = client
        self.tournaments = []
        self.tCategory = None

    # create command group
    tourneyGroup = app_commands.Group(
        name="tournament", description="Tournament Mgmt Commands", guild_ids=[ServerId])

    async def ask_for_tournament(self, event: discord.ScheduledEvent) -> None:
        message: discord.Message = None

        async def yesCallback(interaction):
            # start t config
            tConf = TourneyConfig()
            # delete message
            await message.delete()
            # send the config message and wait
            await interaction.response.send_message(content="Tournament Configuration", view=tConf, ephemeral=True)
            await tConf.wait()
            # init tournament
            t = Tournament(self.client, event)
            try:
                # create tournament and schedule checkins
                await t.create(teamSize=tConf.teamSize, region=tConf.region)
                self.client.loop.create_task(self.client.call_this_in(
                    self.signup_or_checkin,
                    ((event.start_time-timedelta(minutes=(checkinTime+checkinBuffer)) -
                     discord.utils.utcnow())).total_seconds(),
                    t.chalTournament.id, checkinTime, False))
            except Exception as e:
                # handle errors
                await self.client.log(f"Error Creating Tournament: {e}")
                await interaction.channel.send(
                    "An error occured creating the tournament. See {}".format(self.client.usefulChannels["logs"]))
                return
            # add tournament to list
            self.tournaments.append(t)
            # send created message
            await interaction.channel.send(f"Tournament {t.event.name} Created!\n"
                                           f"Tournament ID: {t.chalTournament.id}\n"
                                           f"Challonge URL: {t.chalTournament.full_challonge_url}")

            # set category perms for tournament
            await self.tCategory.set_permissions(
                t.role, view_channel=True, connect=True)

        async def noCallback(interaction):
            await interaction.response.defer()
            await interaction.delete_original_message()

        view = YesNoView(180, yes_callback=yesCallback, no_callback=noCallback)

        message = await self.client.usefulChannels['tournament-mgmt'].send(
            f"{self.client.usefulRoles['t-admin'].mention} Create a tournament for {event.name}?\n", view=view)

    # listen for event creation
    @ commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        await self.ask_for_tournament(event)

    #
    # Helper Functions
    #

    @ commands.command(name="tournament", aliases=["t-make", "t-create"])
    @ commands.has_permissions(administrator=True)
    async def tournament(self, ctx: commands.Context, eventId: int) -> None:
        """Create a tournament"""
        try:
            event = await self.client.server.fetch_scheduled_event(eventId)
        except discord.NotFound:
            await ctx.send(f"**Error:** Event {eventId} does not exist.")
            return

        if len([t for t in self.tournaments if t.event.id == int(eventId)]):
            await ctx.send(f"**Error:** Tournament for {event.name} already exists.")
            return

        await self.ask_for_tournament(event)

    @ commands.command(name="tournament-list", aliases=["t-list"])
    @ commands.has_permissions(administrator=True)
    async def listTourneys(self, ctx: commands.Context, filter: str = None) -> None:
        """List all tournaments"""
        tournaments = await self.client.usefulCogs["db"].getDocuments(
            "tournaments", {})

        if not tournaments:
            await ctx.send("No tournaments found.")
            return

        if filter == "active":
            tournaments = [t for t in self.tournaments]
            await ctx.send(f"__Active Tournaments:__\n" + '\n'.join([f"{t.event.name} - {t.chalTournament.id}" for t in tournaments]))
            return

        await ctx.send("__Tournaments:__\n" + "\n".join([f"{t['name']} - {t['_id']}" for t in tournaments]))

    @ commands.command(name="tournament-delete", aliases=["t-delete"])
    @ commands.has_permissions(administrator=True)
    async def deleteTourney(self, ctx: commands.Context, tourneyId: int) -> None:
        """Delete a tournament"""
        # remove if active

        active: list[Tournament] = [
            t for t in self.tournaments if t.chalTournament.id == tourneyId]
        if active:
            self.tournaments.remove(active[0])

        res = await Tournament.deleteTournament(self.client, tourneyId)
        if not res:
            await ctx.send(f"**Error:** Failed to delete tournament {tourneyId}. Check bot logs for more info.")
            return

        # response
        await ctx.send(f"Tournament {tourneyId} deleted")
        await self.client.log(f"Tournament {tourneyId} deleted by {ctx.author}")

    @ commands.command(name="tournament-get", aliases=["t-get"])
    @ commands.has_permissions(administrator=True)
    async def getTourney(self, ctx: commands.Context, tourneyId: int) -> None:
        """Get a tournament"""
        tourney = await self.client.usefulCogs["db"].getDocument(
            "tournaments", {"_id": tourneyId})

        if not tourney:
            await ctx.send(f"**Error:** Tournament {tourneyId} not found.")
            return

        await ctx.send(f"__Tournament:__\n" + "\n".join([f"{k}: {tourney[k]}" for k in tourney]))

    @ commands.command(name="tournament-teams", aliases=["t-teams"])
    @ commands.has_permissions(administrator=True)
    async def getTourneyTeams(self, ctx: commands.Context, tourneyId: int) -> None:
        """Get a tournament's teams"""
        tourney = await self.client.usefulCogs["db"].getDocument(
            "tournaments", {"_id": tourneyId})

        if not tourney:
            await ctx.send(f"**Error:** Tournament {tourneyId} not found.")
            return

        tourneyTeams = tourney["teams"]

        await ctx.send(f"__Teams:__\n" + "\n".join([f"{t['name']} - {t['_id']}" for t in tourneyTeams]))

    @ commands.command(name="tournament-get-team", aliases=["t-get-team"])
    @ commands.has_permissions(administrator=True)
    async def getTourneyTeam(self, ctx: commands.Context, tourneyId: int, teamId: int) -> None:
        """Get a tournament's team"""
        team = await self.client.usefulCogs["db"].getDocument(
            "tournaments", {"_id": tourneyId, "teams._id": teamId})

        if not team:
            await ctx.send(f"**Error:** Team {teamId} not found.")

        await ctx.send(f"__Team:__\n" + team)

# TODO:
# - BIGGEST TODO: PERSISTENT VIEW FOR SIGNUP MESSAGE (DONT WANNA HAVE A FUCK UP IF THE BOT HAS TO RESTART BEFORE A TOURNAMENT)
# - add pagination for the above commands

# - add tournament-start function (on event start)
#       when the tourney starts get all the matches in the tourney for round 1
#       make a text channel for each match
#       on code posted reply with win winner or loss reaction message
#       wait for reply from each user on dispute ping mod, .winner [team] to manually score
#       ask for next code repeat

#       on all round 1 games complete get round two matches and repeat, etc

# - add tournament-end function (on event end)
#       get final standings
#       remove text channel perms but keep channels in case of dispute
#       command to delete all tournament channels when ready

# - add delete tournament on event cancelled: EZ just call existing delete function but on listener for event cancelled

# - add tournament-matches command (get tournament matches)

# - add tournament-add-team command (add team to tournament)
# - add tournament-remove-team command (remove team from tournament)
# - add tournament-substitute-team command (substitute team in tournament)

# - add tournament-standings command (get tournament standings) usable by everyone

# - make tournament-get command prettier + filters eg by state
# - make tournament-teams command prettier + filters eg signup, checkin, reserve, missing
# - make tournament-get-team command prettier

#

    async def signup_or_checkin(self, event_id: int, duration: int, signup: bool = True):
        #
        # Check what should happen with tourney
        #

        try:
            t: Tournament = [
                t for t in self.tournaments if t.chalTournament.id == event_id][0]

        except IndexError:
            await self.client.log(
                f"Error: Tournament {event_id} not found.")
            return False

        if signup:
            stateToChange = "signups"
            string = "sign ups"
        else:
            stateToChange = "checkins"
            string = "check-ins"

        # check if duration
        if t.states[stateToChange] == "pending" and not duration:
            await self.client.log(
                f"Error: A duration is required to start {string}.")
            return False

        # check if signups already ended
        if t.states[stateToChange] == "ended":
            await self.client.log(
                f"{string.capitalize()} for {t.event.name} have already ended")
            return False

        # check if should close signups
        if not duration:
            closed = await self.closeSignups(t, signup)
            if closed:
                await self.client.log(
                    f"{string.capitalize()} for {t.event.name} have been closed")
                return True
            else:
                await self.client.log(
                    f"Error: {string.capitalize()} for {t.event.name} could not be closed")
                return False

        # check if signups already started
        if type(t.states[stateToChange]) == int:
            await self.client.log(
                f"{string.capitalize()} for {t.event.name} have already started")
            return False

        # passed all checks, start signups

        #
        # Sign up button callback
        #

        async def signupCB(interaction):
            # check user has steam linked
            dbUser = await self.client.usefulCogs['db'].getDocument('users', {
                '_id': str(interaction.user.id)
            })

            if not dbUser or not dbUser['steamID']:
                await interaction.response.send_message(
                    f"**Error:** You must have a linked steam account to sign up."
                    "See the pinned video in <#958874746177597483> for details.", ephemeral=True)
                return

            # get already signed up players
            signedup = [member["discord"]
                        for team in t.teams for member in team.members]

            print(signedup)

            # check if user is already signed up
            if str(interaction.user.id) in signedup:
                await interaction.response.send_message(
                    f"**Error:** You have already completed the {string} for this tournament.", ephemeral=True)
                return

            # signup the user(s)
            success = None
            if t.teamSize > 1:
                signUp = SignUpModal(client=self.client, tournament=t)
                await interaction.response.send_modal(signUp)
                await signUp.wait()
                if signUp.team:
                    success = True
            else:
                # get team id
                teamID = t.event.id + interaction.user.id
                # create team
                team = Team(client=self.client, teamId=teamID)
                try:
                    await team.create(members=[{"discord": str(interaction.user.id), "steam": dbUser['steamID']}])
                    await t.signUpTeam(team)
                except Exception as e:
                    await interaction.response.send_message(
                        f"An error occured creating the team, please contact a moderator", ephemeral=True)
                    await self.client.log(f"Error creating team: {e}")
                    return
                await interaction.response.send_message("Signup successful!", ephemeral=True)
                success = True

            # if signup successful
            if success:
                # update signup message
                msg = await self.client.usefulChannels['signups'].fetch_message(t.states["signups"])
                msg.embeds[0].fields[-1] = f"Sign ups close: __**<t:{int((discord.utils.utcnow()+timedelta(minutes=duration)).timestamp())}:R>**__\n"\
                    f"Teams Signed up: __**{len(t.teams) if len(t.teams) <= t.teamCount else t.teamCount }/{t.teamCount}**__ ({(len(t.teams)-t.teamCount)+'reserves' if len(t.teams) > t.teamCount else ''})"

                await msg.edit(embed=msg.embeds[0])

        async def checkinCB(interaction):
            checkedIn = [member["discord"]
                         for team in t.teams for member in team.members if team.state == "checkedIn"]
            if str(interaction.user.id) in checkedIn:
                await interaction.response.send_message(
                    f"**Error:** Your team has already completed the check-in for this tournament.", ephemeral=True)
                return

            for team in t.teams:
                if interaction.user.id in [member["discord"] for member in team.members]:
                    t.checkInTeam(team)
                    break

            # update checkin message
            msg = await self.client.usefulChannels['signups'].fetch_message(t.states["checkins"])
            msg.embeds[0].fields[-1] = f"Check-ins close: __**<t:{int((discord.utils.utcnow()+timedelta(minutes=duration)).timestamp())}:R>**__\n"\
                f"Teams Checked in: __**{len(['x' for team in t.teams if team.state=='checkedIn'])}/{t.teamCount}**__"

        # creating buttons
        view = ui.View()
        signupBtn = ui.Button(
            label='Sign Up', style=discord.ButtonStyle.secondary, emoji='📝', custom_id=f"{event_id}_signup")
        checkinBtn = ui.Button(
            label='Check In', style=discord.ButtonStyle.secondary, emoji='✅', custom_id=f"{event_id}_checkin")

        # assigning callbacks
        signupBtn.callback = signupCB
        checkinBtn.callback = checkinCB

        # add appropriate button
        view.add_item(signupBtn if signup else checkinBtn)

        # create embed
        embed = discord.Embed(title=f"{string.capitalize()} for {t.event.name}",
                              url=t.chalTournament.full_challonge_url,
                              colour=EmbedColor,
                              description=f"{string.capitalize()} are now **open** for {t.event.name}!")
        embed.set_thumbnail(url=self.client.user.avatar.url)
        embed.add_field(name="Tournament Info",
                        value=t.event.description,
                        inline=False)

        if signup:
            ping = discord.utils.get(self.client.server.roles, name=t.region)
            embed.add_field(name="Sign Up Info",
                            value=f"Sign ups close: __**<t:{int((discord.utils.utcnow()+timedelta(minutes=duration)).timestamp())}:R>**__\n"
                            f"Teams Signed up: __**0/{t.teamCount}**__\n"
                            f"Region: __**{t.region}**__\n"
                            f"Game Mode: __**{t.teamSize}v{t.teamSize}**__\n",
                            inline=False)
        else:
            ping = t.role.mention
            embed.add_field(name="Check In Info",
                            value=f"Check-ins close: __**<t:{int((discord.utils.utcnow()+timedelta(minutes=duration)).timestamp())}:R>**__\n"
                            f"Checked-in: __**0/{t.teamCount}**__",
                            inline=False)

        if not signup:
            # allow players to see checkins
            self.client.usefulChannels['checkins'].set_permissions(
                t.role, send_messages=False)

        message = await self.client.usefulChannels[stateToChange].send(content=ping, embed=embed, view=view)

        await t.updateState(stateToChange, message.id)
        await self.client.log(f"{string.capitalize()} for {t.event.name} have started")

        self.task = self.client.loop.create_task(
            self.client.call_this_in(self.closeSignups, duration*60, t, signup))

        return True

    async def closeSignups(self, t: Tournament, signup: bool = True):
        if signup:
            stateToChange = "signups"
            string = "Sign ups"
        else:
            stateToChange = "checkins"
            string = "Check-ins"

        if t.states[stateToChange] == "ended":
            return False
        try:
            # get the message embed
            message = await self.client.usefulChannels[stateToChange].fetch_message(t.states[stateToChange])
            embed = message.embeds[0]
            # update embed
            embed.description = f"{string} are now **closed** for {t.event.name}!"
            embed.remove_field(-1)
            # edit message and update state
            await message.edit(embed=embed, view=None)
            await t.updateState(stateToChange, "ended")

        except Exception as e:
            await self.client.log(f"Error closing {string} for {t.event.name}: {e}")
            return False

        if not signup:
            missing = [team for team in t.teams if team.state != "checkedIn"]
            if len(missing) > 0:
                await self.client.usefulChannels['checkins'].send(
                    f"{len(missing)} teams did not check in.\n"
                    "\n".join([f"{team.name} ({team.id})\n" for team in missing]))
                await self.client.log(f"{len(missing)} teams did not check in")
                reserves = [team for team in t.teams if team.state ==
                            "reserved"][:len(missing)]

                await self.client.usefulChannels['checkins'].send(
                    "Reserves:\n"
                    "\n".join([f"{team.name} ({team.id})\n" for team in reserves]))

        return True

    @ commands.command(name='signup')
    @ commands.has_permissions(administrator=True)
    async def signups(self, ctx, event_id: int, duration: int = None):
        success = await self.signup_or_checkin(event_id, duration)
        if not success:
            await ctx.send(f"An error occured, please see bot logs for more")

    @ commands.command(name='checkin')
    @ commands.has_permissions(administrator=True)
    async def checkins(self, ctx, event_id: int, duration: int = None):
        success = await self.signup_or_checkin(event_id, duration, False)
        if not success:
            await ctx.send(f"An error occured, please see bot logs for more")


async def setup(client):
    await client.add_cog(Tourney(client))
