import asyncio
import aioble
import bluetooth

import random
import struct
import ubinascii
import network
from micropython import const


def microbit_friendly_name(unique_id):
    length = 5
    letters = 5
    codebook = [
        ['z', 'v', 'g', 'p', 't'],
        ['u', 'o', 'i', 'e', 'a'],
        ['z', 'v', 'g', 'p', 't'],
        ['u', 'o', 'i', 'e', 'a'],
        ['z', 'v', 'g', 'p', 't']
    ]
    name = []

    # Derive our name from the nrf51822's unique ID
    # _, n = struct.unpack("II", machine.unique_id())
    mac_padded = b'\x00\x00' + unique_id # 6バイトのMACアドレスを8バイトにパディング
    _, n = struct.unpack('>II', mac_padded)
    ld = 1;
    d = letters;

    for i in range(0, length):
        h = (n % d) // ld;
        n -= h;
        d *= letters;
        ld *= letters;
        name.insert(0, codebook[i][h]);

    return "".join(name);

class BLEConnection:
    def __init__(self):
        # デバイス名を設定
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.mac = self.wlan.config('mac')
        # 下位バイトをドット区切りの10進数に変換
        # mac_str = '.'.join(str(b) for b in mac[-3:])
        # self.NAME = f"BBC micro:bit [{mac_str}]"
        self.riendly_name = microbit_friendly_name(self.mac)
        self.NAME = f"BBC micro:bit [{self.riendly_name}]"
        print(self.NAME)

        # サービスUUIDと characteristic UUID を定義
        self.IOT_SERVICE_UUID = bluetooth.UUID('0b50f3e4-607f-4151-9091-7d008d6ffc5c')
        IOT_COMMAND_CH__UUID = bluetooth.UUID('0b500100-607f-4151-9091-7d008d6ffc5c')
        IOT_STATE_CH_UUID = bluetooth.UUID('0b500101-607f-4151-9091-7d008d6ffc5c')
        IOT_MOTION_CH_UUID = bluetooth.UUID('0b500102-607f-4151-9091-7d008d6ffc5c')
        IOT_PINEVENT_CH_UUID = bluetooth.UUID('0b500110-607f-4151-9091-7d008d6ffc5c')
        IOT_ACTIONEVENT_CH_UUID = bluetooth.UUID('0b500111-607f-4151-9091-7d008d6ffc5c')
        IOT_ANALOGIN0_CH_UUID = bluetooth.UUID('0b500120-607f-4151-9091-7d008d6ffc5c')
        IOT_ANALOGIN1_CH_UUID = bluetooth.UUID('0b500121-607f-4151-9091-7d008d6ffc5c')
        IOT_ANALOGIN2_CH_UUID = bluetooth.UUID('0b500122-607f-4151-9091-7d008d6ffc5c')
        IOT_MESSAGE_CH_UUID = bluetooth.UUID('0b500130-607f-4151-9091-7d008d6ffc5c')

        # org.bluetooth.characteristic.gap.appearance.xml
        self._ADV_APPEARANCE_GENERIC_TAG = const(512)
        # How frequently to send advertising beacons.
        self._ADV_INTERVAL_MS = 250_000

        # サービスと characteristic を定義
        self.iot_service = aioble.Service(self.IOT_SERVICE_UUID)
        self.command_characteristic = aioble.Characteristic(
            self.iot_service, IOT_COMMAND_CH__UUID, read=True, write=True
        )
        self.state_characteristic = aioble.Characteristic(
            self.iot_service, IOT_STATE_CH_UUID, read=True
        )
        self.motion_characteristic = aioble.Characteristic(
            self.iot_service, IOT_MOTION_CH_UUID, read=True
        )
        self.pinevent_characteristic = aioble.Characteristic(
            self.iot_service, IOT_PINEVENT_CH_UUID, read=True, notify=True
        )
        self.actionevent_characteristic = aioble.Characteristic(
            self.iot_service, IOT_ACTIONEVENT_CH_UUID, read=True, notify=True
        )
        self.analog0_characteristic = aioble.Characteristic(
            self.iot_service, IOT_ANALOGIN0_CH_UUID, read=True, notify=True
        )
        self.analog1_characteristic = aioble.Characteristic(
            self.iot_service, IOT_ANALOGIN1_CH_UUID, read=True, notify=True
        )
        self.analog2_characteristic = aioble.Characteristic(
            self.iot_service, IOT_ANALOGIN2_CH_UUID, read=True, notify=True
        )
        self.message_characteristic = aioble.Characteristic(
            self.iot_service, IOT_MESSAGE_CH_UUID, read=True, notify=True
        )
        aioble.register_services(self.iot_service)

    def state_write(self, buffer):
        self.state_characteristic.write(buffer, send_update=True)

    # Serially wait for connections. Don't advertise while a central is
    # connected.
    async def peripheral_task(self):
        while True:
            try:
                async with await aioble.advertise(
                    self._ADV_INTERVAL_MS,
                    name=self.NAME,
                    services=[self.IOT_SERVICE_UUID],
                    appearance=self._ADV_APPEARANCE_GENERIC_TAG,
                ) as connection:
                    print("Connection from", connection.device)
                    # 送信する3バイトのデータを定義
                    data_to_send = struct.pack('<BBB', 0x01, 0x02, 0x03)
                    self.command_characteristic.write(data_to_send)
                    print("3バイト送信...") # 3バイトのデータを送信
                    # 切断理由を取得して表示
                    reason = await connection.disconnected(timeout_ms=None)
                    print(f"Disconnected. Reason: {reason}")
            except Exception as e:
                print("Error during advertising or connection:", e)
                await asyncio.sleep_ms(1000)


    async def motion_task(self):
        while True:
            #print(i, "motion_characteristic")
            # 送信する2バイトのデータを9個定義（すべての値がゼロ）
            data_to_send = struct.pack('<9H', *([0] * 9))
            self.motion_characteristic.write(data_to_send)
            await asyncio.sleep_ms(1000)

    async def command_task(self, do_command):
        while True:
            # コマンドを待つ
            await self.command_characteristic.written()
            data = self.command_characteristic.read()
            do_command(data)


    async def ble_task(self, do_command):
        # Run both tasks.
        t2 = asyncio.create_task(self.motion_task())
        t3 = asyncio.create_task(self.peripheral_task())
        t4 = asyncio.create_task(self.command_task(do_command))
        await asyncio.gather(t2, t3, t4)
