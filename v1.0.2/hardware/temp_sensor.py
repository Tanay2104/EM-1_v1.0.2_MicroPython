# --- START OF FILE temp_sensor.py ---

import machine
import utime

# Register addresses from the MAX31865 datasheet
_MAX31865_REG_CONFIG = 0x00
_MAX31865_REG_RTD_MSB = 0x01
_MAX31865_REG_RTD_LSB = 0x02
_MAX31865_REG_FAULT_STATUS = 0x07

# Bitmasks for the configuration register
_MAX31865_CONFIG_BIAS = 0x80       # 1 = V_BIAS ON, 0 = OFF
_MAX31865_CONFIG_1SHOT = 0x20      # 1 = 1-shot conversion
_MAX31865_CONFIG_3WIRE = 0x10      # 1 = 3-wire, 0 = 2/4-wire
_MAX31865_CONFIG_FAULT_CLEAR = 0x02 # Write 1 to clear faults
_MAX31865_CONFIG_50HZ = 0x01       # 1 = 50Hz filter, 0 = 60Hz

class MAX31865:
    """
    A MicroPython class for the MAX31865 RTD-to-Digital Converter.
    Handles communication and temperature calculation for PT100/PT1000 sensors.
    """
    def __init__(self, spi, cs_pin, *, wires=2, r_ref=4300.0, r_nominal=1000.0):
        """
        Initializes the MAX31865 sensor.

        Args:
            spi (machine.SPI): The configured SPI bus object.
            cs_pin (machine.Pin): The chip select pin object.
            wires (int): The number of wires for the RTD sensor (2, 3, or 4). Default is 2.
            r_ref (float): The value of the reference resistor in Ohms.
                           Typically 430.0 for PT100, 4300.0 for PT1000.
            r_nominal (float): The nominal resistance of the RTD at 0°C.
                               Typically 100.0 for PT100, 1000.0 for PT1000.
        """
        self.spi = spi
        self.cs = cs_pin
        self.r_ref = r_ref
        self.r_nominal = r_nominal
        self.wires = wires
        
        # Alpha is the temperature coefficient of the RTD sensor.
        # 0.00385 is standard for most Platinum RTDs.
        self._alpha = 0.00385
        
        # Ensure CS pin is an output and set high (inactive)
        self.cs.init(mode=machine.Pin.OUT, value=1)
        
        # Initial configuration
        self.configure()

    def _write_register(self, reg, value):
        """Writes a single byte to the specified register."""
        self.cs.value(0)  # Select chip
        # The first byte is the register address with the write bit (MSB) set.
        self.spi.write(bytes([reg | 0x80, value]))
        self.cs.value(1)  # Deselect chip

    def _read_register(self, reg, num_bytes=1):
        """Reads one or more bytes from the specified register."""
        self.cs.value(0)
        # First byte sent is the register address with the read bit (MSB) clear.
        self.spi.write(bytes([reg & 0x7F]))
        # Read the specified number of bytes
        data = self.spi.read(num_bytes)
        self.cs.value(1)
        return data

    def configure(self, filter_50hz=True):
        """
        Configures the sensor settings like wire mode and AC filter.
        
        Args:
            filter_50hz (bool): Set to True for 50Hz mains filter, False for 60Hz.
        """
        config = 0 # Start with a clean config
        if self.wires == 3:
            config |= _MAX31865_CONFIG_3WIRE
        if filter_50hz:
            config |= _MAX31865_CONFIG_50HZ
        
        self._write_register(_MAX31865_REG_CONFIG, config)
        self.clear_faults()

    def read_rtd_raw(self):
        """
        Performs a 1-shot measurement and returns the raw 15-bit RTD value.
        """
        # Turn on bias voltage and start a 1-shot conversion
        config = self._read_register(_MAX31865_REG_CONFIG)[0]
        self._write_register(_MAX31865_REG_CONFIG, config | _MAX31865_CONFIG_BIAS | _MAX31865_CONFIG_1SHOT)
        
        # Wait for conversion to complete (datasheet: ~60ms)
        utime.sleep_ms(70)
        
        # Read the 2-byte RTD result
        rtd_bytes = self._read_register(_MAX31865_REG_RTD_MSB, 2)
        
        # Turn off bias voltage to save power
        self._write_register(_MAX31865_REG_CONFIG, config)
        
        # Combine the MSB and LSB into a 16-bit value
        raw_reading = (rtd_bytes[0] << 8) | rtd_bytes[1]
        
        # Check for fault bit (LSB)
        if raw_reading & 0x01:
            # A fault occurred, read the fault register to know why
            # For now, we return None to indicate an error
            return None
        
        # The raw RTD value is the top 15 bits, so shift right by 1
        return raw_reading >> 1

    def read_resistance(self):
        """
        Reads the RTD sensor and returns its resistance in Ohms.
        """
        rtd_val = self.read_rtd_raw()
        if rtd_val is None:
            return None # Propagate the fault error
            
        # The MAX31865 ADC has 15-bit resolution (0-32767)
        # The ratio is the raw reading divided by the full-scale value (2^15)
        ratio = rtd_val / 32768.0
        
        return ratio * self.r_ref
        
    @property
    def temperature(self):
        """
        Reads the RTD sensor and calculates the temperature in Celsius.
        This is a simplified calculation valid for temps > 0°C.
        """
        resistance = self.read_resistance()
        if resistance is None:
            return None # Fault occurred
            
        # Simplified Callendar-Van Dusen equation for temp > 0°C
        # Temp = (R_t / R_0 - 1) / alpha
        temp = (resistance / self.r_nominal - 1.0) / self._alpha
        return temp
        
    def read_fault(self):
        """Reads and returns the 8-bit fault status register."""
        return self._read_register(_MAX31865_REG_FAULT_STATUS)[0]

    def clear_faults(self):
        """Clears any latched fault conditions."""
        config = self._read_register(_MAX31865_REG_CONFIG)[0]
        self._write_register(_MAX31865_REG_CONFIG, config | _MAX31865_CONFIG_FAULT_CLEAR)


# --- EXAMPLE USAGE ---
# This block will only run when we execute this file directly.
# It will not run when you `import` the class into another file.
if __name__ == '__main__':
    # Configure your SPI pins according to your wiring
    # SPI(0) uses GPIO 0, 1, 2, 3 on the Pico by default, but you can remap
    # sck=Pin(2), mosi=Pin(3), miso=Pin(4)
    spi = machine.SPI(0, baudrate=1000000, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
    
    # Configure your Chip Select (CS) pin
    cs_pin = machine.Pin(5, machine.Pin.OUT)
    
    # Initialize the sensor for a PT1000 with a 4300 Ohm reference resistor
    # and a 4-wire configuration.
    # For a PT100, use r_ref=430.0 and r_nominal=100.0
    sensor = MAX31865(spi, cs_pin, wires=4, r_ref=4300.0, r_nominal=1000.0)

    while True:
        temp = sensor.temperature
        
        if temp is None:
            # A fault was detected during the reading
            fault_code = sensor.read_fault()
            print(f"Fault detected! Code: {fault_code:#04x}")
            sensor.clear_faults()
        else:
            resistance = sensor.read_resistance()
            print(f"Temperature: {temp:.2f} °C")
            print(f"Resistance: {resistance:.2f} Ohms")
            
        print("-" * 20)
        utime.sleep(2)