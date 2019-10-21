import json
import requests
import csv
import time
from collections import namedtuple

# Object ot manage skyscanner API

class SkyScanner:

    def __init__(self, configDir='./config/', programParamsFileName='programParams.json', tripParamsFileName='tripParams.json', verboseLogs=True):
        # Load config files
        self.programParamsFileName = configDir+programParamsFileName
        self.tripParamsFileName = configDir+tripParamsFileName
        with open(self.programParamsFileName) as jsonProgramParams:
            self.programParams = json.load(jsonProgramParams)
        with open(self.tripParamsFileName) as jsonTripParams:
            self.tripParams = json.load(jsonTripParams)

        # Create params
        self.verboseLogs = verboseLogs
        self.sessions = []
        self.polls = []
        self.outputJsonFileName = self.programParams['outputDirectory']+'/'+self.programParams['outputJsonFileName']
        self.outputCsvFileName = self.programParams['outputDirectory']+'/'+self.programParams['outputCsvFileName']
        self.currentSession = ''

    # Methods for parsing SkyScanner data ouptuts
    def getPlaces(self, data, id):
        for d in data.Places:
            if d.Id == id:
                return d.Code+': '+d.Name
        return ''

    def getCarriers(self, data, id):
        for d in data.Carriers:
            if d.Id == id:
                return d.Code+': '+d.Name
        return ''

    def getAgents(self, data, id):
        for d in data.Agents:
            if d.Id == id:
                return d.Name+' - '+d.Type
        return ''

    def getLeg(self, data, id):
        for d in data.Legs:
            if d.Id == id:
                return d
        return ''

    def getAll(self, obj, func, data):
        l = ''
        for x in obj:
            if l == '':
                l = func(data, x)
            else:
                l = l + '|' + func(data,x)
        return l

    # Print debug if verbose
    def pv(self, *text):
        if self.verboseLogs:
            output = ''
            for x in text:
                output = str(output) + " " + str(x)
            print(output)
    def setPV(self, pv):
        self.verboseLogs = pv

    def getSession(self, outboundAirport, inboundAirport, outboundDate = '', inboundDate = '', testApi = True):
        self.pv('Getting session for',outboundAirport,'to',inboundAirport,'for',outboundDate,'to',inboundDate)
        url_session = 'https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/pricing/v1.0'
        output = {
            'success':False,
            'statusCode':'',
            'headers':'',
            'body':''
        }

        # Generate payload
        payload_session_json = {}
        payload_session_json.update(self.tripParams['requiredParams'])
        payload_session_json.update(self.tripParams['optionalParams'])
        payload_session_json.update({'outboundDate':outboundDate,'inboundDate':inboundDate})
        payload_session_json['originPlace'] = outboundAirport+'-sky'
        payload_session_json['destinationPlace'] = inboundAirport+'-sky'
        self.pv(payload_session_json)

        # Stringify payload
        payload_session_string = ""
        for k in payload_session_json:
            if payload_session_string != "":
                payload_session_string = payload_session_string+"&"+k+"="+str(payload_session_json[k])
            else:
                payload_session_string = k+"="+str(payload_session_json[k])

        # Get new session
        self.pv("Creating session...")
        while True:
            if not(testApi):
                output['body'] = payload_session_json
                break
            resSessionKey = requests.request("POST", url=url_session, data=payload_session_string, headers=self.programParams['sessionHeaders'])

            # Check for valid status codes, if found, generate session and store
            if resSessionKey.status_code in self.programParams['validStatusCodes']:
                self.pv("Session Created:",resSessionKey.status_code)
                location=resSessionKey.headers["Location"]
                sessionKey=location[location.rfind("/")+1:len(location)]
                self.pv("sessionKey:",sessionKey)

                # Generate output
                output['success'] = True
                output['statusCode'] = resSessionKey.status_code
                output['headers'] = resSessionKey.headers
                output['body'] = sessionKey
                break

            # If exceeded API limit, sleep for 1 min
            elif resSessionKey.status_code == 429:
                self.pv("Exceeded limit, sleeping for one minute...")
                self.pv('resPoll:',resSessionKey.status_code, resSessionKey.headers, resSessionKey.text)
                for i in range(60):
                    time.sleep(1)
                    if i % 5 == 0:
                        self.pv(60-i, "more seconds...")

            # If invalid response and limit is not exceeded, error and print error
            else:
                self.pv(resSessionKey.status_code)
                self.pv(resSessionKey.headers)
                self.pv(resSessionKey.text)
                # resSessionKey.raise_for_status()
                output['success'] = False
                output['statusCode'] = resSessionKey.status_code
                output['headers'] = resSessionKey.headers
                output['body'] = resSessionKey.text
                break

        return output

    def getPolls(self, sk, testApi):
        
        self.currentSession = sk
        # Get new data
        if self.programParams['getNewData']:
            self.pv('Polling for session key',sk,'...')
            resPoll = ''
            urlPoll = 'https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/pricing/uk2/v1.0/'+self.currentSession
            output = {
                'success':False,
                'statusCode':'',
                'headers':'',
                'body':''
            }

            while True:
                if not(testApi):
                    output['body'] = urlPoll
                    break
                # Create request
                querystring = {"sortType":"price*","sortOrder":"asc","pageIndex":"0","pageSize":self.programParams['responseSize']}
                resPoll = requests.request("GET", url=urlPoll, headers=self.programParams['sessionHeaders'], params=querystring)
                
                # Check for valid status codes, if found, generate session and store
                if resPoll.status_code in self.programParams['validStatusCodes']:
                    self.pv("Data received:", resPoll.status_code)
                    output['success'] = True
                    output['statusCode'] = resPoll.status_code
                    output['headers'] = resPoll.headers
                    output['body'] = json.loads(resPoll.text, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
                    break

                # If exceeded API limit, sleep for 1 min
                elif resPoll.status_code == 429:
                    self.pv('Exceeded limit, sleeping for one minute...')
                    self.pv('resPoll:',resPoll)
                    for i in range(60):
                        time.sleep(1)
                        if i % 5 == 0:
                            self.pv(60-i, 'more seconds...')

                # If invalid response and limit is not exceeded, error and print error
                else:
                    output['success'] = False
                    output['statusCode'] = resPoll.status_code
                    output['headers'] = resPoll.headers
                    output['body'] = resPoll.text
        else:
            with open(self.outputJsonFileName) as jsonFile:
                output['success'] = True
                output['statusCode'] = 'File'
                output['headers'] = 'File'
                output['body'] = json.load(jsonFile, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

        return output

    def printOutputFileHeaders(self):
        with open(self.outputCsvFileName, mode='w', newline = '') as outputCsv:
            itineraryWriter = csv.writer(outputCsv, delimiter=',')
            header = ["Itinerary","Pricing Option","Agents","OB Leg","OB Origin","OB Destination","OB Stops","OB Carriers","OB Operating Carriers","OB Departure Time","OB Arrival Time","OB Duration HR","OB Duration MIN","OB Inbound Leg","IB Origin","IB Destination","IB Stops","IB Carriers","IB Operating Carriers","IB Departure Time","IB Arrival TIme","IB Duration HR","IB Duration MIN","Price","Link"]
            itineraryWriter.writerow(header)
            return header

    def printPolls(self, data):
        self.pv('Printing data...')
        header = self.printOutputFileHeaders()
        with open(self.outputCsvFileName, mode='a', newline = '') as outputCsv:
            itineraryWriter = csv.writer(outputCsv, delimiter=',')
            for x, i in enumerate(data.Itineraries):
                for y, po in enumerate(i.PricingOptions):
                    row = []
                    option = {}
                    option["Itinerary"] = x
                    option["Pricing Option"] = y
                    option["Agents"] = self.getAll(po.Agents, self.getAgents, data)
                    option["OB Leg"] = i.OutboundLegId
                    oleg = self.getLeg(data, i.OutboundLegId)
                    option["OB Origin"] = self.getPlaces(data, oleg.OriginStation)
                    option["OB Destination"] = self.getPlaces(data, oleg.DestinationStation)
                    option["OB Stops"] = self.getAll(oleg.Stops, self.getPlaces, data)
                    option["OB Carriers"] = self.getAll(oleg.Carriers, self.getCarriers, data)
                    option["OB Operating Carriers"] = self.getAll(oleg.OperatingCarriers, self.getCarriers, data)
                    option["OB Departure Time"] = oleg.Departure
                    option["OB Arrival Time"] = oleg.Arrival
                    option["OB Duration HR"] = int(oleg.Duration / 60)
                    option["OB Duration MIN"] = oleg.Duration % 60
                    if hasattr(i, 'InboundLegId'):
                        option["OB Inbound Leg"] = i.InboundLegId
                        ileg = self.getLeg(data, i.InboundLegId)
                        option["IB Origin"] = self.getPlaces(data, ileg.OriginStation)
                        option["IB Destination"] = self.getPlaces(data, ileg.DestinationStation)
                        option["IB Stops"] = self.getAll(ileg.Stops, self.getPlaces, data)
                        option["IB Carriers"] = self.getAll(ileg.Carriers, self.getCarriers, data)
                        option["IB Operating Carriers"] = self.getAll(ileg.OperatingCarriers, self.getCarriers, data)
                        option["IB Departure Time"] = ileg.Departure
                        option["IB Arrival TIme"] = ileg.Arrival
                        option["IB Duration HR"] = int(ileg.Duration / 60)
                        option["IB Duration MIN"] = ileg.Duration % 60
                    option["Price"] = po.Price
                    option["Link"] = po.DeeplinkUrl
                    for h in header:
                        print('printing:',h)
                        if hasattr(i, h):
                            row.append(option[h])
                    itineraryWriter.writerow(row)