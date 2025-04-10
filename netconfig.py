from server import IoTServer
from hardware import Hardware

if __name__ == "__main__":
    hardware= Hardware()
    hardware.start_wifi()  # Wi-Fiを起動
    hardware.show_text(hardware.ssid)  # 接続完了メッセージを表示
    hardware.connect_wifi()  # Wi-Fi接続
    server = IoTServer()
    server.start_http_server()  # HTTPサーバーを起動（関数から戻らない）
