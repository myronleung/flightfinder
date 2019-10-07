print("Setting up...")

import requests
import json
import csv
import time
from collections import namedtuple

def getPlaces(data, id):
    for d in data.Places:
        if d.Id == id:
            return d.Code+": "+d.Name
    return ""

def getCarriers(data, id):
    for d in data.Carriers:
        if d.Id == id:
            return d.Code+": "+d.Name
    return ""

def getAgents(data, id):
    for d in data.Agents:
        if d.Id == id:
            return d.Name+" - "+d.Type
    return ""

def getLeg(data, id):
    for d in data.Legs:
        if d.Id == id:
            return d
    return ""

def getAll(obj, func, data):
    l = ""
    for x in obj:
        if l == "":
            l = func(data, x)
        else:
            l = l + "|" + func(data,x)
    return l

def getPrices(outboundAirport, inboundAirport, outboundDates, inboundDates, outputCSVFileName, outputJSONFileName, getNewData):
    print("================================")
    print("Generating routes for:")
    print(outboundAirport,"to",inboundAirport)
    # Create Session
    url_session = "https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/pricing/v1.0"
    headers = {
        'x-rapidapi-host': "skyscanner-skyscanner-flight-search-v1.p.rapidapi.com",
        'x-rapidapi-key': "17580d4cf9msh8dd917d5bd4448ep1598cejsn4d622a3587a3",
        'content-type': "application/x-www-form-urlencoded"
        }
    # Generate Payload
    d_payload = {
        # Required
        "country":"US",
        "currency":"USD",
        "locale":"en-US",
        "originPlace":outboundAirport,
        "destinationPlace":inboundAirport ,
        "outboundDate":"2019-12-20",
        "adults":2,
        # Optional
        "inboundDate":"2020-01-04",
        "cabinClass":"economy",
        "children":0,
        "infants":0,
        "includeCarriers":"",
        "excludeCarriers":"",
        "groupPricing":True
    }
    payload = ""
    for k in d_payload:
        if payload != "":
            payload = payload+"&"+k+"="+str(d_payload[k])
        else:
            payload = k+"="+str(d_payload[k])

    responseSize = 20
    output = ""
    location = ""
    sessionKey = ""
    validStatusCodes = [200,201]
    if getNewData:
        print("Creating session...")
        while True:
            res_sessionkey = requests.request("POST", url=url_session, data=payload, headers=headers)
            if res_sessionkey.status_code in validStatusCodes:
                print("Session Created:",res_sessionkey.status_code)
                location=res_sessionkey.headers["Location"]
                sessionKey=location[location.rfind("/")+1:len(location)]
                print("sessionKey:",sessionKey)
                break
            elif res_sessionkey.status_code == 429:
                print("Exceeded limit, sleeping for one minute...")
                for i in range(60):
                    time.sleep(1)
                    if i % 10 == 0:
                        print(60-i, "more seconds...")
            else:
                print(res_sessionkey.status_code)
                print(res_sessionkey.headers)
                print(res_sessionkey.text)
                res_sessionkey.raise_for_status()
            

        # location = "http://partners.api.skyscanner.net/apiservices/pricing/uk2/v1.0/8ab25e59-0576-4e3a-a5b3-79e26ee8ea7c"
        
        # Poll for data
        print("Getting data...")
        res_poll = ""
        url_poll = "https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/pricing/uk2/v1.0/"+sessionKey
        while True:
            querystring = {"sortType":"price*","sortOrder":"asc","pageIndex":"0","pageSize":responseSize}
            res_poll = requests.request("GET", url=url_poll, headers=headers, params=querystring)
            
            if res_poll.status_code in validStatusCodes:
                output = json.loads(res_poll.text, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
                print("Data received:", res_poll.status_code)
                break
            elif res_poll.status_code == 429:
                print("Exceeded limit, sleeping for one minute...")
                for i in range(60):
                    time.sleep(1)
                    if i % 10 == 0:
                        print(60-i, "more seconds...")
            else:
                print(res_poll.status_code)
                print(res_poll.headers)
                print(res_poll.text)
                res_poll.raise_for_status()

        with open('output.json', mode="a") as jsonFile:
            raw_json = json.loads(res_poll.text)
            json.dump(raw_json, jsonFile)

    # Get data from file
    else:
        with open(outputJSONFileName) as jsonFile:
            output = json.load(jsonFile, object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

    print("Printing output...")
    with open(outputCSVFileName, mode='a', newline='') as outputCSV:
        itineraryWriter = csv.writer(outputCSV, delimiter=',')
        # header = ["Itinerary","Pricing Option","Agents","OB Leg","OB Origin","OB Destination","OB Stops","OB Carriers","OB Operating Carriers","OB Departure Time","OB Arrival Time","OB Duration HR","OB Duration MIN","OB Inbound Leg","IB Origin","IB Destination","IB Stops","IB Carriers","IB Operating Carriers","IB Departure Time","IB Arrival TIme","IB Duration HR","IB Duration MIN","Price","Link"]
        # itineraryWriter.writerow(header)
        for x, i in enumerate(output.Itineraries):
            for y, po in enumerate(i.PricingOptions):
                row = []
                option = {}
                option["Itinerary"] = x
                option["Pricing Option"] = y
                option["Agents"] = getAll(po.Agents, getAgents, output)
                option["OB Leg"] = i.OutboundLegId
                oleg = getLeg(output, i.OutboundLegId)
                option["OB Origin"] = getPlaces(output, oleg.OriginStation)
                option["OB Destination"] = getPlaces(output, oleg.DestinationStation)
                option["OB Stops"] = getAll(oleg.Stops, getPlaces, output)
                option["OB Carriers"] = getAll(oleg.Carriers, getCarriers, output)
                option["OB Operating Carriers"] = getAll(oleg.OperatingCarriers, getCarriers, output)
                option["OB Departure Time"] = oleg.Departure
                option["OB Arrival Time"] = oleg.Arrival
                option["OB Duration HR"] = int(oleg.Duration / 60)
                option["OB Duration MIN"] = oleg.Duration % 60
                option["OB Inbound Leg"] = i.InboundLegId
                ileg = getLeg(output, i.InboundLegId)
                option["IB Origin"] = getPlaces(output, ileg.OriginStation)
                option["IB Destination"] = getPlaces(output, ileg.DestinationStation)
                option["IB Stops"] = getAll(ileg.Stops, getPlaces, output)
                option["IB Carriers"] = getAll(ileg.Carriers, getCarriers, output)
                option["IB Operating Carriers"] = getAll(ileg.OperatingCarriers, getCarriers, output)
                option["IB Departure Time"] = ileg.Departure
                option["IB Arrival TIme"] = ileg.Arrival
                option["IB Duration HR"] = int(ileg.Duration / 60)
                option["IB Duration MIN"] = ileg.Duration % 60
                option["Price"] = po.Price
                option["Link"] = po.DeeplinkUrl
                for h in header:
                    row.append(option[h])
                itineraryWriter.writerow(row)


# Outbound Airports
# outboundAirports = [
#     "LAX", # Los Angeles
#     "SFO", # San Francisco
#     "SEA", # Seattle
#     "JFK", # NYC
#     "YVR", # Vancouver
#     "ORD", # Chicago
#     "DEN", # Denver
#     "ATL", # Atlanta
#     "PDX", # Portland
#     "SLC", # Salt Lake City
#     "LAS", # Las Vegas
#     "IAD", # DC
#     "DCA", # DC
#     "PHL", # Philadelphia
#     "DTW", # Detroit
#     "LGA" # NYC 
# ]

# # Inbound Airports
# inboundAirports = [
#     "PEK", # Beijing
#     "CSX", # Changsha
#     "HKG", # Hong Kong
#     "PVG", # Shanghai 
#     "CAN", # Guangdong
#     "SZX", # Shenzhen
#     "CTU", # Chengdu
#     "NRT", # Tokyo
#     "HND", # Tokyo
#     "CTS", # Sapporo
#     "KIX", # Kansai
#     "FUK", # Kyushu
#     "OKA", # Okinawa
#     "ITM", # Osaka
#     "NGO" # Nagoya
# ]

outboundAirports = [
    "PEK", # Beijing
    "CSX", # Changsha
    "HKG", # Hong Kong
    "PVG", # Shanghai 
    "CAN", # Guangdong
    "SZX", # Shenzhen
    "CTU", # Chengdu
]

inboundAirports = [
    "NRT", # Tokyo
    "HND", # Tokyo
    "CTS", # Sapporo
    "KIX", # Kansai
    "FUK", # Kyushu
    "OKA", # Okinawa
    "ITM", # Osaka
    "NGO" # Nagoya
]

# Other Params
outboundDate = "2019-12-20"
inboundDate = "2020-01-04"
routeCombinations = []

# Generate route combinations
for x, o in enumerate(outboundAirports):
    outboundAirports[x] = o+"-sky"

for x, i in enumerate(inboundAirports):
    inboundAirports[x] = i+"-sky"

for x, o in enumerate(outboundAirports):
    for y, i in enumerate(inboundAirports):
        routeCombinations.append({
            "outbound":o,
            "inbound":i
        })

# Create blank file
with open('output.csv', mode='w', newline='') as outputCSV:
    itineraryWriter = csv.writer(outputCSV, delimiter=',')
    header = ["Itinerary","Pricing Option","Agents","OB Leg","OB Origin","OB Destination","OB Stops","OB Carriers","OB Operating Carriers","OB Departure Time","OB Arrival Time","OB Duration HR","OB Duration MIN","OB Inbound Leg","IB Origin","IB Destination","IB Stops","IB Carriers","IB Operating Carriers","IB Departure Time","IB Arrival TIme","IB Duration HR","IB Duration MIN","Price","Link"]
    itineraryWriter.writerow(header)

for r in routeCombinations:
    getPrices(r["outbound"],r["inbound"], outboundDate, inboundDate,'output.csv','output.json',True)