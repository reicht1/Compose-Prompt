import discord
from discord.ext import commands

class ComposePrompt:
	
    def __init__(self, bot):
        self.bot = bot

    @commands.command()		
    async def composetest(self):
        await self.bot.say("Test function works!")


def setup(bot):
    bot.add_cog(ComposePrompt(bot))