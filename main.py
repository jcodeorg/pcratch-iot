# ESP32C6 BLE pcratch(micro:bit) v1.0.3
import os
import sys
import struct
import asyncio
import time
from machine import Pin, I2C, ADC, PWM
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel
from ahtx0 import AHT20
from ble_conn import BLEConnection

# BLEConnection クラスのインスタンスを作成
ble_conn = BLEConnection()

# デバイス情報を取得
def get_device_info():
    info = os.uname()
    return {
        "sysname": info.sysname,
        "nodename": info.nodename,
        "release": info.release,
        "version": info.version,
        "machine": info.machine
    }

device_info = get_device_info()
if 'ESP32C6' in device_info['machine']:
    print("Welcome to ESP32C6")
    # ESP32C6 Pin layout
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
    # アナログ未利用
    adc0 = ADC(Pin(1, Pin.IN))
    #adc0.atten(ADC.ATTN_6DB)
    #adc0.width(ADC.WIDTH_12BIT)   # 12ビットの戻り値を設定(戻り値の範囲 0-4095)
    # 明るさ
    adc1 = ADC(Pin(2, Pin.IN))
    adc1.atten(ADC.ATTN_11DB)    # 11dBの入力減衰率を設定(電圧範囲はおよそ 0.0v - 3.6v)
    adc1.width(ADC.WIDTH_12BIT)   # 12ビットの戻り値を設定(戻り値の範囲 0-4095)
    # スピーカー
    p00 = PWM(Pin(21, Pin.OUT), freq=440, duty=0)	# P00=スピーカー
    p01 = PWM(Pin(19, Pin.OUT), freq=440, duty=0)	# P01
    p02 = PWM(Pin(20, Pin.OUT), freq=440, duty=0)	# P02
    # Pin.IN
    BTNA = 'Pin(17)'
    BTNB = 'Pin(18)'
    PIN7NAME = 'Pin(21)'
    button_a = Pin(17, Pin.IN, Pin.PULL_UP)	# スイッチ
    # pin5 = Pin(21, Pin.IN, Pin.PULL_UP)	# スイッチ
    button_b = Pin(18, Pin.IN, Pin.PULL_UP)	# スイッチ
    # 
    np = NeoPixel(Pin(16, Pin.OUT), 4)	# GPIO 21 番に NeoPixel が4個接続されている
    # I2C
    i2c = I2C(0, scl=Pin(23), sda=Pin(22)) # I2C初期化
    try:
        oled = SSD1306_I2C(128, 64, i2c)  #(幅, 高さ, I2Cオブジェクト)
        # 画面をさかさまにするコマンドを送信
        oled.write_cmd(0xA0)  # セグメントリマップ
        oled.write_cmd(0xC0)  # COM出力スキャン方向
    except Exception as e:
        print(f"Error initializing oled: {e}")
        oled = None  # oledをNoneに設定してプログラムが続行できるようにする

    # AHT20 センサー
    aht21 = AHT20(i2c)

elif 'Raspberry Pi Pico W with RP2040' in device_info['machine']:
    # 人感センサ
    am312 = None

    # am312.width(ADC.WIDTH_12BIT)   # 12ビットの戻り値を設定(戻り値の範囲 0-4095)
    # 明るさ
    adc1 = ADC(0)
    # アナログ未利用
    adc0 = ADC(1)
    # スピーカー
    p00 = PWM(Pin(2, Pin.OUT))
    # Pin.IN
    BTNA = 'Pin(GPIO3, mode=IN, pull=PULL_UP)'
    BTNB = 'Pin(GPIO5, mode=IN, pull=PULL_UP)'
    PIN7NAME = 'Pin(GPIO7, mode=IN, pull=PULL_UP)'
    button_a = Pin(3, Pin.IN, Pin.PULL_UP)	# スイッチ
    #pin5 = Pin(5, Pin.IN, Pin.PULL_UP)	# スイッチ
    button_b = Pin(7, Pin.IN, Pin.PULL_UP)	# スイッチ
    # 
    np = NeoPixel(Pin(21, Pin.OUT), 4)	# GPIO 21 番に NeoPixel が4個接続されている
    # I2C
    i2c = I2C(0, scl=Pin(1), sda=Pin(0)) # I2C初期化
    oled = SSD1306_I2C(128, 64, i2c) #(幅, 高さ, I2Cオブジェクト)
    aht21 = AHT20(i2c)

    # VSYS電源電圧を取得する
    def getVsys():
        Pin(29, Pin.IN)
        volt = ADC(3).read_u16() / 65535 * 3.3 * 3
        return volt

else:
    print("This device is not supported.:", device_info['machine'])


