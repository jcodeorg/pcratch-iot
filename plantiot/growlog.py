# Pcratch IoT 植物工場セットサンプル
# A0: 水中ポンプ制御基板＋USBポンプ（5V）
# A1: 土壌水分センサ（3.3V）Capacitive Soil Moisture Sensor v2.0
# A2: LEDクリップライト ON/OFF(別電源)
# I2C: OLED、温湿度センサ AHT20、照度センサ BH1750

import json
import network
import time
import urequests
from machine import ADC, I2C, PWM, Pin, RTC

from ahtx0 import AHT20
from bh1750 import BH1750
from config import Config
import ntptime
from ssd1306 import SSD1306_I2C


def safe_int(value, default):
    try:
        return int(str(value).strip())
    except Exception:
        return default


JST_OFFSET_SEC = 9 * 3600

LEDPWM_PIN = 2
PUMPPWM_PIN = 0
LED_PIN = 15
RIGHT_BUTTON_PIN = 17
LEFT_BUTTON_PIN = 18

PWM_ON_DUTY = 65535
PWM_OFF_DUTY = 0

MODE_LIST = ["LEDON", "LEDOFF", "PUMPON", "PUMPOFF"]


class DeviceState:
    """LED/PUMP の状態とボタンモードを管理するクラス。"""

    def __init__(self):
        self.led_on = False
        self.pump_on = False
        self.mode = 0
        # スケジュールポンプ用ステートマシン
        self.pump_start_ms = None   # 稼働開始時刻 (ticks_ms)。None=停止中
        self.pump_run_ms = 0        # 稼働時間 (ms)
        self.pump_triggered_min = -1  # 直近トリガーした分 (再トリガー防止用)

    def set_led(self, on):
        self.led_on = on

    def set_pump(self, on):
        self.pump_on = on

    def next_mode(self):
        self.mode = (self.mode + 1) % len(MODE_LIST)
        return self.mode


class Hardware:
    """I2C、OLED、ADC などのハードウェア参照を管理するクラス。"""

    def __init__(self):
        self.i2c = None
        self.oled = None
        self.adc_pin = None

    def has_i2c(self):
        return self.i2c is not None

    def has_oled(self):
        return self.oled is not None

    def has_adc(self):
        return self.adc_pin is not None


