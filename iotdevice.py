# ESP32C6 pcratch-IoT(micro:bit) v1.2.0
import os
import struct
import time
from machine import Pin, I2C, ADC, PWM
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel
from ahtx0 import AHT20

# ボタン関連の定義
MbitMoreDataFormat = {
    "CONFIG": 0x10,     # not used at this version
    "PIN_EVENT": 0x11,
    "ACTION_EVENT": 0x12,
    "DATA_NUMBER": 0x13,
    "DATA_TEXT": 0x14
}
MbitMoreActionEvent = {
  "BUTTON": 0x01,
  "GESTURE": 0x02
}
MbitMoreButtonID = {
    1: 'A',
    2: 'B',
    100: 'P0',
    101: 'P1',
    102: 'P2',
    121: 'LOGO'
}
MbitMoreButtonName = {v: k for k, v in MbitMoreButtonID.items()}

MbitMoreButtonEventID = {
    1: 'DOWN',
    2: 'UP',
    3: 'CLICK',
    4: 'LONG_CLICK',
    5: 'HOLD',
    6: 'DOUBLE_CLICK'
}
MbitMoreButtonEventName = {v: k for k, v in MbitMoreButtonEventID.items()}

class Device:
    def __init__(self, ble_conn):
        self.ble_conn = ble_conn # TODO: BLEConnectionを初期化する
        self.device_info = os.uname()
        self.init_device()
        self.button_state = {
            'A': {'pressed': False, 'press_time': 0, 'down_count': 0},
            'B': {'pressed': False, 'press_time': 0, 'down_count': 0}
        }

    def init_device(self):
        if 'ESP32C6' in self.device_info.machine:
            self.init_esp32c6()
        elif 'Raspberry Pi Pico W with RP2040' in self.device_info.machine:
            self.init_pico_w()
        else:
            print("This device is not supported:", self.device_info.machine)

    def init_esp32c6(self):
        # ESP32C6 Pin layout
        # GPIO0 :A0 :       5V
        # GPIO1 :A1 :       GND
        # GPIO2 :A2 :       3V3
        # GPIO21:   :       GPIO18:   :
        # GPIO22:SDA:       GPIO20:   :
        # GPIO23:SDL:       GPIO19:   :
        # GPIO16:TX :       GPIO17:RX :
        print("Welcome to ESP32C6")
        self.adc0 = ADC(Pin(0, Pin.IN))
        self.adc1 = ADC(Pin(1, Pin.IN))
        self.adc2 = ADC(Pin(2, Pin.IN))
        self.adc2.atten(ADC.ATTN_11DB)
        self.adc2.width(ADC.WIDTH_12BIT)
        self.out0 = PWM(Pin(21, Pin.OUT), freq=50, duty=0)
        self.i2c = I2C(0, scl=Pin(23), sda=Pin(22))
        self.out3 = NeoPixel(Pin(16, Pin.OUT), 4)
        self.out1 = PWM(Pin(19, Pin.OUT), freq=50, duty=0)
        self.out2 = PWM(Pin(20, Pin.OUT), freq=50, duty=0)
        self.inp0 = Pin(17, Pin.IN, Pin.PULL_UP)
        self.inp1 = Pin(20, Pin.IN, Pin.PULL_UP)
        self.p18 = Pin(18, Pin.IN, Pin.PULL_DOWN)
        self.init_oled()
        self.init_aht20()
        self.init_pixcel()
        self.register_button_irq()

    def init_pico_w(self):
        self.p18 = None
        self.adc2 = ADC(0)
        self.adc1 = ADC(1)
        self.out0 = PWM(Pin(2, Pin.OUT))
        self.inp0 = Pin(3, Pin.IN, Pin.PULL_UP)
        self.inp1 = Pin(7, Pin.IN, Pin.PULL_UP)
        self.out3 = NeoPixel(Pin(21, Pin.OUT), 4)
        self.i2c = I2C(0, scl=Pin(1), sda=Pin(0))
        self.init_oled()
        self.init_aht20()
        self.init_pixcel()
        self.register_button_irq()

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
    
    def handle_button_event(self, pin, button_name):
        if pin.value() == 0:  # ボタンが押された
            if not self.button_state[button_name]['pressed']:
                self.button_state[button_name]['pressed'] = True
                self.button_state[button_name]['press_time'] = time.ticks_ms()
                self.button_state[button_name]['down_count'] += 1
                print(f"Button {button_name} DOWN, Count: {self.button_state[button_name]['down_count']}")
                self.button_notification(button_name, "DOWN")
        else:  # ボタンが離された
            if self.button_state[button_name]['pressed']:
                self.button_state[button_name]['pressed'] = False
                press_duration = time.ticks_diff(time.ticks_ms(), self.button_state[button_name]['press_time'])
                if press_duration < 500:
                    self.button_notification(button_name, "CLICK")
                else:
                    self.button_notification(button_name, "UP")

    def register_button_irq(self):
        self.inp0.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: self.handle_button_event(pin, 'A'))
        self.inp1.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: self.handle_button_event(pin, 'B'))

    def analog_out(self, pin, n):
        # print(f"ピン {pin} をアナログ出力 {n} %にする")
        if pin == 0 or pin == 21:
            self.out0.duty_u16(int(65535 * n / 1024))
        elif pin == 1 or pin == 19:
            self.out1.duty_u16(int(65535 * n / 1024))
        elif pin == 2 or pin == 20:
            self.out2.duty_u16(int(65535 * n / 1024))

    async def do_command(self, data):
        # バイナリデータをリストに変換
        data_list = list(data)
        print(data_list)  # 出力: [1, 72, 101, 108, 108, 111]
        command_id = data_list[0]
        if command_id == 65:
            # 文字 s を t ミリ秒間隔で流す
            self.show_text(data[2:].decode('utf-8'), data[1])
        elif command_id == 34:
            # ピン pin をアナログ出力 n %にする
            pin = data[1]
            uint16_value = struct.unpack('<H', data[2:4])[0]     # 続く2バイトを数値に変換
            # print("ピン", pin, "をアナログ出力", uint16_value, "%にする")
            self.analog_out(pin, uint16_value)
        elif command_id == 96:
            # 音を消す
            self.stop_tone()
        elif command_id == 97:
            # 1000000/data[1:5] Hzの音を data[5]/255*100 %の大きさで鳴らす
            # vol は 0 か、それ以外で音量を調節できない
            four_bytes = data[1:5]  # data[2:] から4バイトを取得
            uint32_value = struct.unpack('<I', four_bytes)[0]   # 4バイトを uint32 の数値に変換
            self.play_tone(1000000 / uint32_value, data[5]/255*100)
        elif command_id == 130:
            label = data[1:9].decode('utf-8')
            value = data[9:].decode('utf-8')
            print("label:", label, value)
            # NeoPixcelを光らせる
            if label=='pixcel-0':
                self.pixcel_n(0, value)
            elif label=='pixcel-1':
                self.pixcel_n(1, value)
            elif label=='pixcel-2':
                self.pixcel_n(2, value)
        elif command_id == 66:
            # アイコン表示（上5x3）
            self.draw_icon(data[1:], 0, 0)
        elif command_id == 67:
            # アイコン表示（下5x2）
            self.draw_icon(data[1:], 0, 3)   # 下の部分だけ書き直す
        else:
            print("Command ID", command_id, "is not defined.")
        return True

    def show_text(self, s, t=0):
        # print(f"文字 {s} を {t} ミリ秒間隔で流す")
        # 上10ドットを消去
        if self.oled:
            self.oled.fill_rect(0, 0, self.oled.width, 10, 0)
            self.oled.text(s, 0, 0)
            self.oled.show()

    def draw_icon(self, icon, x, y):
        if self.oled:
            self.oled.fill_rect(x, y, 8, 5, 0)
            for dx, val in enumerate(icon):
                if val:
                    self.oled.pixel(x + dx % 5, y + int(dx / 5), 1)
            self.oled.show()

    def play_tone(self, f, v):
        self.out0.freq(int(f))
        self.out0.duty_u16(int(v * 32768 / 100))

    def stop_tone(self):
        self.play_tone(50, 0)

    def human_sensor(self):
        if self.p18:
            val = self.p18.value()
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

    def rgb(self, r, g, b):
        return (g, r, b)

    def pixcel(self, n, r, g, b):
        self.out3[n] = self.rgb(int(r / 100 * 255), int(g / 100 * 255), int(b / 100 * 255))  # n番の NeoPixel を点灯
        self.out3.write()

    def pixcel_n(self, n, value):
        v = value.split(',')
        try:
            self.pixcel(n, int(v[0]), int(v[1]), int(v[2]))
        except:
            print("Pixcel Error")
            self.pixcel(n, 0, 0, 0)

    def init_pixcel(self):
        self.pixcel(0, 0, 0, 0)

    # ESP32 VSYS電源電圧を取得する
    def getVsys(self):
        Pin(29, Pin.IN)
        volt = ADC(3).read_u16() / 65535 * 3.3 * 3
        return volt

    def button_notification(self, button_name, event_name):
        buffer = bytearray(20)
        buffer[19] = MbitMoreDataFormat["ACTION_EVENT"]
        action = MbitMoreActionEvent["BUTTON"]
        button = MbitMoreButtonName[button_name]
        event = MbitMoreButtonEventName[event_name]
        timestamp = time.ticks_ms()
        packed_data = struct.pack('<BHBI', action, button, event, timestamp)
        buffer[0:8] = packed_data
        self.ble_conn.send_notification(buffer)

    # 定期的にハードウェアのセンサ値を送信する
    '''
    this.gpio = [
        0, 1, 2,
        8,
        12, 13, 14, 15, 16
    ];
    以下は + 24
    const MbitMoreButtonStateIndex = {
        P0: 0,
        P1: 1,
        P2: 2,
        A: 3,
        B: 4,
        LOGO: 5
    };
    '''
    def send_sensor_value(self):
        btna = 1 if self.inp0.value() == 0 else 0
        btnb = 1 if self.inp1.value() == 0 else 0
        gpio_data = (
            (btna << 3+24) |
            (btnb << 4+24) |
            (self.human_sensor() << 5+24)
        )
        light_level = self.lux()
        light_level = max(0, min(255, int(light_level/500*255)))
        temperature, humidity = self.temp_humi()
        temperature = max(0, min(255, int(temperature+128)))
        humidity = max(0, min(255, int(humidity/100*255)))
        buffer = struct.pack('<I3B', gpio_data, light_level, temperature, humidity)
        self.ble_conn.state_write(buffer)
