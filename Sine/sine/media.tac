import sine.useragent as ua
from twisted.application import service
application = service.Application("RTP Media Server")
ua.MediaServer().setServiceParent(application)