class MenuState:
    """階層的なメニュー状態を管理するクラス。"""

    MAIN_MENUS = ["Sensor", "Network", "Manual", "Timer", "Config"]
    NETWORK_MENUS = ["WiFi", "Send Now", "Auto Send"]
    SEND_INTERVALS = [0, 30, 60]  # 0=無効, 30=30分, 60=60分
    MANUAL_MENUS = ["Pump ON/OFF", "LED ON/OFF"]
    TIMER_MENUS = ["LED Start", "LED Hours", "Pump Start", "Pump Run"]
    CONFIG_MENUS = ["Auto WiFi", "Save", "Test Time"]
    PUMP_DURATIONS_SEC = [0, 5, 15, 30, 60]   # 0=OFF, 単位: 秒
    LED_DURATIONS_H = [0, 4, 6, 8, 10, 12]  # 0=OFF, 単位: 時間
    LED_START_HOURS = [8, 9, 10, 11, 12]      # 点灯開始時刻の選択肢（時）
    PUMP_START_HOURS = [8, 9, 10, 11, 12]     # 稼働開始時刻の選択肢（時）

    def __init__(self):
        self.current_level = 0  # 0: main, 1: submenu, 2: executing
        self.main_idx = 0
        self.sub_idx = 0
        self.pump_duration_idx = 0  # デフォルト: OFF（PUMP_DURATIONS_SEC[0]）
        self.led_duration_idx = 0   # デフォルト: OFF（LED_DURATIONS_H[0]）
        self.led_start_idx = 0      # デフォルト: 8:00（LED_START_HOURS[0]）
        self.pump_start_idx = 0     # デフォルト: 8:00（PUMP_START_HOURS[0]）
        self.send_interval_idx = 0  # デフォルト: 無効（SEND_INTERVALS[0]）
        self.auto_wifi = False      # デフォルト: 無効（起動時WiFi自動接続しない）

    def get_current_menu_name(self):
        if self.current_level == 0:
            return self.MAIN_MENUS[self.main_idx]
        # サブメニュー（"Back" を含む）から現在の項目名を返す
        submenu = self.get_submenu_list()
        if submenu and self.sub_idx < len(submenu):
            return submenu[self.sub_idx]
        return self.MAIN_MENUS[self.main_idx]

    def get_submenu_list(self):
        if self.main_idx == 1:
            return list(self.NETWORK_MENUS)
        elif self.main_idx == 2:
            return list(self.MANUAL_MENUS)
        elif self.main_idx == 3:
            return list(self.TIMER_MENUS)
        elif self.main_idx == 4:
            return list(self.CONFIG_MENUS)
        return []

    def enter_submenu(self):
        """メインメニューからサブメニューに進む。"""
        # Sensor を選択した場合はセンサー表示モードに遷移する
        if self.main_idx == 0:  # Sensor
            self.current_level = 2
            return True
        # その他はサブメニューへ
        self.current_level = 1
        self.sub_idx = 0
        return True

    def back_to_main(self):
        """サブメニューからメインメニューに戻る。"""
        self.current_level = 0
        self.sub_idx = 0

    def next_item(self):
        """現在のレベルで次のアイテムに移動。Level 1 で最後の項目を超えるとメインに戻る。"""
        if self.current_level == 0:
            self.main_idx = (self.main_idx + 1) % len(self.MAIN_MENUS)
        elif self.current_level == 1:
            submenu_list = self.get_submenu_list()
            if self.sub_idx >= len(submenu_list) - 1:
                self.back_to_main()
            else:
                self.sub_idx += 1

    def get_send_interval_min(self):
        """現在の自動送信間隔（分）を返す。0 は送信無効。"""
        return self.SEND_INTERVALS[self.send_interval_idx]

    def next_send_interval(self):
        """自動送信間隔を次の設定に切り替える（0→30→60→0...）。"""
        self.send_interval_idx = (self.send_interval_idx + 1) % len(self.SEND_INTERVALS)

    def get_pump_duration_sec(self):
        """現在のポンプ稼働時間（秒）を返す。0 は自動稼働無効。"""
        return self.PUMP_DURATIONS_SEC[self.pump_duration_idx]

    def next_pump_duration(self):
        """ポンプ稼働時間を次の設定に切り替える（OFF→5s→15spu→30s→60s→OFF...）。"""
        self.pump_duration_idx = (self.pump_duration_idx + 1) % len(self.PUMP_DURATIONS_SEC)

    def get_led_duration_h(self):
        """現在の LED 点灯時間（時間）を返す。0 は自動点灯無効。9:00 開始固定。"""
        return self.LED_DURATIONS_H[self.led_duration_idx]

    def next_led_duration(self):
        """LED 点灯時間を次の設定に切り替える（OFF→4h→6h→8h→10h→12h→OFF...）。"""
        self.led_duration_idx = (self.led_duration_idx + 1) % len(self.LED_DURATIONS_H)

    def get_led_start_min(self):
        """現在の LED 点灯開始時刻（分）を返す。"""
        return self.LED_START_HOURS[self.led_start_idx] * 60

    def next_led_start(self):
        """LED 点灯開始時刻を次の選択肢に切り替える。5:00→6:00→...→12:00→5:00..."""
        self.led_start_idx = (self.led_start_idx + 1) % len(self.LED_START_HOURS)

    def get_pump_start_min(self):
        """現在のポンプ稼働開始時刻（分）を返す。"""
        return self.PUMP_START_HOURS[self.pump_start_idx] * 60

    def next_pump_start(self):
        """ポンプ稼働開始時刻を次の選択肢に切り替える。6:00→8:00→...→20:00→6:00..."""
        self.pump_start_idx = (self.pump_start_idx + 1) % len(self.PUMP_START_HOURS)


def init_menu_from_settings(settings, menu):
    """保存済み設定値からメニューのインデックスを復元する。
    値が選択肢にない場合はデフォルトを維持する。"""
    pairs = [
        (MenuState.LED_START_HOURS,   "LED_START_H",  "led_start_idx"),
        (MenuState.LED_DURATIONS_H,   "LED_HOURS_H",  "led_duration_idx"),
        (MenuState.PUMP_START_HOURS,  "PUMP_START_H", "pump_start_idx"),
        (MenuState.PUMP_DURATIONS_SEC, "PUMP_RUN_SEC", "pump_duration_idx"),
        (MenuState.SEND_INTERVALS,    "SEND_MIN",     "send_interval_idx"),
    ]
    for lst, key, attr in pairs:
        value = settings[key]
        if value < 0:
            continue
        try:
            setattr(menu, attr, lst.index(value))
        except ValueError:
            pass
    menu.auto_wifi = settings["AUTO_WIFI"]
    print("Menu settings restored from config")


