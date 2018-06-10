#Composeprompt.py, a cog to allow for the automation of weekly composition prompts
# Written by Tyler Reich and Vincent Bryant

import shutil
import asyncio
import discord
from discord import errors
from discord.errors import Forbidden
from discord.errors import HTTPException
from discord.errors import NotFound                  
from discord.ext import commands
import os
from os import path
from os import makedirs
from os import listdir
import json
from cogs.utils import checks
import sched
import _thread
import re
import time
from time import ctime
from datetime import datetime
from datetime import timedelta
import threading
from random import randint
from cogs.utils.chat_formatting import bold
from cogs.utils.chat_formatting import warning
from cogs.utils.chat_formatting import box

#global variables. To be treated as constants
global dataPath 
dataPath = "./data/composeprompt"
global minPrompts
minPrompts = 10
global busyFile
busyFile = "/busy"
global likeEmoji
likeEmoji = 11088

#default values for JSON files
global newPromptsList
newPromptsList = {'prompts': []}
global newPriPromptsList
newPriPromptsList = {'priprompts': []}
global newSettingsList
newSettingsList = {'settings': {'promptrun': True, 'channel': '-1'}}
global newGlobalSettingsList
newGlobalSettingsList = {'globalsettings': {'promptstarttimes': {}, 'nextpromptreset': {}}}
global newEntriesList
newEntriesList = {'entries': []}
global newDomainWhitelist
newDomainWhitelist = {'whitelist': ["soundcloud", "youtube", "instaud.io", "clyp.it"]}

