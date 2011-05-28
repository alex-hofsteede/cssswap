from urlparse import urlparse, urljoin
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render_to_response, redirect, get_object_or_404
from models import Page, CSSAsset
from django.template import RequestContext
import re
import util

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
        page = util.processpage(page_url)
        if page != None:
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
    html = re.sub(util.delimiter+r'([0-f]+)'+util.delimiter,replacementText,page.raw)
    return HttpResponse(html)
