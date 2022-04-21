from requests import get
import json


class SparrowAPI:
    def __init__(self, client):
        self.client = client
        self.backendURL = "https://serverless.projectsparrow.dev/player/{}"
        self.publicURL = "https://projectsparrow.dev/{}"
        with open('constData.json', 'r') as f:
            data = json.load(f)
            self.levelAdd = data['levels']

    async def getPlayer(self, user_id):
        player = get(self.backendURL.format(f"skill?playerId={user_id}"))
        if player.status_code == 200:
            return player.json()
        else:
            raise Exception(f"Failed to get player {user_id}")

    async def getTrials(self, user_id):
        trials = get(self.backendURL.format(f"trials?playerId={user_id}"))
        if trials.status_code == 200:
            return trials.json()
        else:
            raise Exception(f"Failed to get trials for {user_id}")

    async def getLeaderboard(self):
        leaderboard = get(self.backendURL.format('leaderboard'))
        if leaderboard.status_code == 200:
            return leaderboard.json()
        else:
            raise Exception(f"Failed to get leaderboard")

    async def getRank(self, user_id):
        leaderboard = await self.getLeaderboard()
        t100 = sorted(leaderboard['ratings'],
                      key=lambda x: x['rating'], reverse=True)
        t100Ids = [x['id'] for x in t100]
        try:
            return t100Ids.index(user_id) + 1
        except ValueError:
            return "N/A"

    async def getLevel(self, xp):
        lvl = 1
        lvlxp = 0
        levelAdd = self.levelAdd[f'{lvl}']
        while xp > lvlxp + levelAdd:
            lvlxp += levelAdd
            lvl += 1
            if f'{lvl}' in self.levelAdd:
                levelAdd = self.levelAdd[f'{lvl}']
        return lvl  # if lvl <= 55 else 55

    async def makeProfileUrl(self, user_id):
        return self.publicURL.format('player/{}'.format(user_id))
