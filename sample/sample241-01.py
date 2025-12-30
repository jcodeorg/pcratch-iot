# スマート扇風機
from machine import Pin, ADC, PWM, I2C
import time
from ahtx0 import AHT20

# 風量の状態
MODES = ["切", "弱", "強", "自動"]
current_mode = 0  # 初期状態（切）

# P01をPWM出力で初期化
P01 = PWM(Pin(1, Pin.OUT), freq=50, duty=0)

# I2Cの初期化
i2c = I2C(0, scl=Pin(23), sda=Pin(22))

# 温湿度計の初期化
aht20 = AHT20(i2c)

# 風量を設定する関数
def set_fan_speed(mode):
    if mode == "弱":
        P01.duty(500)   # 低速
    elif mode == "強":
        P01.duty(900)   # 高速
    else:
        P01.duty(0)     # モータ停止

# 割り込み禁止用のフラグとタイマー
last_irq_time = 0
DEBOUNCE_MS = 500  # 500ミリ秒は割り込みを無視

# 風量を変更する関数（割り込みハンドラ）
def change_fan_speed(pin):
    global current_mode, last_irq_time
    now = time.ticks_ms()
    # 前回の割り込みから一定時間経過していなければ無視
    if time.ticks_diff(now, last_irq_time) < DEBOUNCE_MS:
        return
    last_irq_time = now

    current_mode = (current_mode + 1) % len(MODES)
    print(f"風量モード: {MODES[current_mode]}")
    set_fan_speed(MODES[current_mode])

# P17スイッチに割り込みハンドラを設定
P17 = Pin(17, Pin.IN, Pin.PULL_DOWN)
P17.irq(trigger=Pin.IRQ_RISING, handler=change_fan_speed)

# メインループ（ずっとくりかえす）
while True:
    if MODES[current_mode] == "自動":
        temperature = aht20.temperature
        humidity = aht20.relative_humidity
        print(f"温度: {temperature:.1f}C, 湿度: {humidity:.1f}%")

        # 温度に応じて風量を自動調整
        if temperature > 30:
            set_fan_speed("強")
        elif temperature > 25:
            set_fan_speed("弱")
        else:
            set_fan_speed("切")
    time.sleep(1)
