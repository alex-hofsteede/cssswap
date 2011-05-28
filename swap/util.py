from urlparse import urlparse, urljoin
from BeautifulSoup import BeautifulSoup
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

def processpage(page_url):
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
    soup = BeautifulSoup(page_content)
    #TODO urljoin domain to relative URLs in all href and src attributes on img and a tags
    # as well as in any url() statements within CSS. This includes the href of any <link> tags
    #with CSS that we will be downloading in the next step
    href_tags = soup.findAll(href=True)
    for href_tag in href_tags:
        parsed = urlparse(href_tag['href']) #TODO case sensetive, fix this
        if parsed.scheme == '': #Check if it is relative or absolute
            href_tag['href'] = urljoin(page_url,href_tag['href']) 
    css_assets = []

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
        css_asset = createCSSAsset(css_content,page,css_url)
        css_assets.append(css_asset)
        css_link_tag['href'] = '/css/%s' % css_asset.uuid #No need to save a delimited value to regex out later. the link to /css/{uuid} will be constant

    #Grabs any <style> tags and saves the CSS therein. replaces with a
    #uuid that we can then regex out later and replace with modified css
    css_style_tags = soup.findAll('style')
    for css_style_tag in css_style_tags:
        css_content = css_style_tag.string #TODO check that this is indeed a single string 
        css_asset = createCSSAsset(css_content,page)
        css_assets.append(css_asset)
        css_style_tag.string.replaceWith( delimiter + css_asset.uuid + delimiter )

    #Grabs any style="" attributes on normal html tags and saves the CSS therein.
    #replace with uuid, same as above
    css_inline_style_tags = soup.findAll(style=True)
    for css_inline_style_tag in css_inline_style_tags:
        css_content = css_inline_style_tag['style']
        css_asset = createCSSAsset(css_content,page)
        css_assets.append(css_asset)#TODO css_assets is not necessary anymore but perhape we can save cycles by passing it diretly to editpage instead of having to get that all from the DB again
        css_inline_style_tag['style'] =  delimiter + css_asset.uuid + delimiter 
    
    #save all the replacements to the page
    page.raw = unicode(soup)
    page.save()
    return page

