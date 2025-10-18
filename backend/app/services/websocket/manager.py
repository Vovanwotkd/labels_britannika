"""
WebSocket Manager
Управление WebSocket соединениями и broadcasting
"""

import logging
import json
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Менеджер WebSocket соединений

    Функции:
    - Управление активными соединениями
    - Broadcasting сообщений всем клиентам
    - Broadcasting с фильтрацией по комнатам (rooms)

    Использование:
    ```python
    manager = ConnectionManager()

    # Подключение клиента
    await manager.connect(websocket, user_id="operator1")

    # Broadcasting всем
    await manager.broadcast({"type": "order_update", "data": {...}})

    # Broadcasting в комнату
    await manager.broadcast_to_room("orders", {"type": "new_order", ...})

    # Отключение
    manager.disconnect(websocket)
    ```
    """

    def __init__(self):
        """Инициализация manager"""
        # Активные соединения: WebSocket -> user_id
        self.active_connections: Dict[WebSocket, str] = {}

        # Комнаты: room_name -> Set[WebSocket]
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = None):
        """
        Подключить WebSocket клиента

        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя (опционально)
        """
        await websocket.accept()
        self.active_connections[websocket] = user_id or "anonymous"

        logger.info(
            f"🔌 WebSocket connected: user={user_id or 'anonymous'}, "
            f"total={len(self.active_connections)}"
        )

        # Отправляем приветствие
        await self.send_personal_message(websocket, {
            "type": "connected",
            "message": "Successfully connected to WebSocket",
            "user_id": user_id,
        })

    def disconnect(self, websocket: WebSocket):
        """
        Отключить WebSocket клиента

        Args:
            websocket: WebSocket соединение
        """
        user_id = self.active_connections.get(websocket, "unknown")

        # Удаляем из активных соединений
        if websocket in self.active_connections:
            del self.active_connections[websocket]

        # Удаляем из всех комнат
        for room_sockets in self.rooms.values():
            room_sockets.discard(websocket)

        logger.info(
            f"🔌 WebSocket disconnected: user={user_id}, "
            f"total={len(self.active_connections)}"
        )

    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Отправить сообщение конкретному клиенту

        Args:
            websocket: WebSocket соединение
            message: Сообщение (будет сериализовано в JSON)
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"❌ Error sending personal message: {e}")
            # Отключаем клиента при ошибке
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any], exclude: WebSocket = None):
        """
        Broadcast сообщение всем подключенным клиентам

        Args:
            message: Сообщение (будет сериализовано в JSON)
            exclude: Исключить это соединение из broadcast (опционально)
        """
        logger.debug(f"📢 Broadcasting to {len(self.active_connections)} clients: {message.get('type')}")

        # Собираем отключенные соединения
        disconnected = []

        for websocket in self.active_connections.keys():
            if websocket == exclude:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"❌ Error broadcasting to client: {e}")
                disconnected.append(websocket)

        # Удаляем отключенные соединения
        for websocket in disconnected:
            self.disconnect(websocket)

    def join_room(self, websocket: WebSocket, room: str):
        """
        Добавить клиента в комнату

        Args:
            websocket: WebSocket соединение
            room: Название комнаты
        """
        if room not in self.rooms:
            self.rooms[room] = set()

        self.rooms[room].add(websocket)

        user_id = self.active_connections.get(websocket, "unknown")
        logger.debug(f"🚪 User {user_id} joined room '{room}'")

    def leave_room(self, websocket: WebSocket, room: str):
        """
        Удалить клиента из комнаты

        Args:
            websocket: WebSocket соединение
            room: Название комнаты
        """
        if room in self.rooms:
            self.rooms[room].discard(websocket)

            user_id = self.active_connections.get(websocket, "unknown")
            logger.debug(f"🚪 User {user_id} left room '{room}'")

    async def broadcast_to_room(self, room: str, message: Dict[str, Any]):
        """
        Broadcast сообщение всем клиентам в комнате

        Args:
            room: Название комнаты
            message: Сообщение (будет сериализовано в JSON)
        """
        if room not in self.rooms:
            logger.debug(f"📢 Room '{room}' is empty, skipping broadcast")
            return

        sockets = list(self.rooms[room])
        logger.debug(f"📢 Broadcasting to room '{room}' ({len(sockets)} clients): {message.get('type')}")

        disconnected = []

        for websocket in sockets:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"❌ Error broadcasting to room '{room}': {e}")
                disconnected.append(websocket)

        # Удаляем отключенные соединения
        for websocket in disconnected:
            self.disconnect(websocket)

    def get_connections_count(self) -> int:
        """Получить количество активных соединений"""
        return len(self.active_connections)

    def get_room_size(self, room: str) -> int:
        """Получить количество клиентов в комнате"""
        return len(self.rooms.get(room, set()))


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global instance (используется во всём приложении)
manager = ConnectionManager()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def broadcast_order_update(order_id: int, event_type: str, data: Dict[str, Any] = None):
    """
    Broadcast обновление заказа

    Args:
        order_id: ID заказа
        event_type: Тип события (new_order, order_updated, order_cancelled, etc.)
        data: Дополнительные данные
    """
    message = {
        "type": "order_update",
        "event": event_type,
        "order_id": order_id,
        "data": data or {},
        "timestamp": None,  # TODO: добавить timestamp
    }

    await manager.broadcast_to_room("orders", message)


async def broadcast_print_job_update(job_id: int, status: str, order_item_id: int = None):
    """
    Broadcast обновление print job

    Args:
        job_id: ID print job
        status: Новый статус (QUEUED, PRINTING, DONE, FAILED)
        order_item_id: ID order item (опционально)
    """
    message = {
        "type": "print_job_update",
        "job_id": job_id,
        "status": status,
        "order_item_id": order_item_id,
        "timestamp": None,  # TODO: добавить timestamp
    }

    await manager.broadcast_to_room("orders", message)


async def broadcast_printer_status(online: bool, error: str = None):
    """
    Broadcast статус принтера

    Args:
        online: Принтер онлайн?
        error: Сообщение об ошибке (если есть)
    """
    message = {
        "type": "printer_status",
        "online": online,
        "error": error,
        "timestamp": None,  # TODO: добавить timestamp
    }

    await manager.broadcast(message)
