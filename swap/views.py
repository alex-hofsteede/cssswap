from django.http import HttpResponse
from django.shortcuts import render_to_response
from models import Page, CSSAsset
import urllib2
from django.template import RequestContext
from BeautifulSoup import BeautifulSoup
import re

def index(request):
    return render_to_response('index.html',{}, context_instance=RequestContext(request))

def getpage(request):
    if request.method == 'POST':
        page_url = request.POST['url']
        f =  urllib2.urlopen(page_url) 
        page_content = f.read()
        page = Page()
        page.url = page_url
        page.original = page_content
        page.save()
        soup = BeautifulSoup(page_content)
        css_tags = soup.findAll("link",{"rel":re.compile("stylesheet",re.I)})
        css_assets = []
        for css_tag in css_tags:
            css_url = css_tag['href']
            #TODO add domain to relative URLs
            f = urllib2.urlopen(css_url)
            css_content = f.read()
            css_asset = CSSAsset()
            css_asset.url = css_url
            css_asset.original = css_content
            css_asset.page = page
            css_asset.save()
            css_assets.append(css_asset)
        return render_to_response('edit.html', {"styleshets":css_assets}, context_instance=RequestContext(request))
    return '' 

def showpage(request,page_id):
   page = Page.objects.get(pk=page_id) #TODO check for error 
   return HttpResponse(page.original)
