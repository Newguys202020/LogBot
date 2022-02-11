import configparser
import datetime
import os
import pickle
import re
from logging import debug
from os.path import join
from random import randint

import discord
import yfinance
from discord import message
from discord.ext import commands
from discord.utils import get
from google import auth
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from profanity_check import predict, predict_prob
import traceback

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def findMatching(List1, List2):
    for m in List1:
        for n in List2:
            if m == n:
                return n
    return None

def isDate(word, date_format):
    try:
        date_obj = datetime.datetime.strptime(word, date_format)
        pass
        return(True)
    except ValueError:
        return(False)

class tradeClass:
    def __init__ (self, message = None, sheetName = "N/A", ticker = "N/A", side = "N/A", price = "N/A", contract = "N/A", date = "N/A", closingTrade = True, author = None, values = None, service = None, spreadsheet_id = None, openRows = [], editTrade = False, matchingOldRow = None, sideFlag = False, tickerFlag = False, dateFlag = False, optionFlag = False, priceFlag = False, ready = False):
        self.message = message
        self.sheetName = sheetName
        self.ticker = ticker
        self.side = side
        self.price = price
        self.contract = contract
        self.date = date
        self.closingTrade = closingTrade
        self.author = author
        self.values = values
        self.service = service
        self.spreadsheet_id = spreadsheet_id
        self.openRows = openRows
        self.editTrade = editTrade
        self.matchingOldRow = matchingOldRow
        self.sideFlag = sideFlag
        self.tickerFlag = tickerFlag
        self.dateFlag = dateFlag
        self.optionFlag = optionFlag
        self.priceFlag = priceFlag
        self.ready = ready

    async def findTrade(self, message):
        self.message = message
        if len(message.embeds) > 0:
            content = message.embeds[0].description
        else:
            content = message.content
        content = content + " "
        content = content.replace ('*', '')
        content = content.replace('_', '')
        roles = ["@here", "@everyone", "<@&929991236742418453>", "<@&870886407583981608>", "<@&816418921355149332>", "<@&816424914239356940>", "<@&816486624502218752>", "<@&816424702137597953>", "<@&929991236742418453>", "<@&922896772148396073>", "<@&870886476244746240>"]
        for role in roles:
           content = content.replace(role, '')
        words = content.split()
        upperContent = content.upper()
        upperWords = upperContent.split()
        self.author = message.author.id
        self.author = BotCorrection(self.author)
        if self.author in whitelistDict.keys():
            self.sheetName = whitelistDict[self.author]
        buyingWords = ['BTO', 'BUY', 'BUYING', 'BOUGHT' 'PURCHASED', 'STO', 'GRABBED', 'GRABBING']
        sellingWords = ['STC', 'SELL', 'SELLING', 'SOLD', 'SCALE', 'SCALED', 'STOPPED', 'SCALING', 'BTC', 'CLOSE', 'CLOSED', 'CUT', 'CUTTING']
        if (findMatching(upperWords, sellingWords) or findMatching(upperWords, buyingWords)) and len(upperWords) != 1:
            self.sideFlag = True
            match = findMatching(upperWords, sellingWords)
            if match:
                self.side = 'STC'
                index = upperWords.index(match)
                if match == 'STOPPED' and upperWords[index + 1] == 'OUT':
                    index = index + 1
            else:
                match = findMatching(upperWords, buyingWords)
                if match:
                    self.side = 'BTO'
                    index = upperWords.index(match)
            word = words[index + 1]
            fetch = yfinance.Ticker(word).info
            if fetch['regularmarketPrice'] != None:
                    self.ticker = word.upper()
                    self.tickerFlag = True

        if not self.tickerFlag:
            finished = False
            for word in words:
                if finished == False and word.isupper() and word != 'BTO' and word != 'STC':
                    fetch = yfinance.Ticker(word).info
                    if fetch['regularmarketPrice'] != None:
                        self.ticker = word.upper()
                        self.tickerFlag = True
                        finished = True
                        
        if findMatching(upperWords, sellingWords):
            closingPhrases = ["all out", "cut", "stop loss hit", "sl hit", "stopped out"]
            openPhrases = ["scale", "scaling", "derisk", " out"]
            for phrase in openPhrases:
                scanpoint = content.lower().find(phrase)
                if scanpoint != -1:
                    self.closingTrade = False
            for phrase in closingPhrases:
                scanpoint = content.lower().find(phrase)
                if scanpoint != -1:
                    self.closingTrade = True

        match = re.search(r"(@\s*\S+)", content)
        if match:
            self.price = match[0][1:]
            try:
                float(self.price)
                self.priceFlag = True
            except:
                pass
        
        match = re.search(r'(\d+\.?(\d+)?(\s+)?(C|CALL)){1}', content.upper())
        if match:
            self.contract = match[0].replace(' ', '')
            self.contract = self.contract.replace('CALL', 'C')
            self.optionFlag = True
        else:
            match = re.search(r'(\d+\.?(\d+)?(\s+)?(P|PUT)){1}', content.upper())
            if match:
                self.contract = match[0].replace(' ', '')
                self.contract = self.contract.replace('PUT', 'P')
                self.optionFlag = True
        short = False
        finished = False
        for word in upperWords:
            if finished == False:
                dateObj = 0
                if isDate(word,'%m/%d/%y'):
                    dateObj = datetime.datetime.strptime(word, '%m/%d/%y')
                elif isDate(word,'%m/%d/%Y'):
                    dateObj = datetime.datetime.strptime(word, '%m/%d/%Y')
                elif isDate(word,'%m/%d'):
                    dateObj = datetime.datetime.strptime(word, '%m/%d')
                    short = True
                    dateObj = datetime.datetime.replace(dateObj, year = datetime.date.today().year)
                if dateObj != 0:
                    try:
                        if dateObj.strftime("%Y-%m-%d") in yfinance.Ticker(self.ticker).options:
                            if short:
                                self.date = dateObj.strftime('%#m/%#d')
                            else:
                                self.date = dateObj.strftime('%#m/%#d/%y')
                            finished = True
                            self.dateFlag = True
                    except:
                        pass
        if self.optionFlag and self.priceFlag and self.sideFlag and self.tickerFlag and self.dateFlag:
            self.ready = True

    async def updateSheet(self):
        success = False
        try:
            matchingTrade = False
            trade = None
            for row in self.openRows:
                if self.ticker == self.values[row][0] and self.date + " " + self.contract == self.values[row][1]:
                    self.matchingTrade = True
                    self.matchingRow = row
            if self.side == 'BTO':
                if self.editTrade:
                    trade = [[self.ticker, (self.date + " " + self.strike + self.contract), datetime.date.today().strftime("%m/%d/%y"), None, ("$" + self.price)]]
                    rowToUpdate = self.matchingOldRow + 1
                else:
                    if matchingTrade == True:
                        if self.values[self.matchingRow][4][0] == '-':
                            newPrice = str(round(float((-float(self.values[self.matchingRow][4][2:]) + (float(self.price) / 2))),2))
                        else:
                            newPrice = str(round(float((float(self.values[self.matchingRow][4][1:]) + (float(self.price) / 2))),2))
                        while len(self.values[self.matchingRow]) < 13:
                            self.values[self.matchingRow].append("")
                        if self.values[self.matchingRow][12] != "":
                            message = (self.values[self.matchingRow][12] + ", Avg @" + self.price + " to $" + newPrice + " from " + self.values[self.matchingRow][4])
                        else:
                            message = ("Avg down @" + self.price + " to $" + newPrice +  " from " + self.values[self.matchingRow][4])
                        trade = [[self.ticker, (self.date + " " + self.contract), None, None, ("$" + newPrice), None, None, None, None, None, None, None, message]]
                        rowToUpdate = self.matchingRow + 1
                    else:
                        trade = [[self.ticker, (self.date + " " + self.contract), datetime.date.today().strftime("%m/%d/%y"), None, ("$" + self.price)]]
                        rowToUpdate = len(self.values) + 1
                range_name = (self.sheetName + 'A' + str(rowToUpdate) + ':' + 'M' + str(rowToUpdate))
                body = {'values': trade}
                result = self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id, range=range_name, body=body, valueInputOption='USER_ENTERED').execute()
                print(result)
                success = True
            elif self.side == 'STC':
                if not(matchingTrade or self.editTrade):
                    for row in self.values:
                        if len(row) > 2:
                            if (self.ticker == row[0]) and ((self.date + " " + self.contract) == row[1]):
                                matchingTrade = True
                                matchingRow = self.values.index(row)
                if self.editTrade:
                    matchingRow = self.matchingOldRow
                    matchingTrade = True
                if matchingTrade:
                    secondExit = False
                    if self.values[matchingRow][5] != None and self.values[matchingRow][5] != "":
                        secondExit = True
                    if self.editTrade or matchingTrade:    
                        rowToUpdate = matchingRow + 1
                        oldPrice = 0
                        if self.values[matchingRow][6] != None and self.values[matchingRow][6] != "":
                            oldPrice = float(re.sub('[^0-9]', '', (self.values[matchingRow][6])))
                        if self.closingTrade == False:
                            while len(self.values[matchingRow]) < 13:
                                self.values[matchingRow].append("")
                            if self.values[matchingRow][12] != "":
                                message = (self.values[matchingRow][12] + ", Scale @" + self.price)
                            else:
                                message = ("Scale @" + self.price)
                            if not secondExit:
                                trade = [[self.ticker, (self.date + " " + self.contract), None, None, None, ("$" + self.price), ("$" + self.price), None, None, None, None, None, message]]
                        elif not secondExit:
                            trade = [[self.ticker, (self.date + " " + self.contract), None, datetime.date.today().strftime("%m/%d/%y"), None, ("$" + self.price), ("$" + self.price)]]
                        elif float(self.price) > float(oldPrice):
                            trade = [[self.ticker, (self.date + " " + self.contract), None, datetime.date.today().strftime("%m/%d/%y"), None, None, ("$" + self.price)]]
                        range_name = (self.sheetName + 'A' + str(rowToUpdate) + ':' + 'M' + str(rowToUpdate))
                        body = {'values': trade}
                        result = self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id, range=range_name, body=body, valueInputOption='USER_ENTERED').execute()
                        print(result)
                        success = True
            if success == False:
                pass
        except Exception as e:
            traceback.print_exc()
            await debugChannel.send(str(e))
        return success

    async def fetchSheet(self):
        if self.sheetName != "N/A":
            self.spreadsheet_id='1zShOCSTX8apDiIG9Ahu_NcpP_VDIvp76MPO0jyxNyRY'
            creds = None
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
                # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        r"C:\Users\cnewm\Google Drive\Projects\Discord Bot\credentials.json", SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            self.service = build('sheets', 'v4', credentials=creds)

            sheet = self.service.spreadsheets()

            sheetRange = self.sheetName + 'A1:M1000'

            #Get values from sheet
            result = sheet.values().get(spreadsheetId=self.spreadsheet_id, range=sheetRange).execute()
            self.values = result.get('values', [])

            #Get rows of currently open trades
            self.openRows = []
            i = 0
            for row in self.values:
                if len(row) > 11:
                        if row[11] == 'OPEN':
                            self.openRows.append(i)
                i = i + 1

    async def verifyTrade(self, preferences):
        missing = 0
        send = False
        sendError = False
        side = "__Side__"
        ticker = "__Ticker__"
        price = "__Price__"
        date = "__Date__"
        contract = "__Contract__"
        editedSide = self.side
        editedTicker = self.ticker
        editedPrice = self.price
        editedDate = self.date
        editedContract = self.contract
        author = await bot.fetch_user(int(self.author))
        for item in [editedSide, editedTicker, editedPrice, editedDate, editedContract]:
            if item is None:
                item = '-'
        for flag in [self.tickerFlag, self.sideFlag, self.priceFlag, self.dateFlag, self.optionFlag]:
            if flag == False:
                missing += 1
        if preferences['enableErrorCheck'] == 'True' and missing > 0 and missing <= int(preferences['numMissingParts']):
            if self.sideFlag == False:
                try:
                    for row in self.openRows:
                        if (self.ticker == self.values[row][0]) and ((self.date + " " + self.strike + self.contract) == self.values[row][1]):
                            self.side = 'STC'
                        else:
                            self.side = 'BTO'
                        editedSide = "**" + self.side + "**"
                        side = "__**Side**__"
                        self.sideFlag = True
                except:
                    pass
            if self.tickerFlag == False and preferences['checkMissingTicker'] == 'True':
                try:
                    self.ticker == self.values[self.openRows[-1][0]]
                    editedTicker ==  "**" + self.ticker + "**"
                    ticker = "__**Ticker**__"
                    self.tickerFlag = True
                except:
                    pass
            if self.dateFlag == False and preferences['checkMissingDate'] == 'True' and self.tickerFlag == True:
                try:
                    date = (yfinance.Ticker(self.ticker)).options[0]
                    dateObj = datetime.datetime.strptime(date, '%Y-%m-%d')
                    self.date = dateObj.strftime('%#m/%#d')
                    editedDate = "**" + self.date + "**"
                    date = "__**Date**__"
                    self.dateFlag = True
                except:
                    pass
            if self.optionFlag == False and preferences['checkMissingContract'] == 'True' and self.tickerFlag == True and self.side == 'STC':
                found = False
                if self.values is not None:
                    for row in reversed(self.values):
                        if len(row) > 1:
                            if row[0] == self.ticker:
                                match = re.search(r'(\d+\.?(\d+)?(\s+)?(P|C))', row[1])
                                if match:
                                    self.contract = match[0]
                                    found = True
                                    break
                if found:
                    editedContract = "**" + self.contract + "**"
                    contract = "__**Contract**__"
                    self.optionFlag = True
            embed=discord.Embed(title="Trade Verification", description="<@" + str(author.id) + ">, Trade partially detected. See trade with **suggested revisions** and press ✅ to accept or ❌ to reject.", color=0xfff700)
            embed.set_author(name="AutoLog")
            embed.add_field(name=side, value=editedSide, inline=True)
            embed.add_field(name=ticker, value=editedTicker, inline=True)
            embed.add_field(name=date, value=editedDate, inline=True)
            embed.add_field(name=contract, value=editedContract, inline=True)
            embed.add_field(name=price, value=editedPrice, inline=True)
            embed.set_footer(text="To change your preferences, message me \"SetPreferences\"")
            missing = 0
            for flag in [self.tickerFlag, self.sideFlag, self.priceFlag, self.dateFlag, self.optionFlag]:
                if flag == False:
                    missing += 1
            if missing == 0:
                send = True
            else:
                sendError = True
        elif missing == 0 and preferences['confirmAllTrades'] == 'True':
            embed=discord.Embed(title="Trade Verification", description= "<@" + str(author.id) + ">, Trade detected, confirm to log", color=0x003f00)
            embed.set_author(name="AutoLog")
            embed.add_field(name=side, value=editedSide, inline=True)
            embed.add_field(name=ticker, value=editedTicker, inline=True)
            embed.add_field(name=date, value=editedDate, inline=True)
            embed.add_field(name=contract, value=editedContract, inline=True)
            embed.add_field(name=price, value=editedPrice, inline=True)
            embed.set_footer(text="To change your preferences, message me \"SetPreferences\"")
            send = True
            self.ready = False
        if send:
            message = await author.send("<@" + str(author.id) + ">", embed = embed)
            await message.add_reaction('✅')
            await message.add_reaction('❌')
            def check(payload):
                if str(payload.emoji) == '✅':
                    self.ready = True
                return payload.user_id == self.author and (str(payload.emoji) == '✅' or str(payload.emoji) == '❌')
            try:
                await bot.wait_for('raw_reaction_add', check = check, timeout = 28800)
                if self.ready:
                    embed.title = "**__TRADE ACCEPTED__**"
                    embed.color = 0x00ff00
                else:
                    embed.title = '**__TRADE REJECTED__**'
                    embed.color = 0xff0000
                await message.edit(embed=embed)
            except:
                embed.color = 0xff0000
                embed.title = "__**TIMED OUT**__"
                await message.edit(embed = embed)
        elif sendError:
            embed.title = "Information still missing from trade after attempted corrections, see items detected below and send me a new message to correct"
            await author.send(embed = embed)          
        
