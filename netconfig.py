import uasyncio as asyncio
from server import IoTServer  # 作成したモジュールをインポート

async def start_server_async(iot_server):
    """サーバーを非同期で実行"""
    await asyncio.sleep(0)  # 非同期タスクとして動作させるためのダミー
    print("サーバー起動中...")
    iot_server.start_server()

async def main():
    # IoTServerのインスタンスを作成
    iot_server = IoTServer()

    # サーバーを非同期タスクとして実行
    asyncio.create_task(start_server_async(iot_server))

    # 他の非同期タスクを追加（必要に応じて）
    while True:
        print("メイン処理実行中...")
        await asyncio.sleep(5)  # 5秒ごとにログを出力

# 非同期イベントループを開始
asyncio.run(main())