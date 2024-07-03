import goodwe


@service
def goodwe_charge_battery():
    set_operation_mode_charging('192.168.1.190')
    log.info(f"done")


@service
def goodwe_stop_charging():
    set_operation_mode_general('192.168.1.190')
    log.info(f"done")


def set_operation_mode_general(ip_address):
    inverter = goodwe.connect(ip_address)

    operationMode = inverter.get_operation_mode()
    log.info(f"Current operation mode: {operationMode}")

    log.info(f"Stopping charging battery")
    inverter.set_operation_mode(0)  # 0 - General mode

    operationMode = inverter.get_operation_mode()
    log.info(f"Current operation mode: {operationMode}")

    log.info(f"done")


def set_operation_mode_charging(ip_address):
    inverter = goodwe.connect(ip_address)

    operationMode = inverter.get_operation_mode()
    log.info(f"Current operation mode: {operationMode}")

    log.info(f"Starting charging battery")
    inverter.set_operation_mode(4, 20)  # 4 - Eco mode Charge, charge at 20% load until 100% full

    operationMode = inverter.get_operation_mode()
    log.info(f"Current operation mode: {operationMode}")