def load_settings():
    """config.py から設定を読み込み、使いやすい形に正規化する。"""
    cfg = Config.get_config()
    return {
        "SSID": cfg["SSID"],
        "PASSWORD": cfg["PASSWORD"],
        "GAS_URL": cfg["GAS_URL"],
        "DEVICEID": cfg["DEVICEID"],
        "SEND_MIN": safe_int(cfg.get("SEND_MIN", 60), 60),
        "LED_ON": str(cfg.get("LED_ON", "") or "").strip(),
        "LED_OFF": str(cfg.get("LED_OFF", "") or "").strip(),
        "PUMP_ON": str(cfg.get("PUMP_ON", "") or "").strip(),
        "PUMP_MS": max(0, safe_int(cfg.get("PUMP_MS", 3000), 3000)),
        "AUTO_WIFI": str(cfg.get("AUTO_WIFI", "0")).strip() == "1",
        "LED_START_H": safe_int(cfg.get("LED_START_H", ""), -1),
        "LED_HOURS_H": safe_int(cfg.get("LED_HOURS_H", ""), -1),
        "PUMP_START_H": safe_int(cfg.get("PUMP_START_H", ""), -1),
        "PUMP_RUN_SEC": safe_int(cfg.get("PUMP_RUN_SEC", ""), -1),
    }


# LED とポンプの状態（学習者向け）
# - このスクリプトでは簡単のためグローバル変数で状態を管理しています。
# - 実際の組み込み開発では状態管理をクラスや永続化に分離することが多いです。
led_on = False
pump_on = False

settings = load_settings()
SSID = settings["SSID"]
PASSWORD = settings["PASSWORD"]
GAS_URL = settings["GAS_URL"]
DEVICEID = settings["DEVICEID"]
SEND_MIN = settings["SEND_MIN"]
LED_ON = settings["LED_ON"]
LED_OFF = settings["LED_OFF"]
PUMP_ON = settings["PUMP_ON"]
PUMP_MS = settings["PUMP_MS"]
AUTO_WIFI = settings["AUTO_WIFI"]

print("SSID:", SSID)
print("GAS_URL:", GAS_URL)
print("DEVICEID:", DEVICEID)
print("SEND_MIN:", SEND_MIN)
print("LED_ON:", LED_ON)
print("LED_OFF:", LED_OFF)
print("PUMP_ON:", PUMP_ON)
print("PUMP_MS:", PUMP_MS)

# Pin 初期化
led = Pin(LED_PIN, Pin.OUT)
led_pwm = PWM(Pin(LEDPWM_PIN))
pump_pwm = PWM(Pin(PUMPPWM_PIN))

led_pwm.freq(1000)
led_pwm.duty_u16(PWM_OFF_DUTY)
pump_pwm.freq(1000)
pump_pwm.duty_u16(PWM_OFF_DUTY)

# グローバルな状態とハードウェア参照
state = DeviceState()
hw = Hardware()
menu = MenuState()
init_menu_from_settings(settings, menu)
wlan = None
menu_dirty = False
# メインループで実行すべきアクションがあるかを示すフラグ
# 学習メモ: IRQ ハンドラ内では WiFi 接続など重い処理を呼べないため、
#           フラグでメインループに処理を委ねます。
pending_execute = False

# WiFi 接続状態管理（非同期ポーリング方式）
WIFI_STATUS_IDLE = 0        # 未接続
WIFI_STATUS_CONNECTING = 1  # 接続中
WIFI_STATUS_CONNECTED = 2   # 接続済み
WIFI_STATUS_FAILED = 3      # 接続失敗

wifi_status = WIFI_STATUS_IDLE
_wifi_anim_tick = 0           # アイコンアニメーション用カウンタ
_WIFI_ANIM_CHARS = "|/-+"    # 接続中アニメーション文字（4フレーム）
_wifi_connect_start_ms = 0
_wifi_retry_count = 0
_WIFI_CONNECT_TIMEOUT_MS = 15000  # 1回の接続試行タイムアウト（15秒）
_WIFI_MAX_RETRIES = 3             # 最大リトライ回数


def apply_mode(state, mode_name):
    """モード文字列に応じて LED/PUMP を制御する。"""
    print(mode_name)
    if mode_name == "LEDON":
        led_pwm.duty_u16(PWM_ON_DUTY)
        state.set_led(True)

    elif mode_name == "LEDOFF":
        led_pwm.duty_u16(PWM_OFF_DUTY)
        state.set_led(False)

    elif mode_name == "PUMPON":
        pump_pwm.duty_u16(PWM_ON_DUTY)
        state.set_pump(True)

    elif mode_name == "PUMPOFF":
        pump_pwm.duty_u16(PWM_OFF_DUTY)
        state.set_pump(False)


def handle_right_button_event(pin):
    """RIGHT ボタン割り込みハンドラ。

    学習メモ:
    - Level 0（トップ）では RIGHT でメインメニュー項目を循環します。
    - Level 1（サブメニュー）では RIGHT で選択項目を実行／値を変更します。
    - 割り込み内では処理を軽くし、表示更新はメインループで行うようにします。
    """
    time.sleep_ms(80)
    if pin.value() == 1:
        global menu_dirty
        if menu.current_level == 0:
            # Level 0: RIGHT = メインメニュー項目を循環
            menu.next_item()
            menu_dirty = True
            print("Menu:", menu.get_current_menu_name())
        elif menu.current_level == 1:
            # Level 1: RIGHT = 選択中の項目を実行／値を変更
            # 学習メモ: IRQ ハンドラ内では重い処理を直接呼べないため、フラグでメインループに委ねます。
            global pending_execute
            pending_execute = True
            menu_dirty = True
            print("Action pending:", menu.get_current_menu_name())


