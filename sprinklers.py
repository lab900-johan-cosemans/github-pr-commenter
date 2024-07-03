import os
import requests
import xmltodict

#ESP32_SPRINKLERS_IP = os.environ["ESP32_SPRINKLERS_IP"]
ESP32_SPRINKLERS_IP = "10.10.0.185"

@time_trigger('period(now, 5s)')
def update_sprinkler_status():
    log.info("Getting status of the sprinklers on ip " + ESP32_SPRINKLERS_IP)
    url = f'http://{ESP32_SPRINKLERS_IP}/status.xml'
    statusResponseXml = task.executor(requests.get, url)
    #<?xml version="1.0" encoding="UTF-8"?>
    #<ESP32LR42DATA>
    #<RELAYS>
    #<RLY1>on</RLY1>
    #<RLY2>off</RLY2>
    #<RLY3>on</RLY3>
    #<RLY4>on</RLY4>
    #</RELAYS>
    #<INPUTS>
    #<INP1>1</INP1>
    #<INP2>1</INP2>
    #</INPUTS>
    #</ESP32LR42DATA>
    statusResponse = xmltodict.parse(statusResponseXml.text)
    state.set(f'sprinklers.sprinkler_1', convertState(statusResponse['ESP32LR42DATA']['RELAYS']['RLY1']))
    state.set(f'sprinklers.sprinkler_2', convertState(statusResponse['ESP32LR42DATA']['RELAYS']['RLY2']))
    state.set(f'sprinklers.sprinkler_3', convertState(statusResponse['ESP32LR42DATA']['RELAYS']['RLY3']))
    state.set(f'sprinklers.sprinkler_4', convertState(statusResponse['ESP32LR42DATA']['RELAYS']['RLY4']))

def convertState(state):
    return state == 'on'

@service
def set_relay(relay, state):
    log.info("Setting relay " + relay + " to " + state)
    url = f'http://{ESP32_SPRINKLERS_IP}/?Rly{relay}={state}'