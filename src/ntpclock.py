# ESP32C6 pcratch-IoT v1.4.0
# ネットワーク対応時計
import ntptime
import time
import framebuf
import asyncio

days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

class Clock:
    def __init__(self, oled):
        self.oled = oled

    async def get_ntptime(self):
        async def set_time():
            ntptime.settime()

        while True:
            try:
                # asyncio.wait_forを使用して5秒でタイムアウト
                await asyncio.wait_for(set_time(), timeout=5)
                print("時刻同期に成功しました")
                break
            except asyncio.TimeoutError:
                print("時刻同期がタイムアウトしました")
            except Exception as e:
                print(f"時刻同期に失敗しました: {e}")
            await asyncio.sleep(1)

    def display_time(self, temperature = 0, humidity = 0):
        current_time = time.localtime(time.time() + 9 * 3600)  # 9時間（9 * 3600秒）を加算
        formatted_date = "{:04}-{:02}-{:02} {}".format(current_time[0], current_time[1], current_time[2], days_of_week[current_time[6]])
        formatted_time = "{:02}:{:02}:{:02}".format(current_time[3], current_time[4], current_time[5])
        formatted_temp = "{:5.1f}C {:5.1f}%".format(temperature, humidity)

        # 上10ドットをそのままにして、下の部分だけ書き直す
        if self.oled:
            self.oled.fill_rect(0, 0, self.oled.width, self.oled.height - 0, 0)
            self.oled.text(formatted_date, 0, 0)
            self.draw_text_double_size(formatted_time, 0, 30)
            self.oled.line(0, 50, 127, 50, 1)
            self.oled.text(formatted_temp, 0, 54)
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