def handle_left_button_event(pin):
    """LEFT ボタン割り込みハンドラ。

    学習メモ:
    - Level 0（トップ）では LEFT でサブメニューへ移行します（決定）。
    - Level 1（サブメニュー）では LEFT でサブメニュー項目を循環します。
    - Level 2（センサー表示）では LEFT でメインメニューに戻ります。
    - 割り込み内では状態変更のみ行い、重い処理（WiFi接続など）はメインループで扱います。
    """
    time.sleep_ms(80)
    if pin.value() == 1:
        global menu_dirty
        if menu.current_level == 0:
            # Level 0: LEFT = サブメニューへ移行（決定）
            if menu.main_idx == 0:  # Sensor はセンサー表示へ移行
                menu.current_level = 2
            else:
                menu.current_level = 1
                menu.sub_idx = 0  # 先頭項目から開始
            menu_dirty = True
        elif menu.current_level == 1:
            # Level 1: LEFT = サブメニュー項目を循環
            menu.next_item()
            menu_dirty = True
            print("Sub menu:", menu.get_current_menu_name())
        elif menu.current_level == 2:
            # センサー表示中: LEFT でメインメニューに戻る
            menu.back_to_main()
            menu_dirty = True
            print("Back to main (from sensor view)")


def save_menu_settings(menu):
    """現在のメニュー設定値を wifi_config.txt に保存する。
    管理外の設定値（SSID・PASSWORD など）は上書きしない。"""
    updates = {
        "LED_START_H": str(MenuState.LED_START_HOURS[menu.led_start_idx]),
        "LED_HOURS_H": str(MenuState.LED_DURATIONS_H[menu.led_duration_idx]),
        "PUMP_START_H": str(MenuState.PUMP_START_HOURS[menu.pump_start_idx]),
        "PUMP_RUN_SEC": str(MenuState.PUMP_DURATIONS_SEC[menu.pump_duration_idx]),
        "SEND_MIN": str(MenuState.SEND_INTERVALS[menu.send_interval_idx]),
        "AUTO_WIFI": "1" if menu.auto_wifi else "0",
    }
    ok = Config.save_settings(updates)
    print("Settings saved" if ok else "Settings save failed")
    return ok


def execute_menu_action():
    """現在選択されているメニュー項目を実行。"""
    submenu_list = menu.get_submenu_list()
    current_item = submenu_list[menu.sub_idx] if menu.sub_idx < len(submenu_list) else ""

    if menu.main_idx == 1:  # Network
        if menu.sub_idx == 0:  # WiFi 接続/切断トグル
            if is_wifi_connected() or wifi_status == WIFI_STATUS_CONNECTING:
                print("Executing: WiFi Disconnect")
                disconnect_wifi()
            else:
                print("Executing: WiFi Connect")
                start_wifi_connect()
        elif menu.sub_idx == 1:  # センサログ即時送信
            print("Executing: Send Now")
            if is_wifi_connected():
                log_data = read_sensors(hw)
                send_log_to_gcf(log_data)
            else:
                print("WiFi not connected")
        elif menu.sub_idx == 2:  # 自動送信間隔切替
            menu.next_send_interval()
            iv = menu.get_send_interval_min()
            print("Auto Send interval:", "OFF" if iv == 0 else str(iv) + "min")

    elif menu.main_idx == 2:  # Manual
        if menu.sub_idx == 0:  # Pump ON/OFF
            apply_mode(state, "PUMPON" if not state.pump_on else "PUMPOFF")
            print("Pump toggled")
        elif menu.sub_idx == 1:  # LED ON/OFF
            apply_mode(state, "LEDON" if not state.led_on else "LEDOFF")
            print("LED toggled")

    elif menu.main_idx == 3:  # Timer
        if menu.sub_idx == 0:  # LED Start
            menu.next_led_start()
            h = menu.LED_START_HOURS[menu.led_start_idx]
            print("LED Start:", str(h) + ":00")
        elif menu.sub_idx == 1:  # LED Hours
            menu.next_led_duration()
            h = menu.get_led_duration_h()
            print("LED Hours:", "OFF" if h == 0 else str(h) + "h")
        elif menu.sub_idx == 2:  # Pump Start
            menu.next_pump_start()
            h = menu.PUMP_START_HOURS[menu.pump_start_idx]
            print("Pump Start:", str(h) + ":00")
        elif menu.sub_idx == 3:  # Pump Run
            menu.next_pump_duration()
            sec = menu.get_pump_duration_sec()
            print("Pump Run:", "OFF" if sec == 0 else str(sec) + "s")

    elif menu.main_idx == 4:  # Config
        if menu.sub_idx == 0:  # Auto WiFi
            menu.auto_wifi = not menu.auto_wifi
            print("Auto WiFi:", "ON" if menu.auto_wifi else "OFF")
        elif menu.sub_idx == 1:  # Save
            save_menu_settings(menu)
        elif menu.sub_idx == 2:  # Test Time
            set_test_time_jst(8, 59)
            global menu_dirty
            menu_dirty = True


