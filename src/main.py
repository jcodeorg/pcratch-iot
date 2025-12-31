# ESP32C6 pcratch-IoT v1.4.0
import time
from hardware import Hardware

# The boot.py is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

def main():
    hardware = Hardware()
    default_ssid, default_password, default_main_module, hw_version =  hardware.get_wifi_config()
    print("デフォルトSSID:", default_ssid)
    print("デフォルトパスワード:", default_password)
    print("デフォルトメインモジュール:", default_main_module)
    print("ハードウェアバージョン:", hw_version)

    if hardware.PIN17.value() == 1:
        print("ボタンが押されています。netconfig.py を起動します。")
        for i in range(10):
            hardware.PIN15.on()                 # set pin to "on" (high) level
            time.sleep(0.2)
            hardware.PIN15.off()                # set pin to "off" (low) level
            time.sleep(0.2)
        import netconfig as main
    else:
        if default_main_module:
            print(f"ボタンが押されていません。{default_main_module} を起動します。")
            try:
                if default_main_module.endswith(".py"):
                    default_main_module = default_main_module[:-3]  # ".py" を削除
                main = __import__(default_main_module)
            except ImportError:
                print(f"エラー: {default_main_module} モジュールが見つかりません。")
                import netconfig as main
        else:
            print("main1.py を起動します。")
            import main1 as main

if __name__ == "__main__":
    main()