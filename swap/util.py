from urlparse import urlparse, urljoin
from BeautifulSoup import BeautifulSoup, ICantBelieveItsBeautifulSoup, MinimalSoup, BeautifulStoneSoup
import urllib2
from models import Page, CSSAsset, CachedPage
import re
from datetime import datetime

from pygments.lexers import HtmlLexer
from pygments.token import Token, Text, Comment, Operator, Keyword, Name, String, \
     Number, Other, Punctuation, Literal

delimiter = '--REPLACE--'

def createCSSAsset(content,page,url='',name=''):
    css_asset = CSSAsset.create()
    css_asset.url = url
    css_asset.original = content
    css_asset.raw = content
    css_asset.page = page
    css_asset.name = name
    css_asset.save()
    return css_asset 

def makeLinksAbsolute(document, attrs, root_url):
    if type(attrs) is str:
        attrs = [attrs]
    attr_regex = re.compile('|'.join(attrs)+r'\s*=',re.I)
    output_tokens = []
    tokens = HtmlLexer().get_tokens_unprocessed(document)
    for index,token,value in tokens:
        output_tokens.append(value)
        if token == Token.Name.Attribute and attr_regex.match(value):
            index,token,value = tokens.next() # get the attribute value
            output_tokens.append('"'+urljoin(root_url,value.strip("\"' "))+'"')
    return u''.join(output_tokens)

def makeCSSURLsAbsolute(css_content,root_url):
    regex = re.compile(r'''((?:@import\s+(?:url\(?)?|\burl\()\s*['"]?)((?:[^'"()\\]|\\.)*)(['"]?\s*\)?)''',re.I)
    #regex = re.compile(r'''\burl\(\s*['"]?((?:[^'"()\\]|\\.)*)['"]?\s*\)''',re.I)
    def replace(match):
        #print "matched %s : making absolute" % match.group(0)
        return match.group(1) + unicode(urljoin(root_url,match.group(2))) + match.group(3)
    return regex.sub(replace,css_content)

def processPage(page_url):
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
            #Check if urlparse can find a scheme for us, if not, we just put http:// in front
            f =  urllib2.urlopen(page_url) #TODO rate limit this or find some way to stop ourselves from being used as a DOS tool
            page_content = unicode(f.read(),'utf-8')
            #Create a cached page that we can fetch by URL later
            cached_page = CachedPage()
            cached_page.url = page_url
            cached_page.original = page_content
            cached_page.date = datetime.now()
            cached_page.save()
            #print "saved cached page %d" % cached_page.id
        except urllib2.HTTPError, error:
            raise error
            return None
    page = Page.create()
    page.url = page_url
    page.original = page_content
    page.save()
    css_assets = []

    #print page_content
    page_content = makeLinksAbsolute(page_content,[u'href',u'src'], page_url)
    page_content = parseStyleAttributes(page_content, css_assets, page)
    page_content = parseStyleTags(page_content, css_assets, page)
    page_content = parseLinkedStylesheets(page_content, css_assets, page)
    #print page_content

    #save all the replacements to the page
    page.raw = page_content
    page.save()
    return page

def parseTagAttributes(tokens):
    attr_dict = {}
    attr_regex = re.compile(r'([a-zA-Z0-9_:-]+)(\s*=)?')
    end_regex = re.compile(r'(/?\s*>)')
    for index,token,value in tokens:
        if token == Token.Name.Attribute :
            attr_match = attr_regex.match(value)
            if attr_match.group(2):
                index,token,value = tokens.next() # get the attribute value
                attr_dict[attr_match.group(1).lower()] = value.strip("\"' ")
            else:
                attr_dict[attr_match.group(1).lower()] = None
        elif token != Token.Name.Attribute:
            close_match = end_regex.match(value)
            if close_match:
                return (attr_dict,close_match.group(1))

def serializeTagAttributes(attr_dict):
    #TODO is there a way to join with a separator on the beginning and end?
    return " " + " ".join(k + (('="' + v + '"') if v != None else '') for k,v in attr_dict.iteritems()) + " " 

def parseStyleAttributes(document, css_assets, page):
    #Grabs any style="" attributes on normal html tags and saves the CSS therein.
    #replace with uuid, same as above
    attr_regex = re.compile(r'style\s*=',re.I)
    output_tokens = []
    tokens = HtmlLexer().get_tokens_unprocessed(document)
    for index,token,value in tokens:
        output_tokens.append(value)
        if token == Token.Name.Attribute and attr_regex.match(value):
            index,token,value = tokens.next() # get the attribute value
            css_content = value.strip("\"' ")
            css_name = 'style=""'#TODO get the ID attribute from the same tag (could be difficult)
            css_asset = createCSSAsset(css_content, page, name=css_name)
            css_assets.append(css_asset)#TODO css_assets is not necessary anymore but perhape we can save cycles by passing it diretly to editpage instead of having to get that all from the DB again
            output_tokens.append('"' + delimiter + css_asset.uuid + delimiter + '"')
    return "".join(output_tokens)

