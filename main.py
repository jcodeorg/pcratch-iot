# ESP32C6 BLE pcratch(micro:bit) v1.0.3
from machine import Pin, I2C, ADC, PWM
import sys

# ruff: noqa: E402
sys.path.append("")

from micropython import const

import asyncio
import aioble
import bluetooth

import random
import struct
import ubinascii
import network
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel

# デバイス名を設定
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
mac = wlan.config('mac')
mac_str = ubinascii.hexlify(mac).decode('utf-8').upper()
_NAME = f"BBC micro:bit [{mac_str}]"

# サービスUUIDと characteristic UUID を定義
_IOT_SERVICE_UUID = bluetooth.UUID('0b50f3e4-607f-4151-9091-7d008d6ffc5c')
_IOT_COMMAND_CH__UUID = bluetooth.UUID('0b500100-607f-4151-9091-7d008d6ffc5c')
_IOT_STATE_CH_UUID = bluetooth.UUID('0b500101-607f-4151-9091-7d008d6ffc5c')
_IOT_MOTION_CH_UUID = bluetooth.UUID('0b500102-607f-4151-9091-7d008d6ffc5c')
_IOT_PINEVENT_CH_UUID = bluetooth.UUID('0b500110-607f-4151-9091-7d008d6ffc5c')
_IOT_ACTIONEVENT_CH_UUID = bluetooth.UUID('0b500111-607f-4151-9091-7d008d6ffc5c')
_IOT_ANALOGIN0_CH_UUID = bluetooth.UUID('0b500120-607f-4151-9091-7d008d6ffc5c')
_IOT_ANALOGIN1_CH_UUID = bluetooth.UUID('0b500121-607f-4151-9091-7d008d6ffc5c')
_IOT_ANALOGIN2_CH_UUID = bluetooth.UUID('0b500122-607f-4151-9091-7d008d6ffc5c')
_IOT_MESSAGE_CH_UUID = bluetooth.UUID('0b500130-607f-4151-9091-7d008d6ffc5c')

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_TAG = const(512)
# How frequently to send advertising beacons.
_ADV_INTERVAL_MS = 250_000

# サービスと characteristic を定義
iot_service = aioble.Service(_IOT_SERVICE_UUID)
command_characteristic = aioble.Characteristic(
    iot_service, _IOT_COMMAND_CH__UUID, read=True, write=True
)
state_characteristic = aioble.Characteristic(
    iot_service, _IOT_STATE_CH_UUID, read=True
)
motion_characteristic = aioble.Characteristic(
    iot_service, _IOT_MOTION_CH_UUID, read=True
)
pinevent_characteristic = aioble.Characteristic(
    iot_service, _IOT_PINEVENT_CH_UUID, read=True, notify=True
)
actionevent_characteristic = aioble.Characteristic(
    iot_service, _IOT_ACTIONEVENT_CH_UUID, read=True, notify=True
)
analog0_characteristic = aioble.Characteristic(
    iot_service, _IOT_ANALOGIN0_CH_UUID, read=True, notify=True
)
analog1_characteristic = aioble.Characteristic(
    iot_service, _IOT_ANALOGIN1_CH_UUID, read=True, notify=True
)
analog2_characteristic = aioble.Characteristic(
    iot_service, _IOT_ANALOGIN2_CH_UUID, read=True, notify=True
)
message_characteristic = aioble.Characteristic(
    iot_service, _IOT_MESSAGE_CH_UUID, read=True, notify=True
)
aioble.register_services(iot_service)

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
    state_characteristic.write(buffer, send_update=True)

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

async def sensor_task():
    while True:
        send_sensor_value()
        await asyncio.sleep_ms(500)

# Serially wait for connections. Don't advertise while a central is
# connected.
async def peripheral_task():
    while True:
        try:
            async with await aioble.advertise(
                _ADV_INTERVAL_MS,
                name=_NAME,
                services=[_IOT_SERVICE_UUID],
                appearance=_ADV_APPEARANCE_GENERIC_TAG,
            ) as connection:
                print("Connection from", connection.device)
                # 送信する3バイトのデータを定義
                data_to_send = struct.pack('<BBB', 0x01, 0x02, 0x03)
                command_characteristic.write(data_to_send)
                print("3バイト送信...") # 3バイトのデータを送信
                await connection.disconnected(timeout_ms=None)
                print("Disconnected.")
        except Exception as e:
            print("Error during advertising or connection:", e)
            await asyncio.sleep_ms(1000)


async def motion_task():
    while True:
        #print(i, "motion_characteristic")
        # 送信する2バイトのデータを9個定義（すべての値がゼロ）
        data_to_send = struct.pack('<9H', *([0] * 9))
        motion_characteristic.write(data_to_send)
        await asyncio.sleep_ms(1000)

async def command_task():
    while True:
        # コマンドを待つ
        await command_characteristic.written()
        data = command_characteristic.read()
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

# 明るさ
def lux():
    val = adc1.read_u16()/ 65535 * 3.6 * 20/9/10000 * ( 10 ** 6)
    return val

from ahtx0 import AHT20
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



# Run both tasks.
async def main():
    t1 = asyncio.create_task(sensor_task())
    t2 = asyncio.create_task(motion_task())
    t3 = asyncio.create_task(peripheral_task())
    t4 = asyncio.create_task(command_task())
    t5 = asyncio.create_task(disp_task())
    await asyncio.gather(t1, t2, t3, t4, t5)


asyncio.run(main())
# ESP32C6 BLE pcratch(micro:bit) v1.0.3
