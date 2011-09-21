# -*- coding:utf-8 -*-
import urllib2
import urlparse
import httplib
import sys
import os
import posixpath

from HTMLParser import HTMLParser

allowed_downloads = [
    "text/html",
    "text/css",
    "text/javascript",
]
def getContentType(url):
    "Return content type, except character encoding."
    try:
        return urllib2.urlopen(url).info()["Content-type"].split(";")[0]
    except urllib2.HTTPError:
        return None

def RecursiveMkdir(dirname):
    "Recursively make target directory."
    parent = os.path.abspath(os.path.join(dirname,".."))
    if not os.path.isdir(parent):
        RecursiveMkdir(parent)
    os.mkdir(dirname)

def getFinalUrl(url):
    "Navigates Through redirections to get final url."
    parsed = urlparse.urlparse(url)
    conn = httplib.HTTPConnection(parsed.netloc)
    conn.request("HEAD",parsed.path)
    response = conn.getresponse()
    if str(response.status).startswith("3"):
        new_location = [v for k,v in response.getheaders() if k == "location"][0]
        return getFinalUrl(new_location)
    return url

class LinkCollector(HTMLParser):

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


##class ReconstructHTML(HTMLParser):
##    """Converts links that we will download into relative links, including css and javascript sources.
##        Also converts relative links that we won't download into full links.
##    """"
##
##    def reset(self):
##        self.output = ""
##        self.baseUrl = None
##        HTMLParser.reset(self)
##
##    def setBaseUrl(self,url):
##        self.baseUrl = urlparse.urlparse(url)
##
##    def relurl(self,target):
##        "Gets relative url of target, according to our base url."
##
##        target=urlparse.urlparse(target)
##        if base.netloc != target.netloc:
##            raise ValueError('target and base netlocs do not match')
##        base_dir='.'+posixpath.dirname(base.path)
##        target='.'+target.path
##        return posixpath.relpath(target,start=base_dir)
##
##    def link_converter(self,link):
##        
##
##    def hrefhandler(self,attrs):
##
##        href = [v for k,v in attrs if k == "href"][0]
##        final_href = urlparse.urljoin(self.baseUrl,href)
##        final_location = urlparse.urlparse(final_href))
##        
##        if final_location.netloc != self.baseUrl.netloc or getContentType(final_href) not in allowed_downloads:
##            final_href = href
##
##        else:
##            final_href = self.relurl(final_href)


##    def handle_starttag(tag, attrs):
##
##        if tag in ("a","link"):
##            attrs = self.hrefhandler(attrs)
##        elif tag in ("img","script"):
##            attrs = self.srchandler(attrs)
##
##        self.output = "<%s " % tag
##        self.output += " ".join(["%s=\"%s\"" % (k,v) for k,v in attrs])
##        self.output += ">"

    
                
class DownloadQueue(object):
    """
    A loop safe and unique queue iterator. Allows item addition inside for loops.
    Gives only unique items so you don't need to check item when adding it to the queue.
    Half-optimized for potentially big queues.

    @TODO: use database for big queues
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
        


def main():
    try:
        initial_url = sys.argv[1]
    except IndexError:
        print("Usage: downloader.py http://www.example.com")
        sys.exit(1)

    queue = DownloadQueue()
    queue.append(initial_url)
    initial_url_parsed = urlparse.urlparse(initial_url)

    download_dir = os.path.join(os.getcwd(),initial_url_parsed.netloc)


    if not os.path.isdir(download_dir):
        os.mkdir(download_dir)


    for link in queue:
        final_link = getFinalUrl(link)

        final_link_parsed = urlparse.urlparse(final_link)
        link_parsed = urlparse.urlparse(link)
        
        if final_link_parsed.netloc != initial_url_parsed.netloc:
            continue
        
        content = getContentType(final_link)

        if content == "text/html" and not final_link.startswith(initial_url):
            continue
        if content not in allowed_downloads:
            continue

        try:
            url = urllib2.urlopen(final_link)
        except urllib2.HTTPError:
            continue
        
        print "Downloading %s" % link
        response = url.read()
        url.close()
        file_path = os.path.join(download_dir,*link_parsed.path.split("/"))

        #handle directories.
        if final_link_parsed.path.endswith("/"):
            file_path = os.path.join(file_path,"index.html")

        if not os.path.isdir(os.path.dirname(file_path)):
            RecursiveMkdir(os.path.dirname(file_path))

        
        

        

        if content == "text/html":
            link_collect = LinkCollector()
            link_collect.feed(response)
            for new_link in link_collect.links:
                queue.append(urlparse.urljoin(link,new_link))

        output_file = open(file_path,"wb")
        output_file.write(response)
        output_file.close()

if __name__ == "__main__": main()

        
        
        
    

    

    

    
    
