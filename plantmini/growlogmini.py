# Pcratch IoT 植物工場 ミニ版
# センサーの値を読み取り、OLED に表示し、WiFi 経由で GAS にログを送るプログラム
#
# 接続するハードウェア:
#   A1 (GPIO1) : 土壌水分センサ（Capacitive Soil Moisture Sensor v2.0）
#   A2 (GPIO2) : CdS 照度センサ
#   I2C        : OLED (SSD1306 128x64)、温湿度センサ (AHT20)

import json
import network
import time
import urequests
from machine import ADC, I2C, Pin

from ahtx0 import AHT20
import ntptime
from ssd1306 import SSD1306_I2C


# ============================================================
# 定数
# ============================================================

# 日本時間は UTC+9 なので、9時間分の秒数をオフセットとして使う
JST_OFFSET_SEC = 9 * 3600

# WiFi 接続状態を表す定数（数値に意味を持たせるために名前をつける）
WIFI_IDLE       = 0  # 未接続（接続を試みていない）
WIFI_CONNECTING = 1  # 接続中
WIFI_CONNECTED  = 2  # 接続済み
WIFI_FAILED     = 3  # 接続失敗

WIFI_TIMEOUT_MS  = 15000  # 1回の接続試行タイムアウト（15秒）
WIFI_MAX_RETRIES = 3      # 失敗しても最大3回まで再接続を試みる

# WiFi 接続中アイコンのアニメーション用文字（4フレームでくるくる回る）
WIFI_ANIM = "|/-+"


# ============================================================
# 設定の読み込み（wifi_config.txt）
# ============================================================

