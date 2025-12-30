# logwriter
# センサーの値を読み取り、Googleスプレッドシートに書き込む

import urequests
import json
import network
import time
import machine
from machine import Pin, I2C, ADC, PWM, WDT
from ahtx0 import AHT20
from bh1750 import BH1750
from ssd1306 import SSD1306_I2C
from config import Config 

# from bme280 import BME280

# config.txt の内容を読んで設定する
cfg = Config.get_config()
SSID = cfg['SSID']
PASSWORD = cfg['PASSWORD']
GAS_URL = cfg['GAS_URL']
DEVICEID = cfg['DEVICEID']

SLEEPTIME = 20*60 # 秒
WDT_TIMEOUT_MS = 3*60*1000      # 3分以内に feed() しないとリセット
# WDT 初期化
# wdt = WDT(timeout=WDT_TIMEOUT_MS)

# Pin 初期化
led = Pin(15, Pin.OUT)
power = Pin(19, Pin.OUT)
i2c = None
oled = None

def blink_led(times=5, sec=0.1):
    for i in range(times):
        led.value(1)   # LEDを消灯
        time.sleep(sec)
        led.value(0)   # LEDを点灯
        time.sleep(sec)

def print2(text):
    if oled:
        oled.fill_rect(0, 0, oled.width, 10, 0)
        oled.text(text, 0, 0)
        oled.show()
        print("p1:",text)
    else:
        print("p2:",text)


# センサーの値をOLEDに表示
'''
    log_data = {
        "timestamp": time.time(),
        "device_id": "D3102",
        "temperature": temperature,
        "humidity": humidity,
        "soil_moisture": soil_moisture,
        "illuminance": illuminance,
        "pressure": pressure
    }
'''
def disp_sensor_value(data, count):

    if oled:
        # OLED 128 x 64
        t = 6
        oled.fill_rect(0, 10, oled.width, oled.height - 10, 0)
        oled.text( "Temp: {:.1f}C".format(data["temperature"]), 0, t+10)
        oled.text( "Humi: {:.1f}%".format(data["humidity"]), 0, t+20)
        oled.text( "Ligh: {:.1f}Lx".format(data["illuminance"]), 0, t+30)   # 照度センサーの値
        oled.text( "Soil: {:.1f}%".format(data["soil_moisture"]), 0, t+40)
        oled.text(f"Cnt : {count}", 0, t+50)
        oled.show()

def send_log_to_gcf(data):
    url = GAS_URL
    headers = {'Content-Type': 'application/json'}
    try:
        payload = json.dumps(data)
        response = urequests.post(url, headers=headers, data=payload)
        print(f"GAS Response Status: {response.status_code}")
        print(f"GAS Response Text: {response.text}")
        response.close()
        return True
    except Exception as e:
        print(f"Error sending data to GAS: {e}")
        # response.close()
        return False

# Wi-Fiに接続する
def connect_wifi(retries=20):
    wlan = network.WLAN(network.STA_IF)
    for j in range(3):
        wlan.active(True)
        time.sleep(1)
        try:
            wlan.connect(SSID, PASSWORD)
        except Exception as e:
            print2(str(e))

        time.sleep(1)
        for i in range(retries):
            # wdt.feed()
            if wlan.isconnected():
                print2(f"Connected in {i+1} seconds.")
                return wlan
            blink_led(2, 0.5)
            print2(f"Try...{i+1}")
            print(wlan.status())

        print2("Wi-Fi failed")
        wlan.active(False)
        time.sleep(1)
    return None

# 水分率(%) = ((乾燥値 - ADC値) / (乾燥値 - 冠水値)) × 100
def calculate_soil_moisture(adc_value, dry=3000, wet=1400):
    """
    ADC値から土壌水分率(%)を計算する。
    dry: 乾燥時のADC値（高い）
    wet: 冠水時のADC値（低い）
    """
    # 範囲外のADC値に対応（オーバー・アンダーフロー）
    if adc_value >= dry:
        return 0.0
    elif adc_value <= wet:
        return 100.0
    # 線形補間で水分率を計算
    moisture = ((dry - adc_value) / (dry - wet)) * 100
    return round(moisture, 1)  # 小数第1位まで表示


