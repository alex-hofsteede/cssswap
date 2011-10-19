"""
This is another updated version of the parsing logic using the lxml.html parser which has a lot of nice things we
need/want
"""

from urlparse import urlparse, urljoin
#from BeautifulSoup import BeautifulSoup, ICantBelieveItsBeautifulSoup, MinimalSoup, BeautifulStoneSoup
import urllib2, re, time
from models import Page, CSSAsset, CachedPage
from datetime import datetime

import lxml.html

delimiter = '--REPLACE--'
css_types = {"STYLESHEET":1,"INLINE":2,"ATTRIBUTE":3}
re_namespace = "http://exslt.org/regular-expressions"

t1 = -1
def mark(name=None):
    """
    Timing function
    """
    global t1
    if t1 == -1:
        t1 = time.time()
    else:
        t2 = time.time()
        print "%s took %0.3f ms" % (name,(t2-t1) * 1000)
        t1 = t2

def clear():
    global t1
    t1 = -1

def processPage(page_url):
    """
    Main entry point in this class, Grabs a web page given a URL and parses out all the styles, 
    creating classes for each one
    """
    mark()
    try:
        #Check if urlparse can find a scheme for us, if not, we just put http:// in front
        parsed = urlparse(page_url)
        if parsed.scheme == '':
            page_url = u'http://'+ unicode(page_url)
    except:
        return None
    try:
        cached_page = CachedPage.objects.get(url=page_url)
        page_content = cached_page.original
        #print "fetched cached page %d" % cached_page.id
    except: #TODO what is the error we are catching? Not Found?
        try:
            mark("check cache")
            f =  urllib2.urlopen(page_url) #TODO rate limit this or find some way to stop ourselves from being used as a DOS tool
            page_content = unicode(f.read(),'utf-8')
            #Create a cached page that we can fetch by URL later
            cached_page = CachedPage()
            cached_page.url = page_url
            cached_page.original = page_content
            cached_page.date = datetime.now()
            cached_page.save()
            mark("download page")
            #print "saved cached page %d" % cached_page.id
        except urllib2.HTTPError, error:
            raise error
            return None
    page = Page.create()
    page.url = page_url
    page.original = page_content
    page.save()
    css_stylesheets = []
    css_tags = []
    
    doc_tree = lxml.html.document_fromstring(page_content).getroottree()

    mark("save page")
    makeLinksAbsolute(doc_tree, page_url)
    mark("make links absolute")
    parseStyleAttributes(doc_tree, css_tags, page)
    mark("parse style attributes")
    parseStyleTags(doc_tree, css_stylesheets, page)
    mark("parse style tags")
    parseLinkedStylesheets(doc_tree, css_stylesheets, page)
    mark("parse linked stylesheets")
    clear()

    #save all the replacements to the page
    page.raw = lxml.html.tostring(doc_tree)
    page.save()
    return page

def parseStyleAttributes(doc_tree, css_tags, page):
    """
    Grabs any style="" attributes on normal html tags and saves the CSS therein.
    Replaces the style with a delimited UUID tag that we can use later to re-insert the style
    """
    tags = doc_tree.xpath('//*[@style]') #TODO check this xpath expression, and check that it handles all the spacing variants style = style=' etc. 
    for tag in tags:
        css_content = tag.attrib['style'].strip(" ")
        css_name = getPath(tag) 
        css_asset = createCSSAsset(css_content, page, css_types['ATTRIBUTE'], name=css_name)
        css_tags.append(css_asset)#TODO css_tags is not necessary anymore but perhape we can save cycles by passing it diretly to editpage instead of having to get that all from the DB again
        tag.attrib['style'] = delimiter + css_asset.uuid + delimiter 
    
def parseStyleTags(doc_tree, css_stylesheets, page):
    """
    Grabs any <style> tags and saves the CSS therein. replaces with a
    uuid that we can use later to re-insert the style. 
    """
    tags = doc_tree.xpath('//style')#TODO there was an issue here with a double nested style tag, how can we get only the inner one?
    for tag in tags:
        css_content = tag.text_content()
        css_asset = createCSSAsset(css_content, page, css_types['INLINE'], name='<style/>')
        css_stylesheets.append(css_asset)
        parseNestedStylesheets(css_asset, css_stylesheets, page)
        tag.text = delimiter + css_asset.uuid + delimiter 

