import subprocess
import json
import requests
import re
import os


class Trello:
    def __init__(self, client):
        self.baseUrl = "https://api.trello.com/1"
        self.authData = None
        self.client = client
        self.trelloToken = os.environ["TRELLO_API_KEY"]
        with open("tokens.json") as f:
            try:
                self.authData = json.load(f)
                self.authString = f"key={self.trelloToken}&token={self.authData['accessToken']}"
            except KeyError:
                self.authData = None
                self.authString = None

    async def auth(self):
        p = subprocess.Popen(
            ["node", "../tokenServer/index.js"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        for line in p.stdout:
            if line == "Listening on port 3000\n":
                await self.client.log("Server started, waiting for auth...")
            if re.match(r'{"accessToken":"[0-9a-z]+","accessTokenSecret":"[0-9a-z]+"}', line):
                self.authData = json.loads(line)
                self.authString = f"key={self.trelloToken}&token={self.authData['accessToken']}"
                with open("tokens.json", "w") as f:
                    json.dump(self.authData, f)
                await self.client.log("Auth successful")
                await self.__setUserId()
                return True

        if p.stderr:
            await self.client.log(p.stderr.read())
            return False

        if p.returncode != 0:
            await self.client.log("Auth Server Error")
            return False

    async def __setUserId(self):
        url = f"{self.baseUrl}/members/me?{self.authString}"
        r = requests.get(url)
        if r.status_code == 200:
            self.user = json.loads(r.text)["id"]
            with open("trello.json", "r") as f:
                data = json.load(f)
                data["userId"] = self.user
            with open("trello.json", "w") as f:
                json.dump(data, f)
        else:
            await self.client.log(f"Error: Failed to get user id\n{r.text}[{r.status_code}]")

    async def getUser(self):
        url = f"{self.baseUrl}/members/me?{self.authString}"
        r = requests.get(url)
        if r.status_code == 200:
            return json.loads(r.text)
        else:
            await self.client.log(f"Error: Failed to get user\n{r.text}[{r.status_code}]")
            return None

    async def createOrg(self, name):
        url = f"{self.baseUrl}/organizations?displayName={name}&{self.authString}"
        r = requests.post(url)
        if r.status_code == 200:
            return json.loads(r.text)
        else:
            await self.client.log(f"Error: Failed to create organization\n{r.text}[{r.status_code}]")
            return None

    async def createElement(self, type, data):
        url = f"{self.baseUrl}/{type}s?{self.authString}"
        r = requests.post(url, json=data)
        if r.status_code == 200:
            return json.loads(r.text)
        else:
            await self.client.log(f"Error: Failed to create {type}\n{r.text}[{r.status_code}]")
            return None

    async def addComment(self, cardId, text):
        url = f"{self.baseUrl}/cards/{cardId}/actions/comments?{self.authString}"
        r = requests.post(url, json={"text": text})
        if r.status_code == 200:
            return True
        else:
            await self.client.log(f"Error: Failed to add comment\n{r.text}[{r.status_code}]")
            return False

    async def addAttachment(self, cardId, attUrl, name):
        url = f"{self.baseUrl}/cards/{cardId}/attachments?{self.authString}"
        r = requests.post(url, params={"url": attUrl, "name": name})
        if r.status_code != 200:
            await self.client.log(f"Error: Failed to add attachment\n{r.text}[{r.status_code}]")
            return False
        return True

    async def getElement(self, type, id, data):
        url = f"{self.baseUrl}/{type}s/{id}?{self.authString}"
        r = requests.get(url, params=data)
        if r.status_code == 200:
            return json.loads(r.text)
        else:
            await self.client.log(f"Error: Failed to get {type}\n{r.text}[{r.status_code}]")
            return None

    async def updateElement(self, type, id, data):
        url = f"{self.baseUrl}/{type}s/{id}?{self.authString}"
        r = requests.put(url, json=data)
        if r.status_code == 200:
            return True
        else:
            await self.client.log(f"Error: Failed to update {type}\n{r.text}[{r.status_code}]")
            return False
