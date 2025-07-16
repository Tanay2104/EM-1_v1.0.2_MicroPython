# --- START OF FILE motor.py ---

import machine
import rp2
import utime

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def _pio_pulser():
    # type: ignore
    """
    PIO program to generate a continuous square wave on a 'set' pin.
    
    The frequency of this square wave is controlled by the state machine's clock
    frequency, which can be set dynamically from the main Python code.
    
    This program takes exactly 2 cycles to complete one full pulse (high and low).
    - 1 cycle for set(pins, 1)
    - 1 cycle for set(pins, 0)
    This is important for calculating the required PIO frequency.
    """
    wrap_target()
    set(pins, 1)  # Set pin high
    set(pins, 0)  # Set pin low
    wrap()

class Motor:
    """
    A non-blocking Stepper Motor driver using the Raspberry Pi Pico's PIO.
    
    This class abstracts the stepper driver (like a TMC2208 or A4988) by using a
    PIO state machine to generate step pulses in the background. This frees up
    the main CPU to perform other tasks, such as running a PID control loop,
    without being blocked by 'time.sleep()' calls.
    
    The speed of the motor is controlled by adjusting the frequency of the PIO
    state machine.

    #The stepper motor is a Nema 17 0.42 kgcm motor, with a 1.5 times speed reducer.  This then drives a Tr8x2 lead screw.
    """
    # The number of PIO cycles our simple pulser program takes for one pulse.
    # Our _pio_pulser program takes 2 cycles (one for high, one for low).
    _CYCLES_PER_PULSE = 2

    def __init__(self, step_pin: int, dir_pin: int, en_pin: int, sm_id: int = 0):
        """
        Initializes the Motor driver.
        
        Args:
            step_pin (int): The GPIO pin number connected to the driver's STEP input.
            dir_pin (int): The GPIO pin number connected to the driver's DIR input.
            en_pin (int): The GPIO pin number connected to the driver's ENABLE input.
            sm_id (int): The ID of the PIO state machine to use (0-7). Defaults to 0.
        """
        # --- 1. Initialize GPIO Pins ---
        self.step_pin = machine.Pin(step_pin, machine.Pin.OUT)
        self.dir_pin = machine.Pin(dir_pin, machine.Pin.OUT)
        self.en_pin = machine.Pin(en_pin, machine.Pin.OUT)
        
        # --- 2. Set Initial Motor State ---
        # By default, the driver is disabled to save power and prevent heat.
        # The motor will hold no torque.
        self.en_pin.value(1) # Most drivers are enabled on LOW, so HIGH is disabled.
        self.dir_pin.value(0) # Default to one direction.
        
        # --- 3. Initialize the PIO State Machine ---
        # This configures the PIO but does not start it yet.
        # - sm_id: Which of the 8 state machines to use.
        # - _pio_pulser: The PIO assembly program we defined above.
        # - freq: We start with a placeholder frequency. This will be updated.
        # - set_base: The GPIO pin the PIO's 'set()' instructions will control.
        self.sm = rp2.StateMachine(sm_id, _pio_pulser, freq=10000, set_base=self.step_pin)
        
        print(f"Motor initialized on STEP={step_pin}, DIR={dir_pin}, EN={en_pin}")
        # Stop the motor to ensure it's in a known state on startup.
        self.stop()

    def set_speed(self, speed: float, direction: int = None):
        """
        Sets the motor's speed and direction. This is a NON-BLOCKING operation.
        
        Args:
            speed (float): The desired speed in steps per second.
                           A negative value will reverse the direction.
            direction (int, optional): Explicitly set direction. 0 or 1.
                                       If None, direction is determined by the
                                       sign of the speed.
        """
        # --- 1. Set Direction ---
        if direction is not None:
            self.dir_pin.value(direction)
        else:
            # If speed is negative, set direction to 1 (reverse), else 0 (forward).
            self.dir_pin.value(1 if speed < 0 else 0)
        
        # --- 2. Handle Stopping the Motor ---
        # If speed is 0, simply call the stop() method and exit.
        if speed == 0:
            self.stop()
            return
            
        # --- 3. Calculate PIO Frequency and Re-init State Machine ---
        # The core of the non-blocking control.
        # We calculate the frequency the PIO needs to run at to produce the
        # desired number of steps per second.
        # PIO Frequency = (Steps per Second) * (PIO Cycles per Step)
        
        # Use abs(speed) because frequency must be positive.
        pio_frequency = int(abs(speed) * self._CYCLES_PER_PULSE)

        
        # The PIO frequency must be between ~2kHz and 125MHz.
        # We clamp the value to prevent errors if a crazy speed is requested.
        # A min frequency of 1000 means the slowest speed is 500 steps/sec.
        # Adjust this if you need slower movement.
        MIN_PIO_FREQ = 2000
        if pio_frequency < MIN_PIO_FREQ:
            pio_frequency = MIN_PIO_FREQ

        print(f"[DEBUG] Setting PIO frequency to: {pio_frequency} Hz")

            
        # Re-initialize the state machine with the new frequency. This is very fast.
        try:
            self.sm.init(_pio_pulser, freq=pio_frequency, set_base=self.step_pin)

        except Exception as e:
            print(f"[ERROR] Failed to set PIO frequency. Value was: {pio_frequency}. Error: {e}")
            self.stop()
            # Re-raise the exception so the calling code knows something went wrong
            raise
        
        # --- 4. Activate the Motor ---
        # Enable the motor driver (set EN pin to LOW).
        self.en_pin.value(0)
        # Start the PIO state machine. It will now generate pulses independently.
        self.sm.active(1)

    def stop(self):
        """
        Stops the motor immediately and disables the driver.
        """
        # Deactivate the PIO state machine. Pulse generation ceases.
        self.sm.active(0)
        # Disable the motor driver to save power and reduce heat.
        self.en_pin.value(1)

    def home(self, home_switch_pin: int):
        """
        A simple, blocking homing routine.
        
        This is an exception to the non-blocking rule, as homing is a one-time
        setup operation, not part of the real-time brew cycle.
        
        Args:
            home_switch_pin (int): The GPIO pin connected to the homing limit switch.
                                   Assumes the switch is pulled high and goes low
                                   when pressed.
        """
        print("Homing motor...")
        limit_switch = machine.Pin(home_switch_pin, machine.Pin.IN, machine.Pin.PULL_UP)
        
        # Set a slow homing speed and direction
        homing_speed = -500 # steps/sec (negative for reverse)
        self.set_speed(homing_speed)
        
        # Wait until the limit switch is pressed (goes from HIGH to LOW)
        while limit_switch.value() == 1:
            utime.sleep_ms(5) # Small delay to prevent busy-waiting
            
        self.stop()
        print("Homing complete.")

    def convert_pid_to_speed(self, pid_input):
        """
        This function converts the pid output value to motor speed. This is to be implemented later
        """
        return pid_input*10
        

