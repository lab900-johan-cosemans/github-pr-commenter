@time_trigger('period(now, 30s)')
def run_get_info():
    log.debug('running get_station_info')

@service
def log_hello_world():
    log.info(f"hello world!")