bot = commands.Bot(command_prefix = '')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

@bot.command()
async def SetPreferences(ctx, *args):
    global config
    preferencesList = ['confirmAllTrades', 'enableErrorCheck', 'numMissingParts', 'checkMissingSide', 'checkMissingTicker', 'checkMissingDate', 'checkMissingContract', 'checkMissingPrice']
    config.read('userpreferences.ini')
    author = ctx.message.author.id
    author = BotCorrection(author)
    if str(author) not in config.sections():
        config[str(author)] = config['DEFAULT']
        with open('userpreferences.ini', 'w') as configfile:
            config.write(configfile)
    preferences = config[str(author)]
    for preference in args:
        try:
            preference = preference.split('=')
            if preference[0] in preferencesList:
                config[str(author)][preference[0]] = preference[1]
        except:
            pass
    with open('userpreferences.ini', 'w') as configfile:
            config.write(configfile)
    embed=discord.Embed(title="Settings", description="To change your preferences, send me \"SetPreferences(*new values*)\".")
    embed.add_field(name="**__confirmAllTrades__**", value=preferences['confirmAllTrades'], inline=True)
    embed.add_field(name="**__enableErrorCheck__**", value=preferences['enableErrorCheck'], inline=True)
    embed.add_field(name="**__numMissingParts__**", value=preferences['numMissingParts'], inline=True)
    embed.add_field(name="**__checkMissingSide__**", value=preferences['checkMissingSide'], inline=True)
    embed.add_field(name="**__checkMissingTicker__**", value=preferences['checkMissingTicker'], inline=True)
    embed.add_field(name="**__checkMissingDate__**", value=preferences['checkMissingDate'], inline=True)
    embed.add_field(name="**__checkMissingContract__**", value=preferences['checkMissingContract'], inline=True)
    embed.add_field(name="**__checkMissingPrice__**", value=preferences['checkMissingPrice'], inline=True)
    embed.set_footer(text="Example: 'SetPreferences confirmAllTrades=False numMissingParts=1 checkMissingDate=False'")
    await ctx.send(embed=embed)

