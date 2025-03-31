import machine
import network
import socket
import struct
import os

# アクセスポイントの設定
PASSWORD = "12345678"  # アクセスポイントのパスワード

# マイクロビットのユニークIDからフレンドリー名を生成
def microbit_friendly_name(unique_id):
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

    # Derive our name from the nrf51822's unique ID
    # _, n = struct.unpack("II", machine.unique_id())
    mac_padded = b'\x00\x00' + unique_id # 6バイトのMACアドレスを8バイトにパディング
    _, n = struct.unpack('>II', mac_padded)
    ld = 1;
    d = letters;

    for i in range(0, length):
        h = (n % d) // ld;
        n -= h;
        d *= letters;
        ld *= letters;
        name.insert(0, codebook[i][h]);

    return "".join(name);

# クエリ文字列を解析する関数
def parse_query_string(query):
    params = {}
    pairs = query.split("&")
    for pair in pairs:
        if "=" in pair:
            key, value = pair.split("=", 1)
            params[key] = value
    return params

# 簡単なHTTPサーバーを起動
def start_server():
    # ステーションモードでWi-Fiをスキャン
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    # print(sta.config('mac'))  # MACアドレスを表示
    SSID = "PIOT-"+microbit_friendly_name(sta.config('mac'))
    print("SSID:", SSID)
    # アクセスポイントモードでWi-Fiを起動
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=SSID, password=PASSWORD)

    print("アクセスポイントを起動しました")
    print("SSID:", SSID)
    print("IPアドレス:", ap.ifconfig()[0])

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
    print("デフォルトSSID:", default_ssid)
    print("デフォルトパスワード:", default_password)
    print("デフォルトメインモジュール:", default_main_module)

    # HTTPサーバーを起動
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)
    print("HTTPサーバーが起動しました")

    while True:
        print("クライアント接続待機中...")
        cl, addr = s.accept()  # クライアント接続を受け付ける
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
            font-size: 18px; /* ボタンのフォントサイズを調整 */
            margin: 10px; /* ボタン間の余白を設定 */
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
    <button onclick="location.href='/reboot'">リブート</button>
</body>
</html>
"""
                cl.send(response)
                print("GET リクエスト処理終了")

            # POSTリクエストでSSIDとパスワードを保存
            elif "POST / " in request:
                print("POST リクエストを処理中")
                # リクエストボディを取得
                headers, body = request.split("\r\n\r\n", 1)
                print("リクエストボディ:", body)

                # クエリ文字列を解析
                params = parse_query_string(body)
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
                response = """\
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
    <h1>Wi-Fi設定が保存されました</h1>
    <p>デバイスを再起動してください。</p>
    <button onclick="location.href='/'">もどる</button>
</body>
</html>
"""
                cl.send(response)
                print("POST リクエスト処理終了")
            elif "GET /reboot" in request:
                    print("デバイスを再起動します...")
                    machine.reset()  # デバイスを再起動
            else:
                # その他のリクエストには404エラーを返す
                print("404 Not Found")

        except Exception as e:
            print("エラー:", e)

        finally:
            cl.close()  # クライアント接続を閉じる

# サーバーを開始
start_server()
