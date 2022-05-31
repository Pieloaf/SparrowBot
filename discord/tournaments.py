from discord import ScheduledEvent
import discord
import challonge
import re


class Tournament:
    def __init__(self, client, event):
        self.client = client
        self.event: ScheduledEvent = event

        self.teamCount: int = None
        self.teamSize: int = None
        self.region: str = None
        self.role: discord.role = None
        # self.groups: bool = None

        self.teams: list[Team] = []

        self.chalTournament: challonge.Tournament = None

        self.states = {
            'signups': "pending",  # "pending", "{msg-id}", "ended"
            'checkins': "pending",
            'inprogress': "pending",
        }

    @staticmethod
    async def deleteTournament(client, tId):
        # delete db entry
        t = client.db.db.get_collection(
            'tournaments').find_one_and_delete({'_id': tId})
        if not t:
            await client.log(f"Error tournament {tId} not found in database")
            return False

        # delete event and role
        evt = discord.utils.get(
            client.server.scheduled_events, id=t['event'])
        role = discord.utils.get(
            client.server.roles, id=t['role'])

        if evt:
            await evt.delete()
        if role:
            await role.delete()

        # delete challonge
        try:
            chalT = await client.challonge.get_tournament(tId)
            await client.challonge.destroy_tournament(chalT)
        except challonge.exceptions.ChallongeException:
            await client.log(f"Error deleting tournament {tId} from challonge")
            return False

        return True

    async def create(self, teamSize, region, challonge_id=None, role_id=None):
        self.teamCount = 16
        self.teamSize = int(teamSize)
        self.region = region
        # self.groups = groups

        if not role_id:
            self.role = await self.client.tourneyServer.create_role(name=self.event.name)
        else:
            self.role = discord.utils.get(
                self.client.tourneyServer.roles, id=role_id)

        if not challonge_id:
            self.chalTournament = await self.client.challonge.create_tournament(
                name=self.event.name,
                description=self.event.description if self.event.description else '',
                url=f"sparrow_{ re.sub(r'[^a-zA-Z0-9]', '', self.event.name)}",
                signup_cap=self.teamCount,
                start_at=self.event.start_time,
            )
            try:
                await self.client.db.addDocument('tournaments', {
                    '_id': self.chalTournament.id,
                    'event': self.event.id,
                    'name': self.event.name,
                    'server': self.event.guild.id,
                    'teamCount': self.teamCount,
                    'teamSize': self.teamSize,
                    'region': self.region,
                    'state': self.states,
                    'role': self.role.id,
                    'teams': [],
                })

            except Exception as e:
                await self.client.log(f"Error adding tournament to database: {e}")
                return False

            await self.client.log(
                f"Created tournament {self.event.name} [{self.chalTournament.id}]")

        else:
            self.chalTournament = await self.client.challonge.get_tournament(challonge_id)
            await self.client.log(f"Loaded tournament {self.chalTournament.name} [{self.chalTournament.id}]")

        return True

    async def updateState(self, state, value):
        self.states[state] = value
        try:
            await self.client.db.updateDocument('tournaments',
                                                {'_id': self.chalTournament.id},
                                                {"$set": {'state.' + state: value}})
        except Exception as e:
            await self.client.log(f"Error updating state in database: {e}")
            return None

    async def signUpTeam(self, team):
        # add to db
        if len(self.teams) < self.teamCount:
            team.state = "signedup"
            for member in team.members:
                await discord.utils.get(self.event.guild.members, id=int(member["discord"])).add_roles(self.role)
            p = await self.chalTournament.add_participant(display_name=team.name, misc=team.id)
            team.p_id = p['id']
        else:
            team.state = f"reserved {len(self.teams) - self.teamCount}"

        try:
            await self.client.db.updateDocument('tournaments',
                                                {'_id': self.chalTournament.id},
                                                {"$push": {'teams': team.jsonify()}})
        except Exception as e:
            await self.client.log(f"Error adding team to database: {e}")
            return None

        self.teams.append(team)
        await self.client.log(
            f"Team {team.name} [{team.id}] signed up for {self.event.name}")
        return None

    async def checkInTeam(self, team):

        team.state = "checkedIn"

        #  update db
        try:
            await self.client.db.updateDocument('tournaments',
                                                {'_id': self.chalTournament.id,
                                                    'teams.id': team.id},
                                                {"$set": {'teams.$.state': 'checkedIn'}})
        except Exception as e:
            await self.client.log(f"Error updating team state in database: {e}")
            return None

        await self.client.log(
            f"Team {team.name} [{team.id}] checked in for {self.event.name}")

        return 0

    async def removeTeam(self, teamId):
        # get team object
        team = [team for team in self.teams if team.id == teamId]

        if not team:
            await self.client.log(
                f"Team {teamId} not found in tournament {self.event.name}")
            return

        team: Team = team[0]
        # remove from signedup list
        self.teams.remove(team)
        await self.client.db.updateDocument('tournaments',
                                            {'_id': self.chalTournament.id},
                                            {"$pull": {'signedup': team.jsonify()}})
        # remove from teams
        if self.states["signups"] == "ended":
            try:
                self.teams.remove(team)
                await self.client.db.updateDocument('tournaments',
                                                    {'_id': self.chalTournament.id},
                                                    {"$pull": {'teams': team.jsonify()}})
            except ValueError:
                pass

        # remove from checkins and challonge
        if self.states["checkins"] != "pending":
            self.checkedIn.remove(team)
            try:
                p = await self.chalTournament.get_participant(team.p_id)
                await self.chalTournament.remove_participant(p)
            except challonge.APIException as e:
                await self.client.log(f"Error removing team from challonge: {e}")
                await self.client.db.updateDocument('tournaments',
                                                    {'_id': self.chalTournament.id},
                                                    {"$pull": {'checkedIn': team.jsonify()}})

    async def addTeam(self, team):
        await self.signUpTeam(team)

        if self.states["signups"] == "ended":
            self.teams.append(team)
            await self.client.db.updateDocument('tournaments',
                                                {'_id': self.chalTournament.id},
                                                {"$push": {'teams': team.jsonify()}})

        if self.states["checkins"] != "pending":
            await self.checkInTeam(team)

    async def getTeam(self, teamId):
        team = [team for team in self.teams if team.id == teamId]
        if team:
            return team[0]
        else:
            await self.client.log(f"Team {teamId} not found in tournament {self.event.name}")
            return None

    async def getTeams(self):
        try:
            return await self.chalTournament.get_participants()
        except challonge.APIException as e:
            await self.client.log(f"Error getting teams from challonge: {e}")
            return None

    async def getMatch(self, matchId):
        try:
            return await self.chalTournament.get_match(matchId)
        except challonge.APIException as e:
            await self.client.log(f"Error getting match from challonge: {e}")
            return None

    async def getMatches(self):
        try:
            await self.chalTournament.get_matches()
        except challonge.APIException as e:
            await self.client.log(f"Error getting matches from challonge: {e}")
            return None

    async def startTournament(self):
        try:
            await self.chalTournament.start()
        except challonge.APIException as e:
            await self.client.log(f"Error starting tournament: {e}")
            return False
        return True

    async def endTournament(self):
        try:
            await self.chalTournament.finalize()
        except challonge.APIException as e:
            await self.client.log(f"Error ending tournament: {e}")
            return False
        return True

    async def getFinalStandings(self):
        try:
            return await self.chalTournament.get_final_ranking()
        except challonge.APIException as e:
            await self.client.log(f"Error getting final standings: {e}")
            return None


class Team:
    def __init__(self, client, teamId):
        self.client = client
        self.id: int = teamId
        self.p_id: int = None
        self.seed: int = None
        self.name: str = None
        self.state: str = None
        self.members: list = []

    def jsonify(self):
        return {
            '_id': self.id,
            'seed': self.seed,
            'name': self.name,
            'members': self.members,
        }

    async def create(self, members):
        self.members = members
        steamNames = []
        for member in members:
            steamUser = await self.client.steam.getUser(member["steam"])
            steamNames.append(steamUser['personaname'])

        self.name = ' & '.join(steamNames)
