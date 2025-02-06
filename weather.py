# ESP32C6 pcratch-IoT(micro:bit) v1.2.0
# ネットワーク天気予報

# from misakifont import MisakiFont
import urequests
import json

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

class Weather:
    def __init__(self, oled):
        self.oled = oled
        self.font = None

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
        if self.oled:
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
