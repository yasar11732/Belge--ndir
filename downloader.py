# -*- coding:utf-8 -*-
import urllib2
import urlparse
import httplib
import sys
import os
import posixpath

from HTMLParser import HTMLParser
from os import makedirs
from socket import gaierror

# Contents types to be donwloaded
allowed_downloads = [
    "text/html",
    "text/css",
    "text/javascript",
]

def getHeadResponse(url,response_cache = {}):
    try:
        return response_cache[url]
    except KeyError:
        url = urlparse.urlparse(url)
        conn = httplib.HTTPConnection(url.netloc)
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

def getFinalUrl(url):
    "Navigates through redirections to get final url."

    response = getHeadResponse(url)
    try:
        if str(response.status).startswith("3"):
            return getFinalUrl(response.getheader("location"))
    except AttributeError:
        pass
    return url

def getEncoding(url):

    response = getHeadResponse(url)
    content = response.getheader("Content-type")
    try:
        key, equals, value = content.split(";")[1].partition("=")
        return value
    except IndexError, AttributeError:
        return None

def urlok(url):

    response = getHeadResponse(url)
    if str(response.status).startswith("2"):
        return True
    else:
        return False
    
class LinkCollector(HTMLParser):
    """
    Parses a html and gets urls.
    >>> a = LinkCollector()
    >>> a.feed("<a href='http://www.google.com/'>asdf</a>")
    >>> a.links = ['http://www.google.com/']
    """
    def reset(self):
        self.links = []
        HTMLParser.reset(self)

    def handle_starttag(self,tag,attr):
        if tag in ("a","link"):
            key = "href"
        elif tag in ("img","script"):
            key = "src"
        else:
            return
        self.links.extend([v for k,v in attr if k == key])

class AcayipError(Exception):
    "Raised if HTMLReference Fixer called without proper attributes."

class HTMLReferenceFixer(HTMLParser):
    """
    After instantiating, set base url and file path like this:
    a = HTMLReferenceFixer()
    a.baseurl = "some url"
    a.filepath = "filepath"

    This class will convert full urls to relatives if target exists in
    file system. Otherwise, this will convert all links to full urls.

    Handles "a", "script", and "link" html tags.

    Get output from output property after feeding.
    """
    
    def feed(self,data):
        if hasattr(self,"baseurl") and hasattr(self,"filepath"):
            return HTMLParser.feed(self,data)
        else:
            raise AcayipError("You have to fill in baseurl and filepath attrs first.")

    def reset(self):
        self.output = ""
        HTMLParser.reset(self)


    def fixlink(self,link):
        # @TODO: fix links!
        return "link was here!"
        
    def fixsrc(self,attrs):
        new_attrs = []

        for k,v in attrs:
            if k == "src":
                v = self.fixlink(v)
            new_attrs.append((k,v))

        return new_attrs

    def fixhref(self,attrs):
        new_attrs = []

        for k,v in attrs:
            if k == "href":
                v = self.fixlink(v)
            new_attrs.append((k,v))

        return new_attrs
        
    def fixattrs(self,tag,attrs):
        if tag in ("a","link"):
            return self.fixhref(attrs)
        elif tag in ("script","img"):
            return self.fixsrc(attrs)
        else:
            return attrs


    def handle_starttag(self,tag,attrs):

        if tag in ("a","script","link","img"):
            attrs = self.fixattrs(tag,attrs)

        self.output += "<%s" % tag
        for k,v in attrs:
            self.output += " %s=\"%s\"" % (k,v)
        self.output += ">"

    def handle_startendtag(self,tag,attrs):
        if tag in ("a","script","link","img"):
            attrs = self.fixattrs(tag,attrs)

        self.output += "<%s" % tag
        for k,v in attrs:
            self.output += " %s=\"%s\"" % (k,v)
        self.output += " />"

    def handle_endtag(self,tag):
        self.output += "</%s>" % tag

    def handle_data(self,data):
        self.output += data

    def handle_decl(self,data):
        self.output += data

    def handle_charref(self,data):
        self.output += "&#" + data + ";"
        

    def handle_entityref(self,data):
        self.output += "&" + data + ";"

    def handle_comment(self,data):
        self.output += "<!--" + data + "-->"

    def handle_pi(self,data):
        self.output += data

    
