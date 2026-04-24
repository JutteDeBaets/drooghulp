"""Read a Grove Sound Sensor v1.6 via PmodAD1 using custom GPIO wiring."""

import time

try:
    from gpiozero import DigitalInputDevice, DigitalOutputDevice
except ImportError as err:
    raise SystemExit(
        "gpiozero is not installed. Install it with 'pip install gpiozero' or 'sudo apt install python3-gpiozero'."
    ) from err


# Corrected wiring (BCM numbering):
# CLK -> GPIO11 (BOARD pin 23)
# CS  -> GPIO24 (BOARD pin 18)
# D0  -> GPIO23 (BOARD pin 16)
GPIO_CLK = 11
GPIO_CS = 24
GPIO_D0 = 23

SAMPLE_INTERVAL_SECONDS = 0.1
VREF = 3.3
HALF_CLOCK_DELAY_SECONDS = 0.00001


def read_pmodad1_channel0_bitbang(cs, clk, d0):
    """Read a 12-bit sample from PmodAD1 with software clocking."""
    value = 0

    cs.off()
    time.sleep(HALF_CLOCK_DELAY_SECONDS)

    # PmodAD1/ADCS7476 shifts out 16 bits total: leading zeros + 12-bit sample.
    for _ in range(16):
        clk.on()
        time.sleep(HALF_CLOCK_DELAY_SECONDS)

        value = (value << 1) | int(d0.value)

        clk.off()
        time.sleep(HALF_CLOCK_DELAY_SECONDS)

    cs.on()
    return value & 0x0FFF


def main():
    clk = DigitalOutputDevice(GPIO_CLK, active_high=True, initial_value=False)
    cs = DigitalOutputDevice(GPIO_CS, active_high=True, initial_value=True)
    d0 = DigitalInputDevice(GPIO_D0)

    print("Reading Grove Sound Sensor v1.6 via PmodAD1")
    print("Wiring: CLK=GPIO11(pin23), CS=GPIO24(pin18), D0=GPIO23(pin16)")

    try:
        while True:
            value = read_pmodad1_channel0_bitbang(cs, clk, d0)
            voltage = (value / 4095.0) * VREF
            print(f"raw={value:4d}  voltage={voltage:0.3f} V")
            time.sleep(SAMPLE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        cs.close()
        clk.close()
        d0.close()


if __name__ == "__main__":
    main()