pin_right = Pin(RIGHT_BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)
pin_right.irq(trigger=Pin.IRQ_RISING, handler=handle_right_button_event)

pin_left = Pin(LEFT_BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)
pin_left.irq(trigger=Pin.IRQ_RISING, handler=handle_left_button_event)


def blink_led(times=5, sec=0.1):
    for _ in range(times):
        led.value(1)
        time.sleep(sec)
        led.value(0)
        time.sleep(sec)


def print2(text):
    print(text)


def now_jst_tuple():
    """現在時刻を JST の localtime タプルで返す。"""
    return time.localtime(time.time() + JST_OFFSET_SEC)


def now_jst_minute_of_day():
    tm = now_jst_tuple()
    return tm[3] * 60 + tm[4]


def day_key_jst():
    tm = now_jst_tuple()
    return (tm[0], tm[1], tm[2])


def _draw_wifi_icon(oled):
    """OLED 右上（x=120, y=0）に WiFi 接続状態を 1 文字で常時表示する。
    W=接続済み  !=失敗  -=未接続  |/-+=接続中アニメーション"""
    global _wifi_anim_tick
    if wifi_status == WIFI_STATUS_CONNECTED:
        icon = "W"
    elif wifi_status == WIFI_STATUS_CONNECTING:
        icon = _WIFI_ANIM_CHARS[_wifi_anim_tick % 4]
        _wifi_anim_tick += 1
    elif wifi_status == WIFI_STATUS_FAILED:
        icon = "!"
    else:
        icon = "-"
    oled.text(icon, 120, 0)


# センサーの値をOLEDに表示
def disp_sensor_value(hw, state, data, timestr):
    if hw.has_oled():
        hw.oled.fill_rect(0, 0, hw.oled.width, hw.oled.height, 0)
        main_name = menu.MAIN_MENUS[menu.main_idx]
        hw.oled.text("> " + main_name, 0, 0)
        t = 6
        hw.oled.text("Temp: {:.1f}C".format(data["temperature"]), 0, t + 10)
        hw.oled.text("Humi: {:.1f}%".format(data["humidity"]), 0, t + 20)
        hw.oled.text("Ligh: {:.1f}Lx".format(data["illuminance"]), 0, t + 30)
        hw.oled.text("Soil: {}".format(data["soil_moisture"]), 0, t + 40)
        hw.oled.text(f"{timestr}", 0, t + 50)
        _draw_wifi_icon(hw.oled)
        hw.oled.show()


def disp_menu(hw, menu):
    """メニュー画面をOLEDに表示。"""
    if not hw.has_oled():
        return

    hw.oled.fill_rect(0, 0, hw.oled.width, hw.oled.height, 0)

    if menu.current_level == 0:
        # Level 0: Display submenu of selected main item, with selector on left of main item
        main_name = menu.MAIN_MENUS[menu.main_idx]
        # Show main item with selector on left
        hw.oled.text("> " + main_name, 0, 0)
        
        submenu_list = menu.get_submenu_list()
        # Show submenu items (without selector in level 0)
        for i, item in enumerate(submenu_list):
            hw.oled.text("  " + item, 0, 10 + i * 10)
        
        hw.oled.text("[L] Select", 0, 56)

    elif menu.current_level == 1:
        main_name = menu.MAIN_MENUS[menu.main_idx]
        hw.oled.text(main_name, 0, 0)
        submenu_list = menu.get_submenu_list()

        for i, item in enumerate(submenu_list):
            marker = "> " if i == menu.sub_idx else "  "
            hw.oled.text(marker + item, 0, 10 + i * 10)

        status_line = ""

        if menu.main_idx == 1:  # Network
            if menu.sub_idx == 0:  # WiFi
                if wifi_status == WIFI_STATUS_CONNECTING:
                    status_line = "WiFi:..."
                else:
                    status_line = "WiFi:" + ("ON" if is_wifi_connected() else "OFF")
            elif menu.sub_idx == 2:  # Auto Send
                iv = menu.get_send_interval_min()
                status_line = "Auto:" + ("OFF" if iv == 0 else str(iv) + "min")
        elif menu.main_idx == 3:
            if menu.sub_idx == 0:  # LED Start
                h = menu.LED_START_HOURS[menu.led_start_idx]
                status_line = "LED:" + str(h) + ":00"
            elif menu.sub_idx == 1:  # LED Hours
                h = menu.get_led_duration_h()
                status_line = "LED:" + ("OFF" if h == 0 else str(h) + "h")
            elif menu.sub_idx == 2:  # Pump Start
                h = menu.PUMP_START_HOURS[menu.pump_start_idx]
                status_line = "Pump:" + str(h) + ":00"
            elif menu.sub_idx == 3:  # Pump Run
                sec = menu.get_pump_duration_sec()
                status_line = "Pump:" + ("OFF" if sec == 0 else str(sec) + "s")
        elif menu.main_idx == 4:  # Config
            if menu.sub_idx == 0:  # Auto WiFi
                status_line = "AutoWiFi:" + ("ON" if menu.auto_wifi else "OFF")
            elif menu.sub_idx == 2:  # Test Time
                status_line = format_local_time()

        if status_line:
            hw.oled.text(status_line, 0, 56)
        else:
            hw.oled.text("[R] Execute", 0, 56)

    _draw_wifi_icon(hw.oled)
    hw.oled.show()


