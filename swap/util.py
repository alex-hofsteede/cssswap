from urlparse import urlparse, urljoin
from BeautifulSoup import BeautifulSoup, ICantBelieveItsBeautifulSoup, MinimalSoup, BeautifulStoneSoup
import urllib2
from models import Page, CSSAsset
import re

delimiter = '--REPLACE--'

def createCSSAsset(content,page,url=''):
    css_asset = CSSAsset.create()
    css_asset.url = url
    css_asset.original = content
    css_asset.raw = content
    css_asset.page = page
    css_asset.save()
    return css_asset 

def makeLinksAbsolute(soup, attr, root_url):
    link_tags = soup.findAll(attrs={attr:True})
    for link_tag in link_tags:
        link_tag[attr] = urljoin(root_url,link_tag[attr]) 

def makeCSSURLsAbsolute(css_content,root_url):
    regex = re.compile('''\surl\(\s*['"]?([^'"()]+)['"]?\s*\)''',re.I)
    def replace(match):
        print "matched %s : making absolute" % match.group(0)
        return ' url("'+urljoin(root_url,match.group(1))+'")'
    return regex.sub(replace,css_content)

def processPage(page_url):
    try:
        #Check if urlparse can find a scheme for us, if not, we just put http:// in front
        parsed = urlparse(page_url)
        if parsed.scheme == '':
            page_url = 'http://'+page_url
        f =  urllib2.urlopen(page_url) #TODO rate limit this or find some way to stop ourselves from being used as a DOS tool
    except urllib2.HTTPError, error:
        raise error
        return None
    page_content = f.read()
    page = Page.create()
    page.url = page_url
    page.original = page_content
    page.save()
    soup = MinimalSoup(page_content)
    css_assets = []
    makeLinksAbsolute(soup, 'href', page_url)
    makeLinksAbsolute(soup, 'src', page_url)
    parseLinkedStylesheets(soup, css_assets, page)
    parseStyleTags(soup, css_assets, page)
    parseStyleAttributes(soup, css_assets, page)
    
    #save all the replacements to the page
    page.raw = unicode(soup)
    page.save()
    return page

def parseStyleAttributes(soup, css_assets, page):
    #Grabs any style="" attributes on normal html tags and saves the CSS therein.
    #replace with uuid, same as above
    css_inline_style_tags = soup.findAll(style=True)
    for css_inline_style_tag in css_inline_style_tags:
        css_content = css_inline_style_tag['style']
        css_asset = createCSSAsset(css_content,page)
        css_assets.append(css_asset)#TODO css_assets is not necessary anymore but perhape we can save cycles by passing it diretly to editpage instead of having to get that all from the DB again
        css_inline_style_tag['style'] =  delimiter + css_asset.uuid + delimiter 


def parseStyleTags(soup, css_assets, page):
    #Grabs any <style> tags and saves the CSS therein. replaces with a
    #uuid that we can then regex out later and replace with modified css
    css_style_tags = soup.findAll('style')
    for css_style_tag in css_style_tags:
        css_content = css_style_tag.string #TODO check that this is indeed a single string 
        css_content = makeCSSURLsAbsolute(css_content,css_url)
        css_asset = createCSSAsset(css_content,page)
        css_assets.append(css_asset)
        css_style_tag.string.replaceWith( delimiter + css_asset.uuid + delimiter )
        parseNestedStylesheets(css_asset, css_assets, page)


def parseLinkedStylesheets(soup, css_assets, page):
    #Grabs any <link> tags that point to stylesheets, downloads and saves the 
    #linked stylesheet, and replaces the link with our own custom link
    css_link_tags = soup.findAll("link",{'rel':re.compile('stylesheet',re.I)})
    for css_link_tag in css_link_tags:
        css_url = css_link_tag['href']
        try:
            f = urllib2.urlopen(css_url)
        except urllib2.HTTPError, error:
            continue
        css_content = f.read()
        css_content = makeCSSURLsAbsolute(css_content,css_url)
        css_asset = createCSSAsset(css_content,page,css_url)
        css_assets.append(css_asset)
        css_link_tag['href'] = '/css/%s' % css_asset.uuid #No need to save a delimited value to regex out later. the link to /css/{uuid} will be constant
        parseNestedStylesheets(css_asset, css_assets, page)

def parseNestedStylesheets(css_asset, css_assets, page):
    #Ideally we would have had just 1 group matching the URL, with everything else in lookaheads
    # and lookbehinds, unfortunately the lookbehind has to be fixed width and we are matching a
    #variable amount of whitespace. So group(1) is everything between the @import and the actual URL
    #and group(2) is the URL
    regex = re.compile(r'''(?<=@import)(\s+url\(\s*['"]?)([^'"()]+)(?=['"]?\))''',re.I)
    def fetchAndCreateCSS(match):
        css_url = match.group(2)
        try:
            f = urllib2.urlopen(css_url)
        except urllib2.HTTPError, error:
            return match.group(0)
        css_content = f.read()
        css_content = makeCSSURLsAbsolute(css_content,css_url)
        css_sub_asset = createCSSAsset(css_content, page, css_url)
        css_assets.append(css_sub_asset)
        return match.group(1) + '/css/%s' % css_sub_asset.uuid
    css_asset.raw = regex.sub(fetchAndCreateCSS,css_asset.raw)
    css_asset.save()


