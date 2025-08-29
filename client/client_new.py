import asyncio
import websockets
import pygame
import json
import threading
import time
import logging
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 初始化pygame
pygame.init()
info = pygame.display.Info()
screen_height = info.current_h
W = screen_height / 2  # 游戏窗口的高度
screen = pygame.display.set_mode((W, 1.1 * W))
pygame.display.set_caption("五子棋 - WebSocket版本")
cell = W / 16
last_chess_x, last_chess_y = 0, 0

# 加载资源
try:
    image1 = pygame.image.load("client/resources/photo/black.png")
    image2 = pygame.image.load("client/resources/photo/white.png")
    image3 = pygame.image.load("client/resources/photo/chessmap.png")
    image1 = pygame.transform.smoothscale(image1, (cell, cell))
    image2 = pygame.transform.smoothscale(image2, (cell, cell))
    image3 = pygame.transform.smoothscale(image3, (W, W))

    pygame.mixer.init()
    music = pygame.mixer.Sound("client/resources/music/chess.mp3")

    font2 = "client/resources/fonts/simkai.ttf"
    font3 = pygame.font.Font(font2, 36)
except Exception as e:
    logger.warning(f"加载资源文件失败: {e}")

# 按钮数据
button_data = [
    {
        "name": "是",
        "rect": pygame.Rect(cell * 9, W * 1.02, cell * 2, W * 0.06),
        "color": (0, 255, 0),
    },
    {
        "name": "否",
        "rect": pygame.Rect(cell * 12, W * 1.02, cell * 2, W * 0.06),
        "color": (255, 0, 0),
    },
]

# 游戏数据
game_data = {
    "map": [[0 for _ in range(15)] for _ in range(15)],
    "color": 0,  # 1代表黑子权限，-1代表白子权限，0没有权限
    "over": 0,
    "my_turn": False,
}


