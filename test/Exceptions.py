import asyncio
import websockets


async def echo(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")
        message = input()
        await websocket.send(f"{message}")


start_server = websockets.serve(echo, "localhost", 9501)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
