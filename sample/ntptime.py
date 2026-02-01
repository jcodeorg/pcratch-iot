import network
import ntptime
import time

# ===== Wi-Fi 接続 =====
ssid = "YOUR_SSID"
password = "YOUR_PASSWORD"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

time.sleep(1)

wlan.connect(ssid, password)

print("Wi-Fi 接続中...")
while not wlan.isconnected():
    print(".", end="")
    time.sleep(0.5)

print("接続完了:", wlan.ifconfig())

# ===== NTP で時刻同期 =====
print("NTP で時刻を取得中...")
ntptime.host = "ntp.nict.jp"  # 日本の NTP サーバー（一般例）
ntptime.settime()             # RTC に時刻を設定

# ===== 現在時刻を表示 =====
while True:
    JST = 9 * 60 * 60  # 9時間分の秒数
    now = time.localtime(time.time() + JST)  # (year, month, day, hour, min, sec, weekday, yearday)
    print("{:04d}/{:02d}/{:02d} {:02d}:{:02d}:{:02d}".format(
        now[0], now[1], now[2], now[3], now[4], now[5]
    ))
    time.sleep(1)
