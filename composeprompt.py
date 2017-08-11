import discord
from discord.ext import commands

class ComposePrompt:
	
    def __init__(self, bot):
        self.bot = bot

    @commands.command()		
    async def composetest(self):
        """Test function. To be removed"""
        await self.bot.say("Test function works!")
		
    @commands.command(pass_context=True, no_pm=True)		
    async def newprompt(self):
        """Submit a new prompt."""
        await self.bot.say("newprompt function works!")

    @commands.command(pass_context=True, no_pm=True)		
    async def entrysubmit(self):
        """Submit an entry for this week's prompt."""
        await self.bot.say("entrysubmit function works!")
		
    @commands.command(pass_context=True, no_pm=True)		
    async def setpromptstart(self):
        """Set the time when a prompt period begins and ends"""
        await self.bot.say("setpromptstart function works!")

    @commands.command(pass_context=True, no_pm=True)		
    async def priprompt(self):
        """Create a priority prompt"""
        await self.bot.say("priprompt function works!")

    @commands.command(pass_context=True, no_pm=True)		
    async def showentries(self):
        """Show all entries submitted for this week's prompt so far!"""
        await self.bot.say("showentries function works!")

    @commands.command(pass_context=True, no_pm=True)		
    async def prompton(self):
        """Turn prompt mode on for this server"""
        await self.bot.say("prompton function works!")	

    @commands.command(pass_context=True, no_pm=True)	
    async def promptoff(self):
        """Turn prompt mode off for this server"""
        await self.bot.say("promptoff function works!")	

    @commands.command(pass_context=True, no_pm=True)		
    async def setadmin(self):
        """Modify who can access admin commands for this bot on this server"""
        await self.bot.say("setadmin function works!")	
		
def setup(bot):
    bot.add_cog(ComposePrompt(bot))