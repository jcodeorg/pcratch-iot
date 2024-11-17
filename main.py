# ESP32C6 BLE pcratch(micro:bit) v1.0.3
from machine import Pin, I2C, ADC, PWM
import sys

# ruff: noqa: E402
sys.path.append("")
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel
from ahtx0 import AHT20
import asyncio
from ble_ext import BLEDevice
import struct


conn = BLEDevice()

# This would be periodically polling a hardware sensor.
def send_sensor_value():
    # ピンの値を読み取って、デジタル入力データ (32ビット)のビットフィールドに格納
    gpio_data = (
        (pin3.value() << 0) |
        (pin5.value() << 1) |
        (pin7.value() << 2)
    )
    button_state = 0x00  # ボタンの状態 (24ビット)
    light_level = int(adc1.read()/4095*255)  # 明るさ (8ビット)
    temperature = int(adc0.read()/4095*255)  # 温度(0～255)
    sound_level = 0  # 音レベル (8ビット)
    buffer = struct.pack('<I3B', gpio_data, light_level, temperature, sound_level)
    conn.state_write(buffer)

# ESP32C6 Pin layout
#
# GPIO0 :A0 :       5V
# GPIO1 :A1 :       GND
# GPIO2 :A2 :       3V3
# GPIO21:   :       GPIO18:   :
# GPIO22:SDA:       GPIO20:   :
# GPIO23:SDL:       GPIO19:   :
# GPIO16:TX :       GPIO17:RX :

# 人感センサ
am312 = ADC(Pin(0, Pin.IN))
am312.atten(ADC.ATTN_6DB)    # 6dBの入力減衰率を設定
# am312.width(ADC.WIDTH_12BIT)   # 12ビットの戻り値を設定(戻り値の範囲 0-4095)
# 温度なし
adc0 = ADC(Pin(1, Pin.IN))
#adc0.atten(ADC.ATTN_6DB)
#adc0.width(ADC.WIDTH_12BIT)   # 12ビットの戻り値を設定(戻り値の範囲 0-4095)
# 明るさ
adc1 = ADC(Pin(2, Pin.IN))
adc1.atten(ADC.ATTN_11DB)    # 11dBの入力減衰率を設定(電圧範囲はおよそ 0.0v - 3.6v)
adc1.width(ADC.WIDTH_12BIT)   # 12ビットの戻り値を設定(戻り値の範囲 0-4095)
# スピーカー
sp01 = PWM(Pin(19, Pin.OUT), freq=440, duty=0)	# スピーカー
# I2C
SDA = 22
SCL = 23
# Pin.IN
pin3 = Pin(17, Pin.IN, Pin.PULL_UP)	# スイッチ
pin5 = Pin(21, Pin.IN, Pin.PULL_UP)	# スイッチ
pin7 = Pin(18, Pin.IN, Pin.PULL_UP)	# スイッチ
# 
np = NeoPixel(Pin(16, Pin.OUT), 4)	# GPIO 21 番に NeoPixel が4個接続されている

i2c = I2C(0, scl=Pin(SCL), sda=Pin(SDA)) # I2C初期化
display = SSD1306_I2C(128, 64, i2c) #(幅, 高さ, I2Cオブジェクト)

def playtone(frequency, vol):
    sp01.freq(int(frequency))  # Hz
    sp01.duty_u16(int(vol*300))      #


def rgb(r, g, b):
    return (g, r, b)

# n番目のNeoPixcelを 赤、緑、青 0から255
def pixcel(n, r, g, b):
    np[n] = rgb(int(r/100*255), int(g/100*255),int(b/100*255))        # n番の NeoPixel を点灯
    np.write()
pixcel(0, 0, 0, 0)

# 音
def _playTone(f, v):
    sp01.freq(int(f))       	# Hz
    sp01.duty_u16(int(v * 65535 / 100))	#

def cb03( pin ):
    send_sensor_value() # BLE
    if pin.value()==0:
        if str(pin) == 'Pin(17)':
            _playTone(392, 50)	# G 392
            pixcel(0, 100, 0, 0)
            pixcel(1, 50, 0, 50)
        elif str(pin) == 'Pin(18)':
            _playTone(329, 50)	# G 392
            pixcel(0, 0, 100, 0)
            pixcel(1, 50, 50, 0)
        else:
            _playTone(440, 50)	# G 392
            pixcel(0, 0, 0, 100)
            pixcel(1, 0, 50, 50)
    else:
        _playTone(440, 0)
        pixcel(0, 0, 0, 0)
        pixcel(1, 0, 0, 0)


pin3.irq(cb03)
pin5.irq(cb03)
pin7.irq(cb03)


# 明るさ
def lux():
    val = adc1.read_u16()/ 65535 * 3.6 * 20/9/10000 * ( 10 ** 6)
    return val

aht21 = AHT20(i2c)

async def disp_task():
    while True:
        temperature = aht21.temperature
        humidity = aht21.relative_humidity
        temp ="temp:{:6.1f}".format(temperature)
        humi ="hum :{:6.1f}".format(humidity)
        lx   ="lx:  {:6.0f}".format(lux())
        # 人感センサーから16ビットのデータを読み取る
        hs_value = am312.read_u16()
        hs = "Human:{:05d}".format(hs_value)
        sound = adc0.read_u16()
        sd = "A1   :{:05d}".format(sound)
        #print(sound)
        #print(am312.read_u16())
        display.fill(0)
        display.text("Hello Pcratch!", 0, 0)
        display.text(temp, 0, 8*2)
        display.text(humi, 0, 8*3)
        display.text(lx, 0, 8*4)
        display.text(hs, 0, 8*5)
        display.text(sd, 0, 8*6)
        display.show()
        await asyncio.sleep_ms(500)

def do_command(data):
    print(data)
    # Base64 エンコード
    #binary_data = ubinascii.b2a_base64(data).strip()
    #print(binary_data)  # 出力: b'\x01Hello'
    # バイナリデータをリストに変換
    data_list = list(data)
    print(data_list)  # 出力: [1, 72, 101, 108, 108, 111]
    # データを分割して表示
    #command_id = data_list[0]
    #command_message = data_list[1:]
    #print("Command ID:", command_id)  # 出力: Command ID: 1
    #print("Command Message:", command_message)  # 出力: Command Message: [72, 101, 108, 108, 111]
    command_id = data_list[0]
    print(command_id)
    command_message = data[1:]
    if command_id == 65:
        #print("文字", data[2:].decode('utf-8'),"間隔", data[1]*10)
        display.fill(0)
        display.text(data[2:].decode('utf-8'), 0, data[1]*10)
        display.show()
    elif command_id == 97:
        # data[2:] から4バイトを取得
        four_bytes = data[1:5]
        # 4バイトを uint32 の数値に変換
        uint32_value = struct.unpack('<I', four_bytes)[0]
        #print("音", 1000000 / uint32_value, "大きさ", data[5]/255*100)
        playtone(1000000 / uint32_value, data[5]/255*100)
    elif command_id == 3:
        print("Command ID 3: Thank you")
    elif command_id == 4:
        print("Command ID 4: Sorry")
    else:
        print("Command ID", command_id, "is not defined.")


async def sensor_task():
    while True:
        send_sensor_value()
        await asyncio.sleep_ms(500)


async def main():
    t1 = asyncio.create_task(conn.ble_task(do_command))
    t2 = asyncio.create_task(disp_task())
    t3 = asyncio.create_task(sensor_task())
    await asyncio.gather(t1, t2, t3)

asyncio.run(main())
