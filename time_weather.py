# Time and Weather

import network
import ntptime
import time
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
from ahtx0 import AHT20
import framebuf
import urequests
import json
import gc
import misakifont

# WiFi接続情報
SSID = 'AirMacPelWi-Fi'
PASSWORD = '78787878'

# OLEDディスプレイの設定
i2c = I2C(0, scl=Pin(23), sda=Pin(22))
oled = SSD1306_I2C(128, 64, i2c)
# フォントの設定
font = misakifont.MisakiFont(oled)
# AHT20センサーの初期化
aht20 = AHT20(i2c)

def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        pass
    print('WiFi connected:', wlan.ifconfig())

# 曜日のリスト
days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def draw_text_double_size(oled, text, x, y):
    temp_buf = bytearray(8 * 8 // 8)  # 8x8のビットマップ用バッファ
    temp_fb = framebuf.FrameBuffer(temp_buf, 8, 8, framebuf.MONO_HLSB)
    
    for i, c in enumerate(text):
        temp_fb.fill(0)
        temp_fb.text(c, 0, 0)
        
        for dx in range(8):
            for dy in range(8):
                if temp_fb.pixel(dx, dy):
                    oled.pixel(x + i * 16 + dx * 2, y + dy * 2, 1)
                    oled.pixel(x + i * 16 + dx * 2 + 1, y + dy * 2, 1)
                    oled.pixel(x + i * 16 + dx * 2, y + dy * 2 + 1, 1)
                    oled.pixel(x + i * 16 + dx * 2 + 1, y + dy * 2 + 1, 1)

def get_ntptime():
    while True:
        try:
            ntptime.settime()
            break
        except:
            time.sleep(1)

def display_time():
    current_time = time.localtime(time.time() + 9 * 3600)  # 9時間（9 * 3600秒）を加算
    formatted_date = "{:04}-{:02}-{:02} {}".format(current_time[0], current_time[1], current_time[2], days_of_week[current_time[6]])
    formatted_time = "{:02}:{:02}:{:02}".format(current_time[3], current_time[4], current_time[5])
    # AHT20センサーから温度と湿度を取得
    temperature = aht20.temperature
    humidity = aht20.relative_humidity
    temp_hum = "T: {:.1f}C H: {:.1f}%".format(temperature, humidity)
    oled.fill(0)
    oled.text(formatted_date, 0, 0)
    draw_text_double_size(oled, formatted_time, 0, 20)
    oled.text(temp_hum, 0, 50)
    oled.show()

def decode_unicode_escape2(data):
    if isinstance(data, dict):
        print("dict2")
        return {k: decode_unicode_escape(v) for k, v in data.items()}
    elif isinstance(data, list):
        print("list2")
        return [decode_unicode_escape(v) for v in data]
    elif isinstance(data, str):
        decoded = data.encode('latin1').decode('unicode_escape')
        print("str2", decoded)
        return decoded
    else:
        print("???2")
        return data

def decode_unicode_escape(data):
    if isinstance(data, dict):
        print("dict")
        return {k: decode_unicode_escape2(v) for k, v in data.items()}
    elif isinstance(data, list):
        print("list")
        return [decode_unicode_escape2(v) for v in data]
    elif isinstance(data, str):
        print("str")
        return data.encode('latin1').decode('unicode_escape')
    else:
        print("???")
        return data

def fetch_weather(place):
    url = "https://api.aoikujira.com/tenki/week.php?fmt=json"
    response = urequests.get(url)
    data = response.content.decode('utf-8')  # コンテンツをUTF-8でデコード
    response.close()
    print(data[:300])  # 先頭100文字を表示
    json_data = json.loads(data)  # デコードされたデータをJSONとしてパース
    return json_data[place]

# アイコンの定義
weather_icons = {
    "晴": [
        0b0000000000000000,
        0b0000100000100000,
        0b0000010001000000,
        0b0000001110000000,
        0b1000000110000001,
        0b0100000000000010,
        0b0010000000000100,
        0b0001000000001000,
        0b0001000000001000,
        0b0010000000000100,
        0b0100000000000010,
        0b1000000110000001,
        0b0000001110000000,
        0b0000010001000000,
        0b0000100000100000,
        0b0000000000000000
    ],
    "曇": [
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000111111000000,
        0b0011111111110000,
        0b0111111111111000,
        0b1111111111111100,
        0b1111111111111100,
        0b1111111111111100,
        0b0111111111111000,
        0b0011111111110000,
        0b0000111111000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000
    ],
    "雨": [
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b1000000000000000,
        0b0100000000000000,
        0b0010000000000000,
        0b0001000000000000,
        0b0000100000000000,
        0b0000010000000000,
        0b0000001000000000,
        0b0000000100000000
    ]
}

def draw_icon(oled, icon, x, y):
    for dy, row in enumerate(icon):
        for dx in range(16):
            if row & (1 << (15 - dx)):
                oled.pixel(x + dx, y + dy, 1)

def display_weather(weather_data):
    oled.fill(0)
    for i, day in enumerate(weather_data):
        if i >= 3:  # 最初の3日分の天気を表示
            break
        date = day['date']
        weather = day['forecast']
        mintemp = day['mintemp']
        maxtemp = day['maxtemp']

        print(date, weather, mintemp, maxtemp)
        
        font.draw(date.replace("日(", "("), i * 40, 0)  # MisakiFontを使用して日付を表示
        font.draw(weather.replace("曇", "ク"), i * 40, 8)  # MisakiFontを使用して天気を表示
        # oled.text(date[:2], i * 40, 0)
        oled.text(f"{mintemp}/{maxtemp}", i * 40, 50)
        
        # 天気に応じたアイコンを表示
        if "雨" in weather:
            draw_icon(oled, weather_icons["雨"], i * 40, 20)
        if "晴" in weather:
            draw_icon(oled, weather_icons["晴"], i * 40, 20)
        if "曇" in weather:
            draw_icon(oled, weather_icons["曇"], i * 40, 20)
        
    oled.show()


def print_memory_usage():
    gc.collect()  # ガベージコレクションを実行してメモリを解放
    free_memory = gc.mem_free()  # 使用可能なメモリ量を取得
    allocated_memory = gc.mem_alloc()  # 割り当てられたメモリ量を取得
    total_memory = free_memory + allocated_memory  # 合計メモリ量を計算

    print("Free memory: {} bytes".format(free_memory))
    print("Allocated memory: {} bytes".format(allocated_memory))
    print("Total memory: {} bytes".format(total_memory))

# WiFiに接続
connect_wifi(SSID, PASSWORD)

# 現在時刻を取得
get_ntptime()
# 天気情報を取得
weather_data = fetch_weather("東京")

# 時刻表示と天気表示を10秒ずつ交代で行う
while True:
    for _ in range(10):
        display_time()
        time.sleep(1)
    display_weather(weather_data)
    time.sleep(10)
    print_memory_usage() # メモリの使用量を表示
