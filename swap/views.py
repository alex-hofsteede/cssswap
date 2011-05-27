from urlparse import urlparse, urljoin
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render_to_response, redirect, get_object_or_404
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
            #Check if urlparse can find a scheme for us, if not, we just put http:// in front
            parsed = urlparse(page_url)
            if parsed.scheme == '':
                page_url = 'http://'+page_url
            f =  urllib2.urlopen(page_url) #TODO rate limit this or find some way to stop ourselves from being used as a DOS tool
        except urllib2.HTTPError, error:
            return render_to_response('error.html',{'message':error.code}) 
        page_content = f.read()
        page = Page.create()
        page.url = page_url
        page.original = page_content
        page.save()
        #TODO urljoin domain to relative URLs in all href and src attributes on img and a tags
        # as well as in any url() statements within CSS
        soup = BeautifulSoup(page_content)
        css_assets = []

        #Grabs any <link> tags that point to stylesheets, downloads and saves the 
        #linked stylesheet, and replaces the link with our own custom link
        css_link_tags = soup.findAll("link",{'rel':re.compile('stylesheet',re.I)})
        for css_link_tag in css_link_tags:
            css_url = urljoin(page_url,css_link_tag['href'])
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
        return redirect("/editpage/%d" % page.id)
    return HttpResponse('fail')#TODO return something good 

def getCSS(request,uuid):
    css = get_object_or_404(CSSAsset,uuid=uuid)
    return HttpResponse(css.raw)

#TODO protect with token in cookie (that gets generated in getpage). Don't want to allow anyone to edit pages, only the person that originally got it
def editpage(request,page_id):
    page = Page.objects.get(pk=page_id) #TODO use uuids
    stylesheets = CSSAsset.objects.filter(page=page.id)
    return render_to_response('edit.html', {'page':page,'stylesheets':stylesheets}, context_instance=RequestContext(request))

#TODO move util functions like this out of views. 
def getCSSByUUID(uuid):
    return CSSAsset.objects.get(uuid=uuid)

def savepage(request,page_id):
#TODO all kinds of checks / tests needed here so we don't get pwned
    if request.method == 'POST':
        for key,value in request.POST.items():
            match = re.search(r'cssasset_([0-f]+)',key)
            if match:
                css_asset = getCSSByUUID(match.group(1))
                if css_asset:
                    css_asset.raw = value
                    css_asset.save()
    return redirect("/showpage/%s" % page_id)

def showpage(request,page_id):
    page = get_object_or_404(Page,pk=page_id)
    def replacementText(match):
        return getCSSByUUID(match.group(1)).raw
    html = re.sub(delimiter+r'([0-f]+)'+delimiter,replacementText,page.raw)
    return HttpResponse(html)
