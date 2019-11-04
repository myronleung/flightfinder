import json
import csv
from datetime import datetime, timedelta
from skyscanner import SkyScanner

class FlightFinder:

    def __init__(self, sk=SkyScanner(tripParamsFileName='tripParams.json'), verboseLogs=True):
        # Create params
        self.skyscanner = sk
        self.skyscanner.setPV(verboseLogs)
        self.verboseLogs = verboseLogs
        self.testSessionApi = True
        self.testPollApi = True
        
        self.legs = [] # From city group to city group
        self.legOptions = [] # From city to city
        self.routes = [] #Array of city groups
        self.priceOptions = []
        self.cityGroups = self.skyscanner.tripParams['cityGroups']
        self.pv('FlighFinder initiated successfully')

    def generateLegs(self):
        self.pv('Generating legs...')
        legCenters = []
        # Generate legs based off of routes
        for r, route in enumerate(self.routes):
            for g, group in enumerate(route):
                marginCenter = ''
                
                # check to see if last segment and has inbound date
                if g+1 >= len(route):
                    break
                
                # Check if next group only has inbound date
                # NHI: Next Has Inbound
                if self.cityGroups[g+1]['inboundDate'] != '' and self.cityGroups[g+1]['outboundDate'] == '':
                    # back out one day, use as outbound date
                    marginCenter = datetime.strptime(self.cityGroups[g+1]['inboundDate'], '%Y-%m-%d') - timedelta(days=1)
                    # convert marginCenter back to string
                    marginCenter = datetime.strftime(marginCenter,'%Y-%m-%d')
                    legCenters.append({
                        'dateDeterminationType':'NHI',
                        'marginCenter':marginCenter,
                        'from':route[g],
                        'to':route[g+1],
                    })
                # Check if current group has outbound date
                # Current Has Outbound
                elif self.cityGroups[g]['outboundDate'] != '':
                    marginCenter = self.cityGroups[g]['outboundDate']
                    legCenters.append({
                        'dateDeterminationType':'CHO',
                        'marginCenter':marginCenter,
                        'from':route[g],
                        'to':route[g+1],
                    })
                # otherwise current group is based on length of stay
                # LOS: Length of Stay
                else:
                    # Get previous leg marginCenter
                    prevMarginCenter = legCenters[g-1]['marginCenter']
                    # convert to datetime
                    prevMarginCenter = datetime.strptime(prevMarginCenter, '%Y-%m-%d')
                    # add lengthOfStay
                    marginCenter = prevMarginCenter + timedelta(days=self.cityGroups[g]['lengthOfStay'])
                    # convert back to string
                    marginCenter = datetime.strftime(marginCenter,'%Y-%m-%d')
                    legCenters.append({
                        'dateDeterminationType':'LOS',
                        'marginCenter':marginCenter,
                        'from':route[g],
                        'to':route[g+1],
                    })

        self.createLog('./logs/legCenters_log.csv',legCenters)

        # Loop through leg options to add margins
        for lc, legCenter in enumerate(legCenters):
            groupIndex = legCenter['from']
            groupMargin = self.cityGroups[groupIndex]['lengthOfStayMargin']
            marginStart = datetime.strptime(legCenter['marginCenter'],'%Y-%m-%d')-timedelta(days=groupMargin)
            # Check against NHI margin instead of outbound margin if NHI
            if legCenter['dateDeterminationType'] == 'NHI':
                groupIndex = legCenter['to']
                groupMargin = self.cityGroups[groupIndex]['lengthOfStayMargin']
                marginStart = datetime.strptime(legCenter['marginCenter'],'%Y-%m-%d')-timedelta(days=groupMargin)

            for m in range(groupMargin*2+1):
                marginStart = marginStart + timedelta(1)
                fromDate = datetime.strftime(marginStart,'%Y-%m-%d')
                self.legs.append({
                    'from':legCenter['from'],
                    'to':legCenter['to'],
                    'fromDate':fromDate,
                    'toDate':''
                })
        
        self.createLog('./logs/legs_log.csv',self.legs)

    def getLegPriceOptionsSessions(self):
        self.pv('Getting price options...')
        legOptionHeaders = [{
            'fromGroupName':"",
            'fromId':"",
            'fromName':"",
            'fromDate':"",
            'toGroupName':"",
            'toId':"",
            'toName':"",
            'toDate':"",
            'session':""
        }]
        self.createLogHeaders('./logs/legOptions_log.csv',legOptionHeaders)
        for l, leg in enumerate(self.legs):
            # get prices for each city group combination
            for lof, legOptionFrom in enumerate(self.cityGroups[leg['from']]['cities']):
                for lot, legOptionTo in enumerate(self.cityGroups[leg['to']]['cities']):
                    print('getting prices for', legOptionFrom,'to',legOptionTo)
                    # Get Sessions
                    session = self.skyscanner.getSession(legOptionFrom,legOptionTo,leg['fromDate'],leg['toDate'],self.testSessionApi)
                    # add option sessions
                    priceOptionSession = {
                        'fromGroupName':self.cityGroups[leg['from']]['groupLabel'],
                        'fromId':lof,
                        'fromName':legOptionFrom,
                        'fromDate':leg['fromDate'],
                        'toGroupName':self.cityGroups[leg['to']]['groupLabel'],
                        'toId':lot,
                        'toName':legOptionTo,
                        'toDate':leg['toDate'],
                        'session':session
                    }
                    self.legOptions.append(priceOptionSession)
                    self.writeLogRow('./logs/legOptions_log.csv', [priceOptionSession])

                    
        # write leg option log
        # self.createLog('./logs/legOptions_log.csv',self.legOptions)

    def getPriceOptions(self, overrideSessionKey = ''):
        self.skyscanner.printOutputFileHeaders()
        if overrideSessionKey == '':
            for lo, legOption in enumerate(self.legOptions):
                print('polling:',legOption['session']['body'])
                option = self.skyscanner.getPolls(legOption['session']['body'],self.testPollApi)
                # print('option:',option)
                self.skyscanner.setOutputFileName(legOption['fromGroupName']+'-'+legOption['toGroupName']+'.csv')
                self.skyscanner.printPolls(option['body'])
                self.priceOptions.append(option['body'])
        else:
            option = self.skyscanner.getPolls(overrideSessionKey,self.testPollApi)
            self.skyscanner.printPolls(option['body'])

        # write price options to file
        # self.createLog('./logs/priceOptions_log.csv',self.priceOptions)

        with open('./logs/done.csv', mode='w', newline='') as logCsv:
            logWriter = csv.writer(logCsv, delimiter=',')
            now = datetime. now()
            logWriter.writerow(['run completed',now])


    def generateRoutes(self):
        self.pv('Generating routes...')
        self.generateNextRoute([], 0)

        # write route combination log
        if self.verboseLogs:
            with open('./logs/recursion_log.csv', mode='w', newline='') as logCsv:
                logWriter = csv.writer(logCsv, delimiter=',')
                for r, route in enumerate(self.routes):
                    row = []
                    for g, group in enumerate(route):
                        row.append(str(g)+': '+self.cityGroups[g]['groupLabel'])
                    logWriter.writerow(row)
        
    def generateNextRoute(self, cp, index):

        for g, group in enumerate(self.cityGroups):
            
            # Create a branch representing where on the path we are
            currentPath = cp.copy()
            # Create a test route and determine if it has all city groups
            route = cp.copy()
            if self.notInCurrentPath(g, currentPath) and (group['orderFlexible'] == 1 or (group['orderFlexible'] == 0 and index == g)):
                route.append(g)
                # Append to routes if last layer
                if len(self.cityGroups) - 1 == index and len(route) == len(self.cityGroups):
                    self.routes.append(route)
                    return
                else:
                    currentPath.append(g)

            # proceed to next layer if not already on the last layer
            if len(self.cityGroups) - 1 > index:
                self.generateNextRoute(currentPath, index + 1)


    def testSkyScanner(self):
        sessionOutput = self.skyscanner.getSession('LAX','PEK')
        self.pv(sessionOutput)

        pollsOutput = self.skyscanner.getPolls(sessionOutput['body'])
        # self.pv(pollsOutput)

        self.skyscanner.printPolls(pollsOutput['body']) 
        
    
    # Check if paramter route is already in route
    def notInCurrentPath(self, x, currentPath):
        for p in currentPath:
            if x == p:
                return False
        return True

    # Given a date range, create list of applicable dates
    def getDateRanges(self, date, margin):
        # parse date into calculatable field
        dateObject = datetime.strptime(date, '%Y-%m-%d')
        output = []
        startDate = dateObject - timedelta(days=margin)
        for m in range(margin*2+1):
            output.append(datetime.strftime(startDate+timedelta(days=m),'%Y-%m-%d'))
            print(output)
        
        return m

    # Print debug if verbose
    def pv(self, *text):
        if self.verboseLogs:
            output = ''
            for x in text:
                output = str(output) + " " + str(x)
            print(output)

    # create log
    def createLog(self, logFileName, objs):
        if self.verboseLogs:
            with open(logFileName, mode='w', newline='') as logCsv:
                logWriter=csv.writer(logCsv, delimiter=',')
                header = []
                for i, k in enumerate(objs[0]):
                    header.append(k)
                logWriter.writerow(header)
                for o, obj in enumerate(objs):
                    row = []
                    for i, k in enumerate(obj):
                        row.append(str(obj[k]))
                    logWriter.writerow(row)

    def createLogHeaders(self,logFileName, objs):
        with open(logFileName, mode='w', newline='') as logCsv:
            logWriter=csv.writer(logCsv, delimiter=',')
            header = []
            for i, k in enumerate(objs[0]):
                header.append(k)
            logWriter.writerow(header)

    def writeLogRow(self, logFileName, objs):
        with open(logFileName, mode='a', newline='') as logCsv:
            logWriter=csv.writer(logCsv, delimiter=',')
            for o, obj in enumerate(objs):
                row = []
                for i, k in enumerate(obj):
                    row.append(str(obj[k]))
                logWriter.writerow(row)