def BotCorrection(author):
    if author == 835617988869881866: #KM
        author = 197193645638549504
    elif author == 923694445445128202: #Doom
        author = 705472252233253001
    elif author == 930115963058282537: #Viral
        author = 708793806446657629
    elif author == 924421976452370462: #Bean
        author = 275082982249988116
    return author

@bot.command()
async def MonthlyReport(ctx, date):
    if ctx.message.author.id in whitelistDict.keys():
        if isDate(date, '%m/%y'):
            dateObj = datetime.datetime.strptime(date, '%m/%y')
            await ctx.send("Generating monthly report for month " + dateObj.strftime('%#m/%#y'))
            spreadsheet_id = '1zShOCSTX8apDiIG9Ahu_NcpP_VDIvp76MPO0jyxNyRY'
            monthlyID = '1_F15ihDAHvwjOaU3v6wjJo5DVi9UDvuorymyTH9Ttao'
            creds = None
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        r"C:\Users\cnewm\Google Drive\Projects\Discord Bot\credentials.json", SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            cleared = []
            for sheetName in list(whitelistDict.values()):
                if sheetName not in cleared:
                    sheetRange = sheetName + 'A2:M1000'
                    clear_values_request_body = {
                    }
                    request = service.spreadsheets().values().clear(spreadsheetId=monthlyID, range=sheetRange, body=clear_values_request_body)
                    response = request.execute()
                    print(response)
                    sheetRange = sheetName + 'A2:M1000'
                    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=sheetRange).execute()
                    values = result.get('values', [])
                    closedRowNumbers = []
                    closedRows = []
                    i = 0
                    for row in values:
                        if len(row) > 11:
                            if (row[11] == 'CLOSED'):
                                try:
                                    print(row)
                                    date = datetime.datetime.strptime(row[3], '%m/%d/%Y')
                                    if date.strftime('%#m/%#y') == dateObj.strftime('%#m/%#y'):
                                        closedRowNumbers.append(i)
                                except:
                                    await debugChannel.send(myid + " Check " + str(sheetName) + " Row " + str(row))
                        i = i+1     
                    for number in closedRowNumbers:
                        closedRows.append(values[number])
                    sheetRange = sheetName + 'A2:M1000' + str(len(closedRows)+2)
                    data = [
                        {
                            'range': sheetRange,
                            'values': closedRows
                        }
                    ]
                    body = {
                        'valueInputOption': 'USER_ENTERED',
                        'data': data
                    }
                    result = service.spreadsheets().values().batchUpdate(spreadsheetId=monthlyID, body=body).execute()
                    print(result)
                    cleared.append(sheetName)
            sheetName = 'Summary!'
            sheetRange = sheetName + 'Q2:Q3000'
            clear_values_request_body = {
                }
            request = service.spreadsheets().values().clear(spreadsheetId=monthlyID, range=sheetRange, body=clear_values_request_body)
            response = request.execute()
            print(response)
            sheetRange = sheetName + 'B2:I1000'
            result = sheet.values().get(spreadsheetId=monthlyID, range=sheetRange).execute()
            values = result.get('values', [])
            sums = []
            runningSum = 0
            currentRow=0
            for row in values:
                print(row)
                column = 0
                while column < len(row):
                    if row[column] != '' and row[column] != None:
                        try:
                            if currentRow == 0:
                                runningSum = runningSum + float(row[column][:-1])
                            else:
                                runningSum = runningSum + float(row[column][:-1])-float(values[currentRow-1][column][:-1])
                            runningSumFormatted = []
                            runningSumFormatted.append(str(runningSum) + '%')
                            sums.append(runningSumFormatted)
                        except Exception as exception:
                            print(exception)
                    column = column+1
                currentRow=currentRow+1
            sheetRange = sheetName + 'Q2:Q3000'
            data = [
                    {
                        'range': sheetRange,
                        'values': sums
                    }
                ]
            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': data
            }
            result = service.spreadsheets().values().batchUpdate(spreadsheetId=monthlyID, body=body).execute()
            await ctx.send('DONE! View at: https://docs.google.com/spreadsheets/d/1_F15ihDAHvwjOaU3v6wjJo5DVi9UDvuorymyTH9Ttao/edit?usp=sharing')

