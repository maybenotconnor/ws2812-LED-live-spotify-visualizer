#import modules
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from rpi_ws281x import *
import threading
import time
from matplotlib import cm
import math
import logging
from dotenv import load_dotenv
import os

# LED strip configuration:
LED_COUNT = 300       # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
# True to invert the signal (when using NPN transistor level shift)
LED_INVERT = False

# fill variables below with your own spotify dev info! More info in link in README
scope = "user-read-playback-state"

#credentials loaded from .env
load_dotenv('.env')
client_id = os.environ.get("client_id")
client_secret = os.environ.get("client_secret")
redirect_uri = os.environ.get("redirect_uri")

# Authentication with OAuth2
# set open_browser=False to prevent Spotipy from attempting to open the default browser, useful for headless machines
# modify cache_path to your current working directory or anywhere desired. If it fails to read even after logging into spotify, make sure permissions on the file are set properly.
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(open_browser=False,client_id=client_id,client_secret=client_secret,redirect_uri=redirect_uri,scope=scope,cache_path="/home/pi/python-viz/.cache-spotifyviz"))


class Spotify(threading.Thread):
    '''object for all spotify functions and conversion to color/brightness, 
    call run to initate infinite loop using all functions'''

    def __init__(self):
        #initalize variables
        print("initalizing Spotify class")  
        self.toAnalyze = "0"
        threading.Thread.__init__(self)
        self.current_track_id = "0"
        self.progress_ms = "0"
        self.current_segment = 0
        self.currently_playing = "0"
        #self.is_playing = False
        self.start_time = 0
        self.full_loop_time = 0
        
    def run(self):
        #calls getStatus(), runAnalysis(), linearSearch(), getCurrentData()
        #searches for current segment from analysis
        #spotify revolves around this function
        while True:
            Spotify.getStatus()
            #print("Progress: ", Spotify.progress_ms)
            try:
                Spotify.current_track_segment_list = Spotify.runAnalysis(Spotify.current_track_id)
                #print(Spotify.current_track_segment_list)
                #get current segment using linear search, add ping time to current progress in song
                Spotify.current_segment = Spotify.linearSearch(Spotify.current_track_segment_list, Spotify.progress_ms+(self.full_loop_time*1000), Spotify.current_segment)
                #print("Current segment: ",Spotify.current_segment)
                if Spotify.current_segment > 0:
                    Spotify.getCurrentData(Spotify.current_track_segment_list, Spotify.current_segment)
                    self.full_loop_time = time.time() - self.start_time + Lights.light_loop_time
                    #print("time to loop: ", round(self.full_loop_time,4), " progress: ", self.progress_ms)
                else:
                    pass
            except:
                pass
                    
    def getStatus(self):
        global is_playing
        #check for currently playing status, track, and progress in track
        try:
            currently_playing = sp.current_user_playing_track()
            if currently_playing["is_playing"]==True and currently_playing["currently_playing_type"]=="track":
                Spotify.current_track_id = currently_playing["item"]["id"]
                Spotify.progress_ms = currently_playing["progress_ms"]
                #start ping timer
                self.start_time = time.time()
                #print("Current track: ",Spotify.current_track_id)
                is_playing = True
            else:
                is_playing = False
                logging.warning("No song playing! - Spotify (if-else)")
                time.sleep(1) #if no song playing, time.sleep to save resources - results in delay on starting track
        except:
                is_playing = False
                logging.warning("No song playing! - Spotify (exception)")
                time.sleep(1) #if no song playing, time.sleep to save resources - results in delay on starting track

    def runAnalysis(self, track_id):
        #check if last analyzed song is still playing, if not then send analysis request and reassign variable
        while Spotify.toAnalyze != track_id:
            Spotify.toAnalyze = track_id
            current_track_analysis = sp.audio_analysis(Spotify.toAnalyze)
            print("New analysis requested: ",Spotify.toAnalyze)
            Spotify.current_track_segment_list = current_track_analysis["segments"]
            #wait for api to return data, may not be necessary
            #time.sleep(.5)
            #print(current_track_segment_list)
        return Spotify.current_track_segment_list


    def linearSearch(self, seg_list, progress, current_segment_index=0):
        #search for current segment linearly starting from last known location
        #not using binary search because time is moving forward
        for i in range(current_segment_index, len(seg_list)):
            if seg_list[i]["start"] < progress/1000 and (seg_list[i]["start"] + seg_list[i]["duration"]) > progress/1000:
                return i
        logging.error("Linear search error! progress_ms not in track data") #this error rarely occurs, defaults to zero
        return -1
        

    def getCurrentData(self, segment_list, segment):
        #collects data from current segment
        #a segment is typically a single note, less than a second
        #spotify api uses 12 unbounded values for pithes and timbres, based on match confidence compared to predefined parameters
        #current_pitches = segment_list[segment]["pitches"]
        current_timbre = segment_list[segment]["timbre"]
        #loudness measured in -dB 
        current_loudness = segment_list[segment]["loudness_max"]

        #convert data to readable for lights
        global rgb
        global brightness

        #if loudness is too quiet, turn off lights
        if Spotify.convertBrightness(current_loudness) < 25:
            #prevent brightness from being zero
            brightness = 25
            rgb = [0,0,0]
            #logging.warning("low loudness detected") #not an error, just warning of no light output
        elif Spotify.convertBrightness(current_loudness) > 254:
            #prevent overflow errors
            brightness = 255
            rgb = Spotify.convertTimbre(current_timbre)
            #rgb = [254,254,254] #uncomment if want max loudness to send white light
            #print("high loudness detected")
        else:
            brightness = Spotify.convertBrightness(current_loudness)
            rgb = Spotify.convertTimbre(current_timbre)

        #print(brightness)
        #print(rgb)
        

    def convertTimbre(self, timbre):
        #colormap timbre values to be loaded to strip
        #set timbre between 0 and 1 using 1/e^x
        timbre_1 = 1 / (1 + math.exp(-timbre[1]/45)) #using 'brightness'
        #timbre_3 = 1 / (1.05**abs(timbre[3])) #using 'attack'
        #timbre_a = round(1 / -(1 + math.exp((timbre[1]*abs(timbre[3]))/2500))+1, 10) #multiply those two
        #have 12 timbre values to choose from, here are variations I tested -currently set to what I believe to be best and most simple
        #see spotify api docs for more info on how these are calculated - noted they do not recommend using them directly
        
        #convert timbre to rgb using rainbow color map from matplotlib
        rgb = ([round(x*255) for x in cm.gist_rainbow(float(timbre_1))[:3]])
        return rgb

    def convertBrightness(self, current_loudness=0):
        #convert negative loudness to 0-255 brightness using 1.2^x
        return (1.2**(float(current_loudness))*255)


