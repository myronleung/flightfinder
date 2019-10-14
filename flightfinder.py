import json
import csv
from skyscanner import SkyScanner

class FlightFinder:

    def __init__(self, sk=SkyScanner(), verboseLogs=True):
        # Create params
        self.skyscanner = sk
        self.skyscanner.setPV(verboseLogs)
        self.verboseLogs = verboseLogs
        print('FlighFinder initiated successfully')

    def generateLegs(self):
        self.pv('Generating Legs')
        
    def testSkyScanner(self):
        sessionOutput = self.skyscanner.getSession('LAX','PEK')
        self.pv(sessionOutput)

        pollsOutput = self.skyscanner.getPolls(sessionOutput['body'])
        # print(pollsOutput)

        self.skyscanner.printPolls(pollsOutput['body']) 
        
    # Print debug if verbose
    def pv(self, *text):
        if self.verboseLogs:
            output = ''
            for x in text:
                output = output + " " + str(x)
            print(output)
