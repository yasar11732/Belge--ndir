from HTMLParser import HTMLParser
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
