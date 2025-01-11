# ESP32C6 BLE pcratch-IoT(micro:bit) v1.1.3
import network
import os
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
device_info = os.uname()
if 'ESP32C6' in device_info.machine:
    # ESP32C6 Pin layout
    # GPIO0 :A0 :       5V
    # GPIO1 :A1 :       GND
    # GPIO2 :A2 :       3V3
    # GPIO21:   :       GPIO18:   :
    # GPIO22:SDA:       GPIO20:   :
    # GPIO23:SDL:       GPIO19:   :
    # GPIO16:TX :       GPIO17:RX :
    print("Welcome to ESP32C6")
    # ADC
    adc0 = Pin(0, Pin.IN, Pin.PULL_DOWN) # ADC0:人感センサ
    adc1 = ADC(Pin(1, Pin.IN))  # adc2:未使用
    adc2 = ADC(Pin(2, Pin.IN))  # ADC2:明るさ
    adc2.atten(ADC.ATTN_11DB)   # 11dBの入力減衰率を設定(電圧範囲はおよそ 0.0v - 3.6v)
    adc2.width(ADC.WIDTH_12BIT) # 12ビットの戻り値を設定(戻り値の範囲 0-4095)
    # Pin.OUT
    out0 = PWM(Pin(21, Pin.OUT), freq=50, duty=0)	# out0:スピーカー
    out1 = PWM(Pin(19, Pin.OUT), freq=50, duty=0)	# out1
    out2 = PWM(Pin(20, Pin.OUT), freq=50, duty=0)	# out2
    out3 = NeoPixel(Pin(16, Pin.OUT), 4)          	# out3:NeoPixel が4個接続されている
    # Pin.IN
    inp0 = Pin(17, Pin.IN, Pin.PULL_UP)	# ボタンA
    inp1 = Pin(20, Pin.IN, Pin.PULL_UP)	# ボタンB
    # I2C
    i2c = I2C(0, scl=Pin(23), sda=Pin(22))  # I2C初期化
    # oled ディスプレイ
    oled = None
    try:
        oled = SSD1306_I2C(128, 64, i2c)  #(幅, 高さ, I2Cオブジェクト)
        if True:
            pass
        else:
            # 画面をさかさまにするコマンドを送信
            oled.write_cmd(0xA0)  # セグメントリマップ
            oled.write_cmd(0xC0)  # COM出力スキャン方向
    except Exception as e:
        print(f"Error initializing oled: {e}")
    # AHT20 温湿度センサ
    aht20 = None
    try:
        aht20 = AHT20(i2c)        # AHT20 センサー
    except Exception as e:
        print(f"Error initializing aht20: {e}")

elif 'Raspberry Pi Pico W with RP2040' in device_info.machine:
    # 人感センサ
    adc0 = None

    # am312.width(ADC.WIDTH_12BIT)   # 12ビットの戻り値を設定(戻り値の範囲 0-4095)
    # 明るさ
    adc2 = ADC(0)
    # アナログ未利用
    adc1 = ADC(1)
    # スピーカー
    out0 = PWM(Pin(2, Pin.OUT))
    # Pin.IN
    inp0 = Pin(3, Pin.IN, Pin.PULL_UP)	# スイッチ
    inp1 = Pin(7, Pin.IN, Pin.PULL_UP)	# スイッチ
    # 
    out3 = NeoPixel(Pin(21, Pin.OUT), 4)	# GPIO 21 番に NeoPixel が4個接続されている
    # I2C
    i2c = I2C(0, scl=Pin(1), sda=Pin(0)) # I2C初期化
    oled = SSD1306_I2C(128, 64, i2c) #(幅, 高さ, I2Cオブジェクト)
    aht20 = AHT20(i2c)

    # VSYS電源電圧を取得する
    def getVsys():
        Pin(29, Pin.IN)
        volt = ADC(3).read_u16() / 65535 * 3.3 * 3
        return volt

else:
    print("This device is not supported.:", device_info.machine)