def send_log_to_gcf(data):
    """Google Apps Script（GAS）にログを送信する関数。

    学習メモ:
    - `urequests.post` で JSON を送ります。
    - 実機ではネットワークエラーやタイムアウトに備えたリトライ処理が必要です。
    """
    headers = {"Content-Type": "application/json"}
    try:
        payload = json.dumps(data)
        response = urequests.post(GAS_URL, headers=headers, data=payload)
        print(f"GAS Response Status: {response.status_code}")
        print(f"GAS Response Text: {response.text}")
        response.close()
        return True
    except Exception as e:
        print(f"Error sending data to GAS: {e}")
        return False


# 水分率(%) = ((乾燥値 - ADC値) / (乾燥値 - 冠水値)) × 100
def calculate_soil_moisture(adc_value, dry=3000, wet=1400):
    """
    ADC値から土壌水分率(%)を計算する。
    dry: 乾燥時のADC値（高い）
    wet: 冠水時のADC値（低い）
    """
    if adc_value >= dry:
        return 0.0
    elif adc_value <= wet:
        return 100.0
    moisture = ((dry - adc_value) / (dry - wet)) * 100
    return round(moisture, 1)


def init_adc_if_needed(hw):
    if hw.adc_pin is None:
        try:
            hw.adc_pin = ADC(Pin(1, Pin.IN))
            hw.adc_pin.atten(ADC.ATTN_11DB)
            hw.adc_pin.width(ADC.WIDTH_12BIT)
        except Exception as e:
            print("ADC initialization error:", e)


def init_i2c_if_needed(hw):
    if hw.i2c is None:
        try:
            hw.i2c = I2C(0, scl=Pin(23), sda=Pin(22))
        except Exception as e:
            print("I2C initialization error:", e)


def init_oled_if_needed(hw):
    if hw.has_i2c() and not hw.has_oled():
        try:
            hw.oled = SSD1306_I2C(128, 64, hw.i2c)
        except OSError as e:
            print("Error initializing oled:", e)


def read_sensors(hw):
    """センサーから値を読み取り、ログ送信用の辞書を返す。

    学習メモ:
    - ADC（土壌水分）、AHT20（温湿度）、BH1750（照度）を順に初期化して読み取ります。
    - センサーは接続状態や読み取りエラーが起きるため例外処理を行い、安全に動作させます。
    - 戻り値は `temperature`, `humidity`, `soil_moisture`, `illuminance` などを含む辞書です。
    """
    temperature = 0
    humidity = 0
    soil_moisture = 0
    illuminance = 0
    pressure = 0

    init_adc_if_needed(hw)
    if hw.has_adc():
        try:
            soil_moisture = hw.adc_pin.read()
        except Exception as e:
            print("Soil moisture sensor error:", e)

    init_i2c_if_needed(hw)
    init_oled_if_needed(hw)

    if hw.has_i2c():
        try:
            aht20 = AHT20(hw.i2c)
            temperature = round(aht20.temperature, 1)
            humidity = round(aht20.relative_humidity, 1)
        except Exception as e:
            print("AHT20 sensor error:", e)

        for _ in range(2):
            try:
                bh1750 = BH1750(hw.i2c)
                illuminance = round(bh1750.measurement, 1)
                break
            except Exception as e:
                print("BH1750 sensor error:", e)
            time.sleep(1)

    log_data = {
        "timestamp": time.time(),
        "device_id": DEVICEID,
        "temperature": temperature,
        "humidity": humidity,
        "soil_moisture": soil_moisture,
        "illuminance": illuminance,
        "pressure": pressure,
    }
    return log_data


