# センサー読み取りテスト
# A1: 土壌水分センサ（Capacitive Soil Moisture Sensor v2.0）
# A2: CdS 照度センサ（明るいと値が小さく、暗いと値が大きくなる）

# machine モジュールから必要なクラスをインポートする
# Pin  : GPIO ピンの制御
# ADC  : アナログ→デジタル変換（センサーの電圧を数値として読む）
from machine import Pin, ADC
import time  # time.sleep() で待機するために使う


# ---- CdS 照度センサ（A2 ピン）の設定 ----
adc2 = ADC(Pin(2, Pin.IN))     # GPIO2 を入力ピンとして ADC に割り当てる
adc2.atten(ADC.ATTN_11DB)      # 減衰率を 11dB に設定 → 0〜3.3V の範囲を読める
adc2.width(ADC.WIDTH_12BIT)    # 分解能を 12 ビットに設定 → 値の範囲は 0〜4095

# ---- 土壌水分センサ（A1 ピン）の設定 ----
adc1 = ADC(Pin(1, Pin.IN))     # GPIO1 を入力ピンとして ADC に割り当てる
adc1.atten(ADC.ATTN_11DB)      # 減衰率を 11dB に設定 → 0〜3.3V の範囲を読める
adc1.width(ADC.WIDTH_12BIT)    # 分解能を 12 ビットに設定 → 値の範囲は 0〜4095

# ---- メインループ ----
# while True: で無限に繰り返す
while True:
    # adc2.read() で CdS センサーの ADC 値（0〜4095）を読み取って表示する
    # 明るいほど値が小さく、暗いほど値が大きくなる
    print("CdS value          : {:>4d}".format(adc2.read()))

    # adc1.read() で土壌水分センサーの ADC 値（0〜4095）を読み取って表示する
    # 土が乾いているほど値が大きく、濡れているほど値が小さくなる
    print("Soil moisture value: {:>4d}".format(adc1.read()))

    print()          # 見やすくするために空行を出力
    time.sleep(1)    # 1 秒待ってから次の読み取りへ
