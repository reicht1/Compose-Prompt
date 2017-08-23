#Composeprompt.py, a cog to allow for the automation of weekly composition prompts
# Written by Tyler Reich and Vincent Bryant

import discord
from discord.ext import commands
import os
from os import path
from os import makedirs
import json
from cogs.utils import checks

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
global newEntriesList
newEntriesList = {'entries': []}
global newDomainWhitelist
newDomainWhitelist = {'whitelist': []}

class ComposePrompt:

    def __init__(self, bot):
        self.bot = bot
        
        #if dir for JSON files does not exist, make it
        if not os.path.exists(dataPath):
            os.makedirs(dataPath)
        
        if not os.path.exists(dataPath + '/globalsettings.txt'):
            with open(dataPath + '/globalsettings.txt', 'w+') as file:
                json.dump(newGlobalSettingsList, file, indent=4)

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
        #await self.bot.say("I think you wrote \"" + prompt + "\".") #for test

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
                        await self.bot.say("ERROR: This is not the correct channel for submitting prompts.") # Should bot say anything?
                        return
                except ValueError:
                    print("ERROR: Composeprompt is not running in this server.") # Should bot say anything?
                    return

        # Now, open the filepath to prompts.txt and add the prompts.
        promptsList = [] # set up new list
        with open(serverIDPath + '/prompts.txt', 'r') as promptFile:
            try:
                jsonPrompts = json.load(promptFile)
                promptsList = jsonPrompts['prompts']
            except ValueError:
                print("ERROR: Composeprompt: [p]newprompt: Could not get data from JSON file!")
                # I guess the array didn't exist in the prompts.txt file or something.
                return

        newPrompt = {'prompt': prompt, 'author': ctx.message.author.id} # set prompt as dictionary
        promptsList.append(newPrompt) # append new prompt to current list of prompts 
               
        with open(serverIDPath + '/prompts.txt', 'w+') as promptFile:
            json.dump({'prompts': promptsList}, promptFile, indent=4) #rewrite prompts.txt with updated list of prompts

        #await self.bot.say("newprompt function ended!") #for test

    @commands.command(pass_context=True, no_pm=True)		
    async def entrysubmit(self, ctx, *, entry : str):
        """Submit an entry for this week's prompt."""
        
        entryAuthor = ctx.message.author
        jsonEntries = newEntriesList
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        entriesList = []
        
        #get list of existing entries
        with open(serverIDPath + '/entries.txt', 'r') as file:
            try:
                jsonEntries = json.load(file)
                entriesList = jsonEntries['entries']
            except ValueError: #I guess the array didn't exist in the entries.txt file or something.
                print("ERROR: Composeprompt: [p]newprompt: Could not get data from JSON file!")
        
        #append new entry to list of entries
        entriesList.append({'entry': entry, 'author': entryAuthor.id})
        
        #overwrite file with new list
        with open(serverIDPath + '/entries.txt', 'w+') as file:
            json.dump({'entries': entriesList}, file, indent=4)
        
        await self.bot.say("Entry submitted!")

    @commands.command(pass_context=True, no_pm=True)		
    async def setpromptstart(self):
        """Set the time when a prompt period begins and ends"""
        await self.bot.say("setpromptstart function works!")

    @checks.admin_or_permissions(manage_roles=True)
    @commands.command(pass_context=True, no_pm=True)		
    async def priprompt(self, ctx, *, entry : str):
        """Create a priority prompt"""
        entryAuthor = ctx.message.author
        jsonPriPrompts = newPriPromptsList
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        priPromptsList = []
        
        #get list of existing priority prompts
        with open(serverIDPath + '/priorityprompts.txt', 'r') as file:
            try:
                jsonPriPrompts = json.load(file)
                priPromptsList = jsonPriPrompts['priprompts']
            except ValueError: #I guess the array didn't exist in the priorityprompts.txt file or something.
                print("ERROR: Composeprompt: [p]priprompt: Could not get data from JSON file!")
        
        #append new entry to list of entries
        priPromptsList.append({'prompt': entry, 'author': serverID})
        
        #overwrite file with new list
        with open(serverIDPath + '/priorityprompts.txt', 'w+') as file:
            json.dump({'priprompts': priPromptsList}, file, indent=4)
        
        await self.bot.say("priprompt function works!")

    @commands.command(pass_context=True, no_pm=True)
    async def showentries(self, ctx):
        """Show all entries submitted for this week's prompt so far!"""

        entryAuthor = ctx.message.author
        jsonEntries = newEntriesList
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        entriesList = []

        # get list of existing entries
        with open(serverIDPath + '/entries.txt', 'r') as file:
            try:
                jsonEntries = json.load(file)
                entriesList = jsonEntries['entries']
            except ValueError:  # I guess the array didn't exist in the entries.txt file or something.
                print("ERROR: Composeprompt: [p]newprompt: Could not get data from JSON file!")

        # send list of entries via PM to requesting user
        messageText = ""
        for entry in entriesList:
            messageText += "\n- " + (await self.bot.get_user_info(entry['author'])).name + ": " + entry['entry']

        if len(messageText) == 0:
            messageText = "\n- No entries yet! Get working!"

        messageText = "List of entries:" + messageText

        await self.bot.send_message(ctx.message.author, content=messageText, tts=False, embed=None)


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
                
        # see if entries.txt for server exists. If not, create it
        if not os.path.exists(serverIDPath + '/entries.txt'):
            with open(serverIDPath + '/entries.txt', 'w+') as file:
                json.dump(newEntriesList, file, indent=4)

        # see if whitelist.txt for server exists. If not, create it
        if not os.path.exists(serverIDPath + '/whitelist.txt'):
            with open(serverIDPath + '/whitelist.txt', 'w+') as file:
                json.dump(newDomainWhitelist, file, indent=4)
                
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
    async def viewdomains(self, ctx):
        """View domain names on the whitelist stored by this bot"""
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID

        # get list of existing items on whitelist
        with open(serverIDPath + '/whitelist.txt', 'r') as file:
            try:
                jsonWhitelist = json.load(file)
                whitelist = jsonWhitelist['whitelist']
            except ValueError:  # I guess the array didn't exist in the whitelist.txt file?
                print("ERROR: Composeprompt: [p]adddomain: Could not get data from JSON file!")

        whitelistString = ""

        for domain in whitelist:
            whitelistString += "- " + domain + "\n"

        if len(whitelistString) == 0:
            whitelistString = "- no domains here!"

        await self.bot.say("Domains whitelisted:\n" + whitelistString)

    @commands.command(pass_context=True, no_pm=True)
    async def adddomain(self, ctx, domain : str):
        """Add a domain name to the whitelist stored by this bot. Admin-only."""
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        domain = domain.lower() # make domain lowercase

        # get list of existing items on whitelist
        with open(serverIDPath + '/whitelist.txt', 'r') as file:
            try:
                jsonWhitelist = json.load(file)
                whitelist = jsonWhitelist['whitelist']
            except ValueError:  # I guess the array didn't exist in the whitelist.txt file?
                print("ERROR: Composeprompt: [p]adddomain: Could not get data from JSON file!")

        # check if domain name is already on whitelist
        # if not, append new domain name to whitelist
        if domain in whitelist:
            await self.bot.say("Domain \"" + domain + "\" is already in whitelist!")
            return
        else:
            whitelist.append(domain)

        # overwrite file with updated whitelist
        with open(serverIDPath + '/whitelist.txt', 'w+') as file:
            json.dump({'whitelist': whitelist}, file, indent=4)

        with open(serverIDPath + '/whitelist.txt', 'r') as file:
            try:
                jsonWhitelist = json.load(file)
                whitelist = jsonWhitelist['whitelist']
                latest = whitelist[len(whitelist) - 1]
                await self.bot.say("I think you just submitted the domain \"" + latest + "\".")
            except ValueError:
                await self.bot.say("I am:\n⚪ a success message\n⚪ an error message\n🔘 in a relationship, stop staring")

        await self.bot.say("adddomain function works! (I think.)")

    @commands.command(pass_context=True, no_pm=True)
    async def removedomain(self, ctx, domain : str):
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        domain = domain.lower() # make domain lowercase

        # get list of existing items on whitelist
        with open(serverIDPath + '/whitelist.txt', 'r') as file:
            try:
                jsonWhitelist = json.load(file)
                whitelist = jsonWhitelist['whitelist']
            except ValueError:  # I guess the array didn't exist in the whitelist.txt file?
                print("ERROR: Composeprompt: [p]addtowhitelist: Could not get data from JSON file!")

        # find domain name in whitelist and remove it
        if domain in whitelist:
            whitelist.remove(domain)
        else:
            await self.bot.say("\"" + domain + "\" was not in whitelist.")
            return

        # overwrite file with updated whitelist
        with open(serverIDPath + '/whitelist.txt', 'w+') as file:
            json.dump({'whitelist': whitelist}, file, indent=4)

        await self.bot.say("removedomain function\n⚪ doesn't work\n⚪ works!\n🔘 has haunted my waking hours for months now")

    @commands.command(pass_context=True, no_pm=True)
    async def setadmin(self):
        """Modify who can access admin commands for this bot on this server"""
        await self.bot.say("setadmin function works!")

def setup(bot):
    bot.add_cog(ComposePrompt(bot))