# 定期的にハードウェアのセンサ値を送信する
'''
this.gpio = [
    0, 1, 2,
    8,
    12, 13, 14, 15, 16
];
以下は + 24
const MbitMoreButtonStateIndex = {
    P0: 0,
    P1: 1,
    P2: 2,
    A: 3,
    B: 4,
    LOGO: 5
};
'''
def send_sensor_value():
    # state_characteristic に write する
    # gpio_data(32bit, ボタン状態を含む) 明るさ(8bit) 温度(8bit) 音の大きさ(8bit)
    # ピンの値を読み取って、デジタル入力データ (32ビット)のビットフィールドに格納
    btna = 1 if inp0.value() == 0 else 0    # 1 0 を反転
    btnb = 1 if inp1.value() == 0 else 0
    gpio_data = (
        (btna << 3+24) |            # ボタンA
        (btnb << 4+24) |            # ボタンB
        (human_sensor() << 5+24)    # 人感センサ
    )
    light_level = lux()                         # 明るさ
    light_level = max(0, min(255, int(light_level/500*255))) # 500luxを100% とする。0から255の範囲に制限
    temperature, humidity = temp_humi()
    temperature = max(0, min(255, int(temperature+128)))  # 0から255の範囲に制限
    humidity = max(0, min(255, int(humidity/100*255)))  # 0から255の範囲に制限
    buffer = struct.pack('<I3B', gpio_data, light_level, temperature, humidity)
    ble_conn.state_write(buffer)

def rgb(r, g, b):
    return (g, r, b)

# n番目のNeoPixcelを 赤、緑、青 0から255
def pixcel(n, r, g, b):
    out3[n] = rgb(int(r/100*255), int(g/100*255),int(b/100*255))        # n番の NeoPixel を点灯
    out3.write()
pixcel(0, 0, 0, 0)

def pixcel_n(n, value):
    v = value.split(',')
    try:
        pixcel(n, int(v[0]), int(v[1]), int(v[2]))
    except:
        print("Pixcel Error")
        pixcel(n, 0, 0, 0)

# f Hzで、音をならす。音量 v:0 音を止める
def play_tone(f, v):
    out0.freq(int(f))
    out0.duty_u16(int(v * 32768 / 100))

def stop_tone():
    play_tone(50, 0)

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
inp0.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: handle_button_event(pin, 'A'))
inp1.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: handle_button_event(pin, 'B'))

# 人感センサ am312 の値を読み取る
prevalue = 0
def human_sensor():
    global prevalue
    if adc0:
        val = adc0.value()
        if prevalue != val:
            print(val, end="__")
            prevalue = val
        if val != 0:
            return 1
    return 0

# 明るさ
def lux():
    val = adc2.read_u16()/ 65535 * 3.6 * 20/9/10000 * ( 10 ** 6)
    return val

# 温度と湿度
def temp_humi():
    if aht20:
        temperature = aht20.temperature
        humidity = aht20.relative_humidity
    else:
        temperature = 0
        humidity = 0
    return temperature, humidity

# センサーの値を表示
def disp_sensor_value():
    temperature, humidity = temp_humi()
    temp ="temp:{:6.1f}".format(temperature)
    humi ="hum :{:6.1f}".format(humidity)
    lx   ="lx:  {:6.0f}".format(lux())
    # 人感センサの値を読み取る
    hs_value = human_sensor()
    hs = "Human:{:05d}".format(hs_value)
    sound = adc1.read_u16()
    sd = "A1   :{:05d}".format(sound)
    #print(sound)
    # 上10ドットをそのままにして、下の部分だけ書き直す
    if oled:
        oled.fill_rect(0, 10, oled.width, oled.height - 10, 0)
        oled.text(temp, 0, 8*2)
        oled.text(humi, 0, 8*3)
        oled.text(lx, 0, 8*4)
        oled.text(hs, 0, 8*5)
        oled.text(sd, 0, 8*6)
        oled.show()

# 上10ドットに、文字 s を t ミリ秒間隔で流す
def show_text(s, t=0):
    print(f"文字 {s} を {t} ミリ秒間隔で流す")
    # 上10ドットを消去
    if oled:
        oled.fill_rect(0, 0, oled.width, 10, 0)
        oled.text(s, 0, 0)
        oled.show()

def draw_icon(icon, x, y):
    if oled:
        oled.fill_rect(x, y, 8, 5, 0)
        for dx, val in enumerate(icon):
            if val:
                oled.pixel(x + dx % 5, y + int(dx / 5), 1)
        oled.show()

