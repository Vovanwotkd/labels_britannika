"""
WebSocket API
Real-time обновления для UI
"""

import logging
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None),
    room: Optional[str] = Query("orders"),
):
    """
    WebSocket endpoint для real-time обновлений

    Query параметры:
    - user_id: ID пользователя (опционально)
    - room: Комната для подписки (по умолчанию "orders")

    Поддерживаемые комнаты:
    - "orders" - обновления заказов
    - "printer" - статус принтера
    - "all" - все события

    Формат сообщений от сервера:
    ```json
    {
        "type": "order_update",
        "event": "new_order",
        "order_id": 123,
        "data": {...}
    }
    ```

    ```json
    {
        "type": "print_job_update",
        "job_id": 456,
        "status": "DONE",
        "order_item_id": 789
    }
    ```

    ```json
    {
        "type": "printer_status",
        "online": true,
        "error": null
    }
    ```

    Формат сообщений от клиента:
    ```json
    {
        "action": "ping"
    }
    ```

    ```json
    {
        "action": "join_room",
        "room": "printer"
    }
    ```

    ```json
    {
        "action": "leave_room",
        "room": "printer"
    }
    ```
    """
    # Подключаем клиента
    await manager.connect(websocket, user_id=user_id)

    # Добавляем в комнату
    if room:
        manager.join_room(websocket, room)

    try:
        while True:
            # Ждём сообщений от клиента
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_client_message(websocket, message)
            except json.JSONDecodeError:
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": "Invalid JSON"
                })
            except Exception as e:
                logger.error(f"❌ Error handling client message: {e}", exc_info=True)
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"🔌 WebSocket disconnected: user={user_id}")


async def handle_client_message(websocket: WebSocket, message: dict):
    """
    Обработать сообщение от клиента

    Args:
        websocket: WebSocket соединение
        message: Parsed JSON message
    """
    action = message.get("action")

    if action == "ping":
        # Pong
        await manager.send_personal_message(websocket, {
            "type": "pong",
            "timestamp": None,  # TODO: добавить timestamp
        })

    elif action == "join_room":
        # Присоединиться к комнате
        room = message.get("room")
        if room:
            manager.join_room(websocket, room)
            await manager.send_personal_message(websocket, {
                "type": "room_joined",
                "room": room,
            })
        else:
            await manager.send_personal_message(websocket, {
                "type": "error",
                "message": "Room name required"
            })

    elif action == "leave_room":
        # Покинуть комнату
        room = message.get("room")
        if room:
            manager.leave_room(websocket, room)
            await manager.send_personal_message(websocket, {
                "type": "room_left",
                "room": room,
            })
        else:
            await manager.send_personal_message(websocket, {
                "type": "error",
                "message": "Room name required"
            })

    elif action == "get_stats":
        # Статистика соединений
        await manager.send_personal_message(websocket, {
            "type": "stats",
            "total_connections": manager.get_connections_count(),
            "rooms": {
                "orders": manager.get_room_size("orders"),
                "printer": manager.get_room_size("printer"),
            }
        })

    else:
        await manager.send_personal_message(websocket, {
            "type": "error",
            "message": f"Unknown action: {action}"
        })


# ============================================================================
# HELPER ENDPOINT (для тестирования)
# ============================================================================

@router.post("/test/broadcast")
async def test_broadcast(message: str = "Test message", room: Optional[str] = None):
    """
    Тестовый endpoint для broadcasting

    Args:
        message: Сообщение для broadcast
        room: Комната (если None - broadcast всем)
    """
    payload = {
        "type": "test",
        "message": message,
    }

    if room:
        await manager.broadcast_to_room(room, payload)
        return {
            "status": "ok",
            "message": f"Broadcasted to room '{room}'",
            "clients": manager.get_room_size(room)
        }
    else:
        await manager.broadcast(payload)
        return {
            "status": "ok",
            "message": "Broadcasted to all clients",
            "clients": manager.get_connections_count()
        }
