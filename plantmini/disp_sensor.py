# センサー値 OLED 表示サンプル
# A1: 土壌水分センサ（3.3V）Capacitive Soil Moisture Sensor v2.0
# A2: CdS 照度センサ
# I2C: OLED（SSD1306）、温湿度センサ AHT20

import time
from machine import ADC, I2C, Pin

from ahtx0 import AHT20
from ssd1306 import SSD1306_I2C

# ---- ハードウェア初期化 ----

# I2C バス（SCL=23, SDA=22）を初期化する
i2c = I2C(0, scl=Pin(23), sda=Pin(22))

# OLED ディスプレイ（128×64 ピクセル）を初期化する
oled = SSD1306_I2C(128, 64, i2c)

# A1: 土壌水分センサ用 ADC を初期化する
adc_soil = ADC(Pin(1, Pin.IN))
adc_soil.atten(ADC.ATTN_11DB)   # 0〜3.3V の範囲を読む
adc_soil.width(ADC.WIDTH_12BIT) # 分解能 12 ビット（0〜4095）

# A2: CdS 照度センサ用 ADC を初期化する
adc_cds = ADC(Pin(2, Pin.IN))
adc_cds.atten(ADC.ATTN_11DB)
adc_cds.width(ADC.WIDTH_12BIT)


# ---- センサー読み取り ----

def read_sensors():
    """各センサーの値を読み取って辞書で返す。"""
    temperature = 0.0
    humidity = 0.0

    try:
        aht20 = AHT20(i2c)
        temperature = round(aht20.temperature, 1)
        humidity = round(aht20.relative_humidity, 1)
    except Exception as e:
        print("AHT20 error:", e)

    try:
        soil = adc_soil.read()
    except Exception as e:
        print("Soil sensor error:", e)
        soil = 0

    try:
        light = adc_cds.read()
    except Exception as e:
        print("CdS sensor error:", e)
        light = 0

    return {
        "temperature": temperature,
        "humidity": humidity,
        "soil": soil,
        "light": light,
    }


# ---- OLED 表示 ----

def disp_sensor_value(data):
    """センサー値を OLED に表示する。"""
    oled.fill(0)  # 画面を消去する
    oled.text("Sensor", 0, 0)
    oled.text("Temp: {:.1f}C".format(data["temperature"]),  0, 16)
    oled.text("Humi: {:.1f}%".format(data["humidity"]),     0, 26)
    oled.text("Ligh: {}".format(data["light"]),             0, 36)
    oled.text("Soil: {}".format(data["soil"]),              0, 46)
    oled.show()


# ---- メインループ ----

while True:
    data = read_sensors()
    disp_sensor_value(data)
    print(data)
    time.sleep(1)
