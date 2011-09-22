"""
This file holds various parsers to be used by downloader.py
"""
import os
import posixpath

from urlparse import ParseResult, urlsplit, urlunsplit,uses_params, \
     _splitparams, urljoin
from HTMLParser import HTMLParser
from HTTPutils import getFinalUrl
from sys import stderr

class AdvancedParseResult(ParseResult):
    "Adds getUrlWithoutFragments method to urlparse.ParseResult"
    def getUrlWithoutFragments(self):
        scheme, netloc, url, params, query, fragment = self
        if params:
            url = "%s;%s" % (url, params)
        return urlunsplit((scheme, netloc, url, query, ""))

def myurlparse(url, scheme="", allow_fragments=True):
    "Almost same as urlparse.urlparse. It returns AdvancedParseResult instead"
    tuple = urlsplit(url, scheme, allow_fragments)
    scheme, netloc, url, query, fragment = tuple
    if scheme in uses_params and ';' in url:
        url, params = _splitparams(url)
    else:
        params = ''
    return AdvancedParseResult(scheme, netloc, url, params, query, fragment)

class LinkCollector(HTMLParser):
    """
    Parses a html and gets references. This includes anchors, stylesheets,
    external scripts and images.
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
    a.setbaseurl("someurl") # use this method! don't directly set it.
    a.filepath = "filepath"

    This class will convert full urls to relatives if target exists in
    file system. Otherwise, this will convert all links to full urls.

    Handles "a", "script","link" and "img" html tags.
    Get output from output property after feeding.
    """

    def setbaseurl(self,url):
        self.baseurl = myurlparse(url)
        self.downloaddir = os.path.join(os.getcwd(),
                                        self.baseurl.netloc).replace(".","_")

    def feed(self,data):
        if hasattr(self,"baseurl") and hasattr(self,"filepath"):
            return HTMLParser.feed(self,data)
        else:
            raise AcayipError("You have to fill in baseurl and filepath attrs \
                first.")

    def reset(self):
        self.output = ""
        HTMLParser.reset(self)

    def relurl(self,url):
        """Calculates relative url from self.baseurl to url argument.
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
        return posixpath.relpath(target,start=base_dir)

    def fixlink(self,link):
        """
        This method is used for correcting references in anchors, scripts,
        styles and images. If referenced file exists locally, a relative link
        returned. Otherwise, a full url returned. HTML redirections cannot fool
        us, since we are checking them! :)
        """
        linked_target = urljoin(self.baseurl.geturl(),link)
        try:
            real_target = myurlparse(getFinalUrl(linked_target))
        except RuntimeError:
            stderr.write("Failed to get final url for %s" % linked_target)
            return linked_target

        expected_target = real_target
        if real_target.path.endswith("/"):
            expected_target = myurlparse(
                urljoin(
                    real_target.geturl(),"./index.html"))
        
        if real_target.netloc != self.baseurl.netloc:  
            return real_target.geturl()

        target_file = os.path.join(self.downloaddir,
                                   *expected_target.path.split("/"))
        if expected_target.path.endswith("/"):
            target_file = os.path.join(target_file,"index.html")

        if os.path.isfile(target_file):
            return self.relurl(expected_target)
        else:
            return real_target.geturl()

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
        self.output += "<!" + data + ">"

    def handle_charref(self,data):
        self.output += "&#" + data + ";"
        

    def handle_entityref(self,data):
        self.output += "&" + data + ";"

    def handle_comment(self,data):
        self.output += "<!--" + data + "-->"

    def handle_pi(self,data):
        self.output += "<?" + data + ">"