class FiveChessClient:
    def __init__(self, host="127.0.0.1", port=8000):
        self.host = host
        self.port = port
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.authenticated = False
        self.auth_token = "FIVE_CHESS_AUTH_2024"
        self.heartbeat_interval = 25  # 心跳间隔（秒）
        self.running = True
        self.connection_status = "正在连接服务器..."

    async def connect_to_server(self):
        """连接到服务器"""
        try:
            self.websocket = await websockets.connect(f"ws://{self.host}:{self.port}")
            self.connected = True
            logger.info(f"已连接到服务器: {self.host}:{self.port}")

            # 发送认证消息
            await self.authenticate()

            # 开始心跳
            asyncio.create_task(self.heartbeat_loop())

            # 开始监听消息
            await self.listen_messages()

        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            self.connection_status = f"连接失败: {e}"
            self.connected = False

    async def authenticate(self):
        """发送认证消息"""
        auth_message = {
            "type": "auth",
            "data": {"token": self.auth_token},
            "timestamp": time.time(),
        }
        await self.websocket.send(json.dumps(auth_message))
        logger.info("已发送认证消息")

    async def heartbeat_loop(self):
        """心跳循环"""
        while self.connected and self.websocket:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if self.authenticated and self.websocket:
                    heartbeat_message = {
                        "type": "heartbeat",
                        "data": {},
                        "timestamp": time.time(),
                    }
                    await self.websocket.send(json.dumps(heartbeat_message))
                    logger.debug("发送心跳")

            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                break

    async def send_move(self, x, y):
        """发送下棋消息"""
        if not self.authenticated or not self.websocket:
            return

        move_message = {
            "type": "move",
            "data": {"x": x, "y": y},
            "timestamp": time.time(),
        }

        try:
            await self.websocket.send(json.dumps(move_message))
            logger.info(f"发送下棋消息: ({x}, {y})")
        except Exception as e:
            logger.error(f"发送下棋消息失败: {e}")

    async def listen_messages(self):
        """监听服务器消息"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"解析消息失败: {e}")
                except Exception as e:
                    logger.error(f"处理消息失败: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("与服务器的连接已关闭")
            self.connected = False
            self.authenticated = False
            self.connection_status = "与服务器连接中断"
        except Exception as e:
            logger.error(f"监听消息时发生错误: {e}")
            self.connected = False
            self.authenticated = False

    async def handle_message(self, data):
        """处理服务器消息"""
        message_type = data.get("type")
        message_data = data.get("data", {})

        if message_type == "auth_success":
            self.authenticated = True
            self.connection_status = "认证成功，等待对手加入"
            logger.info("认证成功")

        elif message_type == "auth_failed":
            self.connection_status = "认证失败"
            logger.error("认证失败")

        elif message_type == "waiting":
            self.connection_status = "等待其他玩家加入"

        elif message_type == "game_start":
            global game_data
            game_data["color"] = message_data.get("color", 0)
            game_data["my_turn"] = message_data.get("turn", False)
            game_data["over"] = 0
            self.connection_status = message_data.get("message", "游戏开始")
            logger.info(f"游戏开始，我的颜色: {game_data['color']}")

        elif message_type == "game_update":
            global last_chess_x, last_chess_y
            game_data["map"] = message_data.get("chessmap", game_data["map"])
            game_data["over"] = message_data.get("game_over", 0)

            # 更新回合
            current_turn = message_data.get("chesscolor", 0)
            game_data["my_turn"] = current_turn == game_data["color"]

            # 更新最后下棋位置
            last_move = message_data.get("last_move", {})
            if last_move:
                last_chess_x = last_move.get("x", 0)
                last_chess_y = last_move.get("y", 0)

            # 播放音效
            if music and last_move.get("color") != game_data["color"]:
                music.play()

            logger.info(
                f"游戏状态更新，轮到: {current_turn}, 我的回合: {game_data['my_turn']}"
            )

        elif message_type == "opponent_disconnected":
            self.connection_status = "对手已断开连接"
            game_data["over"] = -999  # 特殊标记表示对手断线

        elif message_type == "error":
            error_msg = message_data.get("message", "未知错误")
            self.connection_status = f"错误: {error_msg}"
            logger.error(f"服务器错误: {error_msg}")

        elif message_type == "heartbeat_ack":
            logger.debug("收到心跳响应")

    async def disconnect(self):
        """断开连接"""
        self.running = False
        self.connected = False
        self.authenticated = False

        if self.websocket and not self.websocket.closed:
            await self.websocket.close()

        logger.info("已断开与服务器的连接")


# 全局客户端实例
client = FiveChessClient()


def outtext(text, position, font, size, color):
    """显示文本"""
    pygame.draw.rect(screen, (0, 0, 0), (0, W, W, W * 1.1))

    if font:
        font_obj = pygame.font.Font(font, size)
    else:
        font_obj = pygame.font.Font(None, size)

    text_surface = font_obj.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.center = position
    screen.blit(text_surface, text_rect)
    pygame.display.update()


def draw_game():
    """绘制游戏界面"""
    global game_data, last_chess_x, last_chess_y

    # 绘制棋盘
    screen.blit(image3, (0, 0))

    # 绘制棋子
    for i in range(len(game_data["map"])):
        for j in range(len(game_data["map"])):
            position = (i * cell + cell / 2, j * cell + cell / 2)
            if game_data["map"][i][j] == 1:
                screen.blit(image1, position)
            elif game_data["map"][i][j] == -1:
                screen.blit(image2, position)

    # 显示状态信息
    if not client.connected:
        outtext(
            client.connection_status, (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF"
        )
    elif not client.authenticated:
        outtext("正在认证...", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
    elif game_data["over"] == 0:
        if game_data["my_turn"]:
            if game_data["color"] == 1:
                outtext("请落黑子", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
            else:
                outtext("请落白子", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
        else:
            outtext("请等待对方落子", (W / 2, W * 1.05), font2, int(W / 16), "#FFFFFF")
    else:
        # 游戏结束
        if game_data["over"] == -999:
            outtext(
                "对手断线，游戏结束",
                (W / 2, W * 2 / 5),
                None,
                int(W / 8),
                (235, 111, 45),
            )
        else:
            outtext("GAME OVER", (W / 2, W * 2 / 5), None, int(W / 6), (235, 111, 45))
            if game_data["over"] == 1:
                outtext(
                    "BLACK WIN", (W / 2, W * 3 / 5), None, int(W / 6), (235, 111, 45)
                )
            elif game_data["over"] == -1:
                outtext(
                    "WHITE WIN", (W / 2, W * 3 / 5), None, int(W / 6), (235, 111, 45)
                )
            elif game_data["over"] == 3:
                outtext("平局", (W / 2, W * 3 / 5), None, int(W / 6), (235, 111, 45))

    # 高亮最后下的棋子
    if last_chess_x >= 0 and last_chess_y >= 0:
        highlight_x = last_chess_x * cell + cell / 2
        highlight_y = last_chess_y * cell + cell / 2
        pygame.draw.rect(screen, (255, 0, 0), (highlight_x, highlight_y, cell, cell), 2)

    pygame.display.update()


def handle_click(mouse_x, mouse_y):
    """处理鼠标点击"""
    if not client.authenticated or game_data["over"] != 0 or not game_data["my_turn"]:
        return

    # 计算棋盘位置
    position_x = int(round(mouse_x / cell - 0.5))
    position_y = int(round(mouse_y / cell - 0.5))

    # 验证位置
    if position_x < 0 or position_x >= 15 or position_y < 0 or position_y >= 15:
        return

    if game_data["map"][position_x][position_y] != 0:
        return

    # 发送下棋消息
    asyncio.create_task(client.send_move(position_x, position_y))

    # 临时更新本地状态（服务器会发送确认）
    game_data["map"][position_x][position_y] = game_data["color"]
    game_data["my_turn"] = False

    # 播放音效
    if music:
        music.play()


async def run_client():
    """运行客户端"""
    await client.connect_to_server()


def main():
    """主函数"""
    global game_data

    # 在单独线程中运行异步客户端
    def run_async_client():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_client())
        except Exception as e:
            logger.error(f"客户端运行错误: {e}")
        finally:
            loop.close()

    client_thread = threading.Thread(target=run_async_client, daemon=True)
    client_thread.start()

    # 主游戏循环
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                client.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键点击
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    handle_click(mouse_x, mouse_y)

        # 绘制游戏界面
        draw_game()
        clock.tick(60)  # 60 FPS

    # 清理资源
    asyncio.create_task(client.disconnect())
    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("游戏被用户中断")
    except Exception as e:
        logger.error(f"游戏运行错误: {e}")
    finally:
        pygame.quit()
