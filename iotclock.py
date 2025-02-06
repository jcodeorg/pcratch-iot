# ESP32C6 pcratch-IoT(micro:bit) v1.2.0
# ネットワーク対応時計

import ntptime
import time
import framebuf
import asyncio

days_of_week = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

class Clock:
    def __init__(self, oled):
        self.oled = oled

    async def get_ntptime(self):
        while True:
            try:
                ntptime.settime()
                break
            except:
                await asyncio.sleep(1)

    def display_time(self):
        current_time = time.localtime(time.time() + 9 * 3600)  # 9時間（9 * 3600秒）を加算
        formatted_date = "{:04}-{:02}-{:02}({})".format(current_time[0], current_time[1], current_time[2], days_of_week[current_time[6]])
        formatted_time = "{:02}:{:02}:{:02}".format(current_time[3], current_time[4], current_time[5])

        # 上10ドットをそのままにして、下の部分だけ書き直す
        if self.oled:
            self.oled.fill_rect(0, 10, self.oled.width, self.oled.height - 10, 0)
            self.oled.text(formatted_date, 0, 10)
            self.draw_text_double_size(formatted_time, 0, 30)
            self.oled.show()

    def draw_text_double_size(self, text, x, y):
        temp_buf = bytearray(8 * 8 // 8)  # 8x8のビットマップ用バッファ
        temp_fb = framebuf.FrameBuffer(temp_buf, 8, 8, framebuf.MONO_HLSB)
        
        for i, c in enumerate(text):
            temp_fb.fill(0)
            temp_fb.text(c, 0, 0)
            
            for dx in range(8):
                for dy in range(8):
                    if temp_fb.pixel(dx, dy):
                        self.oled.pixel(x + i * 16 + dx * 2, y + dy * 2, 1)
                        self.oled.pixel(x + i * 16 + dx * 2 + 1, y + dy * 2, 1)
                        self.oled.pixel(x + i * 16 + dx * 2, y + dy * 2 + 1, 1)
                        self.oled.pixel(x + i * 16 + dx * 2 + 1, y + dy * 2 + 1, 1)
