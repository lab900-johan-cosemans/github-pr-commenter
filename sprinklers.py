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
    statusResponse = xmltodict.parse(statusResponseXml.text)
    log.info(statusResponse)



@service
def log_hello_world2():
    log.info("Hello World2")