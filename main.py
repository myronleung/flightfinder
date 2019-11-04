from flightfinder import FlightFinder

ff = FlightFinder(verboseLogs=True)

ff.generateRoutes()
ff.generateLegs()
ff.getLegPriceOptionsSessions()
ff.getPriceOptions()

# ff.getDateRanges('2019-12-20',0)
# ff.getPriceOptions('869b4cf9-0d16-4947-bc91-b3769a01ca5a')