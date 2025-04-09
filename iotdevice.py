# ESP32C6 pcratch-IoT(micro:bit) v1.2.5
import os
import struct
import time
from machine import Pin, I2C, ADC, PWM
from hardware import Hardware

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
MbitMorePinEvent = {
    "RISE": 2,
    "FALL": 3,
    "PULSE_HIGH": 4,
    "PULSE_LOW": 5
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
        self.hardware = Hardware()
        self.button_state = {
            'A': {'pressed': False, 'press_time': 0, 'down_count': 0},
            'B': {'pressed': False, 'press_time': 0, 'down_count': 0}
        }
        self.pin_event_time = {}

    # ボタンの状態を取得
    def get_button_state(self, button_name):
        return self.button_state[button_name]
    
    '''
    def handle_button_event(self, pin, button_name):
        if pin.value() == 1:  # ボタンが押された
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
        self.PIN17.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: self.handle_button_event(pin, 'B'))
        self.PIN18.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: self.handle_button_event(pin, 'A'))
    '''
    def handle_button_event(self, pin, pinIndex):
        # time.sleep_ms(80)  # 80msの遅延を追加してチャタリングを軽減
        current_event = "RISE" if pin.value() == 1 else "FALL"
        if pinIndex not in self.pin_event_time:
            self.pin_event_time[pinIndex] = ''

        if current_event == self.pin_event_time[pinIndex]:
            return  # 同じイベントが発生した場合は無視
        self.pin_event_time[pinIndex] = current_event
        self.pin_notification(pinIndex, current_event)

    def register_button_irq(self):
        self.PIN17.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: self.handle_button_event(pin, 17))
        self.PIN18.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=lambda pin: self.handle_button_event(pin, 18))

    async def do_command(self, data):
        # バイナリデータをリストに変換
        data_list = list(data)
        # print(data_list)  # 出力: [1, 72, 101, 108, 108, 111]
        command_id = data_list[0]
        # print("Command ID:", command_id)
        if command_id == 65:
            # 文字 s を t ミリ秒間隔で流す
            self.hardware.show_text(data[2:].decode('utf-8'), data[1])
        elif command_id == 33:
            # ピン pin を デジタル出力 n にする
            pin = data[1]
            val = data[2]
            self.hardware.digital_out(pin, val)
        elif command_id == 34:
            # ピン pin を PWM 出力 n %にする
            pin = data[1]
            uint16_value = struct.unpack('<H', data[2:4])[0]     # 続く2バイトを数値に変換
            # print("ピン", pin, "を PWM 出力", uint16_value, "%にする")
            self.hardware.analog_out(pin, uint16_value)
        elif command_id == 96:
            # 音を消す
            self.hardware.stop_tone()
        elif command_id == 97:
            # 1000000/data[1:5] Hzの音を data[5]/255*100 %の大きさで鳴らす
            # vol は 0 か、それ以外で音量を調節できない
            four_bytes = data[1:5]  # data[2:] から4バイトを取得
            uint32_value = struct.unpack('<I', four_bytes)[0]   # 4バイトを uint32 の数値に変換
            self.hardware.play_tone(1000000 / uint32_value, data[5]/255*100)
        elif command_id == 130:
            label = data[1:9].decode('utf-8')
            value = data[9:].decode('utf-8')
            print("label:", label, value)
        elif command_id == 66:
            # アイコン表示（上5x3）
            self.hardware.draw_icon(data[1:], 0, 0)
        elif command_id == 67:
            # アイコン表示（下5x2）
            self.hardware.draw_icon(data[1:], 0, 3)   # 下の部分だけ書き直す
        elif command_id == 161:  # SetNeoPixcelColor(n, r, g, b)
            n = data[1]
            r = data[2]
            g = data[3]
            b = data[4]
            self.hardware.pixcel(n, r, g, b)
        else:
            print("Command ID", command_id, "is not defined.")
        return True

    # ボタンのイベントをBLEで通知する
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

    # ピンのイベントをBLEで通知する
    # pinIndex = dataView.getUint8(0);
    # event = dataView.getUint8(1);
    # value: dataView.getUint32(2, true)
    def pin_notification(self, pinIndex, event_name):
        print(f"ピン {pinIndex} に {event_name} イベント")
        buffer = bytearray(20)
        buffer[19] = MbitMoreDataFormat["PIN_EVENT"]
        event = MbitMorePinEvent[event_name]
        timestamp = time.ticks_ms()
        packed_data = struct.pack('<BBI', pinIndex, event, timestamp)
        buffer[0:6] = packed_data
        self.ble_conn.send_notification(buffer)

    # 定期的にハードウェアのセンサ値を送信する
    '''
    // this.gpio = [0, 1, 2, 8, 12, 13, 14, 15, 16];
    this.gpio = [0, 1, 2, 16, 17, 18, 19, 20, 21];
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
        p17 = 0 if self.hardware.PIN17.value() == 0 else 1
        p18 = 0 if self.hardware.PIN18.value() == 0 else 1
        btnb = p17
        btna = p18
        gpio_data = (
            (p17 << 17) |
            (p18 << 18) |
            (btna << 3+24) |
            (btnb << 4+24) |
            (self.hardware.human_sensor() << 5+24)
        )
        light_level = self.hardware.lux()
        light_level = max(0, min(255, int(light_level/500*255)))
        temperature, humidity = self.hardware.temp_humi()
        temperature = max(0, min(255, int(temperature+128)))
        humidity = max(0, min(255, int(humidity/100*255)))
        buffer = struct.pack('<I3B', gpio_data, light_level, temperature, humidity)
        self.ble_conn.state_write(buffer)
