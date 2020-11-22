# -*- coding: utf-8 -*-
import routing
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import re
import time
import datetime
import json
from bs4 import BeautifulSoup
import requests

_addon = xbmcaddon.Addon()

plugin = routing.Plugin()

_baseurl = 'https://xtv.cz/'
_apiurl = 'https://xtv.cz/api/v3/'

@plugin.route('/list_shows/')
def list_shows():
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    soup = BeautifulSoup(get_page(_baseurl+'porady'), 'html.parser')
    porady = soup.find_all('a', {'class': 'nav-link scroll-to'})
    listing = []
    for porad in porady:
        if porad.get('data-target') != 'archiv':
            url = porad.get('data-target')
            name = porad.text
            info = soup.find('div', {'id': url, 'class': 'porad-wrapper'}).find("div", {'class': 'porad-info'})
            desc = info.find('div', {'class': 'porad-popis'}).get_text()
            thumb = info.find('img', {'class': 'porad-logo'})['src']
            show_id = str(re.search('\((\d+)\)', str(info.find('div', {'class': 'porad-toggle'}).get('ng-click'))).group(1))

            list_item = xbmcgui.ListItem(label=name)
            list_item.setInfo('video', {'mediatype': 'tvshow', 'title': name, 'plot': desc})
            list_item.setArt({'poster': thumb})
            listing.append((plugin.url_for(get_list, show_id = show_id, category = 2, page = 0), list_item, True))

    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30004))
    list_item.setArt({'icon': 'DefaultFolder.png'})
    listing.append((plugin.url_for(list_archive), list_item, True))

    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/list_archive/')
def list_archive():
    xbmcplugin.setContent(plugin.handle, 'tvshows')
    porady_dict = json.loads(get_page(_apiurl+'shows'))
    soup = BeautifulSoup(get_page(_baseurl+'porady'), 'html.parser')
    porady = soup.find('div', {'class': 'porady-archiv-list'}).find_all('div', {'class': 'porad-wrapper'})
    listing = []
    for porad in porady:
        url = porad.get('id')
        show_title = (list([x for x in porady_dict if x['slug'] == url]))[0]['title']
        info = soup.find('div', {'id': url, 'class': 'porad-wrapper'}).find("div", {'class': 'porad-info'})
        desc = info.find('div', {'class': 'porad-popis'}).get_text()
        thumb = info.find('img', {'class': 'porad-logo'})['src']
        show_id = str(re.search('\((\d+)\)', str(info.find('div', {'class': 'porad-toggle'}).get('ng-click'))).group(1))

        list_item = xbmcgui.ListItem(show_title)
        list_item.setInfo('video', {'mediatype': 'tvshow', 'title': show_title, 'plot': desc})
        list_item.setArt({'poster': thumb})
        listing.append((plugin.url_for(get_list, show_id = show_id, category = 2, page = 0), list_item, True))

    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/get_list/')
def get_list():
    xbmcplugin.setContent(plugin.handle, 'episodes')
    show_id = plugin.args['show_id'][0] if 'show_id' in plugin.args else ''
    page = int(plugin.args['page'][0] if 'page' in plugin.args else 0)
    category = int(plugin.args['category'][0] if 'category' in plugin.args else 0)
    porady_dict = json.loads(get_page(_apiurl+'shows'))
    data = json.loads(get_page(_apiurl+'loadmore?type=articles&ignore_ids=&page='+str(page)+'&porad='+show_id+'&_='+str(int(time.time()))))
    count = 0
    listing = []
    for item in data[u'items']:
        if item[u'host'] and item[u'premium'] == 0:
            host = item[u'host'].strip()
            desc = item[u'title'].strip()
            perex = item[u'perex'].strip()
            dur = item[u'duration']
            thumb = item[u'cover']
            slug_url = item[u'slug']
            slug_show = item[u'porad']
            show_title = (list([x for x in porady_dict if x['slug'] == slug_show]))[0]['title']
            title = item[u'perex'].strip() if item[u'perex'] else item[u'host']
            title_label = title
            if category == 1:
                title_label = '[COLOR blue]{0}[/COLOR] · {1}'.format(show_title, title)
            date = datetime.datetime(*(time.strptime(item[u'published_at'], "%Y-%m-%d %H:%M:%S")[:6])).strftime("%Y-%m-%d")
            if dur:
                l = dur.strip().split(':')
                duration = 0
                for pos, value in enumerate(l[::-1]):
                    duration += int(value) * 60 ** pos
            list_item = xbmcgui.ListItem(title_label)
            list_item.setInfo('video', {'mediatype': 'episode', 'tvshowtitle': show_title, 'title': title, 'plot': desc, 'duration': duration, 'premiered': date})
            list_item.setArt({'icon': thumb})
            list_item.setProperty('IsPlayable', 'true')
            listing.append((plugin.url_for(get_video, slug_show = slug_show, slug_url = slug_url), list_item, False))
            count +=1
    if int(data[u'is_more']) > 0 and count>0:
        list_item = xbmcgui.ListItem(label=_addon.getLocalizedString(30003))
        list_item.setArt({'icon': 'DefaultFolder.png'})
        listing.append((plugin.url_for(get_list, show_id = show_id, category = 1, page = page + 1), list_item, True))

    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/get_video/')
def get_video():
    soup = BeautifulSoup(get_page('{0}{1}/{2}'.format(_baseurl, plugin.args['slug_show'][0], plugin.args['slug_url'][0])), 'html.parser')
    stream_url = soup.find("source", {"type":"video/mp4"})['src']
    list_item = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedUrl(plugin.handle, True, list_item)
    xbmcplugin.endOfDirectory(plugin.handle)

@plugin.route('/')
def root():
    listing = []
    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30001))
    list_item.setArt({'icon': 'DefaultRecentlyAddedEpisodes.png'})
    listing.append((plugin.url_for(get_list, show_id = 0, category = 1, page = 0), list_item, True))

    list_item = xbmcgui.ListItem(_addon.getLocalizedString(30002))
    list_item.setArt({'icon': 'DefaultTVShows.png'})
    listing.append((plugin.url_for(list_shows), list_item, True))

    xbmcplugin.addDirectoryItems(plugin.handle, listing, len(listing))
    xbmcplugin.endOfDirectory(plugin.handle)

def get_page(url):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0'})
    return r.content

def run():
    plugin.run()
