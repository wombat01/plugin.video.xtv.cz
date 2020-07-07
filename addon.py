# -*- coding: utf-8 -*-
import os
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import urllib2
import re
import time
import datetime
import json
from bs4 import BeautifulSoup
import requests

_useragent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, lkodiazor Gecko) Chrome/52.0.2743.116 Safari/537.36'

_baseurl = 'https://xtv.cz/'
_showurl = 'https://xtv.cz/archiv/'

_scriptname = xbmcaddon.Addon('plugin.video.xtv.cz').getAddonInfo('name')
        
def log(msg, level=xbmc.LOGDEBUG):
    if type(msg).__name__ == 'unicode':
        msg = msg.encode('utf-8')
    xbmc.log("[%s] %s" % (_scriptname, msg.__str__()), level)

def logDbg(msg):
	log(msg,level=xbmc.LOGDEBUG)

def logErr(msg):
	log(msg,level=xbmc.LOGERROR)

def fetchUrl(url):
    logDbg("fetchUrl " + url)
    httpdata = ''
    try:
        request = urllib2.Request(url, headers={'User-Agent': _useragent})
        resp = urllib2.urlopen(request)
        httpdata = resp.read().decode('utf-8')
    except:
        httpdata = None
    finally:
        resp.close() 
    return httpdata

def listShows():
    addDir('Nejnovější', 'url', '0', '', 2)
    soup = BeautifulSoup(fetchUrl(_baseurl+'porady'), 'html.parser')
    porady = soup.find_all('a', {'class': 'nav-link scroll-to'})
    
    for porad in porady:
        if porad.get('data-target'):
            url = porad.get('data-target')
            name = porad.text
            detail = soup.find('div', {'id': url, 'class': 'porad-wrapper'})
            thumb = detail.find('img', {'class': 'porad-logo'})['src']
            id = detail.find('div', {'class': 'porad-toggle'})
            id = str(re.search('\((\d+)\)', str(id.get('ng-click'))).group(1))
            addDir(name, url, id, thumb, 1)      

def listItems(id, page):
    dataurl = "https://xtv.cz/api/v2/loadmore?type=articles&ignore_ids=&page="+str(page)+"&porad="+str(id)+"&_="+str(int(time.time()))   
    data = json.loads(fetchUrl(dataurl))

    if (not data):
        return

    for item in data[u'items']:
        date = datetime.datetime(*(time.strptime(item[u'published_at'], "%Y-%m-%d %H:%M:%S")[:6])).strftime("%Y-%m-%d")
        if item[u'host']:
            title = item[u'host']
            desc = item[u'title']
            dur = item[u'duration']
            thumb = item[u'cover']
            url = _showurl+item[u'slug']
            
            if dur and ':' in dur:
                l = dur.strip().split(':')
                duration = 0
                for pos, value in enumerate(l[::-1]):
                    duration += int(value) * 60 ** pos
                    
            info={'duration':duration,'date':date}
            addResolvedLink(title, url, thumb, desc, info)
    if int(data[u'is_more'])>0:        
        p = page + 1
        u = sys.argv[0]+'?mode=1&url=next&id='+urllib.quote_plus(str(id.encode('utf-8')))+'&page='+urllib.quote_plus(str(p))
        liNext = xbmcgui.ListItem("Další")
        xbmcplugin.addDirectoryItem(handle=addonHandle,url=u,listitem=liNext,isFolder=True)

def videoLink(url): 
    soup = BeautifulSoup(fetchUrl(url), 'html.parser')
    
    title = soup.find("meta", property="og:description")
    desc = soup.find("meta", property="og:title")
    streams = soup.find("source", {"type":"video/mp4"})
    stream_url=streams['src']
        
    liz = xbmcgui.ListItem()
    liz = xbmcgui.ListItem(path=stream_url)
    liz.setInfo('video', {'title': title[u"content"], 'plot' : desc[u"content"]})
    liz.setProperty("isPlayable", "true")
    xbmcplugin.setResolvedUrl(handle=addonHandle, succeeded=True, listitem=liz)
    
def addDir(name,url,id,image,mode):
    u=sys.argv[0]+"?url="+urllib.quote_plus(url.encode('utf-8'))+"&id="+urllib.quote_plus(str(id.encode('utf-8')))+"&mode="+str(mode)+"&name="+urllib.quote_plus(name.encode('utf-8'))
    ok=True
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=image)   
    liz.setInfo( type="Video", infoLabels={ "Title": name } )
    ok=xbmcplugin.addDirectoryItem(handle=addonHandle,url=u,listitem=liz,isFolder=True)
    return ok
    
def addResolvedLink(name, url, image, desc, info={}):
    u=sys.argv[0]+"?url="+urllib.quote_plus(url.encode('utf-8'))+"&mode=10&name="+urllib.quote_plus(name.encode('utf-8'))+"&desc="+urllib.quote_plus(desc.encode('utf-8'))
    ok=True
    
    liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=image)   

    if info['duration']:
        liz.addStreamInfo('video', {'duration': info['duration']})
    liz.setThumbnailImage(image)
    liz.setProperty('IsPlayable', 'true')
    liz.setInfo('video', {'mediatype': 'episode', 'title': name, 'plot': desc, 'premiered': info['date']})
    liz.setProperty('fanart_image', image)
    ok=xbmcplugin.addDirectoryItem(handle=addonHandle, url=u, listitem=liz, isFolder=False)
    return ok
    
def get_params():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
        params=sys.argv[2]
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2:
                param[splitparams[0]]=splitparams[1]
    return param

addonHandle=int(sys.argv[1])
params=get_params()
url=None
id=None
name=None
thumb=None
mode=None
page=0

xbmcplugin.setContent(addonHandle, 'episodes')

try:
    url=urllib.unquote_plus(params["url"])
except:
    pass
    
try:
    id=urllib.unquote_plus(params["id"])
except:
    pass

try:
    name=urllib.unquote_plus(params["name"])
except:
    pass
    
try:
    mode=int(params["mode"])
except:
    pass
    
try:
    page=int(urllib.unquote_plus(params["page"]))
except:
    pass

if mode==None or url==None or len(url)<1:
    listShows()
    logDbg("listShows()")
elif mode==1:
    listItems(id,page)
    logDbg("listItems()")
elif mode==2:
    listItems(str(0),page)
    logDbg("listNewest()")
elif mode==10:
    videoLink(url)
    logDbg("videoLink()")
    
xbmcplugin.endOfDirectory(addonHandle)
