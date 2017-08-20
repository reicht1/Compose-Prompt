#Composeprompt.py, a cog to allow for the automation of weekly composition prompts
# Written by Tyler Reich and Vincent Bryant

import discord
from discord.ext import commands
import os
from os import path
from os import makedirs
import json

#global variables. To be treated as constants
global dataPath 
dataPath = "./data/composeprompt"

#default values for JSON files
global newPromptsList
newPromptsList = {'prompts': []}
global newPriPromptsList
newPriPromptsList = {'priprompts': []}
global newSettingsList
newSettingsList = {'settings': {'promptrun': True, 'channel': '-1'}}
global newGlobalSettingsList
newGlobalSettingsList = {'globalsettings': {}}

class ComposePrompt:

    def __init__(self, bot):
        self.bot = bot
        
        #if dir for JSON files does not exist, make it
        if not os.path.exists(dataPath):
            os.makedirs(dataPath)
        
        if not os.path.exists(dataPath + '/globalsettings.txt'):
            with open(dataPath + '/globalsettings.txt', 'w+') as file:
                json.dump(newGlobalSettingsList, file, indent=4)
            
    @commands.command()		
    async def composetest(self):
        """Test function. To be removed"""
        await self.bot.say("Test function works! Novanebula was here")

    @commands.command(pass_context=True, no_pm=True)		
    async def newprompt(self, ctx, *, prompt : str):
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        promptAuthor = ctx.message.author
        channel = ctx.message.channel
        channelSettings = newSettingsList
        jsonInfo = {}

        """Submit a new prompt."""
        ### 1. user inputs [p]newprompt [prompt goes here] (also error checking) ###
        await self.bot.say("I think you wrote \"" + prompt + "\".") #for test

        # ALLOW MAX PROMPT LENGTH TO BE SET BY ADMIN
        if len(prompt) > 300:
            await self.bot.say("Your prompt was over 300 characters. Prompts should be 300 characters or fewer.")
            return

        ### 2. if word filter is enabled, any words on filter list are removed from input ###

        ### 3. string placed in dataPath + "/" + serverID + '/priorityprompts.txt' as a new prompt entry ###
        # Are we allowed to do this in this server? Let's find out!
        if os.path.exists(serverIDPath + '/settings.txt'):
            with open(serverIDPath + '/settings.txt', 'r') as file:
                try:
                    jsonInfo = json.load(file)
                    if not jsonInfo['settings']['promptrun']:
                        await self.bot.say("ERROR: Composeprompt is not running in this server.")
                        return
                    elif jsonInfo['settings']['channel'] != channel.id:
                        await self.bot.say("ERROR: Composeprompt is not running in this channel.") # Should bot say anything?
                        return
                    else:
                        await self.bot.say("IF PLANTS WORE PANTS WOULD THEY WEAR THEM LIKE THIS [img01.jpg] OR THIS [img02.jpg]???")
                except ValueError:
                    print("ERROR: Composeprompt is not running in this server.") # Should bot say anything?
                    return

        # Now, open the filepath to prompts.txt and add the prompts.
        promptsList = [] # set up new list
        with open(serverIDPath + '/prompts.txt', 'r') as promptFile:
            try:
                jsonPrompts = json.load(promptFile)
                await self.bot.say("...loaded from json file...") # for test
                promptsList = jsonPrompts['prompts']
            except ValueError:
                await self.bot.say("IF PANTS WORE PANTS AM I HIGH??????")
                # I guess the array didn't exist in the prompts.txt file or something.
                return

        with open(serverIDPath + '/prompts.txt', 'w+') as promptFile:
            await self.bot.say("...assigned jsonPrompts to promptsList...") # for test
            newPrompt = {'prompt': prompt, 'author': ctx.message.author.id} # set prompt as dictionary
            await self.bot.say("...created new prompt dictionary...") # for test
            promptsList.append(newPrompt) # append new prompt to current list of prompts
            await self.bot.say("...appended new prompt dictionary to promptsList...") # for test
            print(str(promptsList))
            json.dump({'prompts': promptsList}, promptFile, indent=4) #rewrite prompts.txt with updated list of prompts
            await self.bot.say("...and rewrote prompts list!")


        await self.bot.say("newprompt function ended!") #for test

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
    async def prompton(self, ctx):
        """Turn prompt mode on for this server"""
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        channel = ctx.message.channel
        channelSettings = newSettingsList
        channelSettings['settings']['channel'] = channel.id
        jsonInfo = {}
        promptOn = False
        message = "ERROR"
        
        #see if JSON data folder for server exists. If not, create it
        if not os.path.exists(serverIDPath):
            os.makedirs(serverIDPath)
        
        # see if prompts.txt for server exists. If not, create it
        if not os.path.exists(serverIDPath + '/prompts.txt'):
            with open(serverIDPath + '/prompts.txt', 'w+') as file:
                json.dump(newPromptsList, file, indent=4)
     
        # see if priorityprompts.txt for server exists. If not, create it
        if not os.path.exists(serverIDPath + '/priorityprompts.txt'):
            with open(serverIDPath + '/priorityprompts.txt', 'w+') as file:
                json.dump(newPriPromptsList, file, indent=4)
                
        # see if settings.txt for server exists. If not, create it
        if not os.path.exists(serverIDPath + '/settings.txt'):
            with open(serverIDPath + '/settings.txt', 'w+') as file:
                json.dump(channelSettings, file, indent=4)
            await self.bot.say("Composeprompt set to run in this channel.")    
        else: #if it does exist, see if 'promptrun' is set to True. If not, set it to True
            #get data from JSON file (and update what channel composeprompt is running in)
            with open(serverIDPath + '/settings.txt', 'r') as file:
                try:
                    jsonInfo = json.load(file)
                    jsonInfo['settings']['channel'] = channel.id
                except ValueError:
                    print("ERROR: Assigngamerole: Could not get values from JSON. Assuming list of servers to track is empty")
            
            #if promptrun is false, set it to true
            if jsonInfo['settings']['promptrun']:
                message = "Already running composeprompt in this server. Now running it in this channel."
            else:
                jsonInfo['settings']['promptrun'] = True
                message = "Composeprompt set to run in this channel."
            
            with open(serverIDPath + '/settings.txt', 'w+') as file:
                json.dump(jsonInfo, file, indent=4)
            await self.bot.say(message)    

    @commands.command(pass_context=True, no_pm=True)	
    async def promptoff(self, ctx):
        """Turn prompt mode off for this server"""
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        jsonInfo = {}
        message = "ERROR"
        
        #check to see if settings.txt exists. if not, no need to turn promptrun setting off
        if os.path.exists(serverIDPath + '/settings.txt'):
            #get data from JSON file 
            with open(serverIDPath + '/settings.txt', 'r') as file:
                try:
                    jsonInfo = json.load(file)
                except ValueError:
                    print("ERROR: Assigngamerole: Could not get values from JSON. Assuming list of servers to track is empty")
            
            #if promptrun is false, set it to true
            if jsonInfo['settings']['promptrun']:
                jsonInfo['settings']['promptrun'] = False
                message = "Composeprompt is now off for this server."
            else:
                message = "Composeprompt is already off for this server."
            
            with open(serverIDPath + '/settings.txt', 'w+') as file:
                json.dump(jsonInfo, file, indent=4)
        else:
            message = "Composeprompt is already off for this server."
        
        await self.bot.say(message)	

    @commands.command(pass_context=True, no_pm=True)		
    async def setadmin(self):
        """Modify who can access admin commands for this bot on this server"""
        await self.bot.say("setadmin function works!")

def setup(bot):
    bot.add_cog(ComposePrompt(bot))