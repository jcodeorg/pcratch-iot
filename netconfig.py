import _thread
import time
from server import IoTServer

# サーバーをバックグラウンドスレッドで実行
def server_thread():
    server = IoTServer()
    server.start_wifi()  # Wi-Fiを起動
    server.start_http_server()  # HTTPサーバーを起動

# メインスレッドで他の処理を実行
if __name__ == "__main__":
    # サーバーを別スレッドで起動
    _thread.start_new_thread(server_thread, ())

    # メインスレッドでの処理
    try:
        while True:
            print("メインスレッドで動作中...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("メインスレッドを終了します")