def parseLinkedStylesheets(doc_tree, css_stylesheets, page):
    """
    Grabs any <link> tags that point to stylesheets, downloads and saves the 
    linked stylesheet, and replaces the link to our own saved version
    """
    tags = doc_tree.xpath('//link[re:test(@rel, "^stylesheet$", "i") and @href]',namespaces={'re':re_namespace})
    for tag in tags:
        css_url = tag.attrib['href']
        css_name = urlparse(css_url).path 
        try:
            f = urllib2.urlopen(css_url)
        except urllib2.HTTPError, error:
            print "Failed to open stylesheet at %s" % css_url
            continue
        #TODO other exceptions to handle here, like connection refused. 
        css_content = unicode(f.read(),'utf-8')
        css_content = makeCSSURLsAbsolute(css_content, css_url)
        css_asset = createCSSAsset(css_content, page, css_types['STYLESHEET'], css_url, css_name)
        css_stylesheets.append(css_asset)
        tag.attrib['href'] = u'/css/%s' % css_asset.uuid #No need to save a delimited value to regex out later. the link to /css/{uuid} will be constant
        parseNestedStylesheets(css_asset, css_stylesheets, page)
    

def parseNestedStylesheets(css_asset, css_stylesheets, page):
    """
    Looks through a CSS stylesheet for any @import tags and downloads the imported stylesheets, 
    replacing their reference in the parent stylesheet with the link to our own saved version
    """
    #Group(1) is everything between the @import and the actual URL,
    #group(2) is the URL, and group(3) is any trailing characers
    regex = re.compile(r'''(?<=@import)(\s+(?:url)?\(?\s*['"]?)((?:[^'"()\\]|\\.)*)(['"]?\s*\)?)''',re.I)
    #This replacement function gets called on every match and downloads/parses the stylesheet at that location.
    #TODO we might want to do this asynchronously
    def replace(match):
        css_url = match.group(2)
        css_name = urlparse(css_url).path 
        try:
            f = urllib2.urlopen(css_url)
        except urllib2.HTTPError, error:
            print "Failed to open stylesheet at %s" % css_url
            return match.group(0)
        css_content = unicode(f.read())
        css_content = makeCSSURLsAbsolute(css_content,css_url)
        css_sub_asset = createCSSAsset(css_content, page, css_types['STYLESHEET'], css_url, css_name)
        css_stylesheets.append(css_sub_asset)
        return match.group(1) + u'/css/%s' % css_sub_asset.uuid + match.group(3)
    css_asset.raw = regex.sub(replace,css_asset.raw)
    css_asset.save()

def scrubCSS(css):
    """
    Makes sure CSS doesn't contain any strings that might allow us to get pwned. 
    like closing the style and setting a script tag
    """
    regex = re.compile(r'<\s*/?style',re.I)
#TODO we should really just delete all content after an attempted pwn
#or at least match and remove the whole tag
    return regex.sub('NO PWN, NO PWN, I JUST WANT TO BE ALONE',css) 

def createCSSAsset(content,page,type,url='',name=''):
    """
    Creates a CSSAsset class from the given values
    """
    css_asset = CSSAsset.create()
    css_asset.type = type
    css_asset.url = url
    css_asset.original = content
    css_asset.raw = content
    css_asset.page = page
    css_asset.name = name
    css_asset.save()
    return css_asset 

def makeLinksAbsolute(doc_tree,base_href):
    """
    Makes all links in the document absolute using base_href
    """
    #TODO, this also rewrites all links in css, but we still probably need makeCSSURLsAbsolute for seperate css files
    doc_tree.getroot().make_links_absolute(base_href,True);#TODO do we want to use the resolve_base?

def makeCSSURLsAbsolute(css_content,root_url):
    """
    Looks through a CSS document for any @import or url() rules, and uses urljoin to change the URL 
    into an absolute one
    """
    regex = re.compile(r'''((?:@import\s+(?:url\(?)?|\burl\()\s*['"]?)((?:[^'"()\\]|\\.)*)(['"]?\s*\)?)''',re.I)
    #regex = re.compile(r'''\burl\(\s*['"]?((?:[^'"()\\]|\\.)*)['"]?\s*\)''',re.I)
    def replace(match):
        #print "matched %s : making absolute" % match.group(0)
        return match.group(1) + unicode(urljoin(root_url,match.group(2))) + match.group(3)
    return regex.sub(replace,css_content)

def getPath(element):
    path = ""
    while element != None:
        path = "#%s > %s" % (element.get('id','!'),path)
        element = element.getparent()
    return path
