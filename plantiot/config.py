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
            'SEND_MIN': 60
        }
        try:
            with open("wifi_config.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        config[k.strip()] = v.strip()
        except Exception as e:
            print(f"wifi_config.txt 読み込みエラー: {e}")
        return Config(config)
    
    def __init__(self, config_dict):
        self._config = config_dict
    
    def __getitem__(self, key):
        return self._config[key]
    
    def get(self, key, default=None):
        return self._config.get(key, default)