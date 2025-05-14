# pcratch-iot
Pcratch IoT デバイスのデバイス側のPythonコードです。

起動時に config ファイルを読み込み、起動アプリを選択して起動します。
また、起動時にスイッチを押すと、設定アプリが起動されます。
- ぷくらっちIoT拡張：ぷくらっちの拡張機能と通信して、IoTデバイスを制御できるようになります。  
- 設定：スマホ等から、起動アプリとWiFi設定を変更でるモードです。
- デモ：時計と温度計のデモアプリ

# 修正履歴
v1.4.5.3    2025/04/04 初回出荷版
v1.5.1.1    2025/05/14 P1をPWM出力に設定/明るさの表示誤差修正

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