def is_wifi_connected():
    """現在 Wi-Fi に接続中かどうかを返す。

    学習メモ:
    - グローバルな `wlan` オブジェクトが存在し、接続状態であれば True を返します。
    """
    return wlan is not None and wlan.isconnected()


def start_wifi_connect():
    """非同期 WiFi 接続を開始する（即座に返る）。接続完了は poll_wifi_status() でポーリングする。"""
    global wlan, wifi_status, _wifi_connect_start_ms, _wifi_retry_count
    if wifi_status == WIFI_STATUS_CONNECTING:
        return
    _wifi_retry_count = 0
    wifi_status = WIFI_STATUS_CONNECTING
    _wifi_connect_start_ms = time.ticks_ms()
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep_ms(200)
    try:
        wlan.connect(SSID, PASSWORD)
        print("WiFi connect initiated")
    except Exception as e:
        print("WiFi connect error:", e)
        wifi_status = WIFI_STATUS_FAILED


def poll_wifi_status():
    """WiFi 接続の進行を確認・更新する。メインループから毎回呼び出す。
    接続完了時は NTP 時刻同期も実行する。接続中断・失敗はリトライする。"""
    global wlan, wifi_status, _wifi_connect_start_ms, _wifi_retry_count
    if wifi_status == WIFI_STATUS_CONNECTED:
        # 接続が切断された場合を検出して IDLE に戻す
        if not (wlan is not None and wlan.isconnected()):
            wifi_status = WIFI_STATUS_IDLE
        return
    if wifi_status != WIFI_STATUS_CONNECTING:
        return
    if wlan is None:
        wifi_status = WIFI_STATUS_FAILED
        return
    if wlan.isconnected():
        wifi_status = WIFI_STATUS_CONNECTED
        print("WiFi connected:", wlan.ifconfig()[0])
        set_time(retries=2)
        return
    elapsed = time.ticks_diff(time.ticks_ms(), _wifi_connect_start_ms)
    if elapsed >= _WIFI_CONNECT_TIMEOUT_MS:
        _wifi_retry_count += 1
        if _wifi_retry_count >= _WIFI_MAX_RETRIES:
            wifi_status = WIFI_STATUS_FAILED
            print("WiFi failed after", _WIFI_MAX_RETRIES, "retries")
            wlan.active(False)
        else:
            print("WiFi retry", _wifi_retry_count, "...")
            _wifi_connect_start_ms = time.ticks_ms()
            try:
                wlan.disconnect()
                wlan.connect(SSID, PASSWORD)
            except Exception as e:
                print("WiFi retry error:", e)


def disconnect_wifi():
    global wlan, wifi_status
    print("WiFi disconnecting...")
    if wlan:
        wlan.disconnect()
        wlan.active(False)
        print("WiFi disconnected")
    wifi_status = WIFI_STATUS_IDLE


def connect_wifi(retries_per_attempt=20, attempts=3):
    wlan = network.WLAN(network.STA_IF)
    for _ in range(attempts):
        wlan.active(True)
        time.sleep(1)
        try:
            wlan.connect(SSID, PASSWORD)
        except Exception as e:
            print2(str(e))

        time.sleep(1)
        for i in range(retries_per_attempt):
            if wlan.isconnected():
                print2(f"Connected in {i + 1} seconds.")
                return wlan
            blink_led(2, 0.5)
            print2(f"Try...{i + 1}")
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
    tm = now_jst_tuple()
    return "{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        tm[1], tm[2], tm[3], tm[4], tm[5]
    )


def set_test_time_jst(h=8, m=59):
    """テスト用に内部時計を指定の JST 時刻に設定する。
    JST 時刻を UTC に変換して RTC に書き込む。日付はテスト用固定（2025-01-01）。"""
    utc_total_min = h * 60 + m - 9 * 60  # JST→UTC変換
    if utc_total_min < 0:
        utc_total_min += 24 * 60
    utc_h = utc_total_min // 60
    utc_m = utc_total_min % 60
    # 固定日付（テスト用）: 2025-01-01（水曜日 = weekday 2）UTC
    RTC().datetime((2025, 1, 1, 2, utc_h, utc_m, 50, 0))
    print("Test time set:", format_local_time())


def parse_hhmm_to_min(hhmm):
    hh, mm = hhmm.split(":")
    hh = int(hh)
    mm = int(mm)
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        raise ValueError("time out of range")
    return hh * 60 + mm


def parse_optional_schedule_min(value, label):
    """空文字なら None、形式が不正なら警告して None を返す。"""
    if not value:
        print(f"{label} timer disabled: value is empty")
        return None
    try:
        return parse_hhmm_to_min(value)
    except Exception as e:
        print(f"{label} schedule format error:", e)
        return None


