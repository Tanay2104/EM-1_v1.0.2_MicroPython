from hardware.stepper import Stepper
import time

s1 = Stepper(step_pin=18,dir_pin=5, en_pin=19,steps_per_rev=200,speed_sps=100)

s1.target_deg(90)
time.sleep(5.0)
s1.target_deg(0)
time.sleep(5.0)
s1.free_run(1)