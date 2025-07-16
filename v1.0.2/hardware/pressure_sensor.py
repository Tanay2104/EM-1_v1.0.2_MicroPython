# --- START OF FILE pressure_sensor.py ---

import machine
import utime

class PressureSensor:
    """
    A production-ready MicroPython driver for an analog pressure sensor.
    Features robust taring and a software low-pass filter for stable readings.
    """
    
    # --- Sensor & Circuit Constants ---
    _MIN_VOLTAGE = 0.5
    _MAX_VOLTAGE = 4.5
    _MAX_PRESSURE_BAR = 12.0
    _VOLTAGE_DIVIDER_RATIO = 1/2
    # --- System Constants ---
    _PICO_ADC_REF_VOLTAGE = 3.3
    _ADC_MAX_RAW = 65535
    
    # --- Calculated Slope ---
    # The change in pressure per unit of change in voltage.
    _BAR_PER_VOLT = _MAX_PRESSURE_BAR / (_MAX_VOLTAGE - _MIN_VOLTAGE) # 12.0 / 4.0 = 3.0

    def __init__(self, adc_pin_number: int, filter_alpha: float = 0.1):
        if adc_pin_number not in [26, 27, 28]:
            raise ValueError("Invalid ADC pin. Must be 26, 27, or 28.")
        self.adc = machine.ADC(machine.Pin(adc_pin_number))
        
        self.alpha = filter_alpha
        self._resting_voltage = 0.0
        self._filtered_pressure = 0.0
        self._is_tared = False

    def _read_voltage(self) -> float:
        """Private method to read the raw voltage from the sensor."""
        raw_adc = self.adc.read_u16()
        pico_pin_voltage = (raw_adc / self._ADC_MAX_RAW) * self._PICO_ADC_REF_VOLTAGE
        sensor_voltage = pico_pin_voltage / self._VOLTAGE_DIVIDER_RATIO
        return sensor_voltage

    def tare(self, num_readings: int = 1000):
        """
        Measures the resting voltage of the sensor to set the zero-point.
        This must be called once at startup. A higher number of readings
        gives a more stable zero-point.
        """
        print("Taring sensor...")
        voltage_sum = 0
        for _ in range(num_readings):
            voltage_sum += self._read_voltage()
            utime.sleep_ms(5)
        
        self._resting_voltage = voltage_sum / num_readings
        self._filtered_pressure = 0.0
        self._is_tared = True
        print(f"Tare complete. Resting voltage set to: {self._resting_voltage:.3f}V")

    def read_diagnostics(self) -> dict:
        """
        Returns a dictionary with raw values for debugging.
        This helps diagnose issues without affecting pressure readings.
        """
        raw_adc_value = self.adc.read_u16()
        voltage_at_pico_pin = (raw_adc_value / self._ADC_MAX_RAW) * self._PICO_ADC_REF_VOLTAGE
        calculated_sensor_voltage = voltage_at_pico_pin / self._VOLTAGE_DIVIDER_RATIO
        
        return {
            'raw_adc': raw_adc_value,
            'pico_pin_voltage': f"{voltage_at_pico_pin:.3f}V",
            'sensor_voltage': f"{calculated_sensor_voltage:.3f}V"
        }

    @property
    def pressure(self) -> float:
        """
        Returns the clean, filtered, GAUGE pressure in Bar.
        This is the primary method to use for control.
        """
        if not self._is_tared:
            # This check prevents accidental use before calibration
            # In a real system, you might raise an error instead.
            print("Warning: Sensor not tared. Call tare() first.")
            return 0.0

        # 1. Get the current voltage from the sensor
        current_voltage = self._read_voltage()
        
        # 2. Calculate the raw gauge pressure based on the voltage difference
        voltage_delta = current_voltage - self._resting_voltage
        raw_gauge_pressure = voltage_delta * self._BAR_PER_VOLT
        
        # 3. Apply the exponential moving average filter for smoothing
        self._filtered_pressure = (self.alpha * raw_gauge_pressure) + ((1 - self.alpha) * self._filtered_pressure)
        
        return self._filtered_pressure
    
if __name__ == "__main__":
    try:
        sensor = PressureSensor(adc_pin_number=27)
        print("PressureSensor class initialized.")

        # 2. IMPORTANT: Tare the sensor to set the current atmospheric
        #    pressure as the zero-point. This should only be done once.
        sensor.tare()
        
        utime.sleep(1) # Pause for a second before starting measurements
        print("\n--- Starting Live Gauge Pressure Readings ---")
        time_step = 0

        # 3. Loop and read the useful GAUGE pressure
        while True:
            # The .pressure property now correctly gives you pressure above atmosphere
            current_gauge_pressure = sensor.pressure
            diagnostics = sensor.read_diagnostics()
            # Print the detailed dictionary
            print(f"RAW: {diagnostics['raw_adc']}\t Pico Pin: {diagnostics['pico_pin_voltage']}\t Sensor: {diagnostics['sensor_voltage']} at timestep: {time_step}")            
            print(f"Gauge Pressure: {current_gauge_pressure:.3f} Bar at timestep: {time_step}")
            time_step+=1
            
            utime.sleep(0.5)

    except Exception as e:
        print(f"An error occurred: {e}")