"""
Main entry point for the Drooghulp project.
"""

import time


BOARD_TO_BCM = {
    3: 2,
    5: 3,
    7: 4,
    8: 14,
    10: 15,
    11: 17,
    12: 18,
    13: 27,
    15: 22,
    16: 23,
    18: 24,
    19: 10,
    21: 9,
    22: 25,
    23: 11,
    24: 8,
    26: 7,
    27: 0,
    28: 1,
    29: 5,
    31: 6,
    32: 12,
    33: 13,
    35: 19,
    36: 16,
    37: 26,
    38: 20,
    40: 21,
}


def resolve_bcm_pin(pin, numbering_mode):
    """Convert a BOARD pin to BCM if needed."""
    mode = numbering_mode.upper()
    if mode == "BCM":
        return pin
    if mode == "BOARD":
        if pin not in BOARD_TO_BCM:
            raise ValueError(f"BOARD pin {pin} cannot be mapped to BCM.")
        return BOARD_TO_BCM[pin]
    raise ValueError("PIN_NUMBERING must be either 'BOARD' or 'BCM'.")


def _build_reader(sensor_name, bcm_pin):
    """Try legacy Adafruit_DHT first, then CircuitPython DHT."""
    adafruit_dht_error = None

    try:
        import Adafruit_DHT

        sensor = getattr(Adafruit_DHT, sensor_name)

        def _legacy_read():
            return Adafruit_DHT.read_retry(sensor, bcm_pin, retries=3, delay_seconds=1)

        return _legacy_read, "Adafruit_DHT"
    except Exception as err:
        adafruit_dht_error = err

    try:
        import adafruit_dht
        import board

        board_pin_name = f"D{bcm_pin}"
        if not hasattr(board, board_pin_name):
            raise RuntimeError(f"board.{board_pin_name} is not available on this device.")

        board_pin = getattr(board, board_pin_name)
        if sensor_name == "DHT11":
            sensor = adafruit_dht.DHT11(board_pin, use_pulseio=False)
        else:
            sensor = adafruit_dht.DHT22(board_pin, use_pulseio=False)

        def _circuit_read():
            try:
                return sensor.humidity, sensor.temperature
            except RuntimeError:
                # CircuitPython DHT throws transient RuntimeError on bad reads.
                return None, None

        return _circuit_read, "adafruit-circuitpython-dht"
    except Exception as circuit_error:
        raise RuntimeError(
            "No supported DHT backend is available. "
            "Install Adafruit_DHT or adafruit-circuitpython-dht. "
            f"Adafruit_DHT error: {adafruit_dht_error}; "
            f"CircuitPython error: {circuit_error}"
        )

def main():
    SENSOR_TYPE = "DHT11"
    DHT_PIN = 7
    PIN_NUMBERING = "BOARD"

    bcm_pin = resolve_bcm_pin(DHT_PIN, PIN_NUMBERING)
    read_sensor, backend_name = _build_reader(SENSOR_TYPE, bcm_pin)
    sensor_driver_error_reported = False

    print(f"Using sensor backend: {backend_name}")
    print(f"Sensor type: {SENSOR_TYPE}, pin mode: {PIN_NUMBERING}, BCM pin: {bcm_pin}")

    while True:
        try:
            humidity, temperature = read_sensor()
        except Exception as err:
            humidity, temperature = None, None
            if not sensor_driver_error_reported:
                print(f"Sensor driver error: {err}")
                sensor_driver_error_reported = True
        if humidity is not None and temperature is not None:
            print("Temp={0:0.1f}C Humidity={1:0.1f}%".format(temperature, humidity))
        else:
            print("Sensor failure. Check wiring.")
        time.sleep(2)
    # Add your main logic here

if __name__ == "__main__":
    main()