def load_settings():
    """wifi_config.txt を 1 行ずつ読み込み、KEY=VALUE 形式で設定を取得する。"""
    # デフォルト値（ファイルが読めなかったときの fallback）
    cfg = {
        "SSID":      "",
        "PASSWORD":  "",
        "GAS_URL":   "",
        "DEVICEID":  "D0000",
        "SEND_MIN":  "60",
        "AUTO_WIFI": "0",
    }
    try:
        with open("wifi_config.txt", "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    # "KEY=VALUE" を "=" で分割して辞書に格納する
                    key, _, val = line.partition("=")
                    if key in cfg:
                        cfg[key] = val
    except Exception as e:
        print("wifi_config.txt 読み込みエラー:", e)

    # SEND_MIN は数値として使うので int に変換する（失敗時は 60 分をデフォルトに）
    try:
        send_min = int(cfg["SEND_MIN"])
    except Exception:
        send_min = 60

    return {
        "SSID":      cfg["SSID"],
        "PASSWORD":  cfg["PASSWORD"],
        "GAS_URL":   cfg["GAS_URL"],
        "DEVICEID":  cfg["DEVICEID"],
        "SEND_MIN":  send_min,
        "AUTO_WIFI": cfg["AUTO_WIFI"].strip() == "1",  # "1" のとき True
    }


# 設定を読み込んでグローバル変数に展開する
settings  = load_settings()
SSID      = settings["SSID"]
PASSWORD  = settings["PASSWORD"]
GAS_URL   = settings["GAS_URL"]
DEVICEID  = settings["DEVICEID"]
SEND_MIN  = settings["SEND_MIN"]   # ログ送信間隔（分）。0 のとき送信しない
AUTO_WIFI = settings["AUTO_WIFI"]  # True のとき起動時に自動接続する

print("SSID:", SSID)
print("GAS_URL:", GAS_URL)
print("DEVICEID:", DEVICEID)
print("SEND_MIN:", SEND_MIN)


# ============================================================
# ハードウェア初期化
# ============================================================

# I2C バス（SCL=GPIO23, SDA=GPIO22）を初期化する
try:
    i2c = I2C(0, scl=Pin(23), sda=Pin(22))
except Exception as e:
    print("I2C 初期化エラー:", e)
    i2c = None

# OLED ディスプレイ（128×64 ピクセル）を初期化する
oled = None
if i2c is not None:
    try:
        oled = SSD1306_I2C(128, 64, i2c)
    except Exception as e:
        print("OLED 初期化エラー:", e)

# A1: 土壌水分センサ用 ADC を初期化する
#   atten(ATTN_11DB)   : 0〜3.3V の電圧範囲を読めるようにする
#   width(WIDTH_12BIT) : 0〜4095 の範囲（12ビット分解能）で値を読む
try:
    adc_soil = ADC(Pin(1, Pin.IN))
    adc_soil.atten(ADC.ATTN_11DB)
    adc_soil.width(ADC.WIDTH_12BIT)
except Exception as e:
    print("土壌水分センサ 初期化エラー:", e)
    adc_soil = None

# A2: CdS 照度センサ用 ADC を初期化する（設定は土壌水分センサと同じ）
try:
    adc_cds = ADC(Pin(2, Pin.IN))
    adc_cds.atten(ADC.ATTN_11DB)
    adc_cds.width(ADC.WIDTH_12BIT)
except Exception as e:
    print("CdS センサ 初期化エラー:", e)
    adc_cds = None


# ============================================================
# WiFi 接続管理
# ============================================================

wlan           = None         # WLAN オブジェクト（接続後に使う）
wifi_status    = WIFI_IDLE    # 現在の WiFi 接続状態
_just_connected = False       # 接続成功直後のみ True になるフラグ（即時送信用）
_anim_tick      = 0           # アニメーションのコマ数カウンタ
_connect_start_ms = 0         # 接続を開始した時刻（タイムアウト計測用）
_retry_count      = 0         # 現在の再接続回数


def start_wifi():
    """WiFi 接続を開始する。この関数はすぐに戻り、接続完了は poll_wifi() で確認する。"""
    global wlan, wifi_status, _connect_start_ms, _retry_count
    if wifi_status == WIFI_CONNECTING:
        return  # すでに接続中なので何もしない
    _retry_count = 0
    wifi_status  = WIFI_CONNECTING
    _connect_start_ms = time.ticks_ms()
    wlan = network.WLAN(network.STA_IF)  # ステーションモード（子機として接続）
    wlan.active(True)
    time.sleep_ms(200)  # WiFi モジュールが安定するまで少し待つ
    try:
        wlan.connect(SSID, PASSWORD)
        print("WiFi 接続を開始しました")
    except Exception as e:
        print("WiFi 接続エラー:", e)
        wifi_status = WIFI_FAILED


def poll_wifi():
    """WiFi 接続の進行状況を確認し、wifi_status を更新する。メインループで毎回呼ぶ。"""
    global wlan, wifi_status, _connect_start_ms, _retry_count, _just_connected
    if wifi_status == WIFI_CONNECTED:
        # 接続が切れていたら IDLE に戻して再接続できるようにする
        if wlan is None or not wlan.isconnected():
            wifi_status = WIFI_IDLE
        return
    if wifi_status != WIFI_CONNECTING:
        return  # 接続中でなければ何もしない
    if wlan is None:
        wifi_status = WIFI_FAILED
        return
    if wlan.isconnected():
        # 接続成功！
        wifi_status     = WIFI_CONNECTED
        _just_connected = True  # 接続直後フラグを立てる（メインループで即時送信する）
        print("WiFi 接続しました:", wlan.ifconfig()[0])
        sync_ntp()  # 接続直後に時刻を NTP サーバーから取得する
        return
    # タイムアウトを確認する
    elapsed = time.ticks_diff(time.ticks_ms(), _connect_start_ms)
    if elapsed >= WIFI_TIMEOUT_MS:
        _retry_count += 1
        if _retry_count >= WIFI_MAX_RETRIES:
            # リトライ上限に達したので失敗とする
            wifi_status = WIFI_FAILED
            print("WiFi 接続に失敗しました（リトライ上限）")
            wlan.active(False)
        else:
            # もう一度接続を試みる
            print("WiFi 再接続中... ({}/{})".format(_retry_count, WIFI_MAX_RETRIES))
            _connect_start_ms = time.ticks_ms()
            try:
                wlan.disconnect()
                wlan.connect(SSID, PASSWORD)
            except Exception as e:
                print("WiFi 再接続エラー:", e)


def is_wifi_connected():
    """WiFi に接続中かどうかを返す（True / False）。"""
    return wlan is not None and wlan.isconnected()


# ============================================================
# 時刻
# ============================================================

def sync_ntp(retries=2):
    """NTP サーバーから現在時刻を取得して、ESP32 の内部時計を合わせる。"""
    for i in range(retries):
        try:
            ntptime.host = "ntp.nict.jp"  # 日本の NTP サーバーを指定する
            ntptime.settime()
            print("時刻同期に成功しました")
            return True
        except Exception as e:
            print("時刻同期に失敗しました ({}/{}):".format(i + 1, retries), e)
            time.sleep(1)
    return False


def format_time():
    """現在時刻を JST（日本時間）で "MM-DD HH:MM:SS" 形式の文字列にして返す。"""
    # time.time() は UTC の Unix 時刻（秒）を返すので、JST オフセット（+9時間）を足す
    tm = time.localtime(time.time() + JST_OFFSET_SEC)
    return "{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        tm[1], tm[2], tm[3], tm[4], tm[5]
    )


