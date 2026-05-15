# Pcratch IoT 植物工場セットサンプル
# A0: 水中ポンプ制御基板＋USBポンプ（5V）
# A1: 土壌水分センサ（3.3V）Capacitive Soil Moisture Sensor v2.0
# A2: LEDクリップライト ON/OFF(別電源)
# I2C: OLED、温湿度センサ AHT20、照度センサ BH1750

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
import ntptime

# led & pump state
led_on = False
pump_on = False

# config.txt の内容を読んで設定する
cfg = Config.get_config()
SSID = cfg['SSID']
PASSWORD = cfg['PASSWORD']
GAS_URL = cfg['GAS_URL']
DEVICEID = cfg['DEVICEID']
SEND_MIN = int(cfg.get('SEND_MIN', 60))  # 分単位（60分ごとに送信）
LED_ON = cfg.get('LED_ON', "")   # LED ON 時刻 (24時間表記 "HH:MM")
LED_OFF = cfg.get('LED_OFF', "") # LED OFF 時刻 (24時間表記 "HH:MM")

print("SSID:", SSID)
print("GAS_URL:", GAS_URL)
print("DEVICEID:", DEVICEID)
print("SEND_MIN:", SEND_MIN)
print("LED_ON:", LED_ON)
print("LED_OFF:", LED_OFF)

LEDPWM_PIN = 2           # LEDライト用 PWM ピン
PUMPPWM_PIN = 0          # 水中ポンプ用 PWM ピン

LED_PIN = 15
RIGHT_BUTTON_PIN = 17

# Pin 初期化
led = Pin(LED_PIN, Pin.OUT)      # ESP32内蔵LED
i2c = None
oled = None
adc_pin = None
led_pwm = PWM(Pin(LEDPWM_PIN))     # LED 用 PWM ピン
pump_pwm = PWM(Pin(PUMPPWM_PIN))    # PUMP 用 PWM ピン

led_pwm.freq(1000)
led_pwm.duty_u16(0)
pump_pwm.freq(1000)
pump_pwm.duty_u16(0)
# ==== モード管理 ====
mode = 0
modelist = ["LEDON", "LEDOFF", "PUMPON", "PUMPOFF"]

# ==== PWM 出力関数 ====
def apply_mode(mode_name):
    global pump_on, led_on

    print(mode_name)
    if mode_name == "LEDON":
        led_pwm.duty_u16(65535)   # LED 点灯
        led_on = True

    elif mode_name == "LEDOFF":
        led_pwm.duty_u16(0)       # LED 消灯
        led_on = False

    elif mode_name == "PUMPON":
        pump_pwm.duty_u16(65535)  # ポンプ ON
        pump_on = True

    elif mode_name == "PUMPOFF":
        pump_pwm.duty_u16(0)
        pump_on = False

# ==== ボタン割り込み ====
def handle_button_event(pin, n):
    global mode
    time.sleep_ms(80)  # チャタリング対策
    if pin.value() == 1:  # 押されたときだけ反応（プルダウン前提）
        mode = (mode + 1) % len(modelist)
        apply_mode(modelist[mode])

PIN17 = Pin(RIGHT_BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)  # Right Button
# Pin.IRQ_FALLING | Pin.IRQ_RISING
PIN17.irq(trigger=Pin.IRQ_RISING, handler=lambda pin: handle_button_event(pin, RIGHT_BUTTON_PIN))

def blink_led(times=5, sec=0.1):
    for i in range(times):
        led.value(1)   # LEDを消灯
        time.sleep(sec)
        led.value(0)   # LEDを点灯
        time.sleep(sec)

def print2(text):
    print(text)
    """
    if oled:
        oled.fill_rect(0, 0, oled.width, 10, 0)
        oled.text(text, 0, 0)
        oled.show()
        print("p1:",text)
    else:
        print("p2:",text)
    """