# --- Example Usage ---
# This block demonstrates how to use the Motor class. It will not run when imported.
if __name__ == '__main__':
    # Configure your motor pins according to your wiring.
    # These are example pins, change them to match your setup.
    STEP_PIN = 18
    DIR_PIN = 5
    EN_PIN = 19
    
    try:
        # Create an instance of our non-blocking motor driver
        motor = Motor(step_pin=STEP_PIN, dir_pin=DIR_PIN, en_pin=EN_PIN, sm_id=0)
        
        print("\n--- Running Motor Demo ---")
        
        print("Running forward at 1600 steps/sec for 2 seconds...")
        motor.set_speed(1600, direction=0)
        utime.sleep(2) # Main CPU is free to sleep here, PIO runs in background
        
        print("Running backward at 3200 steps/sec for 3 seconds...")
        motor.set_speed(-3200) # Using negative speed to set direction
        utime.sleep(3)
        
        print("Ramping speed up and down...")
        for speed in range(500, 5000, 100):
            motor.set_speed(speed)
            utime.sleep_ms(20)
        for speed in range(5000, 500, -100):
            motor.set_speed(speed)
            utime.sleep_ms(20)
            
        print("Stopping motor.")
        motor.stop()
        
    except Exception as e:
        print(f"An error occurred: {e}")
        # Make sure motor is stopped in case of an error
        # motor.stop() # This would require motor to be defined outside try