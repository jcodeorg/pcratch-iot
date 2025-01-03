# Time and Weather

import network
import ntptime
import time
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
from ahtx0 import AHT20
# from misakifont import MisakiFont
import framebuf
import urequests
import json
import gc
import asyncio

# アイコンの定義
weather_icons = {
    "晴": [
        0b0000000110000000,
        0b0000000000000000,
        0b0000011111100000,
        0b0000100000010000,
        0b0001000000001000,
        0b1010000000000101,
        0b1010000000000101,
        0b0001000000001000,
        0b0000100000010000,
        0b0000011111100000,
        0b0000000000000000,
        0b0000000110000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000
    ],
    "曇": [
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000011111100000,
        0b0000100000010000,
        0b0111000000001000,
        0b1000000000000010,
        0b1000000000000100,
        0b0111110001010000,
        0b0000001110100000,
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
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b1001001001000000,
        0b0100100100100000,
        0b0010010010010000,
        0b0001001001001000,
        0b0000000000000000
    ]
}

class TimeWeather:
    def __init__(self, oled, aht20):

        # OLEDディスプレイの設定
        # self.i2c = I2C(0, scl=Pin(23), sda=Pin(22))
        self.oled = oled
        # フォントの設定
        if False:
            self.font = MisakiFont(self.oled)
        self.font = None
        # AHT20センサーの初期化
        self.aht20 = aht20
        # 曜日のリスト
        # self.days_of_week = ["月", "火", "水", "木", "金", "土", "日"]
        self.days_of_week = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def load_misakifont(self):
        from misakifont import MisakiFont
        self.font = MisakiFont(self.oled)

    async def connect_wifi(self, ssid, password):
        self.ssid = ssid
        self.password = password

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(self.ssid, self.password)
        while not wlan.isconnected():
            await asyncio.sleep(1)
        print('WiFi connected:', wlan.ifconfig())

    async def get_ntptime(self):
        while True:
            try:
                ntptime.settime()
                break
            except:
                await asyncio.sleep(1)

    def display_time(self):
        current_time = time.localtime(time.time() + 9 * 3600)  # 9時間（9 * 3600秒）を加算
        formatted_date = "{:04}-{:02}-{:02}({})".format(current_time[0], current_time[1], current_time[2], self.days_of_week[current_time[6]])
        formatted_time = "{:02}:{:02}:{:02}".format(current_time[3], current_time[4], current_time[5])
        # AHT20センサーから温度と湿度を取得
        temperature = self.aht20.temperature
        humidity = self.aht20.relative_humidity
        temp_hum = "T:{:.1f}C H:{:.1f}%".format(temperature, humidity)

        # 上10ドットをそのままにして、下の部分だけ書き直す
        self.oled.fill_rect(0, 10, self.oled.width, self.oled.height - 10, 0)
        self.oled.text(formatted_date, 0, 10)
        self.draw_text_double_size(formatted_time, 0, 30)
        self.oled.text(temp_hum, 0, 50)
        self.oled.show()

    def draw_text_double_size(self, text, x, y):
        temp_buf = bytearray(8 * 8 // 8)  # 8x8のビットマップ用バッファ
        temp_fb = framebuf.FrameBuffer(temp_buf, 8, 8, framebuf.MONO_HLSB)
        
        for i, c in enumerate(text):
            temp_fb.fill(0)
            temp_fb.text(c, 0, 0)
            
            for dx in range(8):
                for dy in range(8):
                    if temp_fb.pixel(dx, dy):
                        self.oled.pixel(x + i * 16 + dx * 2, y + dy * 2, 1)
                        self.oled.pixel(x + i * 16 + dx * 2 + 1, y + dy * 2, 1)
                        self.oled.pixel(x + i * 16 + dx * 2, y + dy * 2 + 1, 1)
                        self.oled.pixel(x + i * 16 + dx * 2 + 1, y + dy * 2 + 1, 1)

    # 天気情報を取得
    async def fetch_weather(self, location):
        self.location = location
        url = "https://api.aoikujira.com/tenki/week.php?fmt=json"
        response = urequests.get(url)
        data = response.content.decode('utf-8')  # コンテンツをUTF-8でデコード
        json_data = json.loads(data)  # デコードされたデータをJSONとしてパース
        self.weather_data = json_data[self.location]
        # print(self.weather_data)

    # 16x16のアイコンを描画
    def draw_icon(self, icon, x, y):
        for dy, row in enumerate(icon):
            for dx in range(16):
                if row & (1 << (15 - dx)):
                    self.oled.pixel(x + dx, y + dy, 1)

    # 天気情報を表示
    def display_weather(self):
        # 上10ドットをそのままにして、下の部分だけ書き直す
        self.oled.fill_rect(0, 10, self.oled.width, self.oled.height - 10, 0)
        # self.oled.fill(0)
        for i, day in enumerate(self.weather_data):
            if i >= 3:  # 最初の3日分の天気を表示
                break
            date = day['date']
            forecast = day['forecast']
            mintemp = day['mintemp']
            maxtemp = day['maxtemp']
            print(date, forecast, mintemp, maxtemp)

            # "日(" を "(" に置換
            date = date.replace("日(", "(")
            date = date.replace("(月)", "Mo")
            date = date.replace("(火)", "Tu")
            date = date.replace("(水)", "We")
            date = date.replace("(木)", "Th")
            date = date.replace("(金)", "Fr")
            date = date.replace("(土)", "Sa")
            date = date.replace("(日)", "Su")

            # 天気を置換
            weather = forecast.replace("曇", "C")
            weather = weather.replace("晴", "S")
            weather = weather.replace("雨", "R")
            weather = weather.replace("時々", "p")

            if self.font:
                self.font.draw(date, i * 40, 10)  # MisakiFontを使用して日付を表示
                self.font.draw(weather.replace("曇", "ク"), i * 40, 18)  # MisakiFontを使用して天気を表示
            else:
                self.oled.text(date, i * 40, 10)
                self.oled.text(weather, i * 40, 18)
            self.oled.text(f"{mintemp}/{maxtemp}", i * 40, 50)
            
            # 天気に応じたアイコンを表示
            if "晴" in forecast:
                self.draw_icon(weather_icons["晴"], i * 40, 30)
            if "曇" in forecast:
                self.draw_icon(weather_icons["曇"], i * 40, 30)
            if "雨" in forecast:
                self.draw_icon(weather_icons["雨"], i * 40, 30)
        self.oled.show()

    # メモリ使用量を表示
    def print_memory_usage(self):
        gc.collect()  # ガベージコレクションを実行してメモリを解放
        free_memory = gc.mem_free()  # 使用可能なメモリ量を取得
        allocated_memory = gc.mem_alloc()  # 割り当てられたメモリ量を取得
        total_memory = free_memory + allocated_memory  # 合計メモリ量を計算

        print("Free memory: {} bytes".format(free_memory))
        print("Allocated memory: {} bytes".format(allocated_memory))
        print("Total memory: {} bytes".format(total_memory))


async def main():
    # WiFi接続情報
    SSID = 'AirMacPelWi-Fi'
    PASSWORD = '78787878'
    clock = TimeWeather()
    # WiFiに接続
    await clock.connect_wifi(SSID, PASSWORD)
    # 現在時刻を取得
    await clock.get_ntptime()
    # 天気情報を取得
    await clock.fetch_weather("東京")
    # 時刻表示と天気表示を10秒ずつ交代で行う
    while True:
        for _ in range(10):
            clock.display_time()
            await asyncio.sleep(1)
        clock.display_weather()
        clock.print_memory_usage()
        await asyncio.sleep(10)

# asyncio.run(main())