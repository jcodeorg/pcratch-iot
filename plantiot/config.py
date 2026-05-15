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
            'SEND_MIN': 60,
            'AUTO_WIFI': '0',
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

    @staticmethod
    def save_settings(updates):
        """wifi_config.txt を更新する。
        既存キーはその行を上書き、新規キーはファイル末尾に追加する。
        コメント・空行・不明キーは全て保持する。
        """
        lines = []
        key_line_idx = {}
        try:
            with open("wifi_config.txt", "r") as f:
                for line in f:
                    raw = line.rstrip("\n\r")
                    stripped = raw.strip()
                    if stripped and not stripped.startswith('#') and '=' in stripped:
                        k = stripped.split('=', 1)[0].strip()
                        key_line_idx[k] = len(lines)
                    lines.append(raw)
        except Exception:
            pass  # ファイルが存在しない場合は空から作成

        for key, value in updates.items():
            entry = str(key) + "=" + str(value)
            if key in key_line_idx:
                lines[key_line_idx[key]] = entry
            else:
                lines.append(entry)

        try:
            with open("wifi_config.txt", "w") as f:
                for line in lines:
                    f.write(line + "\n")
            return True
        except Exception as e:
            print("Config save error:", e)
            return False