@bot.command()
async def UpdateLog(ctx):
    if ctx.message.author.id in whitelistDict.keys():
        spreadsheet_id = '1zShOCSTX8apDiIG9Ahu_NcpP_VDIvp76MPO0jyxNyRY'
        tradeLog = '1MkriX2GSB0SgzeoMQ5h-SiFqfIsT3jByj_ng97II028'
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    r"C:\Users\cnewm\Google Drive\Projects\Discord Bot\credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        cleared = []
        for sheetName in whitelistDict.values():
            if sheetName not in cleared:
                sheetRange = sheetName + 'A2:M1000'
                clear_values_request_body = {
                }
                request = service.spreadsheets().values().clear(spreadsheetId=tradeLog, range=sheetRange, body=clear_values_request_body)
                response = request.execute()
                print(response)
                sheetRange = sheetName + 'A2:M1000'
                result = sheet.values().get(spreadsheetId=spreadsheet_id, range=sheetRange).execute()
                values = result.get('values', [])
                closedRowNumbers = []
                closedRows = []
                i = 0
                for row in values:
                    if len(row) > 11:
                        if (row[11] == 'CLOSED'):
                            try:
                                closedRowNumbers.append(i)
                            except:
                                await debugChannel.send(myid + " Check " + str(sheetName) + " Row " + str(row))
                    i = i+1     
                for number in closedRowNumbers:
                    closedRows.append(values[number])
                sheetRange = sheetName + 'A2:M1000' + str(len(closedRows)+2)
                data = [
                    {
                        'range': sheetRange,
                        'values': closedRows
                    }
                ]
                body = {
                    'valueInputOption': 'USER_ENTERED',
                    'data': data
                }
                result = service.spreadsheets().values().batchUpdate(spreadsheetId=tradeLog, body=body).execute()
                print(result)
                cleared.append(sheetName)
        sheetName = 'Summary!'
        sheetRange = sheetName + 'Q2:Q3000'
        clear_values_request_body = {
            }
        request = service.spreadsheets().values().clear(spreadsheetId=tradeLog, range=sheetRange, body=clear_values_request_body)
        response = request.execute()
        print(response)
        sheetRange = sheetName + 'B2:I1000'
        result = sheet.values().get(spreadsheetId=tradeLog, range=sheetRange).execute()
        values = result.get('values', [])
        sums = []
        runningSum = 0
        currentRow=0
        for row in values:
            print(row)
            column = 0
            while column < len(row):
                if row[column] != '' and row[column] != None:
                    try:
                        if currentRow == 0:
                            runningSum = runningSum + float(row[column][:-1])
                        else:
                            runningSum = runningSum + float(row[column][:-1])-float(values[currentRow-1][column][:-1])
                        runningSumFormatted = []
                        runningSumFormatted.append(str(runningSum) + '%')
                        sums.append(runningSumFormatted)
                    except Exception as exception:
                        print(exception)
                column = column+1
            currentRow=currentRow+1
        sheetRange = sheetName + 'Q2:Q3000'
        data = [
                {
                    'range': sheetRange,
                    'values': sums
                }
            ]
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }
        result = service.spreadsheets().values().batchUpdate(spreadsheetId=tradeLog, body=body).execute()
        await ctx.send('DONE! View at: https://docs.google.com/spreadsheets/d/1MkriX2GSB0SgzeoMQ5h-SiFqfIsT3jByj_ng97II028/edit?usp=sharing')