def dene():
    a = HTMLReferenceFixer()
    a.baseurl = ""
    a.filepath = ""
    a.feed("<a href=\"hebele\">hubele</a>")


    a.feed("<p>&lt;</p>")
    return a
class DownloadQueue(object):
    """
    A loop safe and unique queue iterator. Allows item addition inside for loops.
    Gives only unique items so you don't need to check item when adding it to the queue.
    Half-optimized for potentially big queues.

    @TODO: use a temp database for big queues
    """
    def __init__(self):
        self._queue = []
        self._already_given = []
    def __iter__(self):
        return self
    def __next__(self):
        return self.next()
    def reset(self):
        "Clears already given items"
        self._already_given = []
        
    def next(self):
        try:
            item = self._queue.pop(0)
            self._already_given.append(item)
            return item
        except IndexError:
            self.reset()
            raise StopIteration

    def append(self,item):
        if item not in self._queue and item not in self._already_given:
            self._queue.append(item)
        


def main(initial_url):

    # List of 3-item tuples.
    # (file_path, encoding, base_url)
    to_be_processed = []
        
    queue = DownloadQueue()
    
    init_url = urlparse.urlparse(initial_url)

    if init_url.path  == "":
        initial_url += "/"
        init_url = urlparse.urlparse(initial_url)

    queue.append(init_url.geturl())
    download_dir = os.path.join(os.getcwd(),init_url.netloc)


    if not os.path.isdir(download_dir):
        os.mkdir(download_dir)


    for link in queue:
        final_link = urlparse.urlparse(getFinalUrl(link))
        link = urlparse.urlparse(link)
        
        if final_link.netloc != init_url.netloc:
            sys.stderr.write("Skipping %s\n" % link.geturl())
            sys.stderr.write("Reason: Link from different location\n")
            continue
        
        content = getContentType(final_link.geturl())

        if content == "text/html" and not final_link.geturl().startswith(initial_url):
            sys.stderr.write("Skipping %s\n" % link.geturl())
            sys.stderr.write("Reason: Not inside range.\n")
            continue

        if content not in allowed_downloads:
            sys.stderr.write("Skipping %s\n" % link.geturl())
            sys.stderr.write("Reason: Not allowed download.\n")
            continue

        if not urlok(final_link.geturl()):
            sys.stderr.write("Skipping %s\n" % link.geturl())
            sys.stderr.write("Reason: Broken link\n")
            continue
        
        try:
            url = urllib2.urlopen(final_link.geturl())
        except urllib2.HTTPError:
            sys.stderr.write("An error occured: skipping %s\n" % link.geturl())
            continue
        
        
        print "Downloading %s" % link.geturl()
        response = url.read()
        url.close()
        file_path = os.path.join(download_dir,*link.path.split("/"))

        #handle directories.
        if final_link.path.endswith("/"):
            file_path = os.path.join(file_path,"index.html")

        if not os.path.isdir(os.path.dirname(file_path)):
            makedirs(os.path.dirname(file_path))

        
        if content == "text/html":
            link_collect = LinkCollector()
            encoding = getEncoding(final_link.geturl())

            try:
                link_collect.feed(response.decode(encoding))
            except LookupError:
                link_collect.reset()
                link_collect.feed(response)

            for new_link in link_collect.links:
                queue.append(urlparse.urljoin(link.geturl(),new_link))

            to_be_processed.append((file_path,encoding,link.geturl()))

        output_file = open(file_path,"wb")
        output_file.write(response)
        output_file.close()
    print("Beginning fixing url references...")

    for file_path, encoding, url in to_be_processed:
        print("Processing %s" % file_path)
        html_file = open(file_path,"rb")
        html_contents = html_file.read().decode(encoding)
        html_file.close()
        a = HTMLReferenceFixer()
        a.baseurl = url
        a.filepath = file_path
        a.feed(html_contents)
        processed_file = open(file_path,"wb")
        processed_file.write(a.output.encode(encoding))
        processed_file.close()
if __name__ == "__main__":

    try:
        initial_url = sys.argv[1]
    except IndexError:
        initial_url = raw_input(u"Lütfen giriş url\'ini giriniz: ")
    main(initial_url)
