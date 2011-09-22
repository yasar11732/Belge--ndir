from urlparse import urlparse
from httplib import HTTPConnection, HTTPSConnection

def getHeadResponse(url,response_cache = {}):
    "Make a http or https HEAD request, and returns response"
    try:
        return response_cache[url]
    except KeyError:
        url = urlparse(url)
        if url.scheme == "http":
            conn = HTTPConnection(url.netloc,timeout=2)
        elif url.scheme == "https":
            conn = HTTPSConnection(url.netloc,timeout=2)
        else:
            return None
        try:
            conn.request("HEAD",url.path)
        except:
            # Anything can happen, this is SPARTA!
            return None
        response = conn.getresponse()
        response_cache[url.geturl()] = response
        return response

def getHeader(url,header):
    response = getHeadResponse(url)
    if not response:
        return None
    else:
        return response.getheader(header)

def getContentType(url):
    "Returns content type of given url."

    contentType = getHeader(url,"Content-type")
    if contentType:
        return contentType.split(";")[0]

def getFinalUrl(url,already_seen = None):
    "Navigates through redirections to get final url."

    if already_seen is None:
        already_seen = [url]
    
    response = getHeadResponse(url)
    try:
        if str(response.status).startswith("3"):
            location = response.getheader("location")
            if location in already_seen:
                return location
            else:
                already_seen.append(location)
            return getFinalUrl(location,already_seen)
    except AttributeError:
        # response is None
        pass
    return url

def getEncoding(url):

    response = getHeadResponse(url)
    content = response.getheader("Content-type")
    try:
        key, equals, value = content.split(";")[1].partition("=")
        return value
    except (IndexError, AttributeError):
        return None

def urlok(url):

    response = getHeadResponse(url)
    if str(response.status).startswith("2"):
        return True
    else:
        return False
