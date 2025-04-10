# ESP32C6 pcratch-IoT v1.3.2
# ネットワーク天気予報

# from misakifont import MisakiFont
import urequests
import json

# アイコンの定義
weather_icons = {
    "晴": [
        0b0000000100000000,
        0b0000000100000000,
        0b0100000100000100,
        0b0010000000001000,
        0b0001001110010000,
        0b0000010001000000,
        0b0000100000100000,
        0b1110100000101110,
        0b0000100000100000,
        0b0000010001000000,
        0b0001001110010000,
        0b0010000000001000,
        0b0100000100000100,
        0b0000000100000000,
        0b0000000100000000,
        0b0000000000000000
    ],
    "曇": [
        0b0000000111100000,
        0b0000011000010000,
        0b0000100000001100,
        0b0001001111000010,
        0b0011110000110010,
        0b0100100000001100,
        0b1000000000000010,
        0b1000000000000010,
        0b1000000000000010,
        0b0100100000000100,
        0b0011110000111000,
        0b0000001111000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000,
        0b0000000000000000
    ],
    "雨": [
        0b0000000111100000,
        0b0000011000010000,
        0b0000100000001100,
        0b0001001111000010,
        0b0011110000110010,
        0b0100100000001100,
        0b1000000000000010,
        0b1000000000000010,
        0b1000000000000010,
        0b0100100000000100,
        0b0011110000111000,
        0b0000001111000000,
        0b0001001001001000,
        0b0000100100100100,
        0b0000010010010010,
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
        self.weather_data = []
        url = "https://api.aoikujira.com/tenki/week.php?fmt=json"
        try:
            response = urequests.get(url, timeout=5)  # タイムアウトを5秒に設定
            data = response.content.decode('utf-8')  # コンテンツをUTF-8でデコード
            json_data = json.loads(data)  # デコードされたデータをJSONとしてパース
            self.weather_data = json_data[self.location]
        except Exception as e:
            print(f"天気情報の取得中にエラーが発生しました: {e}")

    # 16x16のアイコンを描画
    def draw_icon(self, icon, x, y):
        for dy, row in enumerate(icon):
            for dx in range(16):
                if row & (1 << (15 - dx)):
                    self.oled.pixel(x + dx, y + dy, 1)

    # 天気情報を表示
    def display_weather(self, temperature = 0, humidity = 0):
        if self.oled:
            # 上10ドットをそのままにして、下の部分だけ書き直す
            self.oled.fill_rect(0, 0, self.oled.width, self.oled.height - 0, 0)
            # self.oled.fill(0)
            for i, day in enumerate(self.weather_data):
                if i >= 3:  # 最初の3日分の天気を表示
                    break
                date = day['date']
                forecast = day['forecast']
                mintemp = day['mintemp']
                maxtemp = day['maxtemp']
                # print(date, forecast, mintemp, maxtemp)

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
                weather = weather.replace("時々", "")
                weather = weather.replace("後", "")
                weather = weather.replace("止む", "")

                if self.font:
                    self.font.draw(date, i * 43, 0)  # MisakiFontを使用して日付を表示
                    self.font.draw(weather.replace("曇", "ク"), i * 43, 18)  # MisakiFontを使用して天気を表示
                else:
                    self.oled.text(date, i * 43, 0)
                    # self.oled.text(weather, i * 40, 18)
                self.oled.text(f"{mintemp}|{maxtemp}", i * 43, 40)
                
                # 天気に応じたアイコンを表示
                icon = weather_icons["晴"]
                if "晴" in forecast[0]:
                    icon = weather_icons["晴"]
                if "曇" in forecast[0]:
                    icon = weather_icons["曇"]
                if "雨" in forecast[0]:
                    icon = weather_icons["雨"]
                self.draw_icon(icon, i * 43, 16)
            self.oled.line(0, 50, 127, 50, 1)
            formatted_temp = "{:5.1f}C {:5.1f}%".format(temperature, humidity)
            self.oled.text(formatted_temp, 0, 54)
            self.oled.show()
