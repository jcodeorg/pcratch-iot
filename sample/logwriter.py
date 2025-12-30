# logwriter
# センサーの値を読み取り、Googleスプレッドシートに書き込む

import urequests
import network
import time
import json
import machine
from machine import Pin, I2C, ADC, PWM
from hardware import Hardware

# GoogleスプレッドシートのApps ScriptのウェブアプリのURL
GCF_URL = 'https://script.google.com/macros/s/xxxxxxx/exec'

# WiFi のSSIDとパスワード
SSID = 'ssid'
PASSWORD = 'pass'

# センサ値の読み取り
def read_sensors():
    # 土壌水分
    a1 = ADC(Pin(1, Pin.IN))
    a1.atten(ADC.ATTN_11DB)
    a1.width(ADC.WIDTH_12BIT)
    soil_moisture = a1.read()
    # i2c
    i2c = I2C(0, scl=Pin(23), sda=Pin(22))
    # BME280 温度, 気圧, 湿度
    temperature, pressure, humidity = 1,2,3
    # BH1750 照度
    illuminance = 4
    log_data = {
        "timestamp": time.time(),
        "device_id": "Pcratch3-1-01",
        "temperature": temperature,
        "humidity": humidity,
        "soil_moisture": soil_moisture,
        "illuminance": illuminance,
        "pressure": pressure
    }
    return log_data

# データ送信
def send_data(data):
    headers = {'Content-Type': 'application/json'}
    try:
        payload = json.dumps(data)
        response = urequests.post(GCF_URL, headers=headers, data=payload)
        print(f"GCF Response Status: {response.status_code}")
        print(f"GCF Response Text: {response.text}")
        response.close()
        return True
    except Exception as e:
        print(f"Error sending data to GCF: {e}")
        return False

# Wi-Fi接続関数
def connect_wifi(wlan):
    ssid = SSID
    password = PASSWORD
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, password)
        for _ in range(20):  # 最大20秒待機
            if wlan.isconnected():
                break
            time.sleep(1)
            print("connect...")
    return wlan.isconnected()

# メイン処理
def write_data_interval():
    try:
        wlan = network.WLAN(network.STA_IF)
        if connect_wifi(wlan):
            print("WiFi connected.")

            # データ送信
            log_data = read_sensors()
            print(log_data)
            send_data(log_data)

        else:
            print("Wi-Fi接続失敗")

        # 10分後に再起動（600,000ミリ秒）
        wlan.disconnect()
        wlan.active(False)
    except Exception as e:
        print(f"Error: {e}")
    # print("Deep sleepして10分後に起動します")
    # machine.deepsleep(600000)

def test():
    while True:
        print(read_sensors())
        time.sleep(1)

def test2():
    hardware = Hardware()
    for i in range(4):
        print("..")
        hardware.pixcel(0, 100, 0, 0)
        hardware.digital_out(19, 0)
        time.sleep(0.5)
        hardware.pixcel(0, 0, 100, 0)
        hardware.digital_out(19, 1)
        time.sleep(0.5)

    print(read_sensors())
    machine.deepsleep(5000)

# write_data_interval()
test2()
