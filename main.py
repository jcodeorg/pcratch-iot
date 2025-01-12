# ESP32C6 BLE pcratch-IoT(micro:bit) v1.1.3
import network
import asyncio
from machine import Pin, I2C, ADC, PWM
from ssd1306 import SSD1306_I2C
from neopixel import NeoPixel
from ahtx0 import AHT20

from device import Device
from time_weather import TimeWeather
SSID = 'AirMacPelWi-Fi222'
PASSWORD = '78787878'


# グラフを描く
def draw_graph(oled, x, y, width, height, data, min_value, max_value):
    oled.fill_rect(x, y, width, height, 0)  # グラフエリアをクリア
    if len(data) < 2:
        return
    for i in range(len(data)):
        x0 = x + i
        y0 = y + height - int((data[i] - min_value) / (max_value - min_value) * height)
        if x0 < x + width:  # 画面の幅を超えないようにする
            oled.pixel(x0, y0, 1)

# センサーの値を表示する
connected_displayed = False
def disp_sensor_value(self):
    global connected_displayed
    if self.ble_conn.connection:
        if not connected_displayed:
            self.show_text("Conected!!")
            connected_displayed = True
    else:
        self.show_text(self.ble_conn.NAME[-16:])
        connected_displayed = False
    disp_graph(self)

temp_data = []
humi_data = []

# 温度と湿度をグラフ表示
def disp_graph(self):
    global temp_data, humi_data
    max_data_points = 60  # グラフに表示するデータポイントの数

    # 温度と湿度を取得
    temperature, humidity = self.temp_humi()

    # データをリストに追加
    temp_data.append(temperature)
    humi_data.append(humidity)

    # リストの長さを制限
    if len(temp_data) > max_data_points:
        temp_data.pop(0)
    if len(humi_data) > max_data_points:
        humi_data.pop(0)

    # OLEDディスプレイに表示
    if self.oled:
        self.oled.fill_rect(0, 10, self.oled.width, self.oled.height - 10, 0)
    self.oled.text("Temp: {:.1f}C".format(temperature), 0, 10)
    self.oled.text("Humi: {:.1f}%".format(humidity), 0, 20)
    draw_graph(self.oled, 0, 30, 128, 20, temp_data, 15, 25)  # 温度グラフ
    draw_graph(self.oled, 0, 45, 128, 20, humi_data, 20, 60)  # 湿度グラフ
    self.oled.show()

# 温度と湿度、明るさ、人感センサを表示
def disp_sensors(self):
    temperature, humidity = self.temp_humi()
    temp = "temp:{:6.1f}".format(temperature)
    humi = "hum :{:6.1f}".format(humidity)
    lx = "lx:  {:6.0f}".format(self.lux())
    hs_value = self.human_sensor()
    hs = "Human:{:05d}".format(hs_value)
    sound = self.adc1.read_u16()
    sd = "A1   :{:05d}".format(sound)
    if self.oled:
        self.oled.fill_rect(0, 10, self.oled.width, self.oled.height - 10, 0)
        self.oled.text(temp, 0, 8*2)
        self.oled.text(humi, 0, 8*3)
        self.oled.text(lx, 0, 8*4)
        self.oled.text(hs, 0, 8*5)
        self.oled.text(sd, 0, 8*6)
        self.oled.show()

demonum = 0
brightness = 255
def demo_neopixcel(device):
    global demonum, brightness
    demonum += 1
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255)]
    color = colors[demonum % len(colors)]
    # 明るさを調整
    adjusted_color = (color[0] * brightness // 255, color[1] * brightness // 255, color[2] * brightness // 255)
    device.pixcel(0, adjusted_color[0], adjusted_color[1], adjusted_color[2])
    device.pixcel(1, adjusted_color[0], adjusted_color[1], adjusted_color[2])
    device.pixcel(2, adjusted_color[0], adjusted_color[1], adjusted_color[2])
    brightness = max(0, brightness - 10)  # 25ずつ減少させる（0未満にはならないようにする）

# センサーの値を定期的に送信
async def sensor_task(device):
    neopixcel = False
    while True:
        if device.ble_conn.connection:
            if neopixcel:
                device.pixcel(0, 0,0,0)
                device.pixcel(1, 0,0,0)
                device.pixcel(2, 0,0,0)
                neopixcel = False
            device.send_sensor_value()
        else:
            demo_neopixcel(device)
            neopixcel = True
        await asyncio.sleep_ms(250)

async def main():
    device = Device()
    t1 = asyncio.create_task(device.ble_conn.ble_task(device.do_command))
    disp_sensor_value(device)
    t3 = asyncio.create_task(sensor_task(device))
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            disp_sensor_value(device)
            await asyncio.sleep(1)
        print('WiFi connected:', wlan.ifconfig())

        clock = TimeWeather(device.oled, device.aht20)
        await clock.get_ntptime()
        await clock.fetch_weather("東京")
        await asyncio.sleep(1)
        clock.print_memory_usage()

        while True:
            for _ in range(10):
                clock.display_time()
                await asyncio.sleep(1)
            clock.display_weather()
            clock.print_memory_usage()
            await asyncio.sleep(10)
            for _ in range(10):
                disp_sensor_value(device)
                await asyncio.sleep(1)
    except OSError as e:
        print(f"Failed to connect to WiFi: {e}")

    while True:
        disp_sensor_value(device)
        await asyncio.sleep(1)
    
asyncio.run(main())