def is_in_active_period(now_min, on_min, off_min):
    """ON/OFF の時刻範囲に now_min が含まれるか判定する。"""
    if on_min <= off_min:
        return on_min <= now_min < off_min
    return (now_min >= on_min) or (now_min < off_min)


def control_led_by_schedule(state, on_min, off_min):
    now_min = now_jst_minute_of_day()
    should_on = is_in_active_period(now_min, on_min, off_min)

    if should_on and not state.led_on:
        apply_mode(state, "LEDON")
    elif (not should_on) and state.led_on:
        apply_mode(state, "LEDOFF")


def control_pump_by_schedule(state, on_min, run_ms):
    # ── 稼働中チェック: 時間が来たら自動停止 ──────────────────────────
    if state.pump_start_ms is not None:
        elapsed = time.ticks_diff(time.ticks_ms(), state.pump_start_ms)
        if elapsed >= state.pump_run_ms:
            apply_mode(state, "PUMPOFF")
            print("PUMP schedule end:", format_local_time())
            state.pump_start_ms = None
        return  # 停止判定の有無に関わらず、今回ループの起動チェックはスキップ

    now_min = now_jst_minute_of_day()

    # ── 指定分を外れたらトリガーフラグをリセット（翌日・同日再テスト対応）──
    if now_min != on_min:
        state.pump_triggered_min = -1
        return

    # ── 指定分に到達: 稼働時間 > 0 かつ同分未トリガーなら起動 ────────────
    if run_ms > 0 and state.pump_triggered_min != on_min:
        print("PUMP schedule start:", format_local_time(), "for", run_ms, "ms")
        state.pump_triggered_min = on_min
        state.pump_start_ms = time.ticks_ms()
        state.pump_run_ms = run_ms
        apply_mode(state, "PUMPON")


def apply_schedule_controls(state, menu):
    """メニューのタイマー設定を考慮してスケジュール制御を実行。"""
    # LED タイマー: メニューで選択した開始時刻から指定時間数だけ自動点灯
    led_h = menu.get_led_duration_h()
    if led_h > 0:
        led_on_min = menu.get_led_start_min()
        led_off_min = led_on_min + led_h * 60
        control_led_by_schedule(state, led_on_min, led_off_min)

    # ポンプタイマー: 稼働中の停止チェックも含め常に呼び出す
    pump_sec = menu.get_pump_duration_sec()
    pump_on_min = menu.get_pump_start_min()
    control_pump_by_schedule(state, pump_on_min, pump_sec * 1000)


def run_cycle(hw, state, menu):
    """1サイクル分の制御とセンサー読み取りを行う。"""
    apply_schedule_controls(state, menu)
    log_data = read_sensors(hw)

    # 表示: レベル0=メインメニュー表示、レベル1=サブメニュー表示、レベル2=センサー表示
    # 学習メモ: Sensor が選択されている（main_idx==0）場合はセンサー情報を表示します。
    if menu.main_idx == 0:
        disp_sensor_value(hw, state, log_data, format_local_time())
    else:
        disp_menu(hw, menu)

    return log_data


def main():
    """メイン処理。

    学習メモ:
    - 起動時は Wi-Fi に自動接続しません。
    - Network メニューの "WiFi Connect" から手動で接続してください。
    - 接続後は NTP 時刻同期が自動で行われ、ログ送信が有効になります。
    """
    # スケジュール設定を読み込む（Wi-Fi 接続は不要）
    pump_on_min = parse_optional_schedule_min(PUMP_ON, "PUMP")  # noqa: unused (start time managed by menu)

    # AUTO_WIFI=1 のとき起動時に Wi-Fi へ非同期で自動接続する
    if AUTO_WIFI:
        print("Auto WiFi connecting (async)...")
        start_wifi_connect()

    last_send_ms = time.ticks_ms()

    while True:
        # WiFi 非同期接続の進行確認（接続完了・リトライ・失敗検出）
        poll_wifi_status()

        # pending_execute フラグが立っていればメニュー動作を実行する
        # 学習メモ: WiFi 接続など時間のかかる処理はここで実行します。
        global pending_execute
        if pending_execute:
            pending_execute = False
            execute_menu_action()

        log_data = run_cycle(hw, state, menu)

        # Wi-Fi に接続中かつ自動送信間隔が設定されているときだけログを送信する
        # 学習メモ: 間隔 0 は「無効」を意味します。
        if is_wifi_connected():
            send_interval_min = menu.get_send_interval_min()
            if send_interval_min > 0:
                send_interval_ms = send_interval_min * 60 * 1000
                now_ms = time.ticks_ms()
                if time.ticks_diff(now_ms, last_send_ms) >= send_interval_ms:
                    last_send_ms = now_ms
                    send_log_to_gcf(log_data)

        time.sleep(0.2)


main()
