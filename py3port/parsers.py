# -*- coding: utf-8 -*-
"""
Bu dosyada, indirici tarafından kullanılacak ayrıştırıcılar bulunur.
----------------------------------------------------------------------
This file holds various parsers to be used by downloader.
"""

import os
import posixpath
import logging

from urllib.parse import ParseResult, urlsplit, urlunsplit, uses_params
from urllib.parse import _splitparams, urljoin
from html.parser import HTMLParser
from .HTTPutils import getFinalUrl
from sys import stderr

class AdvancedParseResult(ParseResult):
    """
    urlparse.ParseResult gibidir, ancak fazladan bir metot tanımlar.
    ------------------------------------------------------------
    Adds getUrlWithoutFragments method to urlparse.ParseResult
    """

    def getUrlWithoutFragments(self):
        """
        urllerdeki # işaretinden sonra gelen kısımları atarak döndürür.
        -------------------------------------------------------------
        Removes fragments from url, and returns full url
        """
        scheme, netloc, url, params, query, fragment = self
        if params:
            url = "%s;%s" % (url, params)
        return urlunsplit((scheme, netloc, url, query, ""))

def myurlparse(url, scheme="", allow_fragments=True):
    """
    urlparse.urlparse gibidir, tek farkı, yukarıdaki AdvancedParseResult
    sınıfının bir objesini döndürmesi.
    -------------------------------------------------------------------------
    Almost same as urlparse.urlparse. It returns AdvancedParseResult instead
    """
    tuple = urlsplit(url, scheme, allow_fragments)
    scheme, netloc, url, query, fragment = tuple
    if scheme in uses_params and ';' in url:
        url, params = _splitparams(url)
    else:
        params = ''
    return AdvancedParseResult(scheme, netloc, url, params, query, fragment)

class encodingFinder(HTMLParser):
    """
    Find character encoding from a html file.
    """

    def reset(self):
        self.encoding = None
        HTMLParser.reset(self)

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            our_meta = False
            for k, v in attrs:
                if k == "http-equiv" and v == "content-type":
                    our_meta = True
            for k, v in attrs:
                if k == "content":
                    c_type, charset = v.split(";")
                    key, equals, value = charset.partition("=")

                    if key.rstrip().lstrip() == "charset":
                        self.encoding = value
                    
class LinkCollector(HTMLParser):
    """
    Bir HTML sayfasını ayrıştırır, ve referansları toplar. Şunları içerir:
    <a href="referans"> ...
    <link href="referans"> ...
    <script src="referans"> ...
    <img src="referans"> ...

    Kullanımı:
    >>> a = LinkCollector()
    >>> a.feed("<a href='http://www.google.com/'>asdf</a>")
    >>> a.links
    ['http://www.google.com/']

    Not: HTMLParser.handle_startendtag öntanımlı olarak önce handle_starttag
    sonra handle_endtag çalıştırıyor. Bu yüzden <img src=".." /> çalışıyor. İleride
    bu davranış değiştirse, handle_startendtag'ın üstüne yazmak gerekebilir.
    ----------------------------------------------------------
    Parses a html and gets references. This includes anchors, stylesheets,
    external scripts and images.
    >>> a = LinkCollector()
    >>> a.feed("<a href='http://www.google.com/'>asdf</a>")
    >>> a.links = ['http://www.google.com/']
    """

    def reset(self):
        self.links = []
        HTMLParser.reset(self)

    def handle_starttag(self, tag, attr):
        
        if tag in ("a", "link"):
            key = "href"
        elif tag in ("img", "script"):
            key = "src"
        else:
            return
        try:
            new_link = [v for k, v in attr if k == key][0]
        except IndexError:
            # No referance given ...
            return
        new_link = new_link.split("#")[0]
        if new_link not in self.links:
            self.links.append(new_link)
        
        
class AcayipError(Exception):
    """
    Bildiğin hata...
    -----------------------------------------------------------------
    Raised if HTMLReference Fixer called without proper attributes.
    """
    
