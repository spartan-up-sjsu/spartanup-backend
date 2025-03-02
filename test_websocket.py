import asyncio
import websockets

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws/67c4b7c6cafb28921e48761d/60b8d295f1b2c3d4e8f8e8f8"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send("Test message")
            response = await websocket.recv()
            print("Received:", response)
    except Exception as e:
        print(f"Error connecting to WebSocket: {e}")

asyncio.run(test_websocket())
