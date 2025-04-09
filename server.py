import machine
import network
import socket
import struct
import os
import time
from machine import Pin, PWM
from neopixel import NeoPixel
import uasyncio as asyncio
import framebuf
from hardware import Hardware

class IoTServer:
    def __init__(self):
        # アクセスポイントの設定
        self.PASSWORD = "12345678"
        self.hardware = Hardware()

        #self.speaker = PWM(Pin(21, Pin.OUT))
        #self.speaker.freq(440)
        #self.speaker.duty_u16(0)
        #self.np = NeoPixel(Pin(16, Pin.OUT), 2)
        # self.oled = None
        # self.default_ssid = ""
        # self.default_password = ""
        # self.default_main_module = ""
        self.running = True  # サーバーの実行状態を管理するフラグ

    def start_wifi(self):
        """Wi-FiをSTAモードで起動"""
        sta = network.WLAN(network.AP_IF)
        sta.active(True)
        SSID = "PcratchIoT-" + self.microbit_friendly_name(sta.config('mac'))
        print("SSID:", SSID)
        sta.config(essid=SSID, password=self.PASSWORD)
        print("Wi-Fi接続中...")
        while not sta.isconnected():
            time.sleep(1)
        print("Wi-Fi接続完了:", sta.ifconfig())

    def stop_server(self):
        """サーバーを停止"""
        self.running = False
        print("サーバーを停止します")

    
    def handle_get_bitmap(self, cl):
        """OLEDのビットマップをBMP形式でHTTPレスポンスとして送信"""
        # OLEDのビットマップデータを取得
        bitmap = self.hardware.get_oled_bitmap()
        print(len(bitmap))

        #with open("test.bmp", "rb") as bmp_file:
        #    bitmap = bmp_file.read()

        if bitmap:
            # HTTPレスポンスを作成
            response = b"HTTP/1.1 200 OK\r\n" \
                    b"Content-Type: image/bmp\r\n" \
                    b"Content-Disposition: inline; filename=\"oled_bitmap.bmp\"\r\n" \
                    b"\r\n"

            # クライアントにレスポンスを送信
            try:
                cl.send(response)
                cl.send(bitmap)
                print("ビットマップデータを送信しました")
            except Exception as e:
                print(f"ビットマップ送信中にエラーが発生しました: {e}")
        else:
            # エラー応答
            response = b"HTTP/1.1 500 Internal Server Error\r\n" \
                    b"Content-Type: text/plain\r\n\r\n" \
                    b"OLEDが初期化されていません"
            try:
                cl.send(response)
            except Exception as e:
                print(f"エラー応答送信中にエラーが発生しました: {e}")

    def microbit_friendly_name(self, unique_id):
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

    def parse_query_string(self, query):
        """クエリ文字列を解析"""
        params = {}
        pairs = query.split("&")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                params[key] = value
        return params

    def play_tone(self, frequency, duration):
        """指定した周波数と持続時間で音を再生"""
        self.hardware.play_tone(frequency)
        time.sleep(duration / 2)
        self.hardware.stop_tone()  # 音を止める
        time.sleep(0.01)

    def play_melody(self):
        """Happy Birthday to You を再生"""
        melody = [
            (264, 0.25), (264, 0.25), (297, 0.5), (264, 0.5), (352, 0.5), (330, 1),
            (264, 0.25), (264, 0.25), (297, 0.5), (264, 0.5), (396, 0.5), (352, 1),
            (264, 0.25), (264, 0.25), (440, 0.5), (352, 0.5), (330, 0.5), (297, 1),
            (466, 0.25), (466, 0.25), (440, 0.5), (352, 0.5), (396, 0.5), (352, 1)
        ]
        for note in melody:
            frequency, duration = note
            self.play_tone(frequency, duration)

    def np_reset(self):
        self.hardware.pixcel(0, 0, 0, 0)
        self.hardware.pixcel(1, 0, 0, 0)

    def color_wipe(self, color, delay=200):
        """NeoPixelを指定した色に変化させる"""
        for i in range(2):
            r, g, b = color
            self.hardware.pixcel(i, r / 255 * 100, g / 255 * 100, b / 255 * 100)
            time.sleep_ms(delay)

    def rainbow_cycle(self, delay=20):
        """虹色のアニメーションを作成"""
        for j in range(256):
            for i in range(2):
                pixel_index = (i * 256 // 2) + j
                r, g, b = self.wheel(pixel_index & 255)
                self.hardware.pixcel(i, r / 255 * 100, g / 255 * 100, b / 255 * 100)
            time.sleep_ms(delay)

    def wheel(self, pos):
        """0-255の値をRGBの色に変換"""
        if pos < 85:
            return (pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return (255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return (0, pos * 3, 255 - pos * 3)

    def npoff(self):
        """NeoPixelを消灯"""
        for i in range(2):
            self.hardware.pixcel(i, 0, 0, 0)

    def demo1(self):
        """デモ1: 赤、緑、青の順に点灯"""
        for i in range(3):
            self.color_wipe((255, 0, 0))
            self.color_wipe((0, 255, 0))
            self.color_wipe((0, 0, 255))
            time.sleep(0.5)
        self.npoff()

    def demo2(self):
        """デモ2: 虹色アニメーション"""
        self.rainbow_cycle()
        self.npoff()

    # デフォルトのHTMLレスポンス
    def get_default_response(self):
        def_response = """\
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <title>Wi-Fi設定</title>
    <style>
        body {{
            font-size: 20px; /* フォントサイズを大きく設定 */
        }}
        h1 {{
            font-size: 24px; /* 見出しのフォントサイズをさらに大きく設定 */
        }}
        label, select, input {{
            font-size: 18px; /* ラベルや入力欄のフォントサイズを調整 */
        }}
        button {{
            font-size: 18px; /* ボタンのフォントサイズを調整 */
            margin: 10px; /* ボタン間の余白を設定 */
        }}
    </style>
</head>
<body>
    <h1>処理を完了しました</h1>
    <p>SSIDを変更したら、デバイスを再起動してください。</p>
    <button onclick="location.href='/'">もどる</button>
</body>
</html>
"""
        return def_response

    def get_redirect_response(self):
        redirect_response = """\
HTTP/1.1 302 Found
Location: /
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <title>リダイレクト</title>
</head>
<body>
    <p>デモ1を実行しました。<a href="/">こちら</a>をクリックして戻ってください。</p>
</body>
</html>
"""
        return redirect_response

    def get_root_response(self, ssid_options, py_file_options, default_password):
        """ルートディレクトリのHTMLレスポンスを生成"""
        # HTMLページを送信
        response = f"""\
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <title>Wi-Fi設定</title>
    <style>
        body {{
            font-size: 20px; /* フォントサイズを大きく設定 */
        }}
        h1 {{
            font-size: 24px; /* 見出しのフォントサイズをさらに大きく設定 */
        }}
        label, select, input {{
            font-size: 18px; /* ラベルや入力欄のフォントサイズを調整 */
        }}
        button {{
            font-size: 36px; /* ボタンのフォントサイズを調整 */
            margin: 40px; /* ボタン間の余白を設定 */
        }}
    </style>
</head>
<body>
    <h1>Wi-Fi設定</h1>
    <form action="/" method="post">
        <label for="ssid">SSID:</label>
        <select id="ssid" name="ssid">
            {ssid_options}
        </select><br><br>
        <label for="password">パスワード:</label>
        <input type="password" id="password" name="password" value="{default_password}"><br><br>
        <label for="main_module">メインモジュール:</label>
        <select id="main_module" name="main_module">
            {py_file_options}
        </select><br><br>
        <input type="submit" value="決定">
    </form>
    <button onclick="location.href='/demo1'">デモ1</button>
    <button onclick="location.href='/demo2'">デモ2</button>
    <button onclick="location.href='/demo3'">メロディ</button>

    <img src="/oled_bitmap.bmp" alt="OLED Bitmap">

</body>
</html>
"""
        return response

    def get_config(self):
        # デフォルトのSSIDとパスワードを読み込む
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
        except FileNotFoundError:
            print("wifi_config.txt ファイルが見つかりません。デフォルト値を使用します。")
        return default_ssid, default_password, default_main_module

    def handle_request(self, cl, request):
        # GETリクエストでフォームを表示
        if "GET / " in request:
            print("GET リクエストを処理中")
            """Configを読み込む"""
            default_ssid, default_password, default_main_module = self.get_config()
            print("デフォルトSSID:", default_ssid)
            print("デフォルトパスワード:", default_password)
            print("デフォルトメインモジュール:", default_main_module)

            sta = network.WLAN(network.STA_IF)  # STAモードのインスタンスを作成
            if not sta.active():
                print("STAモードを有効化します...")
                sta.active(True)  # STAモードを有効化
            else:
                print("STAモードは既に有効です")

            # Wi-Fiネットワークをスキャン
            networks = sta.scan()
            ssid_options = ""
            for net in networks:
                ssid = net[0].decode("utf-8")
                selected = "selected" if ssid == default_ssid else ""
                ssid_options += f'<option value="{ssid}" {selected}>{ssid}</option>'

            # ルートディレクトリの *.py ファイルをリストアップ
            py_files = [f for f in os.listdir() if f.endswith(".py")]
            py_file_options = ""
            for py_file in py_files:
                selected = "selected" if py_file == default_main_module else ""
                py_file_options += f'<option value="{py_file}" {selected}>{py_file}</option>'
            response = self.get_root_response(ssid_options, py_file_options, default_password)

            print("GET リクエスト処理終了")
            cl.send(response)

        # POSTリクエストでSSIDとパスワードを保存
        elif "POST / " in request:
            print("POST リクエストを処理中")
            # リクエストボディを取得
            headers, body = request.split("\r\n\r\n", 1)
            print("リクエストボディ:", body)

            # クエリ文字列を解析
            params = self.parse_query_string(body)
            ssid = params.get("ssid", "")
            password = params.get("password", "")
            main_module = params.get("main_module", "")
            print("Wi-Fi設定を保存します:", ssid, password)
            print("選択されたメインモジュール:", main_module)

            # SSIDとパスワードをファイルに保存
            with open("wifi_config.txt", "w") as f:
                f.write(f"SSID={ssid}\n")
                f.write(f"PASSWORD={password}\n")
                f.write(f"MAIN_MODULE={main_module}\n")
            print("設定を保存しました")

            # 保存完了メッセージを送信
            print("POST リクエスト処理終了")
            machine.reset()  # デバイスを再起動
            cl.send(self.get_redirect_response())

        elif "GET /reboot" in request:
            cl.send(self.get_redirect_response())
            print("デバイスを再起動します...")
            machine.reset()  # デバイスを再起動
        elif "GET /demo1" in request:
            print("demo1...")
            self.demo1()
            cl.send(self.get_redirect_response())
        elif "GET /demo2" in request:
            print("demo2...")
            self.demo2()
            cl.send(self.get_redirect_response())
        elif "GET /demo3" in request:
            print("demo3...")
            self.play_melody()
            cl.send(self.get_redirect_response())

        elif "GET /oled_bitmap.bmp" in request:
            print("OLEDビットマップを送信します")
            self.handle_get_bitmap(cl)
        else:
            # その他のリクエストには404エラーを返す
            print("404 Not Found")
            cl.send(self.get_default_response())


    def start_http_server(self):
        """HTTPサーバーを起動"""
        print("HTTPサーバーを起動...")
        addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(1)
        print("HTTPサーバーが起動しました")

        while self.running:
            try:
                cl, addr = s.accept()
                print("クライアント接続:", addr)
                try:
                    request = cl.recv(1024).decode("utf-8")
                    print("リクエスト:", request)
                    self.handle_request(cl, request)  # リクエストを処理
                except Exception as e:
                    print("リクエスト処理中にエラー:", e)
                finally:
                    cl.close()  # ソケットを確実に閉じる
            except Exception as e:
                print("エラー:", e)
