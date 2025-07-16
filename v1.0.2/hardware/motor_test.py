# --- START OF FILE motor_test.py ---

from hardware.motor import Motor
import utime

# --- Configuration ---
# These are the GPIO pins we chose in the wiring step.
# If you used different pins, change them here.
STEP_PIN = 18
DIR_PIN = 5
EN_PIN = 19

print("--- Stepper Motor Test ---")

try:
    # 1. Initialize the Motor class with our pin configuration
    step_motor = Motor(step_pin=STEP_PIN, dir_pin=DIR_PIN, en_pin=EN_PIN)

    # 2. Run a simple movement sequence
    print("Turning FORWARD at 800 steps/sec for 3 seconds...")
    step_motor.set_speed(800)
    utime.sleep(30)

    print("Turning BACKWARD at 1600 steps/sec for 3 seconds...")
    step_motor.set_speed(-1600) # Negative speed reverses direction
    utime.sleep(30)

    # 3. Stop the motor. This is important!
    print("Stopping motor.")
    step_motor.stop()
    
    print("\nTest complete.")

except Exception as e:
    print(f"\nAn error occurred: {e}")
    # In case of an error, it's good practice to try to stop the motor
    # This requires 'motor' to be defined, so it's best inside the try block for now.
    if 'motor' in locals():
        step_motor.stop()