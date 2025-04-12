# ESP32C6 pcratch-IoT v1.4.1
import socket
import os
import time
import machine
from hardware import Hardware

class IoTServer:
    def __init__(self):
        # アクセスポイントの設定
        self.hardware = Hardware()
        self.running = True  # サーバーの実行状態を管理するフラグ
        self.wifi_confifg = ()
        self.networks = []  # Wi-Fiネットワークのリストを初期化

    def stop_server(self):
        """サーバーを停止"""
        self.running = False
        print("サーバーを停止します")

    def parse_query_string(self, query):
        """クエリ文字列を解析"""
        params = {}
        pairs = query.split("&")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                params[key] = value
        return params

    def user_led_demo(self):
        for i in range(2):
            for i in range(4):
                self.hardware.PIN15.value(1)
                time.sleep(0.5)
                self.hardware.PIN15.value(0)
                time.sleep(0.5)
            for i in range(4):
                self.hardware.PIN15.value(1)
                time.sleep(0.1)
                self.hardware.PIN15.value(0)
                time.sleep(0.1)

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

    def npoff(self):
        """NeoPixelを消灯"""
        for i in range(2):
            self.hardware.pixcel(i, 0, 0, 0)

    def color_wipe(self, color, delay=200):
        """NeoPixelを指定した色に変化させる"""
        for i in range(2):
            r, g, b = color
            self.hardware.pixcel(i, r / 255 * 100, g / 255 * 100, b / 255 * 100)
            time.sleep_ms(delay)

    def np_led_demo(self):
        """デモ1: 赤、緑、青の順に点灯"""
        for i in range(3):
            self.color_wipe((255, 0, 0))
            self.color_wipe((0, 255, 0))
            self.color_wipe((0, 0, 255))
            time.sleep(0.5)
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
            font-size: 36px; /* フォントサイズを大きく設定 */
        }}
        select {{
            font-size: 36px;  /* <select> のフォントサイズ */
        }}
        h1 {{
            font-size: 48px; /* 見出しのフォントサイズをさらに大きく設定 */
        }}
        label, select, input {{
            font-size: 18px; /* ラベルや入力欄のフォントサイズを調整 */
        }}
        input, button {{
            font-size: 36px; /* ボタンのフォントサイズを調整 */
            margin: 20px 40px; /* ボタン間の余白を設定 */
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
        <input type="submit" value="設定変更">
        <button type="button" onclick="location.href='/scan'">WiFiスキャン</button>
    </form>
    <button onclick="location.href='/demo1'">Lチカ</button>
    <button onclick="location.href='/demo2'">カラーLEDデモ</button>
    <button onclick="location.href='/demo3'">音楽デモ</button>
    <p><img src="/oled_bitmap.bmp" alt="OLED Bitmap" style="width: 100%; height: auto; border: 5px solid black;"></p>
</body>
</html>
"""
        return response

    def get_wifi_config(self):
            """Configを読み込む"""
            self.wifi_confifg = (self.hardware.get_wifi_config())
            default_ssid, default_password, default_main_module = self.wifi_confifg
            print("デフォルトSSID:", default_ssid)
            print("デフォルトパスワード:", default_password)
            print("デフォルトメインモジュール:", default_main_module)
            # ルートディレクトリの *.py ファイルをリストアップ
            self.py_files = [f for f in os.listdir() if f.endswith(".py")]
            # default_ssid を既存のネットワークリストに追加
            self.networks.append((default_ssid.encode('utf-8'), None, None, None, None, None))

    def scan_wifi_networks(self):
            # Wi-Fiネットワークをスキャン
            sta = self.hardware.get_wifi_sta()
            sta.active(False)
            time.sleep(1)
            sta.active(True)
            self.networks = sta.scan()
            # default_ssid を既存のネットワークリストに追加
            default_ssid, _, _ = self.wifi_confifg
            self.networks.append((default_ssid.encode('utf-8'), None, None, None, None, None))
            print("スキャンしたWi-Fiネットワーク:", self.networks)

    def handle_request(self, cl, request):
        # GETリクエストでフォームを表示
        if "GET / " in request:
            print("GET リクエスト処理...")
            default_ssid, default_password, default_main_module = self.wifi_confifg
            # Wi-Fiネットワークをスキャン
            ssid_options = ""
            for net in self.networks:
                ssid = net[0].decode("utf-8")
                selected = "selected" if ssid == default_ssid else ""
                ssid_options += f'<option value="{ssid}" {selected}>{ssid}</option>'

            py_file_options = ""
            for py_file in self.py_files:
                selected = "selected" if py_file == default_main_module else ""
                py_file_options += f'<option value="{py_file}" {selected}>{py_file}</option>'
            response = self.get_root_response(ssid_options, py_file_options, default_password)

            print("GET レスポンス送信...")
            cl.send(response)
            print("GET レスポンス送信終了")

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
            print("デバイスを再起動します...")
            machine.reset()  # デバイスを再起動

        elif "GET /scan" in request:
            print("Wi-Fiスキャンを開始します...")
            # self.get_wifi_config
            self.scan_wifi_networks()
            cl.send(self.get_redirect_response())

        elif "GET /demo1" in request:
            print("ESP32C6 LEDのデモ...")
            self.user_led_demo()
            cl.send(self.get_redirect_response())
        elif "GET /demo2" in request:
            print("NP_LED のデモ...")
            self.np_led_demo()
            cl.send(self.get_redirect_response())
        elif "GET /demo3" in request:
            print("demo3...")
            self.play_melody()
            cl.send(self.get_redirect_response())

        elif "GET /oled_bitmap.bmp" in request:
            # print("OLEDビットマップを送信します")
            self.hardware.send_oled_bitmap_24(cl)

        else:
            # その他のリクエストには404エラーを返す
            print("404 Not Found")
            cl.send(self.get_default_response())


    def start_http_server(self):
        """HTTPサーバーを起動"""
        print("アクセスポイントを起動...")
        ap = self.hardware.wifi_ap_conect()  # Wi-Fi接続
        while not ap.isconnected():
            time.sleep(1)
        print("アクセスポイント接続完了:", ap.ifconfig())

        print("HTTPサーバーを起動...")
        addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(1)
        print("HTTPサーバーが起動しました")

        self.get_wifi_config()  # CONFIG情報を取得

        while self.running:
            try:
                cl, addr = s.accept()
                print("クライアント接続:", addr)
                try:
                    request = cl.recv(1024).decode("utf-8")
                    # print("リクエスト:", request)
                    self.handle_request(cl, request)  # リクエストを処理
                except Exception as e:
                    print("リクエスト処理中にエラー:", e)
                finally:
                    cl.close()  # ソケットを確実に閉じる
            except Exception as e:
                print("エラー:", e)
