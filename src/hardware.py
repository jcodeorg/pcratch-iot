# ESP32C6 pcratch-IoT v1.5.1.1
import struct
import framebuf
import network
from machine import Pin, I2C, ADC, PWM
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel
from ahtx0 import AHT20

VERSION = 'v1.5.1.1'

class Hardware:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Hardware, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):  # 初期化が1回だけ行われるようにする
            self.initialized = True
            self.version = VERSION
            print(f"Welcome to ESP32C6 pcratch-IoT {self.version}")
            # ESP32C6 Pin layout
            #                     GPIO15: USER LED
            # GPIO0 :A0 :         5V
            # GPIO1 :A1 :         GND
            # GPIO2 :A2 :         3V3
            # GPIO21:   : Speaker GPIO18:   :Left Button
            # GPIO22:SDA:         GPIO20:   :
            # GPIO23:SDL:         GPIO19:   :
            # GPIO16:TX : NP-LED  GPIO17:RX :Right Button
            self.adc0 = Pin(0, Pin.IN, Pin.PULL_DOWN)
            self.PWM01 = PWM(Pin(1, Pin.OUT), freq=50, duty=0)
            self.adc2 = ADC(Pin(2, Pin.IN))
            self.adc2.atten(ADC.ATTN_11DB)
            self.adc2.width(ADC.WIDTH_12BIT)
            self.i2c = I2C(0, scl=Pin(23), sda=Pin(22))
            self.PIN15 = Pin(15, Pin.OUT)    # USER LED
            self.PIN16 = NeoPixel(Pin(16, Pin.OUT), 2)
            self.PIN17 = Pin(17, Pin.IN, Pin.PULL_DOWN)
            self.PIN18 = Pin(18, Pin.IN, Pin.PULL_DOWN)
            self.PWM19 = PWM(Pin(19, Pin.OUT), freq=50, duty=0)
            self.PWM20 = PWM(Pin(20, Pin.OUT), freq=50, duty=0)
            self.PWM21 = PWM(Pin(21, Pin.OUT), freq=50, duty=0)
            self.init_oled()
            self.init_aht20()
            self.init_pixcel()
            self.register_button_irq()
            self.pin_event_time = {}
            self.button_handlers = {}  # ハンドラーを登録する辞書

            self.PASSWORD = "12345678"
            self.wifi_ap = None  # Wi-Fiアクセスポイントのインスタンス
            self.ssid = None  # SSID
            self.wifi_sta = None  # Wi-Fiステーションのインスタンス（インターネット接続）

            self.PIN15 = Pin(15, Pin.OUT)    # create output pin on GPIO0
            # p1 = Pin(3, Pin.OUT)    # create output pin on GPIO0
            # p1.value(1)
            self.device =None

    def get_friendly_name(self, unique_id):
        """ユニークIDからフレンドリー名を生成"""
        length = 5
        letters = 5
        codebook = [
            ['z', 'v', 'g', 'p', 't'],
            ['u', 'o', 'i', 'e', 'a'],
            ['z', 'v', 'g', 'p', 't'],
            ['u', 'o', 'i', 'e', 'a'],
            ['z', 'v', 'g', 'p', 't']
        ]
        name = []
        mac_padded = b'\x00\x00' + unique_id
        _, n = struct.unpack('>II', mac_padded)
        ld = 1
        d = letters

        for i in range(0, length):
            h = (n % d) // ld
            n -= h
            d *= letters
            ld *= letters
            name.insert(0, codebook[i][h])

        return "".join(name)

    def wifi_ap_active(self):
        if self.wifi_ap is None:
            self.wifi_ap = network.WLAN(network.AP_IF)
        if not self.wifi_ap.active():
            self.wifi_ap.active(True)   # APモードを有効化
        return self.wifi_ap

    def get_wifi_ap_ssid(self):
        """ ssid を返却 """
        self.wifi_ap_active()
        if self.ssid is None:
            self.ssid = "PcratchIoT-" + self.get_friendly_name(self.wifi_ap.config('mac'))
        print("SSID:", self.ssid)
        return self.ssid

    def wifi_ap_conect(self):
        """Wi-Fiに接続"""
        self.get_wifi_ap_ssid()
        self.wifi_ap.config(essid=self.ssid, password=self.PASSWORD)
        return self.wifi_ap

    def get_wifi_sta(self):
        """Wi-Fiステーションのインスタンスを返す"""
        if self.wifi_sta is None:
            self.wifi_sta = network.WLAN(network.STA_IF)
        return self.wifi_sta

    def wifi_sta_active(self):
        """Wi-Fiを ステーション (Station) モードで起動 """
        self.get_wifi_sta()
        if not self.wifi_sta.active():
            self.wifi_sta.active(True)
        return self.wifi_sta

    def get_wifi_config(self):
        """デフォルトのSSIDとパスワードを読み込む"""
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
        except Exception as e:
            print(f"wifi_config.txt 読み込みエラー: {e}")
        return default_ssid, default_password, default_main_module

    def init_oled(self):
        self.oled = None
        try:
            self.oled = SSD1306_I2C(128, 64, self.i2c)
        except OSError as e:
            print(f"Error initializing oled: {e}")
    
    # 画面をさかさまにするコマンドを送信
    def flip_display(self):
        self.oled.write_cmd(0xA0)  # セグメントリマップ
        self.oled.write_cmd(0xC0)  # COM出力スキャン方向

    def init_aht20(self):
        self.aht20 = None
        try:
            self.aht20 = AHT20(self.i2c)
        except OSError as e:
            print(f"Error initializing aht20: {e}")

    # ボタンの状態を取得
    def get_button_state(self, button_name):
        return self.button_state[button_name]

    def register_button_handler(self, pinIndex, handler):
        """ボタンイベントのハンドラーを登録"""
        self.button_handlers[pinIndex] = handler
        print(f"register_button_handler {pinIndex} {handler} {len(self.button_handlers)}")

    def handle_button_event(self, pin, pinIndex):
        # time.sleep_ms(80)  # 80msの遅延を追加してチャタリングを軽減
        # print(f"event {pinIndex}")
        current_event = "RISE" if pin.value() == 1 else "FALL"
        if pinIndex not in self.pin_event_time:
            self.pin_event_time[pinIndex] = ''

        if current_event == self.pin_event_time[pinIndex]:
            return  # 同じイベントが発生した場合は無視
        self.pin_event_time[pinIndex] = current_event
        # print(f"event {pinIndex}  {current_event} {len(self.button_handlers)}")
        # 登録されたハンドラーを呼び出す
        if pinIndex in self.button_handlers:
            handler = self.button_handlers[pinIndex]
            # print(f"handler {pinIndex} に {current_event} イベント")
            handler(pinIndex, current_event)  # ハンドラーにイベントを渡す

    def register_button_irq(self):
        """ボタンのIRQを登録"""
        self.PIN17.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: self.handle_button_event(pin, 17))
        self.PIN18.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: self.handle_button_event(pin, 18))

    # print(f"ピン {pin} に {n} を出力")
    def digital_out(self, pin, n):
        duty = 0 if n == 0 else 65535
        if pin == 19:
            self.PWM19.duty_u16(duty)
        elif pin == 20:
            self.PWM20.duty_u16(duty)
        elif pin == 1:
            self.PWM01.duty_u16(duty)
        elif pin == 15: # ユーザLED
            self.PIN15.value(n)

    # print(f"ピン {pin} をアナログ出力 {n} %にする")
    def analog_out(self, pin, n):
        duty = int(65535 * n / 1024)
        if pin == 19:
            self.PWM19.duty_u16(duty)
        elif pin == 20:
            self.PWM20.duty_u16(duty)
        elif pin == 1:
            self.PWM01.duty_u16(duty)
        elif pin == 15: # ユーザLED
            self.PIN15.value(1 if n != 0 else 0)

    def show_text(self, s, t=0):
        # print(f"文字 {s} を {t} ミリ秒間隔で流す")
        # 上10ドットを消去
        if self.oled:
            self.oled.fill_rect(0, 0, self.oled.width, 10, 0)
            self.oled.text(s, 0, 0)
            self.oled.show()
        else:
            print("OLED not initialized", s)

    def draw_icon(self, icon, x, y):
        if self.oled:
            self.oled.fill_rect(x, y, 8, 5, 0)
            for dx, val in enumerate(icon):
                if val:
                    self.oled.pixel(x + dx % 5, y + int(dx / 5), 1)
            self.oled.show()

    def play_tone(self, f, v = 100):
        # print(f"Tone {f}Hz {v}% ...")
        self.PWM21.freq(int(f))
        self.PWM21.duty_u16(32768)  # duty_u16を50%に設定（65535の半分）

    def stop_tone(self):
        # print("Tone off")
        self.PWM21.duty_u16(0)    # 音を消す

    def human_sensor(self):
        if self.adc0:
            val = self.adc0.value()
            if val != 0:
                return 1
        return 0

    def lux(self):
        val = self.adc2.read_u16() / 65535 * 3.6 * 20/9/10000 * (10 ** 6)
        return val

    def temp_humi(self):
        if self.aht20:
            temperature = self.aht20.temperature
            humidity = self.aht20.relative_humidity
        else:
            temperature = 0
            humidity = 0
        return temperature, humidity

    def pixcel(self, n, r, g, b):
        self.PIN16[n] = (int(r / 100 * 255), int(g / 100 * 255), int(b / 100 * 255))  # n番の NeoPixel を点灯
        self.PIN16.write()

    def init_pixcel(self):
        self.pixcel(0, 0, 0, 0)

    # ESP32 VSYS電源電圧を取得する
    def getVsys(self):
        Pin(29, Pin.IN)
        volt = ADC(3).read_u16() / 65535 * 3.3 * 3
        return volt

    def send_oled_bitmap_24(self, cl):
        """OLEDのバッファを24ビットBMP形式で送信（上下正しい）"""
        if self.oled:
            print("send_oled_bitmap_24")
            # OLEDのバッファを取得
            width, height = self.oled.width, self.oled.height
            row_size = (width * 3 + 3) // 4 * 4  # 各行のバイト数（4バイト境界に揃える）
            pixel_array_size = row_size * height
            file_size = 54 + pixel_array_size  # ヘッダー(54バイト) + ピクセルデータ

            # BMPヘッダーを作成
            bmp_header = bytearray([
                0x42, 0x4D,  # "BM" signature
                file_size & 0xFF, (file_size >> 8) & 0xFF, (file_size >> 16) & 0xFF, (file_size >> 24) & 0xFF,  # ファイルサイズ
                0x00, 0x00,  # 予約領域1
                0x00, 0x00,  # 予約領域2
                0x36, 0x00, 0x00, 0x00,  # ピクセルデータのオフセット (54バイト)
                0x28, 0x00, 0x00, 0x00,  # ヘッダーサイズ (40バイト)
                width & 0xFF, (width >> 8) & 0xFF, 0x00, 0x00,  # 幅
                height & 0xFF, (height >> 8) & 0xFF, 0x00, 0x00,  # 高さ
                0x01, 0x00,  # プレーン数 (1)
                0x18, 0x00,  # ビット/ピクセル (24)
                0x00, 0x00, 0x00, 0x00,  # 圧縮形式 (なし)
                pixel_array_size & 0xFF, (pixel_array_size >> 8) & 0xFF, (pixel_array_size >> 16) & 0xFF, (pixel_array_size >> 24) & 0xFF,  # 画像データサイズ
                0x13, 0x0B, 0x00, 0x00,  # 水平解像度 (2835ピクセル/m)
                0x13, 0x0B, 0x00, 0x00,  # 垂直解像度 (2835ピクセル/m)
                0x00, 0x00, 0x00, 0x00,  # 使用色数 (0 = 全色)
                0x00, 0x00, 0x00, 0x00   # 重要色数 (0 = 全色)
            ])

            # HTTPレスポンスヘッダーを送信
            cl.send(b"HTTP/1.1 200 OK\r\n")
            cl.send(b"Content-Type: image/bmp\r\n")
            cl.send(b"Content-Disposition: inline; filename=\"oled_bitmap.bmp\"\r\n")
            cl.send(b"\r\n")

            # BMPヘッダーを送信
            cl.send(bmp_header)

            # OLEDのピクセルデータを取得
            buffer = bytearray(width * height)  # バッファを作成
            fb = framebuf.FrameBuffer(buffer, width, height, framebuf.MONO_HLSB)

            # OLEDの内容をバッファにコピー
            for y in range(height):
                for x in range(width):
                    if self.oled.pixel(x, y):
                        fb.pixel(x, y, 1)

            # ピクセルデータを行ごとに送信
            for y in range(height):  # 上下反転のために通常の順序でループ
                row_data = bytearray(row_size)  # 行データを格納するバッファ
                for x in range(width):
                    flipped_y = height - 1 - y  # 上下反転
                    pixel = fb.pixel(x, flipped_y)
                    if pixel:
                        # 白 (RGB: 255, 255, 255)
                        row_data[x * 3:x * 3 + 3] = b'\xFF\xFF\xFF'
                    else:
                        # 黒 (RGB: 0, 0, 0)
                        row_data[x * 3:x * 3 + 3] = b'\x00\x00\x00'
                # パディングを追加（4バイト境界に揃える）
                row_data[width * 3:] = b'\x00' * (row_size - width * 3)
                # 行データを送信
                cl.send(row_data)

            print("end send_oled_bitmap_24")