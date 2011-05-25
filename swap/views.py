from urlparse import urlparse, urljoin
from django.http import HttpResponse
from django.shortcuts import render_to_response
from models import Page, CSSAsset
import urllib2
from django.template import RequestContext
from BeautifulSoup import BeautifulSoup
import re

delimiter = '--REPLACE--'

def index(request):
    return render_to_response('index.html',{}, context_instance=RequestContext(request))

def createCSSAsset(content,page,url=''):
    css_asset = CSSAsset.create()
    css_asset.url = url
    css_asset.original = content
    css_asset.raw = content
    css_asset.page = page
    css_asset.save()
    return css_asset 

def getpage(request):
    if request.method == 'POST':
        page_url = request.POST['url']
        try:
            f =  urllib2.urlopen(page_url) 
        except urllib2.HTTPError, error:
            return render_to_response('error.html',{'message':error.code}) 
        page_content = f.read()
        page = Page.create()
        page.url = page_url
        page.original = page_content
        page.save()
        #TODO add domain to relative URLs in href and src
        soup = BeautifulSoup(page_content)
        css_link_tags = soup.findAll("link",{'rel':re.compile('stylesheet',re.I)})
        css_assets = []
        for css_link_tag in css_link_tags:
            css_url = urljoin(page_url,css_link_tag['href'])
            try:
                f = urllib2.urlopen(css_url)
            except urllib2.HTTPError, error:
                continue
            css_content = f.read()
            css_assets.append(createCSSAsset(css_content,page,css_url))

        css_style_tags = soup.findAll('style')
        for css_style_tag in css_style_tags:
            css_content = css_style_tag.string #TODO check that this is indeed a single string 
            css_asset = createCSSAsset(css_content,page)
            css_assets.append(css_asset)
            css_style_tag.string.replaceWith( delimiter + css_asset.uuid + delimiter )

        css_inline_style_tags = soup.findAll(style=True)
        for css_inline_style_tag in css_inline_style_tags:
            css_content = css_inline_style_tag['style']
            css_assets.append(createCSSAsset(css_content,page))
        
        #save all the replacements to the page
        page.raw = unicode(soup)
        page.save()

        return render_to_response('edit.html', {'page':page,'stylesheets':css_assets}, context_instance=RequestContext(request))
    return '' 

#TODO move util functions like this out of views. 
def getCSSByUUID(uuid):
    return CSSAsset.objects.get(uuid=uuid)

def savepage(request,page_id):
#TODO all kinds of checks / tests needed here so we don't get pwned
    if request.method == 'POST':
        for key,value in request.POST.items():
            match = re.search(r'cssasset_([a-fA-F0-9]+)',key)
            if match:
                css_asset = getCSSByUUID(match.group(1))
                if css_asset:
                    css_asset.raw = value
                    css_asset.save()
    return showpage(request,page_id)#TODO redirect to named view here

def showpage(request,page_id):
    page = Page.objects.get(pk=page_id) #TODO check for error 
    def replacementText(match):
        return getCSSByUUID(match.group(1)).raw
    html = re.sub(delimiter+r'([a-fA-F0-9]+)'+delimiter,replacementText,page.raw)
    return HttpResponse(html)
