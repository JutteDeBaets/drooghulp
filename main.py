"""Read Grove Sound + Motion + DHT sensors with existing wiring."""

import time

try:
    import RPi.GPIO as GPIO
except ImportError as err:
    raise SystemExit(
        "RPi.GPIO is not installed. Install it with 'pip install RPi.GPIO' or 'sudo apt install python3-rpi.gpio'."
    ) from err


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


def _build_reader(sensor_names, bcm_pin):
    """Prefer CircuitPython DHT with auto-fallback, then legacy Adafruit_DHT."""
    circuit_error = None

    try:
        import adafruit_dht
        import board

        board_pin_name = f"D{bcm_pin}"
        if not hasattr(board, board_pin_name):
            raise RuntimeError(f"board.{board_pin_name} is not available on this device.")

        board_pin = getattr(board, board_pin_name)

        sensor_types = list(sensor_names)
        if not sensor_types:
            sensor_types = ["DHT22"]

        current_index = 0
        failures = 0
        max_failures = 3

        def _make_sensor(sensor_type):
            if sensor_type == "DHT11":
                return adafruit_dht.DHT11(board_pin, use_pulseio=False)
            return adafruit_dht.DHT22(board_pin, use_pulseio=False)

        sensor = _make_sensor(sensor_types[current_index])

        def _circuit_read():
            nonlocal sensor, current_index, failures
            try:
                humidity = sensor.humidity
                temperature = sensor.temperature
                if humidity is None or temperature is None:
                    raise RuntimeError("DHT returned None")
                failures = 0
                return humidity, temperature
            except RuntimeError:
                failures += 1
                if failures >= max_failures:
                    failures = 0
                    current_index = (current_index + 1) % len(sensor_types)
                    try:
                        sensor.exit()
                    except Exception:
                        pass
                    sensor = _make_sensor(sensor_types[current_index])
                return None, None

        label = "|".join(sensor_types)
        return _circuit_read, f"adafruit-circuitpython-dht({label})"
    except Exception as err:
        circuit_error = err

    try:
        import Adafruit_DHT

        sensor = getattr(Adafruit_DHT, sensor_names[0])

        def _legacy_read():
            return Adafruit_DHT.read_retry(sensor, bcm_pin, retries=3, delay_seconds=1)

        return _legacy_read, "Adafruit_DHT"
    except Exception as adafruit_error:
        raise RuntimeError(
            "No supported DHT backend is available. "
            "Install adafruit-circuitpython-dht or Adafruit_DHT. "
            f"CircuitPython error: {circuit_error}; "
            f"Adafruit_DHT error: {adafruit_error}"
        )


# Grove Sound Sensor v1.6 via PmodAD1 (BCM numbering)
GPIO_CLK = 11
GPIO_CS = 24
GPIO_D0 = 23
VREF = 3.3
HALF_CLOCK_DELAY_SECONDS = 0.00001


# Motion sensor (BOARD pin 8 -> BCM 14)
MOTION_BCM_PIN = 14


# DHT sensor (BOARD pin 7 -> BCM 4)
DHT_SENSOR_TYPES = ["DHT22", "DHT11"]
DHT_PIN = 7
DHT_PIN_MODE = "BOARD"


def read_pmodad1_channel0_bitbang():
    """Read a 12-bit sample from PmodAD1 with software clocking."""
    value = 0

    GPIO.output(GPIO_CS, GPIO.LOW)
    time.sleep(HALF_CLOCK_DELAY_SECONDS)

    # PmodAD1/ADCS7476 shifts out 16 bits total: leading zeros + 12-bit sample.
    for _ in range(16):
        GPIO.output(GPIO_CLK, GPIO.HIGH)
        time.sleep(HALF_CLOCK_DELAY_SECONDS)

        value = (value << 1) | int(GPIO.input(GPIO_D0))

        GPIO.output(GPIO_CLK, GPIO.LOW)
        time.sleep(HALF_CLOCK_DELAY_SECONDS)

    GPIO.output(GPIO_CS, GPIO.HIGH)
    return value & 0x0FFF


def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_CLK, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(GPIO_CS, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(GPIO_D0, GPIO.IN)
    GPIO.setup(MOTION_BCM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    bcm_pin = resolve_bcm_pin(DHT_PIN, DHT_PIN_MODE)
    read_dht, backend_name = _build_reader(DHT_SENSOR_TYPES, bcm_pin)
    sensor_driver_error_reported = False

    print("Reading Grove Sound Sensor v1.6 via PmodAD1")
    print("Wiring: CLK=GPIO11(pin23), CS=GPIO24(pin18), D0=GPIO23(pin16)")
    print(f"Motion sensor: BCM {MOTION_BCM_PIN} (BOARD 8)")
    print(f"DHT: {','.join(DHT_SENSOR_TYPES)}, pin mode: {DHT_PIN_MODE}, BCM {bcm_pin}")
    print(f"Using DHT backend: {backend_name}")

    next_dht_time = 0.0
    last_temperature = None
    last_humidity = None

    try:
        while True:
            value = read_pmodad1_channel0_bitbang()
            voltage = (value / 4095.0) * VREF
            motion_state = int(GPIO.input(MOTION_BCM_PIN))

            humidity = None
            temperature = None
            now = time.monotonic()
            if now >= next_dht_time:
                next_dht_time = now + 2.0
                try:
                    humidity, temperature = read_dht()
                    if humidity is not None and temperature is not None:
                        last_humidity = humidity
                        last_temperature = temperature
                except Exception as err:
                    if not sensor_driver_error_reported:
                        print(f"DHT driver error: {err}")
                        sensor_driver_error_reported = True

            temp_val = last_temperature if temperature is None else temperature
            hum_val = last_humidity if humidity is None else humidity
            temp_txt = "--" if temp_val is None else f"{temp_val:0.1f}"
            hum_txt = "--" if hum_val is None else f"{hum_val:0.1f}"
            print(
                "sound_raw={raw:4d} sound_v={v:0.3f}V motion={motion} "
                "temp={temp}C humidity={hum}%"
                .format(raw=value, v=voltage, motion=motion_state, temp=temp_txt, hum=hum_txt)
            )
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        GPIO.cleanup((GPIO_CLK, GPIO_CS, GPIO_D0, MOTION_BCM_PIN))


if __name__ == "__main__":
    main()
