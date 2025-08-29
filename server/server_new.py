import asyncio
import websockets
import json
import logging
import time
from typing import Dict, Set, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FiveChessServer:
    def __init__(self, host="0.0.0.0", port=8000):
        self.host = host
        self.port = port
        self.clients: Dict[str, dict] = {}  # 使用client_id作为key
        self.game_clients: list = []  # 游戏中的客户端websocket列表
        self.game_data = {
            "chessmap": [[0 for _ in range(15)] for _ in range(15)],
            "chesscolor": 1,  # 1代表黑子，-1代表白子
            "game_over": 0,
        }
        self.auth_token = "FIVE_CHESS_AUTH_2024"  # 认证令牌
        self.heartbeat_interval = 30  # 心跳间隔（秒）
        self.heartbeat_timeout = 60   # 心跳超时（秒）
        self.server_state = "waiting"  # waiting, game_in_progress
        
    def reset_game(self):
        """重置游戏状态"""
        self.game_data = {
            "chessmap": [[0 for _ in range(15)] for _ in range(15)],
            "chesscolor": 1,
            "game_over": 0,
        }
        logger.info("游戏状态已重置")
    
    def check_win(self, board):
        """检查游戏是否结束"""
        # 检查是否平局
        count = 0
        for row in board:
            for cell in row:
                if cell == 0:
                    count += 1
        if count == 0:
            return 3  # 平局
        
        # 检查横向
        for row in board:
            for i in range(len(row) - 4):
                if row[i] == row[i + 1] == row[i + 2] == row[i + 3] == row[i + 4] and row[i] != 0:
                    return row[i]
        
        # 检查纵向
        for col in range(len(board[0])):
            for i in range(len(board) - 4):
                if board[i][col] == board[i + 1][col] == board[i + 2][col] == board[i + 3][col] == board[i + 4][col] and board[i][col] != 0:
                    return board[i][col]
        
        # 检查正对角线
        for i in range(len(board) - 4):
            for j in range(len(board[0]) - 4):
                if board[i][j] == board[i + 1][j + 1] == board[i + 2][j + 2] == board[i + 3][j + 3] == board[i + 4][j + 4] and board[i][j] != 0:
                    return board[i][j]
        
        # 检查反对角线
        for i in range(len(board) - 4):
            for j in range(4, len(board[0])):
                if board[i][j] == board[i + 1][j - 1] == board[i + 2][j - 2] == board[i + 3][j - 3] == board[i + 4][j - 4] and board[i][j] != 0:
                    return board[i][j]
        
        return 0  # 游戏继续
    
    async def send_message(self, websocket, message_type, data=None):
        """发送消息给客户端"""
        try:
            message = {
                "type": message_type,
                "data": data,
                "timestamp": time.time()
            }
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"客户端连接已关闭，无法发送消息: {message_type}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def broadcast_to_game_clients(self, message_type, data=None):
        """向游戏中的客户端广播消息"""
        if len(self.game_clients) == 2:
            tasks = []
            for client in self.game_clients:
                tasks.append(self.send_message(client, message_type, data))
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def authenticate_client(self, websocket, auth_data):
        """认证客户端"""
        try:
            token = auth_data.get("data", {}).get("token")
            
            if token == self.auth_token:
                await self.send_message(websocket, "auth_success", {"message": "认证成功"})
                logger.info(f"客户端认证成功")
                return True
            else:
                await self.send_message(websocket, "auth_failed", {"message": "认证失败"})
                logger.warning(f"客户端认证失败")
                return False
                
        except Exception as e:
            logger.error(f"认证处理错误: {e}")
            await self.send_message(websocket, "auth_failed", {"message": "认证错误"})
            return False
    

    
    async def start_game(self):
        """开始游戏"""
        logger.info("游戏开始，两个玩家已连接")
        self.reset_game()
        self.server_state = "game_in_progress"
        
        # 获取两个客户端的websocket
        client_websockets = []
        for client_info in self.clients.values():
            client_websockets.append(client_info['websocket'])
        
        self.game_clients = client_websockets
        
        # 随机分配黑白子
        import random
        first_player = random.choice(client_websockets)
        second_player = client_websockets[1] if client_websockets[0] == first_player else client_websockets[0]
        
        # 发送游戏开始消息
        await self.send_message(first_player, "game_start", {
            "color": 1,  # 黑子
            "turn": True,
            "message": "游戏开始，你执黑子，请先下棋"
        })
        
        await self.send_message(second_player, "game_start", {
            "color": -1,  # 白子
            "turn": False,
            "message": "游戏开始，你执白子，等待对方下棋"
        })
        
        # 设置玩家颜色（通过websocket找到对应的client_id）
        for client_id, client_info in self.clients.items():
            if client_info['websocket'] == first_player:
                client_info["color"] = 1
            elif client_info['websocket'] == second_player:
                client_info["color"] = -1
    
    async def handle_move(self, websocket, message):
        """处理下棋消息"""
        try:
            data = message.get("data", {})
            x, y = data.get("x"), data.get("y")
            
            # 通过websocket找到对应的client_info
            player_color = None
            for client_info in self.clients.values():
                if client_info['websocket'] == websocket:
                    player_color = client_info.get("color")
                    break
            
            if player_color is None:
                await self.send_message(websocket, "error", {"message": "玩家信息未找到"})
                return
            
            # 验证是否轮到该玩家
            if self.game_data["chesscolor"] != player_color:
                await self.send_message(websocket, "error", {"message": "不是你的回合"})
                return
            
            # 验证位置是否有效
            if x < 0 or x >= 15 or y < 0 or y >= 15 or self.game_data["chessmap"][x][y] != 0:
                await self.send_message(websocket, "error", {"message": "无效的位置"})
                return
            
            # 下棋
            self.game_data["chessmap"][x][y] = player_color
            
            # 检查游戏是否结束
            self.game_data["game_over"] = self.check_win(self.game_data["chessmap"])
            
            if self.game_data["game_over"] == 0:
                # 游戏继续，切换回合
                self.game_data["chesscolor"] *= -1
            else:
                # 游戏结束
                self.game_data["chesscolor"] = 0
            
            # 广播游戏状态
            await self.broadcast_to_game_clients("game_update", {
                "chessmap": self.game_data["chessmap"],
                "chesscolor": self.game_data["chesscolor"],
                "game_over": self.game_data["game_over"],
                "last_move": {"x": x, "y": y, "color": player_color}
            })
            
            if self.game_data["game_over"] != 0:
                logger.info(f"游戏结束，结果: {self.game_data['game_over']}")
                
        except Exception as e:
            logger.error(f"处理下棋消息错误: {e}")
            await self.send_message(websocket, "error", {"message": "处理下棋请求失败"})
    
    async def handle_heartbeat(self, websocket, message):
        """处理心跳消息"""
        # 通过websocket找到对应的client_info并更新心跳时间
        for client_info in self.clients.values():
            if client_info['websocket'] == websocket:
                client_info["last_heartbeat"] = time.time()
                break
        await self.send_message(websocket, "heartbeat_ack")
    

    
    async def disconnect_client(self, client_id):
        """断开客户端连接"""
        try:
            if client_id in self.clients:
                websocket = self.clients[client_id]['websocket']
                logger.info(f"断开客户端: {client_id}")
                
                # 如果服务器处于游戏状态
                if self.server_state == "game_in_progress":
                    # 通知另一个客户端并断开其连接
                    for other_client_id, other_client_info in list(self.clients.items()):
                        if other_client_id != client_id:
                            other_websocket = other_client_info['websocket']
                            await self.send_message(other_websocket, "opponent_disconnected", 
                                                  {"message": "对手已断开连接，游戏结束"})
                            # 主动断开另一个客户端
                            if not other_websocket.closed:
                                await other_websocket.close()
                            del self.clients[other_client_id]
                            logger.info(f"主动断开另一个客户端: {other_client_id}")
                    
                    # 重置服务器状态
                    self.game_clients.clear()
                    self.reset_game()
                    self.server_state = "waiting"
                    logger.info("服务器已重置到等待状态")
                
                # 如果服务器处于等待状态，只需清理当前客户端
                elif self.server_state == "waiting":
                    logger.info("等待状态下的客户端断开，服务器保持等待状态")
                
                # 清理当前客户端信息
                if client_id in self.clients:
                    del self.clients[client_id]
                
                # 安全地关闭websocket连接
                try:
                    if hasattr(websocket, 'closed') and not websocket.closed:
                        await websocket.close()
                    elif not hasattr(websocket, 'closed'):
                        await websocket.close()
                except Exception as close_error:
                    logger.debug(f"关闭websocket时出错: {close_error}")
                    
        except Exception as e:
            logger.error(f"断开客户端时发生错误: {e}")
    
    async def handle_message(self, client_id, data):
        """处理客户端消息"""
        try:
            message_type = data.get("type")
            websocket = self.clients[client_id]['websocket']
            
            if message_type == "move":
                await self.handle_move(websocket, data)
            elif message_type == "heartbeat":
                await self.handle_heartbeat(websocket, data)
            else:
                logger.warning(f"未知消息类型: {message_type}")
                
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
    
    async def monitor_heartbeat(self, client_id):
        """监控客户端心跳"""
        while client_id in self.clients:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if client_id not in self.clients:
                    break
                    
                last_heartbeat = self.clients[client_id].get("last_heartbeat", 0)
                if time.time() - last_heartbeat > self.heartbeat_timeout:
                    logger.warning(f"客户端 {client_id} 心跳超时")
                    await self.disconnect_client(client_id)
                    break
                    
            except Exception as e:
                logger.error(f"心跳监控错误: {e}")
                break
    
    async def handle_client(self, websocket, path=None):
        """处理客户端连接"""
        client_id = id(websocket)
        logger.info(f"客户端 {client_id} 连接")
        
        try:
            # 等待认证消息
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            auth_data = json.loads(auth_message)
            
            if not await self.authenticate_client(websocket, auth_data):
                return
            
            # 添加到客户端列表
            self.clients[client_id] = {
                'websocket': websocket,
                'last_heartbeat': time.time(),
                'authenticated': True
            }
            
            logger.info(f"客户端 {client_id} 认证成功，当前连接数: {len(self.clients)}")
            
            # 检查是否可以开始游戏
            if len(self.clients) == 1:
                await self.send_message(websocket, "waiting", {"message": "等待另一个玩家加入..."})
                # 启动心跳监控
                asyncio.create_task(self.monitor_heartbeat(client_id))
            elif len(self.clients) == 2:
                await self.start_game()
            
            # 监听客户端消息
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(client_id, data)
                except json.JSONDecodeError:
                    logger.error(f"客户端 {client_id} 发送了无效的JSON消息")
                except Exception as e:
                    logger.error(f"处理客户端 {client_id} 消息时出错: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端 {client_id} 断开连接")
        except asyncio.TimeoutError:
            logger.warning(f"客户端 {client_id} 认证超时")
        except Exception as e:
            logger.error(f"处理客户端 {client_id} 时出错: {e}")
        finally:
            await self.disconnect_client(client_id)
    
    async def start_server(self):
        """启动服务器"""
        logger.info(f"启动五子棋WebSocket服务器: {self.host}:{self.port}")
        
        # 直接使用handle_client方法
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"服务器已启动，等待客户端连接...")
            await asyncio.Future()  # 保持服务器运行

if __name__ == "__main__":
    server = FiveChessServer()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("服务器被手动停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")