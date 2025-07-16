from machine import Pin
from utime import sleep

pin = Pin("LED", Pin.OUT)
pin2 = Pin(22, Pin.OUT)

print("LED starts flashing...")
while True:
    try:
        pin.toggle()
        pin2.toggle()
        sleep(3) # sleep 3sec
    except KeyboardInterrupt:
        break
pin.off()
print("Finished.")
