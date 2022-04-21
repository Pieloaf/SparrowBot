import requests
import os
import json


class Steam:
    def __init__(self, client) -> None:
        self.apiKey = os.environ["STEAM_API_KEY"]
        self.ISteamUserUrl = "https://api.steampowered.com/ISteamUser"
        self.ISteamUserStatsUrl = "https://api.steampowered.com/ISteamUserStats"
        self.format = "&format=json"
        self.client = client

    async def getUser(self, steamid: int) -> dict:
        url = f"{self.ISteamUserUrl}/GetPlayerSummaries/v2/?key={self.apiKey}&steamids={steamid}{self.format}"
        r = requests.get(url)
        if r.status_code == 200 and json.loads(r.text)["response"]["players"] != []:
            return json.loads(r.text)["response"]["players"][0]

        await self.client.log(f"Error: Failed to get user info for {steamid}")
        await self.client.log(r.text)
        return {}

    async def getCurrentPlayers(self, appid: int) -> dict:
        url = f"{self.ISteamUserStatsUrl}/GetNumberOfCurrentPlayers/v1/?key={self.apiKey}&appid={appid}{self.format}"
        r = requests.get(url)
        if r.status_code == 200 and json.loads(r.text)["response"] != {}:
            return json.loads(r.text)["response"]["player_count"]

        await self.client.log(f"Error: Failed to get current players for {appid}")
        await self.client.log(r.text)
        return {}

    async def resolveVanityUrl(self, vanityUrl: str) -> int:
        url = f"{self.ISteamUserUrl}/ResolveVanityURL/v1/?key={self.apiKey}&vanityurl={vanityUrl}{self.format}"
        print(url)
        r = requests.get(url)
        if r.status_code == 200 and json.loads(r.text)["response"]["success"] == 1:
            return json.loads(r.text)["response"]["steamid"]

        await self.client.log(f"Error: Failed to resolve vanity url {vanityUrl}")
        await self.client.log(r.text)
        return {}
