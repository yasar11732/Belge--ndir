# -*- coding: utf-8 -*-
"""
Bu dosyada, indirici tarafından kullanılan bazı HTTP yardımcıları
bulunur.
-----------------------------------------------------------------------
This file holds some HTTP utilies to be used by downloader.
"""
import logging

from urlparse import urlparse
from httplib import HTTPConnection, ResponseNotReady
from socket import setdefaulttimeout

setdefaulttimeout(5)


httputillogger = logging.getLogger("http-utils")
httputillogger.setLevel(logging.DEBUG)

fh = logging.FileHandler("httputils.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

fh.setFormatter(formatter)
fh.setLevel(logging.DEBUG)

httputillogger.addHandler(fh)





try:
    from httplib import HTTPSConnection
    ssl = True
except ImportError:
    ssl = False

def getHeadResponse(url,response_cache = {}):
    """
    İlk argüman olarak verilen adrese HEAD istemi yaparak, aldığı yanıtı
    döndürür. Yaptığı istemleri önbellekleme yapar. O yüzden eğer binlerce
    farklı adres için kullanılacaksa, fazla ram kullanmaya başlayabilir.
    Eğer önbelleği boşaltmak gerekirse, getHeadResponse("",{}) komutuyla,
    önbellek silinebilir. Ancak, çok gerekli değilse, bunun yapılması tavsiye
    olunmaz.
    ---------------------------------------------------------------------------
    Takes an url as string, tries to make an HEAD request
    and returns the response of the request. Caches responses,
    so only one request per page made in a particular runtime.
    This function may return None if an error occurs.
    """
    try:
        a = response_cache[url]
        httputillogger.debug("Returning headers for %s from cache" % url)
        return a

    except KeyError:

        url = urlparse(url)
        if url.scheme == "http":
            conn = HTTPConnection(url.netloc, timeout=2)
        elif url.scheme == "https" and ssl:
            conn = HTTPSConnection(url.netloc, timeout=2)
        else:
            httputillogger.warning("No compatipable schema for head request, returning none: %s" % url.geturl())
            return None
        try:
            conn.request("HEAD", url.path)
            response = conn.getresponse()
        except:
            httputillogger.warning("Unknown error occured while trying to make a HEAD request, return None: %s" % url.geturl())
            response = None
        
        if response:
            httputillogger.info("Caching HEAD response for %s" % url.geturl())
            response_cache[url.geturl()] = response
        return response
    
def getHeader(url, header):
    """
    İlk argüman olarak verilen adrese HTTP HEAD isteği yaparak, istenen HTTP
    başlığını döndürür.
    ----------------------------------------------------------------------------
    Takes two strings as arguments. first argument spesifies the page and second
    argument spesifies requested header. Returns None if an error occurs.
    """
    response = getHeadResponse(url)
    return response and response.getheader(header)

def getContentType(url):
    """
    Verilen url'in içerik türünü döndürür. (text/html gibi.)
    ------------------------------------------------------------
    Returns content type of given url.
    """

    contentType = getHeader(url, "Content-type")
    return contentType and contentType.split(";")[0]

def getFinalUrl(url,already_seen = None):
    """
    HTTP yönlendirmelerini takip ederek, en son varılan url'i bulur ve onu
    döndürür. Eğer dairesel yönlerdirmeye rastlanırsa, dairesel yönlerdirmeyi
    başlatan url döndürülür. Opsiyonel olarak ikinci bir argüman verilebilir.
    Bu argüman verilirse, elemanları url adresleri olmalıdır. Bu adresler, ilk
    argümanla verilen adrese direk veya dolaylı olarak yönlendirme yapmış
    olarak değerlendirilir.
    --------------------------------------------------------------------------
    Navigates through redirections to get final url. If some url redirects
    to another url that has been previously seen, this is considered as
    circular redirection, and url that start circular redirection is returned.
    For example, in following scnerio, "c" is returned
    a -> b -> c -> b
    This is because "c" starts a circular redirection.

    If this function gets called with optional second argument, this argument
    have to be a list, and need to contain urls that will be considered as
    list of pages that directly of indirectly redirected to given url.
    """

    if already_seen is None:
        already_seen = [url]
    
    response = getHeadResponse(url)
    if response:
        if str(response.status).startswith("3"):
            location = response.getheader("location")
            if location in already_seen:
                return location
            else:
                already_seen.append(location)
            return getFinalUrl(location, already_seen)
    return url

def getEncoding(url):
    """
    Verilen sayfanın karakter kodlamasını bulur. Karakter kodlaması her sayfa
    için bulunamayabilir. Bulunamazsa None döndürür.
    -------------------------------------------------------------------------
    Gets character encoding for a given page. Probably only defined for
    text/html content-type. If no charset info found, returns None.    
    """
    content = getHeader(url,"Content-type")
    httputillogger.debug("content type for %s is %s" % (url,content))
    try:
        key, equals, value = content.split(";")[1].partition("=")

    except IndexError:
        httputillogger.debug("There is no \";\" in content")
        return
    
    if key.strip() == "charset":
        httputillogger.debug("Found charset returning %s" % value.strip())
        return value.strip()
    httputillogger.debug("Couldn\'t get encoding from http headers.")
    return None

def urlok(url):
    """
    Bu sayfaya yapılan HTTP/HTTPS istemi başarılıysa, True, değilse False
    döndürür.
    ----------------------------------------------------------------------
    Returns True if response status for this url starts with 2, otherwise
    returns False. 2xx HTTP status codes means success.
    """
    response = getHeadResponse(url)
    if str(response.status).startswith("2"):
        return True
    else:
        return False
