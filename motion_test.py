"""
Simple GPIO Zero motion sensor input test.

Wiring assumption:
- Sensor signal is connected to physical pin 8 (BOARD), which is BCM 14.
"""

from gpiozero import InputDevice
import time

BOARD_PIN = 8
BCM_PIN = 14


sensor = InputDevice(BCM_PIN, pull_up=False)

print(f"Reading motion sensor on BOARD pin {BOARD_PIN} (BCM {BCM_PIN})")
print("Press Ctrl+C to stop.")

# Polling-only test to keep the script robust on all pin backends.
try:
    previous = None
    while True:
        current = int(sensor.is_active)
        if current != previous:
            if current == 1:
                print("MOTION detected")
            else:
                print("No motion")
            previous = current
        print(f"raw value: {current}")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Stopped.")