# ピン pin をアナログ出力 n %にする (n:0-1024)
# TODO: out1->pin19, out2->pin20にする
def analog_out(pin, n):
    # print(f"ピン {pin} をアナログ出力 {n} %にする")
    if pin == 0 or pin == 21:
        out0.duty_u16(int(65535 * n / 1024))
    elif pin == 1 or pin == 19:
        out1.duty_u16(int(65535 * n / 1024))
    elif pin == 2 or pin == 20:
        out2.duty_u16(int(65535 * n / 1024))

# コマンドを実行
async def do_command(data):
    # バイナリデータをリストに変換
    data_list = list(data)
    print(data_list)  # 出力: [1, 72, 101, 108, 108, 111]
    command_id = data_list[0]
    if command_id == 65:
        # 文字 s を t ミリ秒間隔で流す
        show_text(data[2:].decode('utf-8'), data[1])
    elif command_id == 34:
        # ピン pin をアナログ出力 n %にする
        pin = data[1]
        uint16_value = struct.unpack('<H', data[2:4])[0]     # 続く2バイトを数値に変換
        # print("ピン", pin, "をアナログ出力", uint16_value, "%にする")
        analog_out(pin, uint16_value)
    elif command_id == 96:
        # 音を消す
        stop_tone()
    elif command_id == 97:
        # 1000000/data[1:5] Hzの音を data[5]/255*100 %の大きさで鳴らす
        # vol は 0 か、それ以外で音量を調節できない
        four_bytes = data[1:5]  # data[2:] から4バイトを取得
        uint32_value = struct.unpack('<I', four_bytes)[0]   # 4バイトを uint32 の数値に変換
        play_tone(1000000 / uint32_value, data[5]/255*100)
    elif command_id == 130:
        label = data[1:9].decode('utf-8')
        value = data[9:].decode('utf-8')
        print("label:", label, value)
        # NeoPixcelを光らせる
        if label=='pixcel-0':
            pixcel_n(0, value)
        elif label=='pixcel-1':
            pixcel_n(1, value)
        elif label=='pixcel-2':
            pixcel_n(2, value)
    elif command_id == 66:
        # アイコン表示（上5x3）
        draw_icon(data[1:], 0, 0)
    elif command_id == 67:
        # アイコン表示（下5x2）
        draw_icon(data[1:], 0, 3)   # 下の部分だけ書き直す
    else:
        print("Command ID", command_id, "is not defined.")
    return True

'''
[66, 0, 255, 0, 255, 0, 255, 0, 255, 0, 255, 255, 0, 0, 0, 255]
[67, 0, 255, 0, 255, 0, 0, 0, 255, 0, 0]

[66, 255, 255, 0, 255, 0, 255, 0, 255, 0, 255, 255, 0, 0, 0, 255]
[67, 0, 255, 0, 255, 0, 0, 0, 255, 0, 255]


[130, 65, 66, 67, 68, 0, 0, 0, 0, 97, 98, 99, 100, 101, 102]
ABCD   abcdef
'''

# センサーの値を定期的に送信
async def sensor_task():
    while True:
        send_sensor_value()
        await asyncio.sleep_ms(250)

from time_weather import TimeWeather

async def main():
    t1 = asyncio.create_task(ble_conn.ble_task(do_command))
    show_text(ble_conn.NAME[-16:])
    disp_sensor_value()
    t3 = asyncio.create_task(sensor_task())
    # WiFiに接続
    SSID = 'AirMacPelWi-Fi'
    PASSWORD = '78787878'
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        disp_sensor_value()
        await asyncio.sleep(1)
    print('WiFi connected:', wlan.ifconfig())

    clock = TimeWeather(oled, aht20)
    # await clock.connect_wifi(SSID, PASSWORD)
    # 現在時刻を取得
    await clock.get_ntptime()
    # 天気情報を取得
    await clock.fetch_weather("東京")
    await asyncio.sleep(1)
    clock.print_memory_usage()
    # clock.load_misakifont()
    # clock.print_memory_usage()

    # 時刻表示と天気表示を10秒ずつ交代で行う
    while True:
        for _ in range(10):
            clock.display_time()
            await asyncio.sleep(1)
        clock.display_weather()
        clock.print_memory_usage()
        await asyncio.sleep(10)
        for _ in range(10):
            disp_sensor_value()
            await asyncio.sleep(1)

asyncio.run(main())
