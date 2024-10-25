import asyncio
import pygame
import json
import websockets

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

font2 = "C:/Windows/Fonts/simkai.ttf"
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


async def connect_to_server():
    async with websockets.connect('ws://127.0.0.1:8000') as websocket:
        await websocket.send("OK")
        await handle_server_messages(websocket)


async def handle_server_messages(websocket):
    global game_data, last_chess_x, last_chess_y
    while True:
        data = await websocket.recv()
        if not data:
            continue
        if data == "ERROR":
            Outtext("对方已掉线", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
        elif data == "REFUSE":
            Outtext("对方拒绝新对局", (W / 3, W * 1.05), font2, int(W / 20), "#FFFFFF")
            continue
        elif data == "RUOK?":
            await websocket.send("IMOK!")
            continue
        else:
            temp = json.loads(data)
            game_data["color"] = temp[0]
            game_data["map"][temp[1]][temp[2]] = -temp[0]
            last_chess_x, last_chess_y = temp[1], temp[2]
            Draw()


async def GameMain(websocket):
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
                    await websocket.send(json.dumps((game_data["color"], position_x, position_y)))
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
                        await websocket.send("AGAIN_YES")
                        print("是")
                    if button_data[1]["rect"].collidepoint(event.pos):
                        await websocket.send("AGAIN_NO")
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


async def main():
    await connect_to_server()
    await GameMain()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
