# ESP32C6 plant-IoT v1.0.0
import time
from hardware import Hardware
from config import Config 

def main():
    # config.txt の内容を読んで設定する
    cfg = Config.get_config()
    default_main_module = cfg['MAIN_MODULE']

    if default_main_module:
        print(f"{default_main_module} を起動します。")
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