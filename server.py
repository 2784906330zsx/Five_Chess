import socket
import json
import random
import threading

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
            if row[i] == row[i + 1] == row[i + 2] == row[i + 3] == row[i + 4] and row[i] != 0:
                return row[i]

    for col in range(len(b[0])):
        for i in range(len(b) - 4):
            if b[i][col] == b[i + 1][col] == b[i + 2][col] == b[i + 3][col] == b[i + 4][col] and b[i][col] != 0:
                return b[i][col]

    for i in range(len(b) - 4):
        for j in range(len(b[0]) - 4):
            if b[i][j] == b[i + 1][j + 1] == b[i + 2][j + 2] == b[i + 3][j + 3] == b[i + 4][j + 4] and b[i][j] != 0:
                return b[i][j]

    for i in range(len(b) - 4):
        for j in range(4, len(b[0])):
            if b[i][j] == b[i + 1][j - 1] == b[i + 2][j - 2] == b[i + 3][j - 3] == b[i + 4][j - 4] and b[i][j] != 0:
                return b[i][j]

    return 0

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = "0.0.0.0"
port = 8000
server.bind((host, port))
server.listen(2)
print(f"{host}:{port}绑定成功")
client_list = []

game_error = False
game_data = {
    "chessmap": [[0 for _ in range(15)] for _ in range(15)],
    "chesscolor": 1,  # 先黑后白，1代表下黑子权限，-1代表白子权限，0没有权限
    "game_over": 0,
}

def handle_client():
    global game_error, client_list
    count = random.randint(0, 1)
    try:
        client_list[count].send(json.dumps(game_data).encode())
    except Exception:
        return False

    while not game_error:
        try:
            print(f"等待客户端{count}消息中：")
            data = json.loads(client_list[count % 2].recv(1024).decode())
            print(f"Receive client{count}: {data[0]},{data[1]},{data[2]}")

            if game_data["chesscolor"] == data[0]:
                game_data["chessmap"][data[1]][data[2]] = data[0]
                game_data["game_over"] = if_win(game_data["chessmap"])

                if game_data["game_over"] == 0:
                    game_data["chesscolor"] *= -1
                else:
                    game_data["chesscolor"] = 0
                    client_list[0].send(json.dumps(game_data).encode())
                    client_list[1].send(json.dumps(game_data).encode())

                    while True:
                        client_list[0].settimeout(10)
                        client_list[1].settimeout(10)
                        new_count = 0
                        try:
                            new_game = client_list[0].recv(1024).decode()
                            if new_game == "AGAIN_YES":
                                new_count += 1
                                print(f"Receive {new_game} new game requests")
                            else:
                                client_list[0].send("REFUSE".encode())
                                client_list[1].send("REFUSE".encode())
                                return False

                            if new_count == 2:
                                print("重新开始")
                                return True
                        except socket.timeout:
                            client_list[0].send("REFUSE".encode())
                            client_list[1].send("REFUSE".encode())
                            return False

                count += 1
                client_list[count % 2].send(json.dumps((game_data["chesscolor"], data[1], data[2])).encode())
        except Exception as e:
            print(f"客户端{count}断开连接")
            game_error = True
            return False

def check_connection():
    global client_list
    while len(client_list) == 1:
        try:
            client_list[0].send("RUOK?".encode())
            client_list[0].recv(1024)
        except Exception as e:
            print("客户端断开连接:", e)
            client_list[0].close()
            client_list = []
            print(f"\n已重新开始监听: {host}:{port}:")
            return

def ServerMain():
    global game_error
    global client_list
    try:
        while True:
            game_error = False

            client, client_address = server.accept()
            print(f"连接来自: {client_address}")

            client.settimeout(3)
            try:
                message = client.recv(1024).decode()
                if message == "OK":
                    print("Receive client: OK")
                    client_list.append(client)
                else:
                    client.close()
                    continue
            except socket.timeout:
                client.close()
                continue

            if len(client_list) == 2:
                try:
                    while not game_error:
                        thread = threading.Thread(target=handle_client)
                        thread.start()
                        thread.join()
                    else:
                        raise Exception
                except Exception:
                    game_data["chesscolor"] = 1
                    game_data["game_over"] = 0
                    game_data["chessmap"] = [[0 for _ in range(15)] for _ in range(15)]

                    for client_socket in client_list:
                        client_socket.close()

                    client_list = []
                    print(f"\n已重新开始监听: {host}:{port}:")
                    continue

    except KeyboardInterrupt:
        print("服务器被强制停止")
        server.close()
        for client_socket in client_list:
            client_socket.close()

ServerMain()
