# -*- coding: utf-8 -*-
"""
İndirme işleminin gerçekleştiği yer.

@ TODO: multiprocessing kullansam ya lan :S
-----------------------------------------------------------------------------
Main module.
"""
import os
import sys
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from html.parser import HTMLParseError
from HTTPutils import getEncoding, getFinalUrl, getContentType
from parsers import myurlparse, LinkCollector, HTMLReferenceFixer, encodingFinder

# İndirilecek belge türleri
# Contents types to be downloaded
allowed_downloads = [
    "text/plain",
    "text/html",
    "text/css",
    "text/javascript",
]

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
        self._queue = []
        self._already_given = []

    def __iter__(self):
        return self
        
    def __next__(self):
        try:
            item = self._queue.pop(0)
            self._already_given.append(item)
            return item
        except IndexError:
            self._already_given = []
            raise StopIteration

    def append(self, item):
        if item not in self._queue and item not in self._already_given:
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

    final_location = getFinalUrl(init_url.geturl())

    if not final_location.startswith(initial_url):
        sys.stderr.write("Your page redirects to unwanted url.")
        sys.stderr.write("I refuse to donwload!")
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
            final_location = getFinalUrl(url)

            if not final_location.startswith(initial_url):
                check_cache[url] = None
                return None
            new_link = myurlparse(final_location).getUrlWithoutFragments()
            check_cache[url] = new_link
            return new_link

    for link in queue:
        
        link = myurlparse(link)
        
        if link.netloc != init_url.netloc:
            sys.stderr.write("Skipping %s\n" % link.geturl())
            sys.stderr.write("Reason: Link from different location\n")
            continue
        
        content = getContentType(link.geturl())
        if not content:
            print("Failed to get content type from the server.")
            print("Skipping...")
            continue
        
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

        except HTTPError as e:
            print("The server couldn\'t fullfill the request.")
            print("Error Code: ", e.code)
            print("Skipping...")
            continue

        except URLError as e:
            print("We failed to reach the server.")
            print("Reason: ", e.reason)
            continue
        
        print("Downloading -- İndiriliyor: %s\n" % link.geturl())
        response = url.read()
        url.close()
        file_path = os.path.join(download_dir,*link.path.split("/"))

        #handle directories.
        if link.path.endswith("/"):
            file_path = os.path.join(file_path, "index.html")

        if not os.path.isdir(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "wb") as output_file:
            output_file.write(response)
            
        if content == "text/html":
            print("Searching and checking links, could take a while.")
            print("-------------------------------------------------")
            print("Linkler bulunup kontrol ediliyor, uzun sürebilir.")

            link_collect = LinkCollector()
            encoding = getEncoding(link.geturl())
            if not encoding:
                # If http headers doesn't mention charset,
                # we parse html file to see meta headers
                a = encodingFinder()
                a.feed(response.decode("iso-8859-1"))
                encoding = a.encoding

            # If we still don't have any charset, we go with default.
            encoding = encoding or "iso-8859-1"

            try:
                response_to_be_parsed = response.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                response_to_be_parsed = response

            try:
                link_collect.feed(str(response, encoding))
            except HTMLParseError:
                sys.stderr.write("HTML Parse error, could't get all the links.")

            for new_link in link_collect.links:
                new_link = check_url(urljoin(link.geturl(), new_link))
                if new_link:
                    queue.append(new_link)

            base_url = link.geturl()
            if base_url.endswith("/"):
                base_url += "index.html"
            to_be_processed.append((file_path, encoding, base_url))
            print("Done! -- Tamam!")

    print("Beginning to try to fix references, in some cases,")
    print("this could a really long time.")
    print("--------------------------------------------------")
    print("Referansları düzeltme işlemi başlıyor, bu bazen")
    print("bayağı fazla zaman alabilir.")
    print("--------------------------------------------------")

    for file_path, encoding, url in to_be_processed:
        print(file_path, encoding, url)
        print(("Processing - İşleniyor: %s" % file_path))
        with open(file_path, "r") as html_file:
            html_contents = html_file.read()

        a = HTMLReferenceFixer()
        a.setbaseurl(url)
        a.filepath = file_path

        try:
            a.feed(html_contents)
        except HTMLParseError:
            sys.stderr.write("Couldn\'t parse html file, skipping...")
            continue

        with open(file_path, "w") as processed_file:
            processed_file.write(a.output)

if __name__ == "__main__":

    try:
        initial_url = sys.argv[1]
    except IndexError:
        initial_url = input("Lütfen giriş url\'ini giriniz: ")
    main(initial_url)
