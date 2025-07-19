# test MH-Z19
from machine import UART, Pin
import time

uart = UART(1, baudrate=9600, tx=Pin(17), rx=Pin(16))

def read_co2():
    cmd = b'\xFF\x01\x86\x00\x00\x00\x00\x00\x79'
    uart.write(cmd)
    time.sleep(0.1)
    if uart.any():
        response = uart.read(9)
        # print(response)
        if response and len(response) == 9 and response[0] == 0xFF and response[1] == 0x86:
            co2 = response[2]*256 + response[3]
            return co2
    return None

while True:
    co2 = read_co2()
    if co2:
        print("CO₂濃度:", co2, "ppm")
    else:
        print("読み取り失敗")
    time.sleep(3)
