from server import IoTServer
from hardware import Hardware

if __name__ == "__main__":
    hardware= Hardware()
    ssid = hardware.get_wifi_ap_ssid()  # Wi-Fiを起動準備してssidを取得
    hardware.show_text(ssid)  # 接続完了メッセージを表示
    hardware.wait_wifi_ap_conected()  # Wi-Fi接続
    server = IoTServer()
    server.start_http_server()  # HTTPサーバーを起動（関数から戻らない）
