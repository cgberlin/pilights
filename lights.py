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
sleep        = False
user_bright  = 0
breathe_step = 1
flash_count  = 0 # needed to slow down the flashing
seconds      = 100.0 # minimum request time to stay within dark sky api tier
pi           = pigpio.pi()

# for testing the threads
counter_saved    = 0
request_changed  = False
weather_response = {"currently": {"temperature": 70}}

# firebase admin sdk setup
cred = credentials.Certificate('../pilights_firestore.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# firestore refs
F_STATES  = db.collection(u'states')
F_USER    = db.collection(u'user')
F_WEATHER = db.collection(u'weather')
F_DISPLAY = db.collection(u'display')

# global firestore vars
state_ref       = F_STATES.document(u'control_type')
state           = state_ref.get()
state           = state.to_dict()['type']

user_config_ref = F_USER.document(u'config')
user_color      = user_config_ref.get()
user_color      = user_color.to_dict()['color']

display_ref     = F_DISPLAY.document(u'config')
display_doc     = display_ref.get().to_dict()
pattern         = display_doc['pattern']
flash_speed     = display_doc['flashSpeed']
breathe_speed   = display_doc['breatheSpeed']
user_start_time = display_doc['startTime']
user_end_time   = display_doc['stopTime']

print(os.getenv("DARK_SKY_KEY"))

def on_state_snapshot(doc_snapshot, changes, read_time):
    global state
    
    for doc in doc_snapshot:
        state = doc.to_dict()['type']

def on_user_config_snapshot(doc_snapshot, changes, read_time):
    global user_color

    for doc in doc_snapshot:
        data       = doc.to_dict()
        user_color = data['color']

def on_display_snapshot(doc_snapshot, changes, read_time):
    global pattern
    global flash_speed
    global breathe_speed
    global user_start_time
    global user_end_time
    
    for doc in doc_snapshot:
        data            = doc.to_dict()
        pattern         = data['pattern']
        flash_speed     = data['flashSpeed']
        breathe_speed   = data['breatheSpeed']
        user_start_time = data['startTime']
        user_end_time   = data['stopTime']

user_config_watch = user_config_ref.on_snapshot(on_user_config_snapshot)
state_watch = state_ref.on_snapshot(on_state_snapshot)
display_watch = display_ref.on_snapshot(on_display_snapshot)

# updates the light by pin
def setLights(pin, brightness):
    global user_bright
    global flash_count
    global flash_speed
    global breathe_step
    global breathe_speed
    
    if pattern == "OFF":
        user_bright = 0
    elif pattern == "FLASH":
        flash_count += 1
        if flash_count > flash_speed:
            flash_count = 0
            if user_bright > 0:
                user_bright = 0
            else:
                user_bright = 255
    elif pattern == "BREATHE":
        if user_bright >= 255:
            breathe_step = -1 * breathe_speed / 100
        elif user_bright <= 0:
            breathe_step = 1 * breathe_speed / 100
        user_bright += breathe_step
    else:
        user_bright = 255
    realBrightness = int(int(brightness) * (float(user_bright) / 255.0))
    pi.set_PWM_dutycycle(pin, realBrightness)

# sets everything from user config every cycle
def setUserValues():
    setLights(RED_PIN, user_color['r'])
    setLights(GREEN_PIN, user_color['g'])
    setLights(BLUE_PIN, user_color['b'])

# parse temp then update lights
def convertToRgb(minVal, maxVal, val, colors):
    EPSILON = sys.float_info.epsilon
    # cant take credit, thank you SO
    i_f = float(val - minVal) / float(maxVal - minVal) * (len(colors) - 1)
    i,f = int(i_f // 1), i_f % 1
    if f < EPSILON:
        return colors[i]
    else:
        (r1, g1, b1), (r2, g2, b2) = colors[i], colors[i+1]
        return int(r1 + f * (r2 - r1)), int(g1 + f * (g2 - g1)), int(b1 + f * (b2 - b1))
    
    
def parseTemp(temp):
    percentage_of_heat = ((temp - 40) * 100) / (105 - 40)
    r, g, b = convertToRgb(35, 105, temp, [(16, 0, 255), (255, 0, 0)])
    setLights(BLUE_PIN, int(b))
    setLights(RED_PIN, int(r))
    setLights(GREEN_PIN, int(g))

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
        setUserValues()
    elif state == "PARTY":
        start_time = time.time()
        setLights(RED_PIN, randint(0,255))
        setLights(GREEN_PIN, randint(0,255))
        setLights(BLUE_PIN, randint(0,255))
        time.sleep(1 - ((time.time() - start_time) % 1))
    request_changed = False
    
#pi.stop()
