##WARNING
##THIS SCRIPT IS DEPRECIATED
##
##IT IS MUCH SLOWER THAN MULTITHREADING
##IT IS INCLUDED IN CASE IT IS NEEDED FOR A SPECIFIC USE CASE
##
##FOR DETAILED COMMENTS SEE MULTITHREADING.PY, CODE IS VERY SIMILAR


import spotipy
from spotipy.oauth2 import SpotifyOAuth
from rpi_ws281x import *
import time
from matplotlib import cm
import math

# LED strip configuration:
LED_COUNT = 200       # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
# True to invert the signal (when using NPN transistor level shift)
LED_INVERT = False

# Use your own spotify dev data below!
# set open_browser=False to prevent Spotipy from attempting to open the default browser, authenticate with credentials
scope = "user-read-playback-state"
client_id = "111111111111111111111111111111"
client_secret = "99999999999999999999999999999"
redirect_uri = "http://example.com"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(open_browser=False,client_id=client_id,client_secret=client_secret,redirect_uri=redirect_uri,scope=scope))

class Spotify():
    #object for all spotify functions and conversion to color/brightness

    def __init__(self):
        #initalize variables
        self.toAnalyze = "0"
        self.current_track_id = "0"
        self.progress_ms = "0"
        self.current_segment = 0
        self.currently_playing = "0"
        self.is_playing = False
        self.rgb_list = []
        self.full_loop_time = 0
        
    def run(self):
        #calls getStatus(), runAnalysis(), linearSearch(), getCurrentData()
        #searches for current segment from analysis
        #spotify revolves around this function
        while True:
            start = time.time()
            Spotify.getStatus()
            #print("Progress: ", Spotify.progress_ms)
            if self.is_playing:
                Spotify.current_track_segment_list = Spotify.runAnalysis(Spotify.current_track_id)
                #print(Spotify.current_track_segment_list)
                if Spotify.current_track_segment_list is not None:
                    Spotify.current_segment = Spotify.linearSearch(Spotify.current_track_segment_list, Spotify.progress_ms+(self.full_loop_time*1000), Spotify.current_segment)
                    #print("Current segment: ",Spotify.current_segment)
                    if Spotify.current_segment > 0:
                        Spotify.getCurrentData(Spotify.current_track_segment_list, Spotify.current_segment)
                        self.sendToLights(self.brightness, self.rgb)
                        self.full_loop_time = time.time() - start
                        print("time to full loop is: ", self.full_loop_time)
                    else:
                        print("invalid current segment")
                    
    def getStatus(self):
        #check for currently playing status, track, and progress in track
        currently_playing = sp.current_user_playing_track()
        if currently_playing["is_playing"]==True and currently_playing["currently_playing_type"]=="track":
            Spotify.current_track_id = currently_playing["item"]["id"]
            Spotify.progress_ms = currently_playing["progress_ms"]
            #print("Current track: ",Spotify.current_track_id)
            self.is_playing = True
        else:
            self.is_playing = False
            print("No song playing!")
            self.clearColor(strip)
            time.sleep(2) #if no song playing, time.sleep

    def runAnalysis(self, track_id):
        #check if last analyzed song is still playing, if not then send analysis request
        if Spotify.toAnalyze != track_id:
            Spotify.toAnalyze = track_id
            current_track_analysis = sp.audio_analysis(Spotify.toAnalyze)
            print("New analysis requested: ",Spotify.toAnalyze)
            Spotify.current_track_segment_list = current_track_analysis["segments"]
            time.sleep(.5)
            return Spotify.current_track_segment_list
        else:
            return Spotify.current_track_segment_list


    def linearSearch(self, seg_list, progress, current_segment_index=0):
        #search for current segment linearly starting from last known location
        for i in range(current_segment_index, len(seg_list)):
            if seg_list[i]["start"] < progress/1000 and (seg_list[i]["start"] + seg_list[i]["duration"]) > progress/1000:
                return i
        return -1
        print("Linear search error! progress_ms not in track data")

    def getCurrentData(self, segment_list, segment):
        #collects data from current segment
        current_pitches = segment_list[segment]["pitches"]
        current_timbre = segment_list[segment]["timbre"]
        current_loudness = segment_list[segment]["loudness_max"]
        #convert data to readable for lights
        self.rgb = Spotify.convertTimbre(current_timbre)
        self.brightness = Spotify.convertBrightness(current_loudness)
        #print(self.brightness)
        #print(self.rgb)

    def convertTimbre(self, timbre):
        #colormap timbre values to be loaded to strip
        #set timbre between 0 and 1
        #print(timbre[1])
        timbre_conv = 1 / (1 + math.exp(-timbre[1]/45))
        #print(timbre_conv)
        #convert timbre_conv to rgb using rainbow color map
        rgb = ([round(x*255) for x in cm.gist_rainbow(float(timbre_conv))[:3]])
        return rgb

    def convertBrightness(self, current_loudness=0):
        #convert negative loudness to 0-255 brightness
        return (1.05**(float(current_loudness)-1)+.05)*255
    
    def sendToLights(self, brightness, rgb):
        #show color data on lights
        start = time.time()
        #loop 3 times to duplicate each color value in list
        for _ in range(3):
            #queue rgb to list
            self.rgb_list.append([rgb[0],rgb[1],rgb[2]])

            #shorten rgb_list to strip length
            if len(self.rgb_list) > strip.numPixels():
                self.rgb_list.pop(0)

            #set strip brightness
            if int(brightness) > 255:
                brightness = 255
            strip.setBrightness(int(brightness))

            #send strip colors
            for i, vals in enumerate(reversed(self.rgb_list)):
                strip.setPixelColor(i, Color(vals[0], vals[1], vals[2]))
            strip.show()
            light_loop_time = time.time() - start
            print("time to light loop is: ", light_loop_time)
            print("loop time difference is: ", self.full_loop_time - light_loop_time)

    def clearColor(self, strip):
        #clear color across display a pixel at a time
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0,0,0))
            strip.show()

#intialize strip
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)

# Intialize the library (must be called once before other functions).
strip.begin()

#initialize class object
Spotify = Spotify()

#start loop
Spotify.run()
