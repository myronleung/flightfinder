import json
import requests
import csv
import time
from collections import namedtuple

# Object ot manage skyscanner API

class SkyScanner:

    def __init__(self, configFileName='config.json'):
        self.configFileName = configFileName
        with open(self.configFileName) as jsonFile:
            self.config = json.load(jsonFile)
        self.sessions = []
        self.polls = []
        self.tripParams = self.config['tripParams']
        self.programParams = self.config['programParams']
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

    def getSession(self, outboundAirport, inboundAirport):
        print('Getting session for',outboundAirport,'to',inboundAirport,'for',self.tripParams['requiredParams']['outboundDate'],'to',self.tripParams['optionalParams']['inboundDate'])
        url_session = 'https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/pricing/v1.0'
        output = {
            'success':False,
            'statusCode':'',
            'headers':'',
            'body':''
        }

        # Generate payload
        payload_session_json = self.tripParams['requiredParams']
        payload_session_json.update(self.tripParams['optionalParams'])
        payload_session_json['originPlace'] = outboundAirport+'-sky'
        payload_session_json['destinationPlace'] = inboundAirport+'-sky'

        # Stringify payload
        payload_session_string = ""
        for k in payload_session_json:
            if payload_session_string != "":
                payload_session_string = payload_session_string+"&"+k+"="+str(payload_session_json[k])
            else:
                payload_session_string = k+"="+str(payload_session_json[k])

        # Get new session
        print("Creating session...")
        while True:
            resSessionKey = requests.request("POST", url=url_session, data=payload_session_string, headers=self.programParams['sessionHeaders'])

            # Check for valid status codes, if found, generate session and store
            if resSessionKey.status_code in self.programParams['validStatusCodes']:
                print("Session Created:",resSessionKey.status_code)
                location=resSessionKey.headers["Location"]
                sessionKey=location[location.rfind("/")+1:len(location)]
                print("sessionKey:",sessionKey)

                # Generate output
                output['success'] = True
                output['statusCode'] = resSessionKey.status_code
                output['headers'] = resSessionKey.headers
                output['body'] = sessionKey
                break

            # If exceeded API limit, sleep for 1 min
            elif resSessionKey.status_code == 429:
                print("Exceeded limit, sleeping for one minute...")
                for i in range(60):
                    time.sleep(1)
                    if i % 5 == 0:
                        print(60-i, "more seconds...")

            # If invalid response and limit is not exceeded, error and print error
            else:
                print(resSessionKey.status_code)
                print(resSessionKey.headers)
                print(resSessionKey.text)
                # resSessionKey.raise_for_status()
                output['success'] = False
                output['statusCode'] = resSessionKey.status_code
                output['headers'] = resSessionKey.headers
                output['body'] = resSessionKey.text
                break

        return output

    def getPolls(self, sk):
        self.currentSession = sk
        # Get new data
        if self.programParams['getNewData']:
            print('Polling for data...')
            resPoll = ''
            urlPoll = 'https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/pricing/uk2/v1.0/'+self.currentSession
            output = {
                'success':False,
                'statusCode':'',
                'headers':'',
                'body':''
            }

            while True:
                # Create request
                querystring = {"sortType":"price*","sortOrder":"asc","pageIndex":"0","pageSize":self.programParams['responseSize']}
                resPoll = requests.request("GET", url=urlPoll, headers=self.programParams['sessionHeaders'], params=querystring)
                
                # Check for valid status codes, if found, generate session and store
                if resPoll.status_code in self.programParams['validStatusCodes']:
                    print("Data received:", resPoll.status_code)
                    output['success'] = True
                    output['statusCode'] = resPoll.status_code
                    output['headers'] = resPoll.headers
                    output['body'] = json.loads(resPoll.text, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
                    break

                # If exceeded API limit, sleep for 1 min
                elif resPoll.status_code == 429:
                    print('Exceeded limit, sleeping for one minute...')
                    for i in range(60):
                        time.sleep(1)
                        if i % 5 == 0:
                            print(60-i, 'more seconds...')

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
        print('Printing data...')
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
                        row.append(option[h])
                    itineraryWriter.writerow(row)


# Sample session: c086af04-75fb-4b88-871a-acdcfc196e7f
ss = SkyScanner('config.json')

sessionOutput = ss.getSession('LAX','PEK')
print(sessionOutput)

pollsOutput = ss.getPolls(sessionOutput['body'])
# print(pollsOutput)

ss.printPolls(pollsOutput['body'])