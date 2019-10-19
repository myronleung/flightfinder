from flightfinder import FlightFinder

ff = FlightFinder(verboseLogs=True)

ff.generateLegs()

print(ff.legs)