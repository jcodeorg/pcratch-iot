from machine import Pin
import time

# GPIO17 を入力（プルダウン）に設定
switch = Pin(17, Pin.IN, Pin.PULL_DOWN)

while True:
    if switch.value() == 0:
        print("SWITCH: OFF")
    else:
        print("SWITCH: ON")
    time.sleep(0.5)