class HTMLReferenceFixer(HTMLParser):
    """
    Bir html belgesinideki referansları, gösterilen dosyanın yerel sürücüde
    var olup olmadığını kontrol ederek düzeltir. Bir objesini oluşturulup,
    bir değişkene atandıktan sonra, şu şekilde ayarlanmalıdır:

    >>> a = HTMLReferenceFixer()
    >>> a.setbaseurl("http://birurladresi.com")
    >>> a.filepath = "dosya_yolu"

    Burada, http://birurladresi.com, urlleri çevirirken, bu dosyanın url
    adresi olarak sayacağımız adres. dosya_yolu ise, işlenecek dosyanın
    yerel sürücüde olduğunu varsayacağımız yer. Daha sonra gerekli dosyayı
    açıp, feed metoduyla işleme sokmanız gerekiyor. İşlenmiş halini de "output"
    özelliğinden alabilirsiniz.

    >>> dosya = open(bir_dosya,"r")
    >>> a.feed(dosya.read())
    >>> dosya.close
    >>> dosya = open(bir_dosya,"w")
    >>> dosya.write(a.output)
    >>> dosya.close()
    ---------------------------------------------------------------------------
    After instantiating, set base url and file path like this:
    a = HTMLReferenceFixer()
    a.setbaseurl("someurl") # use this method! don't directly set it.
    a.filepath = "filepath"

    This class will convert full urls to relatives if target exists in
    file system. Otherwise, this will convert all links to full urls.

    Handles "a", "script","link" and "img" html tags.
    Get output from output property after feeding.
    """

    def __getattribute__(self, attr):
        print("Getting attribute %s" % attr)
        return HTMLParser.__getattribute(self, attr)
    
    def setbaseurl(self, url):
        self.baseurl = myurlparse(url)
        self.downloaddir = os.path.join(os.getcwd(),
                                        self.baseurl.netloc).replace(".", "_")

    def feed(self, data):
        if hasattr(self, "baseurl") and hasattr(self, "filepath"):
            return HTMLParser.feed(self, data)
        else:
            raise AcayipError("You have to fill in baseurl and filepath attrs first.")

    def reset(self):
        self.output = ""
        HTMLParser.reset(self)

    def relurl(self, url):
        """
        Argüman olarak verilen url, tam teşekküllü bir url olmalıdır. Bu metot
        objenin temel aldığı adresden, verilen url'e giden, dolaylı yolu bulur.
        Örneğin;
        >>> self.setbaseurl("http://www.google.com/hebel/hubel.mp3")
        >>> self.filepath = "/home/yasar/www.google.com/hebel/hubel.mp3"
        >>> self.relurl("http://www.google.com/")
        ../
        ------------------------------------------------------------------
        Calculates relative url from self.baseurl to url argument.
        >>> self.setbaseurl("http://www.google.com/hebel/hubel.mp3")
        >>> self.filepath = "/home/yasar/www.google.com/hebel/hubel.mp3"
        >>> self.relurl("http://www.google.com/")
        ../
        >>>
        """
        
        if self.baseurl.netloc != url.netloc:
            raise ValueError('target and base netlocs do not match')
        base_dir='.'+posixpath.dirname(self.baseurl.path)
        target='.'+url.path
        return posixpath.relpath(target, start=base_dir)

    def fixlink(self, link):
        """
        Bu sınıfın asıl işi yapan metodu. İşlenecek bütün referanslar, bu metoda
        gönderilir. link argümanıyla gösterilen dosyanın, dosya sisteminde
        nerede bulunması gerektiğini hesaplar, eğer gerçekten orada o dosya
        varsa, objenin baseurl'inden, o dosyaya giden, dolaylı referansı
        döndürür. Eğer bu dosya yerel sürücüde bulunamıyorsa, bahsedilen
        dosyanın internet üzerinde bulunduğu adresi döndürür. Böylece bozuk
        linkler ortadan kaldırılmış olur. Ayrıca, HTTP yönlendirmelerini de
        göz önünde bulundurur.
        ------------------------------------------------------------------------
        This method is used for correcting references in anchors, scripts,
        styles and images. If referenced file exists locally, a relative link
        returned. Otherwise, a full url returned. HTTP redirections cannot fool
        us, since we are checking them! :)
        """
        
        linked_target = urljoin(self.baseurl.geturl(), link)
        try:
            real_target = myurlparse(getFinalUrl(linked_target))
        except RuntimeError:
            stderr.write("Failed to get final url for %s" % linked_target)
            return linked_target

        expected_target = real_target
        if real_target.path.endswith("/"):
            expected_target = myurlparse(
                urljoin(
                    real_target.geturl(), "./index.html"))
        
        if real_target.netloc != self.baseurl.netloc:
            return real_target.geturl()

        target_file = os.path.join(self.downloaddir,
                                   *expected_target.path.split("/"))
        if expected_target.path.endswith("/"):
            target_file = os.path.join(target_file, "index.html")

        if os.path.isfile(target_file):
            return self.relurl(expected_target)
        else:
            return real_target.geturl()

    def fixsrc(self, attrs):
        new_attrs = []

        for k, v in attrs:
            if k == "src":
                v = self.fixlink(v)
            new_attrs.append((k, v))

        return new_attrs

    def fixhref(self, attrs):
        new_attrs = []

        for k, v in attrs:
            if k == "href":
                v = self.fixlink(v)
            new_attrs.append((k, v))

        return new_attrs
        
    def fixattrs(self, tag, attrs):
        if tag in ("a", "link"):
            return self.fixhref(attrs)
        elif tag in ("script", "img"):
            return self.fixsrc(attrs)
        else:
            return attrs


    def handle_starttag(self, tag, attrs):
        
        if tag in ("a", "script", "link", "img"):
            attrs = self.fixattrs(tag, attrs)

        self.output += "<%s" % tag
        for k, v in attrs:
            self.output += " %s=\"%s\"" % (k, v)
        self.output += ">"

    def handle_startendtag(self, tag, attrs):
        
        if tag in ("a", "script", "link", "img"):
            attrs = self.fixattrs(tag, attrs)

        self.output += "<%s" % tag
        for k, v in attrs:
            self.output += " %s=\"%s\"" % (k, v)
        self.output += " />"

    def handle_endtag(self, tag):
        self.output += "</%s>" % tag

    def handle_data(self, data):
        self.output += data

    def handle_decl(self, data):
        self.output += "<!" + data + ">"

    def handle_charref(self, data):
        self.output += "&#" + data + ";"
        

    def handle_entityref(self, data):
        self.output += "&" + data + ";"

    def handle_comment(self, data):
        self.output += "<!--" + data + "-->"

    def handle_pi(self, data):
        self.output += "<?" + data + ">"
