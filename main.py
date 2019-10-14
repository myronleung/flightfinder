from skyscanner import SkyScanner

# Sample session: c086af04-75fb-4b88-871a-acdcfc196e7f
ss = SkyScanner(
    configDir='./config/', 
    programParamsFileName='programParams.json', 
    tripParamsFileName='tripParams.json')

sessionOutput = ss.getSession('LAX','PEK')
print(sessionOutput)

pollsOutput = ss.getPolls(sessionOutput['body'])
# print(pollsOutput)

ss.printPolls(pollsOutput['body'])