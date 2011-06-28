from urlparse import urlparse, urljoin
from BeautifulSoup import BeautifulSoup
import urllib2

def makeLinksAbsolute(soup,attr):
    #TODO urljoin domain to relative URLs in all href and src attributes on img and a tags
    # as well as in any url() statements within CSS. This includes the href of any <link> tags
    #with CSS that we will be downloading in the next step
    link_tags = soup.findAll(href=True)
    for link_tag in link_tags:
        print str(link_tag)
        parsed = urlparse(link_tag[attr]) #TODO case sensetive, fix this
        if parsed.scheme == '': #Check if it is relative or absolute
            link_tag[attr] = urljoin(page_url,link_tag[attr]) 

f =  urllib2.urlopen('http://localhost/~alexhofsteede/csstest.html')
soup = BeautifulSoup(f.read()) 
makeLinksAbsolute(soup,'href')
