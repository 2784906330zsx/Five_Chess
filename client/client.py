import socket
import threading
import pygame
import json

import select

pygame.init()
info = pygame.display.Info()
screen_height = info.current_h
W = screen_height / 2  # 游戏窗口的高度
screen = pygame.display.set_mode((W, 1.1 * W))
pygame.display.set_caption("五子棋")
cell = W / 16
last_chess_x, last_chess_y = 0, 0

image1 = pygame.image.load("resources/black.png")
image2 = pygame.image.load("resources/white.png")
image3 = pygame.image.load("resources/chessmap.png")
image1 = pygame.transform.smoothscale(image1, (cell, cell))
image2 = pygame.transform.smoothscale(image2, (cell, cell))
image3 = pygame.transform.smoothscale(image3, (W, W))
pygame.mixer.init()
music = pygame.mixer.Sound("resources/chess.mp3")

button_data = [
    {"name": "是", "rect": pygame.Rect(cell * 9, W * 1.02, cell * 2, W * 0.06), "color": (0, 255, 0)},
    {"name": "否", "rect": pygame.Rect(cell * 12, W * 1.02, cell * 2, W * 0.06), "color": (255, 0, 0)},
]

game_data = {
    "map": [[0 for _ in range(15)] for _ in range(15)],
    "color": 0,  # 先黑后白，1代表下黑子权限，-1代表白子权限，0没有权限
    "over": 0,
}

font1 = None
font2 = "resources/HarmonyOS_Sans_SC_Regular.ttf"
font3 = pygame.font.Font(font2, 36)


def Outtext(text, position, font, size, color):
    pygame.draw.rect(screen, (0, 0, 0), (0, W, W, W * 1.1))
    font = pygame.font.Font(font, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.center = position
    screen.blit(text_surface, text_rect)
    pygame.display.update()


def Draw():
    global game_data, last_chess_x, last_chess_y
    screen.blit(image3, (0, 0))
    for i in range(len(game_data["map"])):
        for j in range(len(game_data["map"])):
            position = (i + 1 / 2) * cell, (j + 1 / 2) * cell
            if game_data["map"][i][j] == 1:
                screen.blit(image1, position)
            elif game_data["map"][i][j] == -1:
                screen.blit(image2, position)

    if game_data["color"] == 0:
        Outtext("请等待对方落子", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
    elif game_data["color"] == 1:
        Outtext("请落黑子", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
    elif game_data["color"] == -1:
        Outtext("请落白子", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")

    if game_data["over"] != 0:
        Outtext("GAME OVER", (W / 2, W * 2 / 5), None, int(W / 6), (235, 111, 45))
        if game_data["over"] == 1:
            Outtext("BLACK  WIN", (W / 2, W * 3 / 5), None, int(W / 6), (235, 111, 45))
        elif game_data["over"] == -1:
            Outtext("WHITE  WIN", (W / 2, W * 3 / 5), None, int(W / 6), (235, 111, 45))
        elif game_data["over"] == 3:
            Outtext("平局", (W / 2, W * 3 / 5), None, int(W / 6), (235, 111, 45))

    last_chess_x, last_chess_y = (last_chess_x + 1 / 2) * cell, (last_chess_y + 1 / 2) * cell
    pygame.draw.rect(screen, (255, 0, 0), (last_chess_x, last_chess_y, cell, cell), 2)
    pygame.display.update()


def ConnectServer(host, port):
    client_socket.setblocking(True)
    client_socket.settimeout(3)
    connecting = True

    while connecting:
        try:
            client_socket.connect((host, port))
            client_socket.send("OK".encode())
            rlist, wlist, xlist = select.select([], [client_socket], [], 1)
            if client_socket in wlist:
                Outtext("服务器连接成功，正在等待对手", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
                client_socket.setblocking(False)  # 非阻塞模式
                connecting = False
        except Exception:
            Outtext("连接服务器失败，正在尝试重连", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
            continue


screen.blit(image3, (0, 0))
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockets_to_listen = [client_socket]

host = "127.0.0.1"
# host = "8.218.192.192"
port = 8000

Outtext("正在连接服务器...", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
connect_thread = threading.Thread(target=ConnectServer, args=(host, port))  # 创建连接线程
connect_thread.start()
connect_thread.join()  # 等待连接线程完成


def getMessage():
    global game_data, last_chess_x, last_chess_y
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                raise Exception
            else:
                temp = data.decode()
                if temp == "ERROR":
                    Outtext("对方已掉线", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
                elif temp == "REFUSE":
                    Outtext("对方拒绝新对局", (W / 3, W * 1.05), font2, int(W / 20), "#FFFFFF")
                    continue
                elif temp == "RUOK?":
                    client_socket.send("IMOK!".encode())
                    continue
                else:
                    temp = json.loads(temp)
                    game_data["color"] = temp[0]
                    game_data["map"][temp[1]][temp[2]] = -temp[0]
                    last_chess_x, last_chess_y = temp[1], temp[2]
                Draw()
        except Exception:
            game_data["color"] = 0
            Outtext("与服务器连接中断", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
            ConnectServer(host, port)
            continue


# 接收服务器消息的进程，需要一直保持运行
get_message_threading = threading.Thread(target=getMessage)
get_message_threading.start()


def GameMain():
    global game_data, button_data, last_chess_x, last_chess_y
    while game_data["over"] == 0:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 0
            if event.type == pygame.MOUSEBUTTONDOWN and game_data["over"] == 0 and game_data["color"] != 0:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()

                    position_x = int(round(mouse_x / (cell / 2) / 2, 0) - 1)
                    position_y = int(round(mouse_y / (cell / 2) / 2, 0) - 1)

                    if position_x >= 15 or position_y >= 15:
                        continue
                    if position_x <= -1 or position_y <= -1:
                        continue
                    if game_data["map"][position_x][position_y] != 0:
                        continue

                    game_data["map"][position_x][position_y] = game_data["color"]
                    last_chess_x, last_chess_y = position_x, position_y
                    client_socket.send(json.dumps((game_data["color"], position_x, position_y)).encode())
                    game_data["color"] = 0
                    music.play()
                    Draw()
    else:
        Outtext("是否继续对局？", (W / 3, W * 1.05), font2, int(W / 20), "#FFFFFF")
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 0

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if button_data[0]["rect"].collidepoint(event.pos):
                        client_socket.send("AGAIN_YES".encode())
                        print("是")
                    if button_data[1]["rect"].collidepoint(event.pos):
                        client_socket.send("AGAIN_NO".encode())
                        print("否")

                for button in button_data:
                    mouse_pos = pygame.mouse.get_pos()
                    if button["rect"].collidepoint(mouse_pos):
                        button_color = (255, 255, 255)
                    else:
                        button_color = button["color"]

                    pygame.draw.rect(screen, button_color, button["rect"])
                    text = font3.render(button["name"], True, (0, 0, 0))
                    text_rect = text.get_rect(center=button["rect"].center)
                    screen.blit(text, text_rect)

            pygame.display.update()


GameMain()