# ============================================================
# センサー読み取り
# ============================================================

def read_sensors():
    """全センサーの値を読み取り、辞書（dict）で返す。"""
    temperature = 0.0
    humidity    = 0.0
    soil        = 0
    light       = 0

    # 土壌水分センサ（A1）: 値が大きいほど乾燥している
    if adc_soil is not None:
        try:
            soil = adc_soil.read()
        except Exception as e:
            print("土壌水分センサ 読み取りエラー:", e)

    # CdS 照度センサ（A2）: 明るいほど値が小さく、暗いほど値が大きくなる
    if adc_cds is not None:
        try:
            light = adc_cds.read()
        except Exception as e:
            print("CdS センサ 読み取りエラー:", e)

    # AHT20 温湿度センサ（I2C）
    if i2c is not None:
        try:
            aht20 = AHT20(i2c)
            temperature = round(aht20.temperature, 1)
            humidity    = round(aht20.relative_humidity, 1)
        except Exception as e:
            print("AHT20 センサ 読み取りエラー:", e)

    return {
        "timestamp":   time.time(),   # Unix 時刻（UTC 秒）
        "device_id":   DEVICEID,
        "temperature": temperature,   # 気温（℃）
        "humidity":    humidity,      # 湿度（%）
        "soil_moisture": soil,          # 土壌水分（ADC 生値 0〜4095）
        "illuminance":   light,          # 照度（ADC 生値 0〜4095）
    }


# ============================================================
# OLED 表示
# ============================================================

def draw_wifi_icon():
    """OLED 右上（x=120, y=0）に WiFi 接続状態を 1 文字で表示する。
    W=接続済み  -=未接続  !=失敗  |/-+=接続中（アニメーション）"""
    global _anim_tick
    if wifi_status == WIFI_CONNECTED:
        icon = "W"
    elif wifi_status == WIFI_CONNECTING:
        # 接続中は 4 文字を順番に切り替えてアニメーションに見せる
        icon = WIFI_ANIM[_anim_tick % 4]
        _anim_tick += 1
    elif wifi_status == WIFI_FAILED:
        icon = "!"
    else:
        icon = "-"
    oled.text(icon, 120, 0)


def disp_sensors(data, timestr):
    """センサー値と時刻を OLED に表示する。"""
    if oled is None:
        return  # OLED が使えない場合は何もしない
    oled.fill(0)  # 画面を黒（消去）にする
    oled.text("Sensor",                                        0,  0)
    oled.text("Temp: {:.1f}C".format(data["temperature"]),    0, 16)
    oled.text("Humi: {:.1f}%".format(data["humidity"]),       0, 26)
    oled.text("Ligh: {}".format(data["illuminance"]),               0, 36)
    oled.text("Soil: {}".format(data["soil_moisture"]),              0, 46)
    oled.text(timestr,                                        0, 56)
    draw_wifi_icon()  # 右上に WiFi アイコンを描く
    oled.show()       # ここで初めて実際に画面に反映される


# ============================================================
# ログ送信（Google Apps Script）
# ============================================================

def send_log(data):
    """センサーデータを JSON にして GAS の URL へ HTTP POST で送信する。"""
    headers = {"Content-Type": "application/json"}
    try:
        response = urequests.post(GAS_URL, headers=headers, data=json.dumps(data))
        print("送信成功 ステータス:", response.status_code)
        response.close()  # メモリを解放するために必ず閉じる
        return True
    except Exception as e:
        print("送信エラー:", e)
        return False


# ============================================================
# メイン処理
# ============================================================

# AUTO_WIFI=1 のとき、起動直後に WiFi 接続を開始する
if AUTO_WIFI:
    print("WiFi 自動接続を開始します...")
    start_wifi()

last_send_ms = time.ticks_ms()  # 最後にログを送信した時刻を記録する

while True:
    # --- ① WiFi の接続状態を更新する（毎ループ必ず呼ぶ）---
    poll_wifi()

    # --- ② センサーを読み取って OLED に表示する ---
    data = read_sensors()
    disp_sensors(data, format_time())

    # --- ③ GAS へログを送信する ---
    if is_wifi_connected() and SEND_MIN > 0:
        now_ms = time.ticks_ms()
        send_interval_ms = SEND_MIN * 60 * 1000  # 分 → ミリ秒に変換
        # WiFi 接続直後は間隔を問わず即時送信する
        if _just_connected or time.ticks_diff(now_ms, last_send_ms) >= send_interval_ms:
            _just_connected = False  # フラグをリセットする
            last_send_ms = now_ms
            send_log(data)

    time.sleep(0.2)  # 0.2 秒待ってから次のループへ

