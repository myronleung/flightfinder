import json
import csv
from skyscanner import SkyScanner

class FlightFinder:

    def __init__(self, sk=SkyScanner(tripParamsFileName='tripParams_test.json'), verboseLogs=True):
        # Create params
        self.skyscanner = sk
        self.skyscanner.setPV(verboseLogs)
        self.verboseLogs = verboseLogs
        
        self.legs = []
        self.routes = [] #Array of city groups
        self.cityGroups = self.skyscanner.tripParams['cityGroups']
        self.pv('FlighFinder initiated successfully')

    def generateLegs(self):
        self.pv('Generating Legs')
        # Recursion
        # status = self.generateLegCombinations(
        #     groups=self.skyscanner.tripParams["cityGroups"],
        #     currentGroup=0,
        #     numGroups=len(self.skyscanner.tripParams["cityGroups"])
        #     )

        # Iteration
        # Get flexibly city group labels
        flexCityGroups = []
        for i, cg in enumerate(self.skyscanner.tripParams['cityGroups']):
            if cg['flexible'] == "True":
                flexCityGroups.append(i)

        for i, group in enumerate(self.skyscanner.tripParams['cityGroups']):
            self.pv(str(i)+'/'+str(len(self.skyscanner.tripParams['cityGroups'])-1)+':', group['cities'])
            # Create list of destination city groups. Must include all flexible city groups
            destinationCityGroup = []

            # group is a lsit of all city groups
            for city in group['cities']:

                # flexCityGroup is the list of city group indexes that can be moved out of order
                for fCityGroup in flexCityGroups:
                    
                    # do not match to self city group
                    # this conditional defines which city group is eligible to be in the next city group. Conditions are:
                        # current city will not generate route to self
                        # current city is not last city in city groups -- This may need to change later, may need to move up a couple levels
                        # last city is not flexible
                    # i is the index of the current city group flightfinder is analyzing
                    if i != fCityGroup and i != len(self.skyscanner.tripParams['cityGroups'])-1 and group['flexible'] != "False":

                        # match cities against each eligible fCity Group
                        # loop through city in the flex city group
                        for fCity in self.skyscanner.tripParams['cityGroups'][fCityGroup]['cities']:
                            # print(city, "->", fCity)
                            self.legs.append({
                                'from':city,
                                'to': fCity
                            })

            # Create dict for each pair

        # self.pv('Legs Generated:', status)

    def generateRoutes(self):
        routes = []
            
        self.generateNextRoute([], routes, 0)

        with open('./logs/recursion_log.csv', mode='w', newline='') as logCsv:
            logWriter = csv.writer(logCsv, delimiter=',')
            for r in routes:
                logWriter.writerow(r)
        
    def generateNextRoute(self, cp, routes, index):

        for g, group in enumerate(self.cityGroups):
            
            # Create a branch representing where on the path we are
            currentPath = cp.copy()
            # Create a test route and determine if it has all city groups
            route = cp.copy()
            if self.notInCurrentPath(g, currentPath) and (group['orderFlexible'] == 1 or (group['orderFlexible'] == 0 and index == g)):
                route.append(g)
                # Append to routes if last layer
                if len(self.cityGroups) - 1 == index and len(route) == len(self.cityGroups):
                    routes.append(route)
                    return
                else:
                    currentPath.append(g)

            # proceed to next layer if not already on the last layer
            if len(self.cityGroups) - 1 > index:
                self.generateNextRoute(currentPath, routes, index + 1)


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

    # Print debug if verbose
    def pv(self, *text):
        if self.verboseLogs:
            output = ''
            for x in text:
                output = str(output) + " " + str(x)
            print(output)