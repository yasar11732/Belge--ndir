# -*- coding: utf-8 -*-
"""
İndirme işleminin gerçekleştiği yer.

@ TODO: multiprocessing kullansam ya lan :S
-----------------------------------------------------------------------------
Main module.
"""
import os
import sys
import logging
import HTTPutils
import shutil

from collections import deque
from sets import ImmutableSet
from urllib2 import urlopen
from urllib2 import HTTPError, URLError
from urlparse import urljoin
from HTMLParser import HTMLParseError

from parsers import myurlparse, LinkCollector, HTMLReferenceFixer, encodingFinder

# İndirilecek belge türleri
# Contents types to be downloaded
allowed_downloads = ImmutableSet([
    "text/plain",
    "text/html",
    "text/css",
    "text/javascript",
])


main_logger = logging.getLogger("indirici")
main_logger.setLevel(logging.DEBUG)

fh = logging.FileHandler("indirici.log")
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

fh.setFormatter(formatter)
ch.setFormatter(formatter)

main_logger.addHandler(fh)
main_logger.addHandler(ch)
    
class DownloadQueue(object):
    """
    Döngü içerisinde listeye ekleme yapıldığında sıkıntı çıkarmayacak bir
    sıralayıcı. Bir kere sunduğu bir objeyi, bir daha sunmaz, böylece, sıraya
    eklerken, daha önce eklenmiş mi diye kontrol etmeye gerek duyulmaz.
    --------------------------------------------------------------------------
    A loop safe and unique queue iterator. Allows item addition inside for loops.
    Gives only unique items so you don't need to check item when adding it to the queue.
    Half-optimized for potentially big queues.

    @TODO: use a temp database for big queues
    """

    def __init__(self):
        self._queue = deque()
        self._already_given = set()

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()
        
    def __next__(self):
        try:
            item = self._queue.popleft()
            self._already_given.add(item)
            main_logger.debug("Returning %s from url queue." % item)
            return item
        except IndexError:
            self._already_given = set()
            raise StopIteration

    def append(self, item):
        if item not in self._queue and item not in self._already_given:
            main_logger.debug("Appending %s to download queue." % item)
            self._queue.append(item)
        


    
def main(initial_url):

    # List of 3-item tuples.
    # (file_path, encoding, base_url)
    # (dosya_yolu, kodlama, temel_url)
    to_be_processed = []
        
    queue = DownloadQueue()
    
    init_url = myurlparse(initial_url)

    if init_url.path  == "":
        initial_url += "/"
        init_url = myurlparse(initial_url)

    final_location = HTTPutils.getFinalUrl(init_url.geturl())

    if not final_location.startswith(initial_url):
        main_logger.critical("The page you have given redirects to %s")
        main_logger.critical("Aborting...")
    final_location = myurlparse(final_location)
    
    queue.append(final_location.getUrlWithoutFragments())
    
    download_dir = os.path.join(os.getcwd(), init_url.netloc).replace(".", "_")


    if not os.path.isdir(download_dir):
        os.mkdir(download_dir)

    def check_url(url,check_cache = {}):
        """
        Verilen url indirelecek mi diye bakar. Eğer, indirelecekse,
        gereken düzenlemeler de yapılmış olarak url döndürür, eğer
        indirilmeyecekse, None döndürür.
        ------------------------------------------------------------------
        Checks to see if url is ok for download
        """
        try:
            return check_cache[url]
        except KeyError:
            if not url.startswith(initial_url):
                check_cache[url] = None
                return None
            final_location = HTTPutils.getFinalUrl(url)

            if not final_location.startswith(initial_url):
                check_cache[url] = None
                return None
            new_link = myurlparse(final_location).getUrlWithoutFragments()
            check_cache[url] = new_link
            return new_link

    for link in queue:
        
        link = myurlparse(link)
        
        if link.netloc != init_url.netloc:
            main_logger.info("Skipping link from other internet location: %s" % link.geturl())
            continue
        
        content = HTTPutils.getContentType(link.geturl())
        if not content:
            main_logger.warning("Couldn\'t get content type for %s, skipping" % link.geturl())
            continue
        
        if content == "text/html" and not link.geturl().startswith(initial_url):
            main_logger.info("Skipping %s, because not in download subdirectory." % link.geturl())
            continue

        if content not in allowed_downloads:
            main_logger.info("Skipping %s because it is not in allowed downloads." % link.geturl())
            continue
        
        try:
            url = urlopen(link.geturl(), timeout=5)

        except HTTPError as e:
            main_logger.warning("Server couldn\'t fullfill the request. [%s], Skipping" % e.code)
            continue

        except URLError as e:
            main_logger.warning("We failed to reach %s because %s" % (link.geturl(), e.reason))
            main_logger.warning("Skipping %s" % link.geturl())
            continue
        
        main_logger.info("Downloading %s" % link.geturl())
        response = url.read()
        url.close()
        file_path = os.path.join(download_dir,*link.path.split("/"))

        #handle directories.
        if link.path.endswith("/"):
            file_path = os.path.join(file_path, "index.html")

        if not os.path.isdir(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w") as output_file:
            output_file.write(response)
            
        if content == "text/html":
            main_logger.info("Parsing page for further links, could take a while.")

            link_collect = LinkCollector()
            encoding = HTTPutils.getEncoding(link.geturl())
            if not encoding:
                main_logger.debug("Couldn\'t get encoding in http headers for %s" % link.geturl())
                # If http headers doesn't mention charset,
                # we parse html file to see meta headers
                a = encodingFinder()
                a.feed(response)
                encoding = a.encoding
            if not encoding:
                main_logger.debug("Set default encoding for %s" % link.geturl())
                encoding = "iso-8859-1"

            try:
                response_to_be_parsed = response.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                main_logger.debug("Decoding failed for %s, feeding raw binary data" % link.geturl())
                response_to_be_parsed = response

            try:
                link_collect.feed(unicode(response, encoding))
            except HTMLParseError:
                main_logger.warning("HTML Parse error, could't get all the links.")

            for new_link in link_collect.links:
                new_link = check_url(urljoin(link.geturl(), new_link))
                if new_link:
                    queue.append(new_link)

            base_url = link.geturl()
            if base_url.endswith("/"):
                base_url += "index.html"
            to_be_processed.append((file_path, encoding, base_url))
            main_logger.info("Done parsing for links.")

    main_logger.info("Starting to fix references, this could take a while...")

    for file_path, encoding, url in to_be_processed:
        main_logger.info("processing %s" % file_path)
        with open(file_path, "r") as html_file:
            html_contents = html_file.read()

        a = HTMLReferenceFixer()
        a.setbaseurl(url)
        a.filepath = file_path

        try:
            a.feed(unicode(html_contents, encoding))
        except HTMLParseError:
            main_logger.warning("Couldn\'t parse %s, skipping" % (file_path))
            continue

        with open(file_path, "w") as processed_file:
            processed_file.write(a.output.encode(encoding))

if __name__ == "__main__":
    
    try:
        initial_url = sys.argv[1]
    except IndexError:
        initial_url = raw_input("Lütfen giriş url\'ini giriniz: ")

    if not initial_url.startswith("http"):
        initial_url = "http://" + initial_url
    main(initial_url)
