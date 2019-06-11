#!/usr/bin/python
# cody berlin 2019
# i know i mixed single and double quotes, deal with it

import os
import sys
import requests 
import json
import termios
import tty
import pigpio # because no neopixel
import time
from random import randint
from _thread import start_new_thread # PYTHON 3
# from thread import start_new_thread # PYTHON 2
#import pyrebase
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# pin connections //// sad no neopixel for this one but *shrug*
RED_PIN   = 17
GREEN_PIN = 22
BLUE_PIN  = 24

# global states
sleep     = False
seconds   = 100.0 # minimum request time to stay within dark sky api tier
pi = pigpio.pi()

# for testing the threads
counter_saved    = 0
request_changed  = False
weather_response = {"currently": {"temperature": 70}}

# firebase admin sdk setup
cred = credentials.Certificate('../pilights_firestore.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# firestore refs
F_STATES = db.collection(u'states')
F_USER = db.collection(u'user')
F_WEATHER = db.collection(u'weather')

# global firestore vars
state_ref = F_STATES.document(u'control_type')
state = state_ref.get()
state = state.to_dict()['type']

user_config_ref = F_USER.document(u'config')
user_color = user_config_ref.get()
user_color = user_color.to_dict()['color']

print(user_color)
print(state)

def on_state_snapshot(doc_snapshot, changes, read_time):
    global state
    
    for doc in doc_snapshot:
        print(u'received docs: {}'.format(doc.id))
        print(doc.to_dict()['type'])
        state = doc.to_dict()['type']

def on_user_config_snapshot(doc_snapshot, changes, read_time):
    global user_color

    for doc in doc_snapshot:
        print(u'received docs: {}'.format(doc.id))
        data = doc.to_dict()
        user_color = data['color']

user_config_watch = user_config_ref.on_snapshot(on_user_config_snapshot)
state_watch = state_ref.on_snapshot(on_state_snapshot)

# updates the light by pin
def setLights(pin, brightness):
    #realBrightness = int(int(brightness) * (float(255) / 255.0))
    pi.set_PWM_dutycycle(pin, brightness)

# sets everything from user config every cycle
def setUserValues():
    setLights(RED_PIN, user_color['r'])
    setLights(GREEN_PIN, user_color['g'])
    setLights(BLUE_PIN, user_color['b'])

# parse temp then update lights
def parseTemp(temp):
    percentage_of_heat = ((temp - 40) * 100) / (105 - 40)
    blue = 100 + (percentage_of_heat * 2)
    red = 255 - (percentage_of_heat * 2)
    #print(blue)
    #print(red)
    setLights(BLUE_PIN, int(blue))
    setLights(RED_PIN, int(red))

def weatherWatcher():
    global state
    global sleep
    global seconds
    global counter_saved
    global weather_response
    global request_changed

    # env var dark sky key // screw you mr. github scraper
    dark_key = os.getenv("DARK_SKY_KEY")
    weather_url = "https://api.darksky.net/forecast/"+dark_key+"/33.9850,-118.4695"

    start_time = time.time()
    counter    = 1
    # could probs do some clever recursive function that sleeps itself and checks for state changes but f it, keep looping
    while True:
        if state == "WEATHER":
            r    = requests.get(url = weather_url).json()
            weather_response = r
            request_changed = True
            
        time.sleep(seconds - ((time.time() - start_time) % seconds))


start_new_thread(weatherWatcher, ())


while sleep == False:
    if state == "WEATHER":
        temp = weather_response["currently"]["temperature"]
        parseTemp(temp)
    elif state == "USER":
        print(user_color)
        setUserValues()
    elif state == "PARTY":
        start_time = time.time()
        setLights(RED_PIN, randint(0,255))
        setLights(GREEN_PIN, randint(0,255))
        setLights(BLUE_PIN, randint(0,255))
        time.sleep(1 - ((time.time() - start_time) % 1))
    request_changed = False
    
#pi.stop()
