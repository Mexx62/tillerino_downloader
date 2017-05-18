#! python2

import re
import urllib
import urllib2
import cookielib
import time
import zipfile
import os
import datetime
import shutil
import irclib
import ircbot
import pyglet
import ConfigParser
import sys

config = ConfigParser.RawConfigParser()
config.read('settings.cfg')
try:
    downloadRankedMaps = config.get('Settings', 'download-ranked-maps')
    downloadNonRankedMaps = config.get('Settings', 'download-non-ranked-maps')
    username = config.get('Infos', 'username')
    password = config.get('Infos', 'password')
    irc_pw = config.get('Infos', 'irc_pw')
    path = config.get('Infos', 'path_to_osu')
    path_copy = config.get('Infos', 'copy_path')
    copy = config.get('Settings', 'copy')
    download_video = config.get('Settings', 'download-video')
    user = config.get('Settings', 'user-download-from-pm')
    user = user.replace(' #separated like user1;user2', '')
    user = user.split(';')
    only_download_from_pm = config.get('Settings', 'only-download-from-pm')
except ConfigParser.NoSectionError:
    config.add_section('Settings')
    config.add_section('Infos')
    with open('settings.cfg', 'wb') as configfile:
        config.write(configfile)
    config.set('Settings', 'download-ranked-maps', '1')
    config.set('Settings', 'download-non-ranked-maps', '1')
    config.set('Settings', 'copy', '0')
    config.set('Settings', 'download-video', '0')
    config.set('Settings', 'user-download-from-pm', 'Tillerino #separated like user1;user2')
    config.set('Settings', 'only-download-from-pm', '1')
    config.set('Infos', 'path_to_osu', 'C:\\path\\to\\osu!\\Songs\\')
    config.set('Infos', 'copy_path', 'D:\\osz\\backup\\folder\\')
    config.set('Infos', 'username', '')
    config.set('Infos', 'password', '')
    config.set('Infos', 'irc_pw', '')
    with open('settings.cfg', 'wb') as configfile:
        config.write(configfile)
    sys.exit('Please fill the settings.sfg file with your infos and preferences!')
except ConfigParser.NoOptionError:
    sys.exit('Please fill the settings.sfg file with your infos and preferences!')


def formatted(line):
    split = line.split()
    return '{:0>6}'.format(str(split[0]))


def findbeatmap(id):
    with open(path + 'beatmaplist.txt', 'r') as f:
        listid = f.readlines()
        if formatted(listid[int(id)]) == formatted(id):
            return 1
        else:
            return 0


def formatdate(date):  # Apr 15, 2015 to 2015-04-15, I guess there's a better way to do this though
    ranked = Bot.datetokeep
    month = ranked[:3]
    endofdate = ranked[3:]
    if month == 'Jan':
        date = 'January' + endofdate
    elif month == 'Feb':
        date = 'February' + endofdate
    elif month == 'Mar':
        date = 'March' + endofdate
    elif month == 'Apr':
        date = 'April' + endofdate
    elif month == 'May':
        date = 'May' + endofdate
    elif month == 'Jun':
        date = 'June' + endofdate
    elif month == 'Jul':
        date = 'July' + endofdate
    elif month == 'Aug':
        date = 'August' + endofdate
    elif month == 'Sep':
        date = 'September' + endofdate
    elif month == 'Oct':
        date = 'October' + endofdate
    elif month == 'Nov':
        date = 'November' + endofdate
    elif month == 'Dec':
        date = 'December' + endofdate
    return datetime.datetime.strptime(date, '%B %d, %Y').date().isoformat()


