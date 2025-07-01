# main.py

import machine
import utime
from temp_sensor import MAX31865 # Import your sensor class
from utils.pid import PID               # Import your PID class

# --- HARDWARE SETUP ---
# 1. Setup the Heater Pin (e.g., connected to a MOSFET or relay on GP15)
heater_pin = machine.Pin("LED", machine.Pin.OUT)

# 2. Setup the Temperature Sensor
spi = machine.SPI(0, baudrate=1000000, sck=machine.Pin(2), mosi=machine.Pin(3), miso=machine.Pin(4))
cs_pin = machine.Pin(5, machine.Pin.OUT)
# For your PT1000 sensor
temp_sensor = MAX31865(spi, cs_pin, wires=2, r_nominal=1000.0, r_ref=4300.0)

# --- CONTROL SETUP ---
# 3. Setup the PID Controller
# These constants (P, I, D) will need tuning! Start with small values.
pid = PID(proportional_const=1.5, integral_const=0.1, differential_const=0.5, set_point=80.0) # Target: 80.0°C

# --- MAIN LOOP ---
print("Starting temperature control loop...")

while True:
    # 1. MEASURE: Get the current temperature.
    # The '.temperature' is a "property". It looks like a variable,
    # but it runs all the complex read functions behind the scenes!
    current_temp = temp_sensor.temperature
    
    # Always check if the reading is valid!
    if current_temp is None:
        print("Fault detected from temperature sensor! Turning heater off.")
        heater_pin.value(0) # Safety first!
        utime.sleep(2)      # Wait before trying again
        continue            # Skip the rest of this loop iteration

    # 2. DECIDE: Feed the current temperature into the PID controller.
    # It will return a control value. A positive value means "needs heat",
    # a negative value means "too hot".
    control_output = pid.update(current_temp)

    # Print the status for monitoring
    print(f"Set Point: {pid.set_point}°C, Current Temp: {current_temp:.2f}°C, PID Output: {control_output:.2f}")

    # 3. ACT: Decide whether to turn the heater on or off.
    # This is a simple "On/Off" or "Bang-Bang" control based on the PID output.
    if control_output > 0:
        # The PID controller says we are below the set point and need heat.
        heater_pin.value(1) # Turn heater ON
        print("Heater: ON")
    else:
        # The PID controller says we are at or above the set point.
        heater_pin.value(0) # Turn heater OFF
        print("Heater: OFF")
        
    # 4. WAIT: Pause for a moment before the next cycle.
    # This sample_time is important for PID stability.
    # Don't make it too fast or too slow. 1-2 seconds is a good start.
    utime.sleep(1) 