@bot.event
async def on_ready():
    global debugChannel
    global myid
    global whitelistDict
    global whitelistChannels
    global guildID
    global guild
    global preferences
    global config
    config = configparser.ConfigParser()
    config.read('userpreferences.ini')
    guildID = 926092726225752135
    guild = await bot.fetch_guild(guildID)
    await bot.change_presence(activity=discord.Game('*Not Financial Advice*'))
    debugChannel = bot.get_channel(id = 926143170897666049)
    print("Debug Channel = " + debugChannel.name)
    whitelistChannels = [905573115495596053, 905573227902943243, 905573189583777803, 816405843141853214, 920181354979786762, 926143170897666049]
    whitelistDict = {
        708793806446657629 : "Viral!",
        275082982249988116 : "Bean!",
        197193645638549504 : "KM!",
        835617988869881866 : "KM!",
        705472252233253001 : "Doom!",
        923694445445128202 : "Doom!",
        225032550647726081 : "Newman!"
    }
    
    myid = '<@225032550647726081>'
    await debugChannel.send("%s Connected to server as %s" % (myid, bot.user.name))

@bot.event
async def on_message(message):
    global whitelistChannels
    author = message.author.id
    author = BotCorrection(author)
    if author != 807517564535701504:
        if isinstance(message.channel, discord.channel.DMChannel) or message.channel.id in whitelistChannels:
            trade = tradeClass()
            await trade.findTrade(message)
            global config
            config.read('userpreferences.ini')
            if str(author) not in config.sections():
                config[str(author)] = config['DEFAULT']
                with open('userpreferences.ini', 'w') as configfile:
                    config.write(configfile)
            await trade.fetchSheet()
            await trade.verifyTrade(config[str(author)])
            if trade.ready:
                success = await trade.updateSheet()
                if success:
                    print("Logged Trade")
                    await debugChannel.send("Logged Trade: %s, %s, %s, %s, %s" % (trade.side, trade.ticker, trade.contract, trade.date, trade.price))
                else:
                    print("ERROR LOGGING TRADE")
                    await debugChannel.send("%s Trade found but could not be logged %s, %s, %s, %s, %s, %s" % (myid, str(whitelistDict[author]),trade.side, trade.ticker, trade.contract, trade.date, trade.price))
        if "807517564535701504>" in message.content:
            authorid = "<@" + str(author) + ">"
            if author in whitelistDict.keys() and predict([message.content]) > 0.5:
                reactions = ["My nuts, your mouth. Do the math.", "If only I gave a fuck", "Did anyone ask you?", "Tendie losing bitch", "Shut the fuck up", "No one gives a shit", "Oh yeah fucker? I'll crush your windpipe", "Can't we just be friends?", "Suck my robotic cock", "No.", "Try reading through all your shit every day then come talk to me", "I'll break both your kneecaps, try me asshole", "Say that again, I dare you", "The fuck do you want?", "You rang, asshole?", "I don't give a shit", "I'm not your fucking butler", "I don't have time for this shit"]
                randReaction = randint(0,len(reactions)-1)
                await message.channel.send(authorid + " " + reactions[randReaction])
            elif "?" in message.content:
                reactions = ["When in doubt, buy TSLA", "As I see it, yes", "Yes", "No", "It's very likely", "No chance", "Maybe", "It's very unlikely", "YOLO", "Stonks only go up", "Better not tell you now", "Don't count on it", " It is certain", "My sources say no"]
                randReaction = randint(0,len(reactions)-1)
                await message.channel.send(authorid + " " + reactions[randReaction])
            else:
                await message.channel.send(authorid + " You Called?")
        else:
            await bot.process_commands(message)

if __name__ == '__main__':
    bot.run('token')
