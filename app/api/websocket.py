"""
WebSocket 实时通知 - 实现实时消息推送
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, List, Set
import json
from datetime import datetime

from app.models.models import User
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 用户 ID -> WebSocket 连接列表（支持同一用户多端连接）
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # 在线用户 ID 集合
        self.online_users: Set[int] = set()

    async def connect(self, websocket: WebSocket, user_id: int):
        """接受连接"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.online_users.add(user_id)
        print(f"用户 {user_id} 已连接 WebSocket，当前在线用户：{len(self.online_users)}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """断开连接"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    self.online_users.discard(user_id)
        print(f"用户 {user_id} 已断开 WebSocket，当前在线用户：{len(self.online_users)}")

    async def send_personal_message(self, message: dict, user_id: int):
        """向特定用户发送消息"""
        if user_id in self.active_connections:
            # 向该用户的所有连接发送消息（支持多端）
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"发送消息失败：{e}")

    async def broadcast(self, message: dict):
        """广播消息给所有在线用户"""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    def get_online_users(self) -> Set[int]:
        """获取在线用户列表"""
        return self.online_users

    def is_user_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.online_users


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket 通知连接
    客户端通过 JWT token 认证后建立连接
    """
    from app.api.auth import verify_token

    # 验证 token
    try:
        user = verify_token(token)
        if not user:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # 建立连接
    await manager.connect(websocket, user.id)

    # 发送欢迎消息
    await manager.send_personal_message({
        "type": "connected",
        "message": "连接成功",
        "user_id": user.id,
        "timestamp": datetime.now().isoformat()
    }, user.id)

    try:
        # 保持连接并处理客户端消息
        while True:
            try:
                data = await websocket.receive_text()
                # 处理客户端发送的消息（如心跳、已读确认等）
                message = json.loads(data)
                if message.get("type") == "heartbeat":
                    # 心跳响应
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif message.get("type") == "mark_read":
                    # 标记已读确认（可以在这里处理业务逻辑）
                    print(f"用户 {user.id} 确认已读通知：{message.get('notification_id')}")
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
    except Exception as e:
        print(f"WebSocket 错误：{e}")
        manager.disconnect(websocket, user.id)


async def send_notification_to_user(user_id: int, notification_data: dict):
    """
    向用户发送实时通知

    Args:
        user_id: 用户 ID
        notification_data: 通知数据
    """
    message = {
        "type": "notification",
        "data": notification_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.send_personal_message(message, user_id)


async def broadcast_notification(notification_data: dict):
    """
    广播通知给所有在线用户

    Args:
        notification_data: 通知数据
    """
    message = {
        "type": "broadcast",
        "data": notification_data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(message)


@router.get("/online-users")
def get_online_users(current_user: User = Depends(lambda: None)):
    """获取在线用户列表（用于调试）"""
    return {
        "online_users": list(manager.get_online_users()),
        "count": len(manager.get_online_users())
    }


# 工具函数：在创建通知时发送 WebSocket 消息
def notify_user_sync(user_id: int, notification_title: str, notification_content: str, notification_id: int = None):
    """
    同步方式通知用户（用于非异步上下文）
    注意：这个函数需要在一个有事件循环的上下文中调用
    """
    import asyncio

    notification_data = {
        "id": notification_id,
        "title": notification_title,
        "content": notification_content
    }

    try:
        # 尝试获取当前事件循环
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果事件循环正在运行，创建任务
            loop.create_task(send_notification_to_user(user_id, notification_data))
        else:
            # 否则运行直到完成
            loop.run_until_complete(send_notification_to_user(user_id, notification_data))
    except RuntimeError:
        # 没有事件循环，创建新的
        asyncio.run(send_notification_to_user(user_id, notification_data))