# センサーの値をOLEDに表示
def disp_sensor_value(data, timestr):

    if oled:
        # OLED 128 x 64
        t = 6
        # oled.fill_rect(0, 10, oled.width, oled.height - 10, 0)
        oled.fill_rect(0, 0, oled.width, oled.height, 0)
        oled.text( "Pump:" + ("ON " if pump_on else "OFF") + " LED:" + ("ON " if led_on else "OFF"), 0, t+0)
        oled.text( "Temp: {:.1f}C".format(data["temperature"]), 0, t+10)
        oled.text( "Humi: {:.1f}%".format(data["humidity"]), 0, t+20)
        oled.text( "Ligh: {:.1f}Lx".format(data["illuminance"]), 0, t+30)   # 照度センサーの値
        oled.text( "Soil: {}".format(data["soil_moisture"]), 0, t+40)
        oled.text(f"{timestr}", 0, t+50)
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
    global i2c, oled, adc_pin
    # 初期化
    temperature = 0
    humidity = 0
    soil_moisture = 0
    illuminance = 0
    pressure = 0  # BME280 を使う場合に備えて

    # 土壌水分（1回だけ初期化）
    if not adc_pin:
        try:
            adc_pin = ADC(Pin(1, Pin.IN))
            adc_pin.atten(ADC.ATTN_11DB)
            adc_pin.width(ADC.WIDTH_12BIT)   # 0〜4095 の範囲
        except Exception as e:
            print("ADC initialization error:", e)
    
    if adc_pin:
        try:
            soil_moisture = adc_pin.read()
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

# Connect Wi-Fi
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

def set_time(retries=5):
    for i in range(retries):
        try:
            ntptime.host = "ntp.nict.jp"
            ntptime.settime()
            print("時刻同期に成功しました")
            return True
        except Exception as e:
            print(f"時刻同期に失敗しました ({i + 1}/{retries}): {e}")
            time.sleep(1)
    return False

def format_local_time():
    # ntptime.settime() の時刻(UTC)を JST(UTC+9) に補正
    tm = time.localtime(time.time() + 9 * 3600)
    return "{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        tm[1], tm[2], tm[3], tm[4], tm[5]
    )

def parse_hhmm_to_min(hhmm):
    hh, mm = hhmm.split(":")
    hh = int(hh)
    mm = int(mm)
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        raise ValueError("time out of range")
    return hh * 60 + mm

def control_led_by_schedule(on_min, off_min):
    # JST の現在時刻を分単位に変換
    tm = time.localtime(time.time() + 9 * 3600)
    now_min = tm[3] * 60 + tm[4]

    # on <= off: 同日内, on > off: 日付またぎ
    if on_min <= off_min:
        should_on = on_min <= now_min < off_min
    else:
        should_on = (now_min >= on_min) or (now_min < off_min)

    if should_on and not led_on:
        apply_mode("LEDON")
    elif (not should_on) and led_on:
        apply_mode("LEDOFF")

def main():
    wlan = connect_wifi()
    if wlan and set_time():
        now_str = format_local_time()
        print("現在時刻:", now_str)
        print2(now_str)
    else:
        print("時刻同期できませんでした")

    try:
        led_on_min = parse_hhmm_to_min(LED_ON)
        led_off_min = parse_hhmm_to_min(LED_OFF)
    except Exception as e:
        print("LED schedule format error:", e)
        led_on_min = None
        led_off_min = None

    log_data = read_sensors()
    if led_on_min is not None:
        control_led_by_schedule(led_on_min, led_off_min)
    disp_sensor_value(log_data, format_local_time())    # OLED に表示
    send_log_to_gcf(log_data)   # GAS に送信

    last_send_ms = time.ticks_ms()
    send_interval_ms = SEND_MIN * 60 * 1000
    while True:
        if led_on_min is not None:
            control_led_by_schedule(led_on_min, led_off_min)

        log_data = read_sensors()
        # print(log_data)
        disp_sensor_value(log_data, format_local_time())    # OLED に表示

        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, last_send_ms) >= send_interval_ms:
            last_send_ms = now_ms
            send_log_to_gcf(log_data)   # GAS に送信

        time.sleep(1)

main()