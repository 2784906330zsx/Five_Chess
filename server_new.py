import json
import random
import websockets
import asyncio

import logging

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def if_win(b):
    count = 0
    for row in game_data["chessmap"]:
        for j in row:
            if j == 0:
                count += 1

    if count == 0:
        return 3

    for row in b:
        for i in range(len(row) - 4):
            if (
                row[i] == row[i + 1] == row[i + 2] == row[i + 3] == row[i + 4]
                and row[i] != 0
            ):
                return row[i]

    for col in range(len(b[0])):
        for i in range(len(b) - 4):
            if (
                b[i][col]
                == b[i + 1][col]
                == b[i + 2][col]
                == b[i + 3][col]
                == b[i + 4][col]
                and b[i][col] != 0
            ):
                return b[i][col]

    for i in range(len(b) - 4):
        for j in range(len(b[0]) - 4):
            if (
                b[i][j]
                == b[i + 1][j + 1]
                == b[i + 2][j + 2]
                == b[i + 3][j + 3]
                == b[i + 4][j + 4]
                and b[i][j] != 0
            ):
                return b[i][j]

    for i in range(len(b) - 4):
        for j in range(4, len(b[0])):
            if (
                b[i][j]
                == b[i + 1][j - 1]
                == b[i + 2][j - 2]
                == b[i + 3][j - 3]
                == b[i + 4][j - 4]
                and b[i][j] != 0
            ):
                return b[i][j]

    return 0


CONNECTIONS = set()
已连接用户 = {}
棋局 = {}


async def register(websocket: websockets.WebSocketServerProtocol):
    global 已连接用户

    try:
        message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
    except asyncio.TimeoutError:
        await websocket.close()
        return

    if not message.startswith("你好！"):
        await websocket.close()
        return

    try:
        if message.startswith("你好！我的id是"):
            用户id = int(message[len("你好！我的id是") :])
        elif message == "你好！":
            用户id = random.randint(100000, 999999)
        else:
            await websocket.close()
            return
    except:
        await websocket.close()
        return

    try:
        已连接用户[用户id] = websocket
        await websocket.send(f"你好！你的id是{用户id}")

        async for message in websocket:
            if message == "创建棋局":
                pass
            elif message.startswith("加入棋局"):
                棋局id = int(message[len("加入棋局") :])
                
            else:
                await websocket.send(f"Hello {message}!")
                await websocket.send(f"当前用户数：{len(CONNECTIONS)}")

    except:
        await websocket.close()
    finally:
        del 已连接用户[用户id]


async def main():
    async with websockets.serve(register, "0.0.0.0", 8000):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