class ComposePrompt:

    def __init__(self, bot):
        self.bot = bot

        #if dir for JSON files does not exist, make it
        if not os.path.exists(dataPath):
            os.makedirs(dataPath)
        
        #if globalsettings.txt does not exist, make
        if not os.path.exists(dataPath + '/globalsettings.txt'):
            with open(dataPath + '/globalsettings.txt', 'w+') as file:
                json.dump(newGlobalSettingsList, file, indent=4)

        #print("printing directories...")
        directoryList = os.listdir(dataPath)
        for directory in directoryList:
            if os.path.exists(dataPath + '/' + directory + busyFile):
                shutil.rmtree(dataPath + '/' + directory + busyFile)
                
        #start checking loop
        thread = threading.Thread(target=self.periodicCheck, args=()).start()
      
    @commands.command(pass_context=True, no_pm=True)        
    async def newprompt(self, ctx, *, prompt : str):
        """Submit a new prompt."""
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        promptAuthor = ctx.message.author
        channel = ctx.message.channel
        channelSettings = newSettingsList
        jsonInfo = {}

        ### 1. user inputs [p]newprompt [prompt goes here] (also error checking) ###

        # ALLOW MAX PROMPT LENGTH TO BE SET BY ADMIN
        if len(prompt) > 500:
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

        await self.bot.say("Prompt submitted!")

    @commands.command(pass_context=True, no_pm=True)        
    async def entrysubmit(self, ctx, *, entry : str):
        """Submit an entry for this week's prompt."""
        
        submittedMessage = ctx.message.content
        entryAuthor = ctx.message.author
        jsonEntries = newEntriesList
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        entriesList = []
        entryDomain = ""
        
        #get if a prompt does exist for this week
        with open(serverIDPath + '/settings.txt', 'r') as file:
            try:          
                jsonSettings = json.load(file)
                settingsList = jsonSettings['settings']
                
                if "prompt" not in settingsList:
                    await self.bot.say("Not currently accepting entries, as there is no prompt this week.")
                    return
                
            except ValueError: #I guess the array didn't exist in the entries.txt file or something.
                print("ERROR: Composeprompt: [p]newprompt: Could not get data from settings JSON file!")
                return
        
        #get list of existing entries
        with open(serverIDPath + '/entries.txt', 'r') as file:
            try:
                jsonEntries = json.load(file)
                entriesList = jsonEntries['entries']
            except ValueError: #I guess the array didn't exist in the entries.txt file or something.
                print("ERROR: Composeprompt: [p]newprompt: Could not get data from entries JSON file!")
                return
        
        #check and see if it has url in domain
        regEx = "([a-zA-Z0-9]*\.[a-zA-Z0-9]*\.?[a-zA-Z0-9]*)" #what you're looking for is in group 3       
        strictURLregEx = "http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+" 
        result = re.search(regEx, submittedMessage)
        
        #if there is no url, return and do not submit entry
        if result is None:
            await self.bot.say("No URL detected.")
            return
        
        foundURL = re.search(strictURLregEx, entry)
        if foundURL is not None:
            entry = entry.replace(foundURL.group(0), "<" + foundURL.group(0) + ">")
               
        entryDomain = result.group(0)
    
        #get list of accepted domains
        with open(serverIDPath + '/whitelist.txt', 'r') as file:
            try:
                whitelist = json.load(file)
                whitelist = whitelist['whitelist']
            except ValueError: #I guess the array didn't exist in the entries.txt file or something.
                print("ERROR: Composeprompt: [p]entrysubmit: Could not get data from whitelist JSON file!")
     
        #check if URL is from any of the domains
        whitelisted = False;
        for domain in whitelist:
            domainRegexResult = re.search(str.lower(domain), str.lower(entryDomain))
            
            if domainRegexResult is not None:
                whitelisted = True;
        
        if not whitelisted:
            await self.bot.say("Website is not whitelisted.")
            return
        
        #append new entry to list of entries
        entriesList.append({'entry': entry, 'author': entryAuthor.id})
        
        #overwrite file with new list
        with open(serverIDPath + '/entries.txt', 'w+') as file:
            json.dump({'entries': entriesList}, file, indent=4)
        
        await self.bot.say("Entry submitted!")

    @checks.admin()
    @commands.command(pass_context=True, no_pm=True)        
    async def setpromptstart(self, ctx, *, promptTime : str):
        """Set the prompt time when a prompt period begins and ends"""
        #regular expression for imput format should be:
        serverID = ctx.message.server.id
        regEx = "(sunday|monday|tuesday|wednesday|thursday|friday|saturday) (1[0-2]|[1-9]):([0-5][0-9]) ([ap]m)"
        result = re.search(regEx, promptTime.lower())
        newTime = ""
        globalSettings = newGlobalSettingsList
        schedulerTime = 0
        newTimeStruct = []
        
        #if the expected format of the prompt time was not found, exit this function
        if (result is None):
            await self.bot.say("Could not find a time of the week\nPlease input in the format of <Day of the week> <Hour>:<Minute> <AM/PM>\nExample: Friday 5:00 PM")
            return
        
        with open(dataPath + "/globalsettings.txt", "r") as settingsFile:
            try:
                globalSettings = json.load(settingsFile)
            except ValueError:
                await self.bot.say("ERROR: Composeprompt: [p]newprompt: Could not get data from globalsettings.txt JSON file!")
                return
                
        newTime = result.group(0)
   
        schedulerTime = int(self.convertToSchedulerTime(newTime))
        newTimeStruct = self.convertToStructTime(newTime)
        
        globalSettings["globalsettings"]["promptstarttimes"][serverID] = newTime
        globalSettings["globalsettings"]["nextpromptreset"][serverID] = [newTimeStruct.year, newTimeStruct.month, newTimeStruct.day, newTimeStruct.hour, newTimeStruct.minute]
                
        with open(dataPath + "/globalsettings.txt", "w+") as settingsFile:
            json.dump(globalSettings, settingsFile, indent=4)
          
        await self.bot.say("Prompt reset time set to " + newTime)
      
    @checks.admin()
    @commands.command(pass_context=True, no_pm=True)
    async def priprompt(self, ctx, *, entry : str):
        """Create a priority prompt"""
        entryAuthor = ctx.message.author.id
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
        priPromptsList.append({'prompt': entry, 'author': entryAuthor})
        
        #overwrite file with new list
        with open(serverIDPath + '/priorityprompts.txt', 'w+') as file:
            json.dump({'priprompts': priPromptsList}, file, indent=4)

        await self.bot.say("Priority prompt submitted!")

    @commands.command(pass_context=True, no_pm=True)
    async def viewentries(self, ctx):
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
        
        if len(entriesList) == 0:
            await self.bot.send_message(ctx.message.author, content="No entries yet! Get working!", tts=False, embed=None)
            return
        
        await self.bot.send_message(ctx.message.author, content=bold("List of entries:"), tts=False, embed=None)
        
        for entry in entriesList:
            userObject = await self.bot.get_user_info(entry['author'])
            messageText = userObject.name +":\n" + entry['entry']
            await self.bot.send_message(ctx.message.author, content=messageText, tts=False, embed=None)

    @commands.command(pass_context=True, no_pm=True)
    async def myentries(self, ctx):
        
        entryAuthor = ctx.message.author
        jsonEntries = newEntriesList
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        entriesList = []
        count = 0;

        # get list of existing entries
        with open(serverIDPath + '/entries.txt', 'r') as file:
            try:
                jsonEntries = json.load(file)
                entriesList = jsonEntries['entries']
            except ValueError:  # I guess the array didn't exist in the entries.txt file or something.
                print("ERROR: Composeprompt: [p]newprompt: Could not get data from JSON file!")

        # send list of entries via PM to requesting user
        messageText = ""
        
        if len(entriesList) == 0:
            await self.bot.send_message(ctx.message.author, content="No one has submitted anything yet.\nAnd that includes you.", tts=False, embed=None)
            return
        
        await self.bot.send_message(ctx.message.author, content=bold("List of entries:"), tts=False, embed=None)
        
        for entry in entriesList:
            if entry['author'] == entryAuthor.id:
                count = count + 1
                messageText = "Entry #" + str(count) + ": " + entry['entry']
                await self.bot.send_message(ctx.message.author, content=messageText, tts=False, embed=None)
        
        if count is 0:
            await self.bot.send_message(ctx.message.author, content="This list is empty because you have submitted exactly nothing.\nGood job.", tts=False, embed=None)
        
    @commands.command(pass_context=True, no_pm=True)
    async def deletemyentry(self, ctx, num):
    
        #if num is not a valid number, then this function stops
        try:
            int(num)
        except ValueError:
            await self.bot.say("No such entry exists.")
            return
        
        entryAuthor = ctx.message.author
        jsonEntries = newEntriesList
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        entriesList = []
        count = 0;

        # get list of existing entries
        with open(serverIDPath + '/entries.txt', 'r') as file:
            try:
                jsonEntries = json.load(file)
                entriesList = jsonEntries['entries']
            except ValueError:  # I guess the array didn't exist in the entries.txt file or something.
                print("ERROR: Composeprompt: [p]newprompt: Could not get data from JSON file!")

        # send list of entries via PM to requesting user
        messageText = ""
        
        index = 0
        for entry in entriesList:   
            if entry['author'] == entryAuthor.id:
                count = count + 1
                if count == int(num):
                    deletedEntry = entriesList.pop(index)
                    #await self.bot.send_message(ctx.message.author, content="Removed " + str(deletedEntry['entry']), tts=False, embed=None)
                    await self.bot.say("Removed " + str(deletedEntry['entry']))
                    with open(serverIDPath + '/entries.txt', 'w+') as file:
                        json.dump({"entries": entriesList}, file, indent=4)
                    
                    return
            index = index + 1
        await self.bot.say("No such entry exists.")
            
    @checks.admin()
    @commands.command(pass_context=True, no_pm=True)
    async def viewprompts(self, ctx):
        """Show all prompts AND priority prompts stored by this bot."""
        promptAuthor = ctx.message.author
        jsonPrompts = newPromptsList
        jsonPriPrompts = newPriPromptsList
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        promptsList = []

        # get list of existing PRIORITY PROMPTS
        with open(serverIDPath + '/priorityprompts.txt', 'r') as file:
            try:
                jsonPriPrompts = json.load(file)
                priPromptsList = jsonPriPrompts['priprompts']
            except ValueError:
                print("ERROR: Composeprompt: [p]viewprompts: Could not get data from priprompts JSON file!")

        await self.bot.send_message(ctx.message.author, content="Loading priority prompts and prompts...", tts=False, embed=None)

        # send list of prompts via PM to requesting user
        messageText = ""

        if len(priPromptsList) == 0:
            await self.bot.send_message(ctx.message.author, content="There are no priority prompts loaded.", tts=False, embed=None)
        else:
            messageText = "*List of priority prompts:*"
            index = 1
            for priPrompt in priPromptsList:
                userObject = await self.bot.get_user_info(priPrompt['author'])
                messageText = messageText + "\nP" + str(index) + ". " + userObject.name + ": " + priPrompt['prompt']
                index += 1
                if index % 5 == 0:
                    await self.bot.send_message(ctx.message.author, content=messageText, tts=False, embed=None)
                    messageText = "";
            if index % 5 != 0:
                await self.bot.send_message(ctx.message.author, content=messageText, tts=False, embed=None)

        # get list of existing PROMPTS
        with open(serverIDPath + '/prompts.txt', 'r') as file:
            try:
                jsonPrompts = json.load(file)
                promptsList = jsonPrompts['prompts']
            except ValueError:
                print("ERROR: Composeprompt: [p]viewprompts: Could not get data from prompts JSON file!")

        # send list of prompts via PM to requesting user
        messageText = ""

        if len(promptsList) == 0:
            await self.bot.send_message(ctx.message.author, content="No prompts yet! You should add some!", tts=False, embed=None)
        else:
            messageText = "List of prompts:\n"
            index = 1
            for prompt in promptsList:
                userObject = await self.bot.get_user_info(prompt['author'])
                messageText += str(index) + ". " + userObject.name + ": " + prompt['prompt'] + "\n"
                index += 1
                if index % 5 == 0:
                    await self.bot.send_message(ctx.message.author, content=messageText, tts=False, embed=None)
                    messageText = "";
            if index % 5 != 0:
                await self.bot.send_message(ctx.message.author, content=messageText, tts=False, embed=None)
    @checks.admin()
    @commands.command(pass_context=True, no_pm=True)
    async def deleteprompt(self, ctx, num):
        """Delete a specific prompt by index number."""
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        dataFile = ""

        # Depending on whether the num input begins with a P or not
        # (i.e. whether the input refers to a prompt or priority prompt),
        # specify the appropriate filename and keyname.
        if num[0].lower() == "p":
            dataFile = "/priorityprompts.txt"
            baseList = newPriPromptsList
            keyName = "priprompts"
            try:
                num = int(num[1:])
            except ValueError:
                await self.bot.say("Invalid input!")
        else:
            dataFile = "/prompts.txt"
            baseList = newPromptsList
            keyName = "prompts"
            try:
                num = int(num)
            except ValueError:
                await self.bot.say("Invalid input!")

        baseList = []
        with open(serverIDPath + dataFile, "r") as promptsFile:
            try:
                baseList = json.load(promptsFile)
            except ValueError:
                await self.bot.say("ERROR: Composeprompt: [p]newprompt: Could not get data from JSON file!")
                return

        if num < 1 or num > len(baseList[keyName]):
            await self.bot.say("Invalid index number.")
            return

        poppedPrompt = baseList[keyName].pop(num - 1)

        await self.bot.say("You have deleted the prompt '" + poppedPrompt['prompt'] + "'")

        with open(serverIDPath + dataFile, 'w+') as file:
            json.dump({keyName: baseList[keyName]}, file, indent=4)

    @checks.admin()
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
                    print("ERROR: Composeprompt: prompton could not get values from JSON.")
                    return
            
            #if promptrun is false, set it to true
            if jsonInfo['settings']['promptrun']:
                message = "Already running composeprompt in this server. Now running it in this channel."
            else:
                jsonInfo['settings']['promptrun'] = True
                message = "Composeprompt set to run in this channel."
            
            with open(serverIDPath + '/settings.txt', 'w+') as file:
                json.dump(jsonInfo, file, indent=4)
            await self.bot.say(message)    

    @checks.admin()
    @commands.command(pass_context=True, no_pm=True)    
    async def promptoff(self, ctx):
        """Turn prompt mode off for this server"""
        serverID = ctx.message.server.id
        serverIDPath = dataPath + "/" + serverID
        jsonInfo = {}
        message = "ERROR"
        globalSettings = {}
        
        #remove information about server from globalsettings.txt 
        #this with block gets information
        with open(dataPath + '/globalsettings.txt', 'r') as file:
            try:
                globalSettings = json.load(file)
                print(globalSettings["globalsettings"]["nextpromptreset"][serverID], globalSettings["globalsettings"]["promptstarttimes"][serverID])
                globalSettings["globalsettings"]["nextpromptreset"].pop(serverID, None)
                globalSettings["globalsettings"]["promptstarttimes"].pop(serverID, None)              
            except ValueError:
                print("ERROR: Composeprompt: Could not get values from globalsettings JSON. Assuming list of servers to track is empty.")
                return
        #this with block sets information
        with open(dataPath + '/globalsettings.txt', 'w+') as file:
            try:
                json.dump(globalSettings, file, indent=4)
            except ValueError:
                print("ERROR: Composeprompt: Could not write to globalsettings JSON.")
        
        
        #check to see if settings.txt exists. if not, no need to turn promptrun setting off
        if os.path.exists(serverIDPath + '/settings.txt'):
            #get data from JSON file 
            with open(serverIDPath + '/settings.txt', 'r') as file:
                try:
                    jsonInfo = json.load(file)
                except ValueError:
                    print("ERROR: Composeprompt: Could not get values from settings JSON. Assuming list of servers to track is empty.")
                    return
            
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

    @checks.admin()
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

        await self.bot.say("Domain added to whitelist!")

    @checks.admin()
    @commands.command(pass_context=True, no_pm=True)
    async def deletedomain(self, ctx, domain : str):
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

        await self.bot.say("Domain removed from whitelist!")
        
    #turn human readable time of the week into seconds before time of the week occurs next
    def convertToSchedulerTime(self, humanTime : str):
        dayOfWeek = -1
        hour = -1
        minute = -1
        pm = False
    
        #get different elements of the string, and convert it to a number
        #group 0 = entire match
        #group 1 = day of the week
        #group 2 = hour
        #group 3 = minute
        #group 4 = am or pm
        regEx = "(sunday|monday|tuesday|wednesday|thursday|friday|saturday) (1[0-2]|[1-9]):([0-5][0-9]) ([ap]m)"
        result = re.search(regEx, humanTime)
        
        #convert day of the week to a number
        if result.group(1) == 'monday':
            dayOfWeek = 0
        elif result.group(1) == 'tuesday':
            dayOfWeek = 1
        elif result.group(1) == 'wednesday':
            dayOfWeek = 2
        elif result.group(1) == 'thursday':
            dayOfWeek = 3
        elif result.group(1) == 'friday':
            dayOfWeek = 4
        elif result.group(1) == 'saturday':
            dayOfWeek = 5
        elif result.group(1) == 'sunday':
            dayOfWeek = 6
        else:
            dayOfWeek = "ERROR"
        
        #convert hour into a number used by the time_struct
        if result.group(4) == 'pm':
            pm = True
        else:
            pm = False
        
        if result.group(2) == '12':
            if pm:
                hour = 12
            else:
                hour = 0
        else:
            if pm:
                hour = int(result.group(2)) + 12
            else:
                hour = int(result.group(2)) 

        #get the minute for time_struct
        minute = int(result.group(3))
        
        #get the time right now, and get datetime object of when prompt switches
        nowTime = datetime.today()
        endTime = datetime(year = nowTime.year, month = nowTime.month, day = nowTime.day, hour = hour, minute = minute, second = 0)
        
        if (dayOfWeek == nowTime.weekday()):
            if hour > nowTime.hour or (hour == nowTime.hour and minute > nowTime.minute):
                pm = pm
            else:
                endTime = endTime + timedelta(days = 7)
        else:
            while(dayOfWeek != endTime.weekday()):
                endTime = endTime + timedelta(days = 1)
        
        #get difference between now and when the prompt switches
        secondsResult = (endTime - nowTime).total_seconds()
        
        #returns seconds left until reset time
        return secondsResult
 
    #turn human readable time of the week into a datetime object (perhaps later convertToSchedulerTime and concertToStuctTime can be
    #optimized, as most of these two functions is the same)
    def convertToStructTime(self, humanTime : str):
        dayOfWeek = -1
        hour = -1
        minute = -1
        pm = False
    
        #get different elements of the string, and convert it to a number
        #group 0 = entire match
        #group 1 = day of the week
        #group 2 = hour
        #group 3 = minute
        #group 4 = am or pm
        regEx = "(sunday|monday|tuesday|wednesday|thursday|friday|saturday) (1[0-2]|[1-9]):([0-5][0-9]) ([ap]m)"
        result = re.search(regEx, humanTime)
        
        #convert day of the week to a number
        if result.group(1) == 'monday':
            dayOfWeek = 0
        elif result.group(1) == 'tuesday':
            dayOfWeek = 1
        elif result.group(1) == 'wednesday':
            dayOfWeek = 2
        elif result.group(1) == 'thursday':
            dayOfWeek = 3
        elif result.group(1) == 'friday':
            dayOfWeek = 4
        elif result.group(1) == 'saturday':
            dayOfWeek = 5
        elif result.group(1) == 'sunday':
            dayOfWeek = 6
        else:
            dayOfWeek = "ERROR"
        
        #convert hour into a number used by the time_struct
        if result.group(4) == 'pm':
            pm = True
        else:
            pm = False
        
        if result.group(2) == '12':
            if pm:
                hour = 12
            else:
                hour = 0
        else:
            if pm:
                hour = int(result.group(2)) + 12
            else:
                hour = int(result.group(2)) 

        #get the minute for time_struct
        minute = int(result.group(3))
        
        #get the time right now, and get datetime object of when prompt switches
        nowTime = datetime.today()
        endTime = datetime(year = nowTime.year, month = nowTime.month, day = nowTime.day, hour = hour, minute = minute, second = 0)
        
        
        if (dayOfWeek == nowTime.weekday()):
            if hour > nowTime.hour or (hour == nowTime.hour and minute > nowTime.minute):
                pm = pm
            else:
                endTime = endTime + timedelta(days = 7)
        else:
            while(dayOfWeek != endTime.weekday()):
                endTime = endTime + timedelta(days = 1)
        
        #get difference between now and when the prompt switches
        resultStruct = endTime
        
        #returns seconds left until reset time
        return resultStruct
  
    ##test command to activate promptRestart
    #@checks.admin()
    #@commands.command(pass_context=True, no_pm=True)
    #async def testCommand(self, ctx):
    #    asyncio.run_coroutine_threadsafe(self.promptRestart(ctx.message.server.id), self.bot.loop)
   
    #runs continuously, checking to see if it is time to activate promptRestart 
    def periodicCheck(self):
        waitTime = 60
        servers = {}
        continueChecking = True;
        #continue this loop indefinitely
        while(continueChecking):
            with open(dataPath + '/globalsettings.txt', 'r') as file:
                servers = json.load(file)
                servers = servers["globalsettings"]["nextpromptreset"]
                nowTime = datetime.today()
                
            for serverID in servers: #for each server, load the prompt time
                loadTime = servers[serverID]
                newDateTime = datetime(year = int(loadTime[0]), month = int(loadTime[1]), day = int(loadTime[2]), hour = int(loadTime[3]), minute = int(loadTime[4]))
                schedulerTime = (newDateTime - nowTime).total_seconds()
                
                if schedulerTime < 0:
                    continueChecking = asyncio.run_coroutine_threadsafe(self.promptRestart(serverID), self.bot.loop)           
        
            #wait, and then do it all again
            time.sleep(waitTime)
   
    #print out existing entries (if they exist) and choose a new one. Return false if the instance of periodicCheck() that called it is duplicate. Returns True 
    #otherwise.
    async def promptRestart(self, serverID):    
        serverIDPath = dataPath + "/" + serverID
        channel = -1
        prompts = {}
        priPrompts = []
        promptsToUse = {}
        newPrompt = {}
        canidatePrompts = []
        channelObject = None
        prompts = {}
        
        #if this bot isn't even logged in yet, don't bother
        if not self.bot.is_logged_in:
            return True
        
        #see if busy file exists for this server. If so, promptRestart is already running and this instance should abort
        if os.path.isdir(serverIDPath + busyFile):
            print("Crap, promptRestart is already running!")
            return False
        else:
            os.makedirs(serverIDPath + busyFile)
        
        if not os.path.isfile(serverIDPath + '/settings.txt'):
            #remove busyfile        
            if os.path.isdir(serverIDPath + busyFile):
                shutil.rmtree(serverIDPath + busyFile)
            return True
        
        #get settings information from JSON file
        with open(serverIDPath + '/settings.txt', 'r') as file:
            try:
                settings = json.load(file)
                settings = settings['settings']
            except ValueError:
                print("could not get settings from global settings")
                await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from globalsettings.txt JSON file!")
                return True
       
        print("checking if promptrun is in settings")
        #check to see if composeprompt is supposed to be running in this server
        if "promptrun" in settings:
            if settings["promptrun"] is False:
                return True
        else:
            return True     
       
        #if it gets to this point, then it is supposed to be running this this server
      
        #get which channel composeprompt should run in for this server
        if "channel" in settings:
            channel = settings["channel"]
            channelObject = self.bot.get_channel(settings["channel"])
        else:
            channel = self.bot.get_server(serverID)
            channelObject = channel
            await self.bot.send_message(channel, 'Error. Bot does not have channel to run in. Using default channel')    
     
        with open(serverIDPath + '/entries.txt', 'r') as file:    
            try:
                entries = json.load(file)
            except ValueError:
                await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from entires.txt JSON file!")
                return True
                
        #get prompts from file
        with open(serverIDPath + '/prompts.txt', 'r') as file:
            try:
                prompts = json.load(file)
            except ValueError:
                await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from prompts.txt JSON file!")
                return True
       
        #get if there was a prompt for the previous week. If so, show it and what was submitted last week.
        if "prompt" in settings:
            userMention = await self.bot.get_user_info(settings["prompt"]["author"])  
            await self.bot.send_message(self.bot.get_channel(channel), bold("Last week's prompt was:\n") + box(settings["prompt"]["prompt"]) + "Submitted by " + userMention.mention)  
 
            #see if list of entries is empty
            if len(entries["entries"]) > 0:
                #if not empty, print out all the entires
                await self.bot.send_message(self.bot.get_channel(channel), bold("Here's what people submitted!:\n"))

                for entry in entries["entries"]:
                    userMention = await self.bot.get_user_info(entry["author"])   
                    await self.bot.send_message(self.bot.get_channel(channel), "Submission by " + userMention.mention + " :\n" + entry["entry"])   

                # delete entries
                with open(serverIDPath + '/entries.txt', 'w+') as file:
                    json.dump(newEntriesList, file, indent=4)
                
            else:
                #state that there were no entries
                await self.bot.send_message(self.bot.get_channel(channel), warning('There were no submitted entries this week. Gosh darn it!'))
               
        #see if there are any priority prompts
        with open(serverIDPath + '/priorityprompts.txt', 'r') as file:    
            try:
                priPrompts = json.load(file)
            except ValueError:
                await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from prompts.txt JSON file!")
                return True
        
        #see if priority list is empty. If it has stuff in it, use that first. Else, use regular prompts
        
        if len(priPrompts["priprompts"]) > 0:
            promptsToUse = priPrompts["priprompts"][0]
            priPrompts["priprompts"].pop(0)

            with open(serverIDPath + '/priorityprompts.txt', 'w+') as file:
                json.dump({"priprompts": priPrompts["priprompts"]}, file, indent=4)
              
        else:  #use regular prompts     
            #see if candidate exist if so, choose winner. Otherwise, randomly choose a prompt from all available prompts           
            candidatePrompts = [];
            settings = {}
            with open(serverIDPath + '/settings.txt', 'r') as file:
                try:
                    settings = json.load(file)
                except ValueError:
                    await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from settigns.txt JSON file!")
                    return True
                     
            #see if there are condidate prompts
            if 'candidateprompts' in settings['settings']:
                #see which prompt has the most votes on it.  
                topReacted = settings['settings']['candidateprompts']
                highestNum = 0;
                authors = []
                server = self.bot.get_server(serverID)
                for candidatePrompt in settings['settings']['candidateprompts']:
                    channelObject = server.get_channel(settings['settings']["channel"])  
                    candidateMessage = await self.bot.get_message(channelObject, candidatePrompt['id'])

                    #count the number of stars on each reaction
                    for reaction in candidateMessage.reactions:
                        if(type(reaction.emoji) is str and str(ord(reaction.emoji[0])) == str(likeEmoji) and reaction.count >= highestNum):                          
                            if reaction.count > highestNum:
                                topReacted = []
                            highestNum = reaction.count
                            topReacted.append(candidatePrompt)
                    
                promptsToUse = topReacted[randint(0, len(topReacted) - 1)]               
            else:             
                if len(prompts["prompts"]) >= minPrompts:
                    #randomly choose a new prompt to set for this week's prompt
                    #ensure the chosen prompt is placed at the front of the list
                    #do not consider last week's chosen prompt for this week
                    index = randint(1, len(prompts["prompts"]) - 1)
                    promptsToUse = prompts["prompts"][index]
                    prompts["prompts"][index], prompts["prompts"][0] = prompts["prompts"][0], prompts["prompts"][index] #swap prompts
                    settings["prompt"] = promptsToUse
                    
                else:
                    promptsToUse["prompt"] = "There are not enough prompts. Please submit some!"
                    promptsToUse["author"] = self.bot.user.id
                    settings.pop("prompt", None)
     
            try:
                promptToRemove = promptsToUse
                promptToRemove.pop("id", None)
                prompts["prompts"].remove(promptToRemove)
            except Exception as e:
                print("Exception:")
                print(str(e))
       
            with open(serverIDPath + '/prompts.txt', 'w+') as promptFile:
                json.dump({'prompts': prompts["prompts"]}, promptFile, indent=4)  # rewrite prompts.txt with updated list of prompts

        #print out new prompt
        userMention = await self.bot.get_user_info(promptsToUse["author"])       
        await self.bot.send_message(self.bot.get_channel(channel), bold("This week's prompt:\n") + box(promptsToUse["prompt"]) + "Submitted by " + userMention.mention)     

        if(len(priPrompts["priprompts"]) <= 0):
            settings = {}
            with open(serverIDPath + '/settings.txt', 'r') as file:
                try:
                    settings = json.load(file)
                except ValueError:
                    print("couldn't write settings!")
                    await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from settings.txt JSON file!")
                    return True
        
            #if there are enough promtps, choose 5 canidate prompts
            print(str(len(prompts["prompts"])) + " " + str(minPrompts))
            if len(prompts["prompts"]) >= minPrompts:
                #choose 5 more prompts
                index = randint(0, len(prompts["prompts"]) - 1)
                await self.bot.send_message(self.bot.get_channel(channel), bold("This week's canidate prompts"))
            
                for i in range(1, 6):
                    canidatePrompts.append(prompts["prompts"][(index + i) % len(prompts["prompts"])])
                    message = await self.bot.send_message(self.bot.get_channel(channel), box(canidatePrompts[i-1]["prompt"]))
                    canidatePrompts[i-1]["id"] = message.id
                    
                await self.bot.send_message(self.bot.get_channel(channel), bold("Please vote for the prompt you'd like to do next week by reacting to it with a " +  str(chr(likeEmoji)) + "!"))
                #re-write settings              
                settings['settings']['candidateprompts'] = canidatePrompts;               
            else:
                #at this point, you are running out of prompts
                await self.bot.send_message(self.bot.get_channel(channel), bold("No canidate prompts for this week. Please submit some ideas for new ones."))
                settings['settings'].pop('candidateprompts', None)
            
            #set new prompt and re-write settings
            settings['settings']['prompt'] = promptsToUse
            with open(serverIDPath + '/settings.txt', 'w+') as file: 
                json.dump({'settings': settings['settings']}, file, indent=4)
        else:
            await self.bot.send_message(self.bot.get_channel(channel), "Next week's prompt has already been decided...");
            
            #re-write settings to remove canidateprompts...since there are none
            settings = {}
            with open(serverIDPath + '/settings.txt', 'r') as file:
                try:
                    settings = json.load(file)
                except ValueError:
                    print("Had trouble writing to settings!")
                    await self.bot.say("ERROR: Composeprompt: promptRestart: Could not write data to settings.txt JSON file!")
                    return True
            
            settings['settings'].pop('candidateprompts', None)
            settings['settings']['prompt'] = promptsToUse
            
            with open(serverIDPath + '/settings.txt', 'w+') as file: 
                json.dump({'settings': settings['settings']}, file, indent=4)
              
        #restart prompt timer 
        with open(dataPath + '/globalsettings.txt', 'r') as file:  
            try:
                globalSettings = json.load(file)
            except ValueError:
                await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from globalsettings.txt JSON file!")
                print("globalsettings not working")
                return True

        isInList = False     
        for x in globalSettings["globalsettings"]["promptstarttimes"]:
            if x == serverID:
                isInList = True
                break

        #record new time and start new timer
        if isInList:
            newTimeStruct = self.convertToStructTime(globalSettings["globalsettings"]["promptstarttimes"][serverID])
            globalSettings["globalsettings"]["nextpromptreset"][serverID] = [newTimeStruct.year, newTimeStruct.month, newTimeStruct.day, newTimeStruct.hour, newTimeStruct.minute]
        
            with open(dataPath + "/globalsettings.txt", "w+") as settingsFile:
                json.dump(globalSettings, settingsFile, indent=4)
        
        #remove busyfile   
        if os.path.isdir(serverIDPath + busyFile):
            shutil.rmtree(serverIDPath + busyFile)
            
        return True

def setup(bot):
    bot.add_cog(ComposePrompt(bot))