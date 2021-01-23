# ws2812-LED-live-spotify-visualizer
This is a music visualizer for ws281x LED strips, tested on ws2812b.
Color and brightness data are collected using the Spotify API's audio analysis feature on the song currently playing.
This was designed to be run on a raspberry pi, tested on model 3B. It does not require audio input, instead polls data from linked Spotify account's currently playing. 

# Quick Start Guide:
## Materials
Raspberry Pi 3B
ws2812B LED strip
Power Supply for LEDS
Spotify Premium 

## Spotify Setup
You will need to input your Spotify Dev client_id, client_secret, and redirect URI into the beginning of the python script you choose to run.
For a guide to getting those values, I recommend visting https://github.com/markkohdev/spotify-api-starter in the section of registering your app. The 3 values it asks to put in the .sh file should go in the .py from this repo.

## Lights Setup
To wire the lights to the pi, I used this tutorial: https://tutorials-raspberrypi.com/connect-control-raspberry-pi-ws2812-rgb-led-strips/
Note that you will need to add your strip length and GPIO pin into the .py from this repo.

## How to run
In this repository there are two versions of the script - you only need one.
multithreading.py uses multithreading to display to the lights while waiting for a response from Spotify. This is the script you should be using.
To run the script, simply run 
'''sudo python3 multithreading.py'''
It will only work as root to control the GPIO pin.
If it does not work and there is no error messages, make sure you folowed the steps in the links above properly. And don't forget your dependencies!
To stop the script, keep in mind it was indended to run indefintely, so ctl+c may not stop the script. Use ctrl+z to kill.

# Headless Implementation
I designed this to run headless on my pi. To launch it at startup, place a .service file into systemd. There are tutorials for this online, seek and ye shall find.
Keep in mind that it is not possible to input into systemd services, therefore make sure you have logged in previously and all users have permission to the .cache file. You can change the location of this file in Line 27 in the authentication request.

# Notes and Personalization / Advanced Usage
There are currently no example videos of this in action. I may upload something someday, but until then I will describe it as producing the waveform across the strip. Try for yourself to see.

As stated before there are two .py files in the repo. linear.py is NOT intended for regular use. It runs the loop start to finish, meaning it is INCREDIBLY slow. It is only present if anyone is interested to develop it for special cases, for example using <10 LEDS or prerendering.

The color is determined by the Spotify API's timbre values, specifically #2. Spotify developers recommend NOT using this directly, but I did it anyway since pitch values do not scale across octaves. If you look in the code, there are other equations and values I experimented with. Simple uncomment those lines and replace the value in the cm.gist_rainbow function.

The color mapped from the values uses matplotlib's colormap function. Currently it uses gist_rainbow, but you can change it to preference by choosing a colormap at this link https://matplotlib.org/3.3.3/tutorials/colors/colormaps.html and replacing it instead of gist_rainbow. 

The brightness is mapped using the decibel value of the segment. Note that values below 25 (scale 0-255) will result in no pixel output and a console message. This is not an error, it is intentional to break up space in songs and trying to find color of silence.

The script uses multithreading to perform the Spotify data gather and LED strip simultaniously. The variables 'rgb' and 'brightness' are passed between them *without* a lock. This could result in lost or incorrect data, but improves performance. Due to the GIL, this script could most likely be improved by using multiprocessing instead. I did not try this but it is likely possible.

Lastly, feel free to pull request and change as you see fit. There is much more I would have added had I more time, such as tinkering with colors and sync/performance. This is my first full project therefore code could more than likely be optimized. Check the comments in multithreading.py for more info on how it works. Thank you.
