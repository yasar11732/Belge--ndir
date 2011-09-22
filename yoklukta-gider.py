# -*- coding: utf-8 -*-

import os
import sys

from urllib2 import urlopen, HTTPError, URLError
from urlparse import urljoin
from os import makedirs
from HTTPutils import getEncoding, getFinalUrl, getContentType
from parsers import myurlparse, LinkCollector, HTMLReferenceFixer

# Contents types to be donwloaded
allowed_downloads = [
    "text/plain",
    "text/html",
    "text/css",
    "text/javascript",
]

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
    
    init_url = myurlparse(initial_url)

    if init_url.path  == "":
        initial_url += "/"
        init_url = myurlparse(initial_url)

    final_location = getFinalUrl(init_url.geturl())

    if not final_location.startswith(initial_url):
        sys.stderr.write("Your page redirects to unwanted url.")
        sys.stderr.write("I refuse to donwload!")
    final_location = myurlparse(final_location)
    
    queue.append(final_location.getUrlWithoutFragments())
    
    download_dir = os.path.join(os.getcwd(),init_url.netloc).replace(".","_")


    if not os.path.isdir(download_dir):
        os.mkdir(download_dir)


    for link in queue:
        
        link = myurlparse(link)
        
        if link.netloc != init_url.netloc:
            sys.stderr.write("Skipping %s\n" % link.geturl())
            sys.stderr.write("Reason: Link from different location\n")
            continue
        
        content = getContentType(link.geturl())

        if content == "text/html" and not link.geturl().startswith(initial_url):
            sys.stderr.write("Skipping %s\n" % link.geturl())
            sys.stderr.write("Reason: Not inside range.\n")
            continue

        if content not in allowed_downloads:
            sys.stderr.write("Skipping %s\n" % link.geturl())
            sys.stderr.write("Reason: Not allowed download.\n")
            continue
        
        try:
            url = urlopen(link.geturl(), timeout=5)
        except (HTTPError,URLError) :
            sys.stderr.write("An HTTP error occured: skipping %s\n" % link.geturl())
            continue
        
        
        print "Downloading %s" % link.geturl()
        response = url.read()
        url.close()
        file_path = os.path.join(download_dir,*link.path.split("/"))

        #handle directories.
        if link.path.endswith("/"):
            file_path = os.path.join(file_path,"index.html")

        if not os.path.isdir(os.path.dirname(file_path)):
            makedirs(os.path.dirname(file_path))

        
        if content == "text/html":
            link_collect = LinkCollector()
            encoding = getEncoding(link.geturl())

            try:
                link_collect.feed(response.decode(encoding))

            except:
                sys.stderr.write("Malformed page, skipping %s" % link.geturl())
                continue

            for new_link in link_collect.links:
                new_link = urljoin(link.geturl(),new_link)
                if not new_link.startswith(initial_url):
                    continue
                final_location = getFinalUrl(new_link)

                if not final_location.startswith(initial_url):
                    continue
                new_link = myurlparse(final_location)
                queue.append(new_link.getUrlWithoutFragments())

            base_url = link.geturl()
            if base_url.endswith("/"):
                base_url += "index.html"
            to_be_processed.append((file_path,encoding,base_url))

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
        a.setbaseurl(url)
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