def parseStyleTags(document, css_assets, page):
    #Grabs any <style> tags and saves the CSS therein. replaces with a
    #uuid that we can then regex out later and replace with modified css
    output_tokens = []
    tokens = HtmlLexer().get_tokens_unprocessed(document)
    intag = False
    instyle = False
    for index,token,value in tokens:
        if not instyle:
            output_tokens.append(value)

        if not intag and token == Token.Name.Tag and re.match(r'<\s*style\s*',value):
            intag = True
        elif intag and token == Token.Name.Tag and re.match(r'\s*>',value):
            intag = False
            instyle = True
            stylesheet_tokens = []
        elif instyle and token == Token.Name.Tag and re.match(r'<\s*/\s*style\s*>',value):
            instyle = False
            css_content = "".join(stylesheet_tokens) 
            css_content = makeCSSURLsAbsolute(css_content,page.url)
            css_asset = createCSSAsset(css_content, page, name='<style/>')
            css_assets.append(css_asset)
            parseNestedStylesheets(css_asset, css_assets, page)
            output_tokens.append( delimiter + css_asset.uuid + delimiter )
            output_tokens.append(value)
        elif instyle:
            stylesheet_tokens.append(value)
    return "".join(output_tokens)


def parseLinkedStylesheets(document, css_assets, page):
    #Grabs any <link> tags that point to stylesheets, downloads and saves the 
    #linked stylesheet, and replaces the link with our own custom link
    output_tokens = []
    tokens = HtmlLexer().get_tokens_unprocessed(document)
    tag_regex = re.compile(r'<\s*link',re.I)
    for index,token,value in tokens:
        output_tokens.append(value)
        if token == Token.Name.Tag and tag_regex.match(value):
            attr_dict,close_tag = parseTagAttributes(tokens)
            if 'href' in attr_dict and attr_dict['href'] and 'rel' in attr_dict and attr_dict['rel'] and attr_dict['rel'].lower() == 'stylesheet':
                css_url = attr_dict['href']
                css_name = urlparse(css_url).path 
                try:
                    f = urllib2.urlopen(css_url)
                except urllib2.HTTPError, error:
                    continue
                #TODO other exceptions to handle here, like connection refused. 
                css_content = unicode(f.read(),'utf-8')
                css_content = makeCSSURLsAbsolute(css_content, css_url)
                css_asset = createCSSAsset(css_content, page, css_url, css_name)
                css_assets.append(css_asset)
                attr_dict['href'] = u'/css/%s' % css_asset.uuid #No need to save a delimited value to regex out later. the link to /css/{uuid} will be constant
                parseNestedStylesheets(css_asset, css_assets, page)
            output_tokens.append(serializeTagAttributes(attr_dict))
            output_tokens.append(close_tag)
    return "".join(output_tokens)



def parseNestedStylesheets(css_asset, css_assets, page):
    #Ideally we would have had just 1 group matching the URL, with everything else in lookaheads
    # and lookbehinds, unfortunately the lookbehind has to be fixed width and we are matching a
    #variable amount of whitespace. So group(1) is everything between the @import and the actual URL
    #and group(2) is the URL, and group(3) is any trailing characers
    regex = re.compile(r'''(?<=@import)(\s+(?:url)?\(?\s*['"]?)((?:[^'"()\\]|\\.)*)(['"]?\s*\)?)''',re.I)
    #This replacement function gets called on every match and downloads/parses the stylesheet 
    #at that location.
    #TODO we might want to do this asynchronously
    def replace(match):
        css_url = match.group(2)
        css_name = urlparse(css_url).path 
        try:
            f = urllib2.urlopen(css_url)
        except urllib2.HTTPError, error:
            return match.group(0)
        css_content = unicode(f.read())
        css_content = makeCSSURLsAbsolute(css_content,css_url)
        css_sub_asset = createCSSAsset(css_content, page, css_url, css_name)
        css_assets.append(css_sub_asset)
        return match.group(1) + u'/css/%s' % css_sub_asset.uuid + match.group(3)
    css_asset.raw = regex.sub(replace,css_asset.raw)
    css_asset.save()


