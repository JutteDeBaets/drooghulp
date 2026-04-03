"""
Main entry point for the Drooghulp project.
"""

import time

import Adafruit_DHT11


def _ensure_adafruit_pi_platform():
    """Fallback for newer Pi models not detected by legacy Adafruit_DHT."""
    detector = Adafruit_DHT.common.platform_detect
    if detector.pi_version() is None:
        detector.pi_version = lambda: 3
        detector.platform_detect = lambda: detector.RASPBERRY_PI

def main():
    _ensure_adafruit_pi_platform()

    DHT_SENSOR = Adafruit_DHT.DHT11
    DHT_PIN = 7
    sensor_driver_error_reported = False

    while True:
        try:
            humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
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
