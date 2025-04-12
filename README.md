# pcratch-iot
Pcratch IoT デバイスのデバイス側のPythonコードです。

起動時に config ファイルを読み込み、起動アプリを選択して起動します。
また、起動時にスイッチを押すと、設定アプリが起動されます。
- ぷくらっちIoT拡張：ぷくらっちの拡張機能と通信して、IoTデバイスを制御できるようになります。  
- 設定：スマホ等から、起動アプリとWiFi設定を変更でるモードです。
- デモ：時計と温度計のデモアプリ


python -m venv myenv

cd src
..\myenv\Scripts\activate
# ファイルのコピー
mpremote cp -r ./ :
# REPL
mpremote repl
