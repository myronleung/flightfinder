from flightfinder import FlightFinder

ff = FlightFinder(verboseLogs=True)

ff.generateRoutes()
ff.generateLegs()
ff.getLegPriceOptionsSessions()
# ff.getDateRanges('2019-12-20',0)