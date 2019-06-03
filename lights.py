#!/usr/bin/python

import os
import sys
import requests 
import json
#import termios
#import tty
#import pigpio # because no neopixel
import time
from _thread import start_new_thread # PYTHON 3
# from thread import start_new_thread # PYTHON 2
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# pin connections //// sad not neopixel for this one but *shrug*
RED_PIN   = 17
GREEN_PIN = 22
BLUE_PIN  = 24

# global states
sleep     = False
state     = True
seconds   = 60.0 

# for testing the threads
counter_saved    = 0
request_changed  = False
weather_response = False

# firebase admin sdk setup 
cred = credentials.Certificate('../pilights_firestore.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

def weatherWatcher():
    global state
    global sleep
    global seconds
    global counter_saved
    global weather_response
    global request_changed

    # env var dark sky key // screw you mr. github scraper
    dark_key = os.getenv('DARK_SKY_KEY')
    weather_url = "https://api.darksky.net/forecast/"+dark_key+"/33.9850,-118.4695"

    
    start_time = time.time()
    counter    = 1
    while True:
        r    = requests.get(url = weather_url).json()
        weather_response = r
        request_changed = True
        time.sleep(seconds - ((time.time() - start_time) % seconds))


start_new_thread(weatherWatcher, ())


while sleep == False:
    if weather_response:
        print(weather_response['currently']['temperature'])
    request_changed = False
    
#pi.stop()