class Lights(threading.Thread):
    #control light effects on separate thread
    def __init__(self):
        self.rgb_list = []
        self.light_loop_time = 0
        print("initalizing Lights class")
        threading.Thread.__init__(self)
    
    def run(self):
        #infinite loop color data to led strip
        #get values from other class, note no locking is used - was too slow
        global brightness
        global rgb
        global is_playing

        while True:
            while is_playing==True:
                #start light loop ping timer
                start = time.time()

                for _ in range(1):
                    try:
                        #queue current rgb to list
                        Lights.addStack([rgb[0],rgb[1],rgb[2]])
                    except:
                        pass

                    
                    #set strip brightness
                    strip.setBrightness(int(brightness))

                    #send strip colors, starting at end with most recent value - appears to move like a waveform
                    for i, vals in reversed(list(enumerate(self.rgb_list))):
                        strip.setPixelColor(i, Color(vals[0], vals[1], vals[2]))
                    strip.show()
                #get ping time
                self.light_loop_time = time.time() - start

            else:
                time.sleep(.2)
                #if not playing, turn off lights
                logging.warning("No song playing! - Lights")
                Lights.colorWipe(strip, Color(0, 0, 0), 3)
                #reset the stack to zero
                for i in self.rgb_list:
                    Lights.addStack([0,0,0])
                    
    def addStack(self, to_append):
        #add rgb values to stack to display
        try:
            self.rgb_list.append(to_append)
        except:
            logging.error("Could not add RGB values to list")
        #shorten rgb_list to strip length
        while len(self.rgb_list) > strip.numPixels():
            self.rgb_list.pop(0)
    
    def colorWipe(self, strip, color, wait_ms=10):
        #Wipe color across display a pixel at a time, taken directly from library example
        for i in reversed(range(strip.numPixels())):
            strip.setPixelColor(i, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)

#intialize strip using values in top
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)

# Intialize the strip library (must be called once before other functions)
strip.begin()

#initialize class objects
Spotify = Spotify()
Lights = Lights()

#initalize global variables
rgb = []
brightness = 255
is_playing = False

#wait to start to resolve startup error on my pi - not necessary for all
time.sleep(10)

#start multiple threads to run concurrently, infinitely
#note ctrl+c may not end processes, use ctrl+z
Spotify.start()
time.sleep(1)
Lights.start()

#restrict main thread from finishing
while True:
    pass




