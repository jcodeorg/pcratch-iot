# ESP32C6 pcratch-IoT v1.3.4
from machine import Pin
from neopixel import NeoPixel
import time

# ボタンの初期化 (例: GPIOピン17)
button = Pin(17, Pin.IN, Pin.PULL_DOWN)

# 起動時にボタンが押されているか確認
time.sleep(0.5)  # 電源投入時の安定化のための遅延

# NeoPixelの初期化
np = NeoPixel(Pin(16, Pin.OUT), 2)
np[0] = (0,0,0)
np[1] = (0,0,0)
np.write()

# デフォルトのSSID、パスワード、メインモジュールを読み込む
default_ssid = ""
default_password = ""
default_main_module = ""
try:
    with open("wifi_config.txt", "r") as f:
        for line in f:
            if line.startswith("SSID="):
                default_ssid = line.strip().split("=", 1)[1]
            elif line.startswith("PASSWORD="):
                default_password = line.strip().split("=", 1)[1]
            elif line.startswith("MAIN_MODULE="):
                default_main_module = line.strip().split("=", 1)[1]
except FileNotFoundError:
    print("wifi_config.txt ファイルが見つかりません。デフォルト値を使用します。")
print("デフォルトSSID:", default_ssid)
print("デフォルトパスワード:", default_password)
print("デフォルトメインモジュール:", default_main_module)

if button.value() == 1:
    print("ボタンが押されています。netconfig.py を起動します。")
    LED_PIN = 15
    p0 = Pin(LED_PIN, Pin.OUT)    # create output pin on GPIO0
    p1 = Pin(3, Pin.OUT)    # create output pin on GPIO0
    p1.value(1)
    for i in range(10):
        p0.on()                 # set pin to "on" (high) level
        time.sleep(0.2)
        p0.off()                # set pin to "off" (low) level
        time.sleep(0.2)
    import netconfig as main
else:
    if default_main_module:
        print(f"ボタンが押されていません。{default_main_module} を起動します。")
        try:
            main = __import__(default_main_module)
        except ImportError:
            print(f"エラー: {default_main_module} モジュールが見つかりません。")
    else:
        print("iotmain.py を起動します。")
        import main1 as main
