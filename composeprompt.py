#Composeprompt.py, a cog to allow for the automation of weekly composition prompts
# Written by Tyler Reich and Vincent Bryant

import asyncio
import discord
from discord.ext import commands
import os
from os import path
from os import makedirs
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

#default values for JSON files
global newPromptsList
newPromptsList = {'prompts': []}
global newPriPromptsList
newPriPromptsList = {'priprompts': []}
global newSettingsList
newSettingsList = {'settings': {'promptrun': True, 'channel': '-1'}}
global newGlobalSettingsList
newGlobalSettingsList = {'globalsettings': {'promptstarttimes': {}}}
global newEntriesList
newEntriesList = {'entries': []}
global newDomainWhitelist
newDomainWhitelist = {'whitelist': []}

class ComposePrompt:

    currentTimers = {}

    def __init__(self, bot):
        self.bot = bot

        #if dir for JSON files does not exist, make it
        if not os.path.exists(dataPath):
            os.makedirs(dataPath)
        
        if not os.path.exists(dataPath + '/globalsettings.txt'):
            with open(dataPath + '/globalsettings.txt', 'w+') as file:
                json.dump(newGlobalSettingsList, file, indent=4)
                
        #FIXME: load timer from globalsettings.txt

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
        globalSettings["globalsettings"]["promptstarttimes"][serverID] = newTime
            
        with open(dataPath + "/globalsettings.txt", "w+") as settingsFile:
            json.dump(globalSettings, settingsFile, indent=4)
        
        schedulerTime = int(self.convertToSchedulerTime(newTime))
        threading.Timer(schedulerTime, self.runAsync, [ctx.message.server.id,]).start()
        await self.bot.say("Prompt reset time set to " + newTime)
        
        #FIXME: cancel previously loaded events for this server, so that the server doesn't have two prompt reset times
        
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
        
        if len(entriesList) == 0:
            await self.bot.send_message(ctx.message.author, content="No entries yet! Get working!", tts=False, embed=None)
            return
        
        await self.bot.send_message(ctx.message.author, content=bold("List of entries:"), tts=False, embed=None)
        
        for entry in entriesList:
            userObject = await self.bot.get_user_info(entry['author'])
            messageText = userObject.name +":\n" + entry['entry']
            await self.bot.send_message(ctx.message.author, content=messageText, tts=False, embed=None)

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
                    print("ERROR: Composeprompt: prompton Could not get values from JSON.")
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

        await self.bot.say("adddomain function works! (I think.)")

    @checks.admin()
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
      
    #test function for testing the scheduler library
    async def testfunction(self, args : str):
        print("Test function called, it said ", str(args))
        
    #turn human readable time into a time readable by the timer
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
        
        if (dayOfWeek == nowTime.weekday()) and (hour > nowTime.hour or (hour == nowTime.hour and minute > nowTime.minute)):
            print("should be set for today!")
        else:
            #print("days should have been increased")
            endTime = endTime + timedelta(days = 7)
        
        #get difference between now and when the prompt switches
        secondsResult = (endTime - nowTime).total_seconds()
        
        #returns seconds left until reset time
        return secondsResult
   
    @checks.admin()
    @commands.command(pass_context=True, no_pm=True)
    async def testCommand(self, ctx):
        asyncio.run_coroutine_threadsafe(self.promptRestart(ctx.message.server.id), self.bot.loop)
   
    # hopefully we can get rid of this middleman function
    def runAsync(self, serverID):
        asyncio.run_coroutine_threadsafe(self.promptRestart(serverID), self.bot.loop)
        print("done with runAsync")
    
    
    #print out existing entries (if they exist) and 
    async def promptRestart(self, serverID):       
        serverIDPath = dataPath + "/" + serverID
        channel = -1
        prompts = []
        priPrompts = []
        promptToUse = {}
        newPrompt = {}
        
        #get settings information from JSON file
        with open(serverIDPath + '/settings.txt', 'r') as file:
            try:
                settings = json.load(file)
                settings = settings['settings']
            except ValueError:
                await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from globalsettings.txt JSON file!")
                return
       
        #check to see if composeprompt is supposed to be running in this server
        if "promptrun" in settings:
            if settings["promptrun"] is False:
                return
        else:
            return         
       
        #get which channel composeprompt should run in for this server
        if "channel" in settings:
            channel = settings["channel"]
        else:
            channel = self.bot.get_server(serverID)
            await self.bot.send_message(channel, 'Error. Bot does not have channel to run in. Using default channel')    
        
        with open(serverIDPath + '/entries.txt', 'r') as file:    
            try:
                entries = json.load(file)
            except ValueError:
                await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from prompts.txt JSON file!")
                return
        
        #get if there was a prompt for the previous week. If so, show it.
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
                
            #FIXME delete entries
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
                return
        
        #see if priority list is empty. If it has stuff in it, use that first. Else, use regular prompts
        if len(priPrompts["priprompts"]) > 0:
            promptToUse = priPrompts["priprompts"][0]
            priPrompts["priprompts"].pop(0)

            with open(serverIDPath + '/priorityprompts.txt', 'w+') as file:
                json.dump({"priprompts": priPrompts["priprompts"]}, file, indent=4)
              
        else:
            #get new prompt from regular prompts
            with open(serverIDPath + '/prompts.txt', 'r') as file:    
                try:
                    prompts = json.load(file)
                except ValueError:
                    await self.bot.say("ERROR: Composeprompt: promptRestart: Could not get data from prompts.txt JSON file!")
                    return
            
            #randomly choose a new prompt to set for this week's prompt
            index = randint(0, len(prompts["prompts"]) - 1)
            promptToUse = prompts["prompts"][index]
            settings["prompt"] = promptToUse
            
            with open(serverIDPath + '/settings.txt', 'w+') as file: 
                json.dump({'settings': settings}, file, indent=4)
        
        #print out new prompt
        userMention = await self.bot.get_user_info(promptToUse["author"])       
        await self.bot.send_message(self.bot.get_channel(channel), bold("This week's prompt:\n") + box(promptToUse["prompt"]) + "Submitted by " + userMention.mention)
        
        
    
def setup(bot):
    bot.add_cog(ComposePrompt(bot))