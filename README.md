# pcratch-iot
Pcratch IoT デバイスのデバイス側のPythonコードです。

電源投入時 main.py が実行されます。
main.py は、wifi_config.txt ファイルを読み込み、指定されたアプリを選択して起動します。
wifi_config.txt ファイルが存在し無い場合は、main1.py を起動します。
また、P17スイッチを押しながら起動すると netconfig.py を起動します。

- ぷくらっちIoTモード(main1.py)：ぷくらっちの拡張機能と通信して、IoTデバイスを制御できるようになります。
- デモ(main2.py)：インターネット時計と天気予報、温度計のデモアプリ
- 設定(netconfig.py)：スマホ等から、起動アプリとWiFi設定を変更でるモードです。

# 修正履歴
v1.4.5.3    2025/04/04 初回出荷版
v1.5.1.1    2025/05/14 P1をPWM出力に設定/明るさの表示誤差修正
v1.5.1.2    2025/05/28 wifi_config.txt が存在しない場合でも動作するよう対応
v1.5.1.3    2025/06/05 バージョン番号をOLEDに表示

# 環境作成（初回のみ）
python -m venv myenv

# 仮想環境を有効化するコマンド
cd src
..\myenv\Scripts\activate

# ファイルのコピー
mpremote cp -r ./ :

# REPL
mpremote repl
# reset
mpremote reset
