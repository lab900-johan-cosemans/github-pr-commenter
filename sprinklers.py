import os

#@time_trigger('period(now, 5s)')
#def log_hello_world():
#    log.info("Hello World")


@service
def log_hello_world2():
    log.info("Hello World2")