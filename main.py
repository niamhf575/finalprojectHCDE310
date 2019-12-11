
import webapp2, os, urllib2, json, urllib
import jinja2

import logging

#sources for icons & other citations on aboutPage.html

lastfmapikey = #your key here
darkskykey= #your key here

#function to call the DarkSky API, returns the day's weather as the url for one of my weather icons
def getWeather(lat,lng,date):
    key = darkskykey
    baseurl =  'https://api.darksky.net/forecast/%s/%s,%s,%s?exclude=currently,minutely,hourly'%(key,lat,lng,date)
    try:
        s = json.load(urllib2.urlopen(baseurl))["daily"]["data"][0]["icon"]+".png"
        return "assets/"+s
    except:
        logging.error("Couldn't call getWeather")


#function to call last.fm
def getlastfm(method="artist.search", params={}, datatype="json"):
    try:
        base = "http://ws.audioscrobbler.com/2.0/?"
        params['api_key'] = lastfmapikey
        params['method']=method
        params['format']=datatype
        logging.debug(params)
        params = urllib.urlencode(params)
        url = base+params
        f= urllib2.urlopen(url)
        f = f.read()
        f = json.loads(f)
        return f
    except:
        logging.error("Couldn't call getlastfm.")

#returns the album cover of the artist's most popular album as a png
def getArtistPNG(artist):
    f = getlastfm(method="artist.getTopAlbums", params={"artist": artist})["topalbums"]["album"][0]["image"][2]["#text"]
    return f

#returns the last.fm page url for the artist
def getArtistURL(artist):
    f = getlastfm(method = "artist.getInfo", params={"artist":artist})["artist"]["url"]
    logging.error(artist)
    return f

#creates a list of tracks the user listened to, where each track is a dictionary
def getPages(pages, user):
    list=[]
    for i in range(pages):
        page = getlastfm(method='user.getRecentTracks', params={"user": user, "limit": "200", "page": str(i + 1)}) #max limit 200
        list.append(page["recenttracks"]["track"])
    return list

#sorts artist listens by date
def sortByDate(history, dict={}):
    for listen in history:
        if "date" in listen:
            date = listen["date"]["#text"][:11]
            dict[date] = dict.get(date,{})
            dict[date][listen["artist"]["#text"]]= dict[date].get(listen["artist"]["#text"],0)+1
    return dict

#a timestamp for each date
def timestampsForDates(history,dict={}):
    for listen in history:
        if "date" in listen:
            date = listen["date"]["#text"][:11]
            dict[date] = listen["date"]["uts"]
    return dict

#this takes in the listening history once it has
#been sorted by day and sorts it by weather
def sortbyWeather(sortedHistory,timesDict, lat, long):
    final={}
    for date in sortedHistory:
        weather = getWeather(date=timesDict[date], lat=lat, lng=long)
        final[weather]=final.get(weather,{})
        for artist in sortedHistory[date]:
            final[weather][artist]=final[weather].get(artist,0)+sortedHistory[date][artist]
    return final

#this gets 10 pages of listening history
#and returns a dictionary of that listening history
#sorted by weather. this goes back 2000 tracks, but try 20 or 50 pages if you can
def getResults(username,lat,long):
    results = getPages(10, username)
    dict={}
    times={}
    for result in results:
        dict=sortByDate(result, dict)
        times=timestampsForDates(result,times)
    return sortbyWeather(dict,times,lat,long)

#getTop5 takes a last.fm username, latitude, and longitude, then returns a dictionary of
#the top 5 artists for each weather
def getTop5(username, lat,long):
    try:
        sortedByWeather = getResults(username,lat,long)
        top5 = {}
        for weather in sortedByWeather:
            top5[weather] = {"artists":[], "images":[]}
            listArtistCounts=[(artist,sortedByWeather[weather][artist])for artist in sortedByWeather[weather]]
            listArtistCounts=sorted(listArtistCounts, key=lambda artist:artist[1], reverse=True)
            for i in range(5):
                if i<len(listArtistCounts):
                    top5[weather]["artists"].append(listArtistCounts[i][0])
            top5[weather]["images"] = [(getArtistPNG(artist.encode("utf-8"))) for artist in top5[weather]["artists"]]
            top5[weather]["artists"] = [(artist, getArtistURL(artist.encode("utf-8"))) for artist in top5[weather]["artists"]]
        if None in top5:
            top5.pop(None)
        return top5
    except:
        logging.error("Couldn't call getTop5")
        return None

#code for generating web pages:

JINJA_ENVIRONMENT = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class MainHandler(webapp2.RequestHandler):
    def get(self):
        temp_vals = {}
        template = JINJA_ENVIRONMENT.get_template('searchform.html')
        self.response.write(template.render(temp_vals))

    def post(self):
        temp_vals = {}
        username = self.request.get('username')
        lat = self.request.get('latitude')
        long = self.request.get('longitude')
        temp_vals["top5"] = getTop5(username=username, lat=lat, long=long)
        temp_vals["username"] = username
        if temp_vals["top5"]:
            template = JINJA_ENVIRONMENT.get_template('resultsform.html')
            self.response.write(template.render(temp_vals))
        else:
            temp_vals["warning"] = "There was an issue with your request. Please try again."
            template = JINJA_ENVIRONMENT.get_template('searchform.html')
            self.response.write(template.render(temp_vals))

class AboutHandler(webapp2.RequestHandler):
    def get(self):
        temp_vals = {}
        template = JINJA_ENVIRONMENT.get_template('aboutPage.html')
        self.response.write(template.render(temp_vals))



application = webapp2.WSGIApplication([ \
                                          ('/about', AboutHandler),
                                          ('/.*', MainHandler)
                                      ],
                                     debug=True)


