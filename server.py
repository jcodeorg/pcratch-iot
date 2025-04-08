import machine
import network
import socket
import struct
import os
import time
from machine import Pin, PWM
from neopixel import NeoPixel
import uasyncio as asyncio

class IoTServer:
    def __init__(self):
        # アクセスポイントの設定
        self.PASSWORD = "12345678"
        self.speaker = PWM(Pin(21, Pin.OUT))
        self.speaker.freq(440)
        self.speaker.duty_u16(0)
        self.np = NeoPixel(Pin(16, Pin.OUT), 2)
        self.default_ssid = ""
        self.default_password = ""
        self.default_main_module = ""

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
        self.speaker.freq(frequency)
        self.speaker.duty_u16(32768)
        time.sleep(duration / 2)
        self.speaker.duty_u16(0)
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
        """NeoPixelをリセット"""
        self.np[0] = (0, 0, 0)
        self.np[1] = (0, 0, 0)
        self.np.write()

    def color_wipe(self, color, delay=200):
        """NeoPixelを指定した色に変化させる"""
        for i in range(len(self.np)):
            self.np[i] = color
            self.np.write()
            time.sleep_ms(delay)

    def rainbow_cycle(self, delay=20):
        """虹色のアニメーションを作成"""
        for j in range(256):
            for i in range(len(self.np)):
                pixel_index = (i * 256 // len(self.np)) + j
                self.np[i] = self.wheel(pixel_index & 255)
            self.np.write()
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

    def demo1(self):
        """デモ1: 赤、緑、青の順に点灯"""
        for i in range(3):
            self.color_wipe((255, 0, 0))
            self.color_wipe((0, 255, 0))
            self.color_wipe((0, 0, 255))
            self.np_reset()
            time.sleep(0.5)

    def demo2(self):
        """デモ2: 虹色アニメーション"""
        self.rainbow_cycle()
        self.np_reset()

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

    def start_server(self):
        print("start_server...")
        """Configを読み込む"""
        default_ssid, default_password, default_main_module = self.get_config()
        print("デフォルトSSID:", default_ssid)
        print("デフォルトパスワード:", default_password)
        print("デフォルトメインモジュール:", default_main_module)
        """HTTPサーバーを起動"""
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        SSID = "PcratchIoT-" + self.microbit_friendly_name(sta.config('mac'))
        print("SSID:", SSID)

        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=SSID, password=self.PASSWORD)

        print("アクセスポイントを起動しました")
        print("SSID:", SSID)
        print("IPアドレス:", ap.ifconfig()[0])

        addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
        s = socket.socket()
        # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(1)
        # s.setblocking(False)  # 非同期処理のためにノンブロッキングモードに設定
        print("HTTPサーバーが起動しました")
        while True:
            cl, addr = s.accept()
            print("クライアント接続:", addr)
            try:
                request = cl.recv(1024).decode("utf-8")
                print("リクエスト:", request)

                # GETリクエストでフォームを表示
                if "GET / " in request:
                    print("GET リクエストを処理中")
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

                    cl.send(response)
                    print("GET リクエスト処理終了")

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
                    cl.send(self.get_redirect_response())
                    print("POST リクエスト処理終了")
                    machine.reset()  # デバイスを再起動
                elif "GET /reboot" in request:
                    cl.send(self.get_redirect_response())
                    print("デバイスを再起動します...")
                    machine.reset()  # デバイスを再起動
                elif "GET /demo1" in request:
                    print("demo1...")
                    cl.send(self.get_redirect_response())
                    self.demo1()
                elif "GET /demo2" in request:
                    print("demo2...")
                    cl.send(self.get_redirect_response())
                    self.demo2()
                elif "GET /demo3" in request:
                    print("demo3...")
                    cl.send(self.get_redirect_response())
                    self.play_melody()
                else:
                    # その他のリクエストには404エラーを返す
                    print("404 Not Found")
                    cl.send(self.get_default_response())
            except Exception as e:
                print("エラー:", e)
            finally:
                cl.close()  # クライアント接続を閉じる
