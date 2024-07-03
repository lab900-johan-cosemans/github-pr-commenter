import os
import requests
import xmltodict

#ESP32_SPRINKLERS_IP = os.environ["ESP32_SPRINKLERS_IP"]
ESP32_SPRINKLERS_IP = "10.10.0.185"

@time_trigger('period(now, 5s)')
def log_hello_world():
    log.info("Getting status of the sprinklers on ip " + ESP32_SPRINKLERS_IP)
    url = f'http://{ESP32_SPRINKLERS_IP}/status.xml'
    statusResponseXml = task.executor(requests.get, url)
#<?xml version="1.0" encoding="UTF-8"?>
#<ESP32LR42DATA>
#<RELAYS>
#<RLY1>on</RLY1>
#<RLY2>on</RLY2>
#<RLY3>on</RLY3>
#<RLY4>on</RLY4>
#</RELAYS>
#<INPUTS>
#<INP1>1</INP1>
#<INP2>1</INP2>
#</INPUTS>
#</ESP32LR42DATA>
    statusResponse = xmltodict.parse(statusResponseXml.text)
#    log.info(statusResponse)
    log.info(statusResponse['ESP32LR42DATA']['RELAYS']['RLY1'])



@service
def log_hello_world2():
    log.info("Hello World2")