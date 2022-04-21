from pymongo import MongoClient
from discord.ext import commands
import os


class dbCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.db_creds = {
            'host': 'localhost',
            'port': 27017,
            'db': 'sparrow',
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASS']
        }
        self.dbClient = MongoClient(
            "mongodb://{user}:{password}@{host}:{port}/{db}".format(**self.db_creds))
        self.db = self.dbClient.get_database(self.db_creds['db'])

    async def addDocument(self, collection, document):
        try:
            res = self.db.get_collection(collection).insert_one(document)
        except Exception as e:
            await self.client.log(f"Error adding {collection[:-1]} to {collection} collection: {e}")
            return
        await self.client.log(f"Added {res.inserted_id} to {collection} collection")
        return res

    async def addDocuments(self, collection, documents):
        try:
            res = self.db.get_collection(collection).insert_many(documents)
        except Exception as e:
            await self.client.log(f"Error adding multiple {collection} to {collection} collection: {e}")
            return
        await self.client.log(f"Added multiple {collection} to {collection} collection")
        return res

    async def getDocument(self, collection, document):
        try:
            return self.db.get_collection(collection).find_one(document)
        except Exception as e:
            await self.client.log(f"Error getting {collection[:-1]} from {collection} collection: {e}")

    async def getDocuments(self, collection, document):
        try:
            return self.db.get_collection(collection).find(document)
        except Exception as e:
            await self.client.log(f"Error getting multiple {collection} from {collection} collection: {e}")

    async def updateDocument(self, collection, filter, newData):
        try:
            res = self.db.get_collection(
                collection).update_one(filter, newData)
        except Exception as e:
            await self.client.log(f"Error updating {collection[:-1]} in {collection} collection: {e}")
            return
        await self.client.log(f"Updated {res.modified_count} {collection} in {collection} collection")
        return res

    async def updateDocuments(self, collection, filter, newData):
        try:
            res = self.db.get_collection(
                collection).update_many(filter, newData)
        except Exception as e:
            await self.client.log(f"Error updating multiple {collection} in {collection} collection: {e}")
            return
        await self.client.log(f"Updated {res.modified_count} {collection} in {collection} collection")
        return res

    async def deleteDocument(self, collection, document):
        try:
            res = self.db.get_collection(collection).delete_one(document)
        except Exception as e:
            await self.client.log(f"Error deleting {collection[:-1]} from {collection} collection: {e}")
            return
        await self.client.log(f"Deleted {res.deleted_count} {collection} from {collection} collection")
        return res

    async def deleteDocuments(self, collection, document):
        try:
            res = self.db.get_collection(collection).delete_many(document)
        except Exception as e:
            await self.client.log(f"Error deleting multiple {collection} from {collection} collection: {e}")
            return
        await self.client.log(f"Deleted {res.deleted_count} {collection} from {collection} collection")
        return res

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def getUser(self, ctx, userid):
        user = await self.getDocument('users', {'_id': userid})
        await ctx.send(f"```{user}```")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def getById(self, ctx, collection, id):
        document = await self.getDocument(collection, {'_id': int(id)})
        await ctx.send(f"```{document}```")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def getByKey(self, ctx, collection, key, value):
        documents = await self.getDocuments(collection, {key: value})
        await ctx.send(f"{len(documents)} documents found")
        for document in documents:
            await ctx.send(f"```{document}```")


async def setup(client):
    await client.add_cog(dbCog(client))