# This would be periodically polling a hardware sensor.
def send_sensor_value():
    # state_characteristic に write する
    # gpio_data(32bit) light_level(8bit) temperature(8bit) sound_level(8bit)
    # ピンの値を読み取って、デジタル入力データ (32ビット)のビットフィールドに格納
    gpio_data = (
        (button_a.value() << 0) |
        # (pin5.value() << 1) |
        (button_b.value() << 2)
    )
    button_state = 0x00  # ボタンの状態 (24ビット)
    # light_level = int(adc1.read_u16()/65535*100)  # 明るさ (8ビット)
    light_level = int(lux())  # 明るさ (8ビット)
    light_level = max(0, min(255, light_level))  # 0から255の範囲に制限
    temperature = int(adc0.read_u16()/65535*100)  # 温度(0～255)
    sound_level = 0  # 音レベル (8ビット)
    buffer = struct.pack('<I3B', gpio_data, light_level, temperature, sound_level)
    # TODO: 送信するデータを更新
    ble_conn.state_write(buffer)

#
def playtone(frequency, vol):
    p00.freq(int(frequency))  # Hz
    p00.duty_u16(int(vol*300))      #


def rgb(r, g, b):
    return (g, r, b)

# n番目のNeoPixcelを 赤、緑、青 0から255
def pixcel(n, r, g, b):
    np[n] = rgb(int(r/100*255), int(g/100*255),int(b/100*255))        # n番の NeoPixel を点灯
    np.write()
pixcel(0, 0, 0, 0)

# 音
def _playTone(f, v):
    p00.freq(int(f))       	# Hz
    p00.duty_u16(int(v * 65535 / 100))	#

MbitMoreDataFormat = {
    "CONFIG": 0x10,     # not used at this version
    "PIN_EVENT": 0x11,
    "ACTION_EVENT": 0x12,
    "DATA_NUMBER": 0x13,
    "DATA_TEXT": 0x14
}
MbitMoreActionEvent = {
  "BUTTON": 0x01,
  "GESTURE": 0x02
}
MbitMoreButtonID = {
    1: 'A',
    2: 'B',
    100: 'P0',
    101: 'P1',
    102: 'P2',
    121: 'LOGO'
}
MbitMoreButtonName = {v: k for k, v in MbitMoreButtonID.items()}

MbitMoreButtonEventID = {
    1: 'DOWN',
    2: 'UP',
    3: 'CLICK',
    4: 'LONG_CLICK',
    5: 'HOLD',
    6: 'DOUBLE_CLICK'
}
# キーと値を入れ替えた辞書を定義
MbitMoreButtonEventName = {v: k for k, v in MbitMoreButtonEventID.items()}


# const dataFormat = dataView.getUint8(19);
# dataFormat === MbitMoreDataFormat.ACTION_EVENT
# button A が押されたときの処理
# const actionEventType = dataView.getUint8(0);

def on_press_a222():
    # バッファを定義して19バイト目をACTION_EVENTにする
    # print("Buffer dump:")
    buffer = bytearray(20)
    buffer[19] = MbitMoreDataFormat["ACTION_EVENT"]
    action = MbitMoreActionEvent["BUTTON"]      # byte
    button = MbitMoreButtonName["A"]            # uint16
    event = MbitMoreButtonEventName["DOWN"]     # byte
    timestamp = int(time.time())                # uint32
    packed_data = struct.pack('<BHBI', action, button, event, timestamp)
    buffer[0:8] = packed_data
    # print("Buffer dump:", buffer)
    ble_conn.send_notification(buffer)

def on_release_a222():
    pass


def cb03( pin ):
    # send_sensor_value() # BLE
    # print(str(pin))
    if pin.value()==0:
        if str(pin) == BTNA:    # Button A
            # print("on_press_a")
            # on_press_a()
            # print("on_press_a done")
            _playTone(392, 50)	# G 392
            pixcel(0, 100, 0, 0)
            pixcel(1, 0, 100, 0)
            pixcel(2, 0, 0, 100)
        elif str(pin) == BTNB:  # Button B
            # on_press_b()
            _playTone(329, 50)	# G 392
            pixcel(2, 100, 0, 0)
            pixcel(0, 0, 100, 0)
            pixcel(1, 0, 0, 100)
        else:
            _playTone(440, 50)	# G 392
            pixcel(1, 100, 0, 0)
            pixcel(2, 0, 100, 0)
            pixcel(0, 0, 0, 100)
    else:
        # on_release_a()
        _playTone(440, 0)
        pixcel(0, 0, 0, 0)
        pixcel(1, 0, 0, 0)
        pixcel(2, 0, 0, 0)



def send_notification222(buffer):
    # asyncio.create_task(ble_conn.async_send_notification(buffer))
    ble_conn.send_notification(buffer)

# 0: actionEventType=MbitMoreActionEvent.BUTTON
# 1-2: const buttonName = MbitMoreButtonID[dataView.getUint16(1, true)];
# 3: const eventName = MbitMoreButtonEventID[dataView.getUint8(3)];
# 4-7: this.buttonEvents[buttonName][eventName] = dataView.getUint32(4, true); // Timestamp
def button_notification(buttonName, eventName):
    # バッファを定義して19バイト目をACTION_EVENTにする
    buffer = bytearray(20)
    buffer[19] = MbitMoreDataFormat["ACTION_EVENT"]
    action = MbitMoreActionEvent["BUTTON"]      # 0: byte
    button = MbitMoreButtonName[buttonName]     # 1-2: uint16
    event = MbitMoreButtonEventName[eventName]  # 3: byte
    timestamp = time.ticks_ms()                 # 4-7: uint32
    packed_data = struct.pack('<BHBI', action, button, event, timestamp)
    buffer[0:8] = packed_data
    # print("Buffer dump:", buffer)
    ble_conn.send_notification(buffer)

