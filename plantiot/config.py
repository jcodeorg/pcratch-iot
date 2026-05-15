class Config:
    @staticmethod
    def get_config():
        """
        wifi_config.txt から SSID, PASSWORD, MAIN_MODULE を読み込む
        他の設定値は固定値で返す
        """
        config = {
            'SSID': '',
            'PASSWORD': '',
            'MAIN_MODULE': 'main1.py',
            'GAS_URL': '',
            'DEVICEID': 'D0000',
        }
        try:
            with open("wifi_config.txt", "r") as f:
                for line in f:
                    if line.startswith("SSID="):
                        config['SSID'] = line.strip().split("=", 1)[1]
                    elif line.startswith("PASSWORD="):
                        config['PASSWORD'] = line.strip().split("=", 1)[1]
                    elif line.startswith("MAIN_MODULE="):
                        config['MAIN_MODULE'] = line.strip().split("=", 1)[1]
                    elif line.startswith("GAS_URL="):
                        config['GAS_URL'] = line.strip().split("=", 1)[1]
                    elif line.startswith("DEVICEID="):
                        config['DEVICEID'] = line.strip().split("=", 1)[1]
        except Exception as e:
            print(f"wifi_config.txt 読み込みエラー: {e}")
        return config