def read_sensors():
    global i2c, oled
    # 初期化
    temperature = 0
    humidity = 0
    soil_moisture = 0
    illuminance = 0
    pressure = 0  # BME280 を使う場合に備えて

    # 土壌水分
    try:
        a1 = ADC(Pin(1, Pin.IN))
        a1.atten(ADC.ATTN_11DB)
        a1.width(ADC.WIDTH_12BIT)
        soil_moisture = calculate_soil_moisture(a1.read())
    except Exception as e:
        print("Soil moisture sensor error:", e)

    # I2C 初期化
    if not i2c:
        try:
            #time.sleep(0.4)
            i2c = I2C(0, scl=Pin(23), sda=Pin(22))
            #time.sleep(0.4)
        except Exception as e:
            print("I2C initialization error:", e)

    if i2c:
        # oled の初期化
        if not oled:
            try:
                oled = SSD1306_I2C(128, 64, i2c)
            except OSError as e:
                print(f"Error initializing oled: {e}")

        # AHT20 温度・湿度
        try:
            aht20 = AHT20(i2c)
            temperature = round(aht20.temperature, 1)
            humidity = round(aht20.relative_humidity, 1)
        except Exception as e:
            print("AHT20 sensor error:", e)

        # BH1750 照度
        for i in range(2):
            try:
                # print("I2C devices:", i2c.scan())
                bh1750 = BH1750(i2c)
                illuminance = round(bh1750.measurement, 1)
                # print("BH1750",illuminance)
                break;
            except Exception as e:
                print("BH1750 sensor error:", e)
            time.sleep(1)

        # BME280（もし使うなら）
        # try:
        #     bme = BME280(i2c)
        #     temperature, pressure, humidity = bme.read_data()
        # except Exception as e:
        #     print("BME280 sensor error:", e)

    log_data = {
        "timestamp": time.time(),
        "device_id": DEVICEID,
        "temperature": temperature,
        "humidity": humidity,
        "soil_moisture": soil_moisture,
        "illuminance": illuminance,
        "pressure": pressure
    }
    return log_data

# Sleepメイン処理
def post_data_loop():
    print2("ready")
    power.value(1)   # センサー電源をONにする
    blink_led()
    time.sleep(1)
    print("start1")
    sleep_time = SLEEPTIME # 秒
    disp_sensor_value(read_sensors(), 0)
    log_data = read_sensors()
    print(log_data)
    print2("start2")

    success = False
    wlan = connect_wifi()
    if wlan:
        for i in range(10):
            # 送信するデータ
            print2(f"Post...{i + 1}")
            log_data = read_sensors()
            print(log_data)
            
            if send_log_to_gcf(log_data):
                success = True
                print2("Data sent!")
                break
            else:
                print2("Failed!")
            blink_led(2, 0.5)
            blink_led(4, 0.25)

    if not success:
        print("リトライ失敗。次の試行まで待機します。")

    if False:
        # 成功しても失敗しても Deep sleep
        print("Deep sleep開始")
        power.value(0)   # センサー電源をOFF
        led.value(1)   # LEDを消灯
        # wdt.feed()  # WDTに餌を与える
        machine.deepsleep(sleep_time*1000)
        print("Deep sleepから復帰")
    else:
        print("次の書き込みまで待機...", sleep_time)
        for i in range(sleep_time):
        #    wdt.feed()  # WDTに餌を与える
            print(i)
            disp_sensor_value(read_sensors(), sleep_time - i)
            time.sleep(1)
        print("待機終了")

def test_sensors():
    power.value(1)   # センサー電源をONにする
    while True:
        disp_sensor_value(read_sensors(), 100)
        time.sleep(1)

while True:
    post_data_loop()
# test_sensors()