def needtoupdate(newdate, id):  # returns 1 if newdate is more recent than the date linked to the id in beatmaplist.txt
    with open(path + 'beatmaplist.txt', 'r') as f:
        listid = f.readlines()
        try:
            olddate = listid[int(id)].split()[1]
        except IndexError:
            print("No previous date registered -> I'm downloading the map to be sure it's updated")
            return 1  # downloads if no date written in beatmaplist.txt
    print('Comparing old/new ' + olddate + ' ' + newdate)
    olddate = formatdate(olddate)
    oldyear = olddate.split('-')[0]
    newyear = newdate.split('-')[0]
    if newyear > oldyear:
        return 1
    oldmonth = olddate.split('-')[1]
    newmonth = newdate.split('-')[1]
    if newmonth > oldmonth:
        return 1
    oldday = olddate.split('-')[2]
    newday = newdate.split('-')[2]
    if newday > oldday:
        return 1
    return 0


class Bot(ircbot.SingleServerIRCBot):
    def __init__(self):
        ircbot.SingleServerIRCBot.__init__(self, [("irc.ppy.sh", 6667, irc_pw)], username, username, 60)
        cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        authentication_url = 'https://osu.ppy.sh/forum/ucp.php?mode=login'
        logindata = {
            'autologin': 'on',
            'login': 'login',
            'password': password,
            'redirect': '/forum/',
            'sid': '',
            'username': username
        }
        data = urllib.urlencode(logindata)
        responselogin = self.opener.open(authentication_url, data)
        responselogin2 = responselogin.read()
        if re.findall('incorrect password.', responselogin2):
            print "Incorrect password."
        else:
            print "I'm now connected at " + time.strftime("%c")
        if not os.path.isfile(
                        path + 'beatmaplist.txt'):  # if no beatmaplist.txt file, create it and fill it with either the IDs or 000000 if you don't have the map
            with open(path + 'beatmaplist.txt', 'wb+') as self.beatmaps:
                list = next(os.walk(path))[1]
                Bot.list2 = ['000000'] * 999999
                for elements in list:
                    try:
                        Bot.list2[int(formatted(elements))] = formatted(elements)
                    except ValueError:
                        pass
                for rows in Bot.list2:
                    self.beatmaps.write(str(rows) + '\n')

    def on_pubmsg(self, serv, ev):
        auteur = irclib.nm_to_n(ev.source())
        message = ev.arguments()[0]
        channel = ev.target()
        id = re.findall('http://osu.ppy.sh/[sb]/([0-9]+)', message)
        songmap = re.findall('(/b/|/s/)', message)
        eternalslumber = re.findall('.+ (has been revived from eternal slumber)', message)
        if id and not only_download_from_pm:
            print time.strftime("%c") + " " + channel + ": " + auteur + ":"
            print "     " + message
            print "id: " + id[0]
            url = 'http://osu.ppy.sh' + songmap[0] + id[0]
            print url
            response = self.opener.open(url)
            html = response.read()
            if download_video == '0':
                Bot.downloadid = re.findall('/d/([0-9]+n?)">', html)
            else:
                Bot.downloadid = re.findall('/d/([0-9]+)">', html)
            if not Bot.downloadid:
                print("Beatmap isn't found")
                return
            Bot.updatedate = re.findall(
                'Updated:\n</td>\n<td class="colour">\n\w{3} \d{1,2}, \d{4}<br/>\n(\w{3} \d{1,2}, \d{4})\n</td>', html)
            Bot.rankeddate = re.findall(
                'Ranked:\n</td>\n<td class="colour">\n\w{3} \d{1,2}, \d{4}<br/>\n(\w{3} \d{1,2}, \d{4})\n</td>', html)
            print "download ID with array: " + Bot.downloadid[0]
            if Bot.rankeddate:
                print('Beatmap ranked in : ' + Bot.rankeddate[0])
                Bot.datetokeep = Bot.rankeddate[0]
                if downloadRankedMaps == '0':
                    print('Map ranked, aborting download.\n')
                    return
            if Bot.updatedate:
                print('Beatmap updated in : ' + Bot.updatedate[0])
                Bot.datetokeep = Bot.updatedate[0]
                if downloadNonRankedMaps == '0':
                    print('Map not ranked, aborting download\n')
                    return
            if ((eternalslumber == [] and findbeatmap(id[0]) == 0) or needtoupdate(formatdate(Bot.datetokeep),
                                                                                   id[0]) == 1):
                downloadlink = 'http://osu.ppy.sh/d/' + Bot.downloadid[0]
                print 'Downloading at ' + time.strftime("%c") + " because bancho"
                sound = pyglet.resource.media('gos.wav')
                sound.play()
                response2 = self.opener.open(downloadlink)
                data = response2.read()
                with open(path + id[0] + '.osz', 'wb') as beatmap:
                    beatmap.write(data)
                print 'Download completed at ' + time.strftime("%c")
                info = os.stat(path + id[0] + '.osz')
                size = info.st_size
                if size < 1000000:
                    os.remove(path + id[0] + '.osz')
                    downloadlink = 'http://bloodcat.com/osu/s/' + Bot.downloadid[0]
                    print("Download failed, i'm downloading the map on Bloodcat")
                    response2 = urllib2.urlopen(downloadlink)
                    data = response2.read()
                    with open(path + id[0] + '.osz', 'wb') as beatmap:
                        beatmap.write(data)
                    if data == "* File not found or inaccessible!":
                        print("Filenot found on Bloodcat, i'm giving up")
                with zipfile.ZipFile(path + id[0] + '.osz', 'r') as zf:
                    for file in zf.namelist():
                        test = re.findall('(.+?)\([^\(]+?\) \[.+?\].osu', file)
                        if test: break
                print "file name and artist: " + test[0][:-1]
                os.rename(path + id[0] + '.osz', path + id[0] + ' ' + test[0][:-1] + '.osz')
                print 'file rename completed'
                if copy == 1:
                    shutil.copyfile(path + id[0] + ' ' + test[0][:-1] + '.osz', path_copy + id[0] + '.osz')
                print('Download to file completed\n')
                sound = pyglet.resource.media('sound.wav')
                sound.play()
                with open(path + 'beatmaplist.txt', 'r+') as self.beatmaps:
                    ids = self.beatmaps.readlines()
                    if Bot.rankeddate:
                        ids[int(formatted(id[0]))] = formatted(id[0]) + ' ' + formatdate(Bot.datetokeep) + '\n'
                    i = 0
                    self.beatmaps.seek(0)
                    for _ in ids:
                        self.beatmaps.write(str(ids[i]))
                        i += 1
                print('date written to beatmaplist\n')
            else:
                print "you have this map already.\n"
                sound = pyglet.resource.media('sound.wav')
                sound.play()

    def on_action(self, serv, ev):
        auteur = irclib.nm_to_n(ev.source())
        message = ev.arguments()[0]
        channel = ev.target()
        id = re.findall('http://osu.ppy.sh/[sb]/([0-9]+)', message)
        songmap = re.findall('(/b/|/s/)', message)
        if id and not only_download_from_pm:
            print time.strftime("%c") + " " + channel + ": " + auteur + ": ACTION"
            print "*" + auteur + " " + message + "*"
            url = 'http://osu.ppy.sh' + songmap[0] + id[0]
            response = self.opener.open(url)
            html = response.read()
            if download_video == '0':
                Bot.downloadid = re.findall('/d/([0-9]+n?)">', html)
            else:
                Bot.downloadid = re.findall('/d/([0-9]+)">', html)
            if not Bot.downloadid:
                print("Beatmap isn't found")
                return
            Bot.updatedate = re.findall(
                'Updated:\n</td>\n<td class="colour">\n\w{3} \d{1,2}, \d{4}<br/>\n(\w{3} \d{1,2}, \d{4})\n</td>', html)
            Bot.rankeddate = re.findall(
                'Ranked:\n</td>\n<td class="colour">\n\w{3} \d{1,2}, \d{4}<br/>\n(\w{3} \d{1,2}, \d{4})\n</td>', html)
            if Bot.rankeddate:
                print('Beatmap ranked in : ' + Bot.rankeddate[0])
                Bot.datetokeep = Bot.rankeddate[0]
                if downloadRankedMaps == '0':
                    print('Map ranked, aborting download.\n')
                    return
            if Bot.updatedate:
                print('Beatmap updated in : ' + Bot.updatedate[0])
                Bot.datetokeep = Bot.updatedate[0]
                if downloadNonRankedMaps == '0':
                    print('Map not ranked, aborting download.\n')
                    return
            if (findbeatmap(id[0]) == 0 or needtoupdate(formatdate(Bot.datetokeep), id[0])) == 1:
                downloadlink = 'http://osu.ppy.sh/d/' + Bot.downloadid[0]
                print 'Downloading at ' + time.strftime("%c")
                sound = pyglet.resource.media('gos.wav')
                sound.play()
                response2 = self.opener.open(downloadlink)
                data = response2.read()
                with open(path + id[0] + '.osz', 'wb') as beatmap:
                    beatmap.write(data)
                print 'Download completed at ' + time.strftime("%c")
                info = os.stat(path + id[0] + '.osz')
                size = info.st_size
                if size < 1000000:
                    os.remove(path + id[0] + '.osz')
                    downloadlink = 'http://bloodcat.com/osu/s/' + Bot.downloadid[0]
                    print("Download failed, i'm downloading the map on Bloodcat")
                    response2 = urllib2.urlopen(downloadlink)
                    data = response2.read()
                    with open(path + id[0] + '.osz', 'wb') as beatmap:
                        beatmap.write(data)
                    if data == "* File not found or inaccessible!":
                        print("File not found on Bloodcat, i'm giving up.")
                with zipfile.ZipFile(path + id[0] + '.osz', 'r') as zf:
                    for file in zf.namelist():
                        test = re.findall('(.+?)\([^\(]+?\) \[.+?\].osu', file)
                        if test: break
                print "file name and artist: " + test[0][:-1]
                os.rename(path + id[0] + '.osz', path + id[0] + ' ' + test[0][:-1] + '.osz')
                if copy == 1:
                    shutil.copyfile(path + id[0] + ' ' + test[0][:-1] + '.osz', path_copy + id[0] + '.osz')
                    print('Copy completed')
                sound = pyglet.resource.media('sound.wav')
                sound.play()
                with open(path + 'beatmaplist.txt', 'r+') as self.beatmaps:
                    ids = self.beatmaps.readlines()
                    if Bot.rankeddate:
                        ids[int(formatted(id[0]))] = formatted(id[0]) + ' ' + formatdate(Bot.datetokeep) + '\n'
                    i = 0
                    self.beatmaps.seek(0)
                    for rows in ids:
                        self.beatmaps.write(str(ids[i]))
                        i += 1
                print('date written to beatmaplist\n')
            else:
                print "you have this map already.\n"
                sound = pyglet.resource.media('sound.wav')
                sound.play()

    def on_privmsg(self, serv, ev):
        auteur = irclib.nm_to_n(ev.source())
        message = ev.arguments()[0]
        channel = ev.target()
        if auteur in user:
            id = re.findall('http://osu.ppy.sh/[sb]/([0-9]+)', message)
            songmap = re.findall('(/b/|/s/)', message)
            if id:
                print time.strftime("%c") + " " + channel + ": " + auteur + ":"
                print "     " + message
                print "id: " + id[0]
                url = 'http://osu.ppy.sh' + songmap[0] + id[0]
                print url
                response = self.opener.open(url)
                html = response.read()
                if download_video == '0':
                    Bot.downloadid = re.findall('/d/([0-9]+n?)">', html)
                else:
                    Bot.downloadid = re.findall('/d/([0-9]+)">', html)
                if not Bot.downloadid:
                    print("Beatmap isn't found")
                    return
                Bot.rankeddate = re.findall(
                    'Ranked:\n</td>\n<td class="colour">\n\w{3} \d{1,2}, \d{4}<br/>\n(\w{3} \d{1,2}, \d{4})\n</td>', html)
                print "download ID with array: " + Bot.downloadid[0]
                if Bot.rankeddate:
                    print('Beatmap ranked in : ' + Bot.rankeddate[0])
                    Bot.datetokeep = Bot.rankeddate[0]
                    if downloadRankedMaps == '0':
                        print('Map ranked, aborting download.\n')
                        return
                if findbeatmap(id[0]) == 0 or needtoupdate(formatdate(Bot.datetokeep), id[0]) == 1:
                    downloadlink = 'http://osu.ppy.sh/d/' + Bot.downloadid[0]
                    print 'Downloading at ' + time.strftime("%c")
                    sound = pyglet.resource.media('gos.wav')
                    sound.play()
                    response2 = self.opener.open(downloadlink)
                    data = response2.read()
                    with open(path + id[0] + '.osz', 'wb') as beatmap:
                        beatmap.write(data)
                    print 'Download completed at ' + time.strftime("%c")
                    info = os.stat(path + id[0] + '.osz')
                    size = info.st_size
                    if size < 1000000:
                        os.remove(path + id[0] + '.osz')
                        downloadlink = 'http://bloodcat.com/osu/s/' + Bot.downloadid[0]
                        print("Download failed, i'm downloading the map on Bloodcat")
                        response2 = urllib2.urlopen(downloadlink)
                        data = response2.read()
                        with open(path + id[0] + '.osz', 'wb') as beatmap:
                            beatmap.write(data)
                        if data == "* File not found or inaccessible!":
                            print("File not found on Bloodcat, i'm giving up")
                            os.remove(path + id[0] + '.osz')
                    with zipfile.ZipFile(path + id[0] + '.osz', 'r') as zf:
                        for file in zf.namelist():
                            test = re.findall('(.+?)\([^\(]+?\) \[.+?\].osu', file)
                            if test: break
                    print "file name and artist: " + test[0][:-1]
                    os.rename(path + id[0] + '.osz', path + id[0] + ' ' + test[0][:-1] + '.osz')
                    print 'file rename completed'
                    if copy == 1:
                        shutil.copyfile(path + id[0] + ' ' + test[0][:-1] + '.osz', path_copy + id[0] + '.osz')
                        print('Copy completed\n')
                    sound = pyglet.resource.media('sound.wav')
                    sound.play()
                    with open(path + 'beatmaplist.txt', 'r+') as self.beatmaps:
                        ids = self.beatmaps.readlines()
                        if Bot.rankeddate:
                            ids[int(formatted(id[0]))] = formatted(id[0]) + ' ' + formatdate(Bot.datetokeep) + '\n'
                        i = 0
                        self.beatmaps.seek(0)
                        for _ in ids:
                            self.beatmaps.write(str(ids[i]))
                            i += 1
                    print('date written to beatmaplist\n')
                else:
                    print "you have this map already.\n"
                    sound = pyglet.resource.media('sound.wav')
                    sound.play()

    def on_welcome(self, serv, ev):
        serv.join('#announce')
        print 'you have joined #announce'
        serv.join('#osu')
        print 'you have joined #osu'
        serv.join('#taiko')
        print 'you have joined #taiko'
        serv.join('#mania')
        print 'you have joined #mania'
        serv.join('#ctb')
        print 'you have joined #ctb'
        serv.join('#multiplayer')
        print 'you have joined #multiplayer'
        serv.join('#videogames')
        print 'you have joined #videogames'
        serv.join('#spectator')
        print 'you have joined #spectator'
        serv.join('#modhelp')
        print 'you have joined #modhelp'
        serv.join('#modreqs')
        print 'you have joined #modreqs'
        serv.join('#help')
        print 'you have joined #help'


if __name__ == "__main__":
    Bot().start()
    pyglet.app.run()