# ボタンの状態を保持する変数
button_state = {
    'A': {'pressed': False, 'press_time': 0, 'down_count': 0},
    'B': {'pressed': False, 'press_time': 0, 'down_count': 0}
}

# ボタンの処理
def handle_button_event(pin, button_name):
    global button_state
    if pin.value() == 0:  # ボタンが押された
        if not button_state[button_name]['pressed']:
            button_state[button_name]['pressed'] = True
            button_state[button_name]['press_time'] = time.ticks_ms()
            button_state[button_name]['down_count'] += 1
            print(f"Button {button_name} DOWN, Count: {button_state[button_name]['down_count']}")
            # DOWNイベントの処理
            button_notification(button_name, "DOWN")
    else:  # ボタンが離された
        if button_state[button_name]['pressed']:
            button_state[button_name]['pressed'] = False
            press_duration = time.ticks_diff(time.ticks_ms(), button_state[button_name]['press_time'])
            if press_duration < 500:
                # print(f"Button {button_name} CLICK")
                # CLICKイベントの処理
                button_notification(button_name, "CLICK")
                # ble_conn.send_notification(f'Button {button_name} CLICK'.encode())
            else:
                # print(f"Button {button_name} UP")
                # UPイベントの処理
                button_notification(button_name, "UP")
                # ble_conn.send_notification(f'Button {button_name} UP'.encode())

# IRQハンドラとして登録
button_a.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: handle_button_event(pin, 'A'))
button_b.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: handle_button_event(pin, 'B'))


# 明るさ
def lux():
    val = adc1.read_u16()/ 65535 * 3.6 * 20/9/10000 * ( 10 ** 6)
    return val


async def disp_task():
    while True:
        temperature = aht21.temperature
        humidity = aht21.relative_humidity
        temp ="temp:{:6.1f}".format(temperature)
        humi ="hum :{:6.1f}".format(humidity)
        lx   ="lx:  {:6.0f}".format(lux())
        # 人感センサーから16ビットのデータを読み取る
        hs_value = am312.read_u16() if am312 else 0
        hs = "Human:{:05d}".format(hs_value)
        sound = adc0.read_u16()
        sd = "A1   :{:05d}".format(sound)
        #print(sound)
        #print(am312.read_u16())
        # 上10ドットをそのままにして、下の部分だけ書き直す
        oled.fill_rect(0, 10, oled.width, oled.height - 10, 0)
        # oled.text(ble_conn.NAME[-16:], 0, 0)
        oled.text(temp, 0, 8*2)
        oled.text(humi, 0, 8*3)
        oled.text(lx, 0, 8*4)
        oled.text(hs, 0, 8*5)
        oled.text(sd, 0, 8*6)
        oled.show()
        await asyncio.sleep_ms(500)

# 文字 s を t ミリ秒間隔で流す
def scroll(s, t):
    print(f"文字 {s} を {t} ミリ秒間隔で流す")
    # 上10ドットを消去
    oled.fill_rect(0, 0, oled.width, 10, 0)
    oled.text(s, 0, 0)
    oled.show()

# ピン pin をアナログ出力 n %にする (n:0-1024)
# TODO: pin1->pin19, pin2->pin20にする
def analog_out(pin, n):
    # print(f"ピン {pin} をアナログ出力 {n} %にする")
    if pin == 0 or pin == 21:
        p00.duty_u16(int(65535 * n / 1024))
    elif pin == 1 or pin == 19:
        p01.duty_u16(int(65535 * n / 1024))
    elif pin == 2 or pin == 20:
        p02.duty_u16(int(65535 * n / 1024))

# コマンドを実行
def do_command(data):
    # print(data)
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
    # print(command_id)
    # command_message = data[1:]
    if command_id == 65:
        # 文字 s を t ミリ秒間隔で流す
        scroll(data[2:].decode('utf-8'), data[1])
    elif command_id == 34:
        # ピン pin をアナログ出力 n %にする
        pin = data[1]
        uint16_value = struct.unpack('<H', data[2:4])[0]     # 続く2バイトを数値に変換
        # print("ピン", pin, "をアナログ出力", uint16_value, "%にする")
        analog_out(pin, uint16_value)
    elif command_id == 97:
        # 1000000/data[1:5] Hzの音を data[5]/255*100 %の大きさで鳴らす
        four_bytes = data[1:5]  # data[2:] から4バイトを取得
        uint32_value = struct.unpack('<I', four_bytes)[0]   # 4バイトを uint32 の数値に変換
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
        await asyncio.sleep_ms(250)


async def main():
    t1 = asyncio.create_task(ble_conn.ble_task(do_command))
    t2 = asyncio.create_task(disp_task())
    t3 = asyncio.create_task(sensor_task())
    while True:
        await asyncio.sleep(1)
    # await asyncio.gather(t1, t2, t3)
    # print("main() done!!")

asyncio.run(main())
