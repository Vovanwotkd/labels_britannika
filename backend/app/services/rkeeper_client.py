"""
RKeeper 7 XML API Client
Модуль для работы с RKeeper API
"""
import httpx
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.setting import Setting
from ..core.database import SessionLocal

logger = logging.getLogger(__name__)


class RKeeperClient:
    """Клиент для работы с RKeeper 7 XML API"""

    def __init__(self):
        self.base_url = None
        self.username = None
        self.password = None

    def _get_setting_value(self, db: Session, key: str, default: str = "") -> str:
        """Получает значение настройки из БД"""
        setting = db.query(Setting).filter(Setting.key == key).first()
        return setting.value if setting and setting.value else default

    async def _load_config(self):
        """Загружает конфигурацию из настроек"""
        db = SessionLocal()
        try:
            self.base_url = self._get_setting_value(db, "rkeeper_url")
            self.username = self._get_setting_value(db, "rkeeper_user")
            self.password = self._get_setting_value(db, "rkeeper_pass")
        finally:
            db.close()

    async def _send_request(self, xml_body: str) -> ET.Element:
        """
        Отправляет XML запрос к RKeeper API

        Args:
            xml_body: XML тело запроса

        Returns:
            XML элемент с ответом

        Raises:
            httpx.HTTPError: При ошибке HTTP запроса
            ValueError: При ошибке в ответе RKeeper
        """
        if not self.base_url:
            await self._load_config()

        headers = {
            "Content-Type": "application/xml; charset=utf-8"
        }

        auth = None
        if self.username and self.password:
            auth = (self.username, self.password)

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                self.base_url,
                content=xml_body.encode('utf-8'),
                headers=headers,
                auth=auth
            )
            response.raise_for_status()

            # Парсим XML ответ
            root = ET.fromstring(response.content)

            # Проверяем статус ответа
            status = root.get("Status")
            if status != "Ok":
                error_text = root.get("ErrorText", "Unknown error")
                raise ValueError(f"RKeeper API error: {error_text}")

            return root

    async def get_tables(self) -> List[Dict[str, str]]:
        """
        Получает список активных столов из RKeeper

        Returns:
            Список словарей с данными столов:
            [
                {
                    "ident": "1",
                    "code": "1",
                    "name": "Киоск",
                    "status": "rsInactive",
                    "hall": "1"
                },
                ...
            ]
        """
        xml_request = '''<?xml version="1.0" encoding="UTF-8"?>
<RK7Query>
    <RK7CMD CMD="GetRefData" RefName="TABLES" PropMask="{Ident,Code,Name,Status,Hall}"/>
</RK7Query>'''

        root = await self._send_request(xml_request)

        # Извлекаем элементы столов
        tables = []
        items = root.find(".//Items")

        if items is not None:
            for item in items.findall("Item"):
                status = item.get("Status", "")

                # Фильтруем только активные столы (не удалённые и не неактивные)
                if status not in ["rsDeleted", "rsInactive"]:
                    tables.append({
                        "ident": item.get("Ident", ""),
                        "code": item.get("Code", ""),
                        "name": item.get("Name", ""),
                        "status": status,
                        "hall": item.get("Hall", "")
                    })

        return tables

    async def get_order_list(self, only_opened: bool = True) -> List[Dict[str, any]]:
        """
        Получает список заказов из RKeeper

        Args:
            only_opened: Вернуть только активные заказы (по умолчанию True)

        Returns:
            Список словарей с данными заказов:
            [
                {
                    "visit_id": str,
                    "order_ident": str,
                    "table_code": str,
                    "table_name": str,
                    "order_sum": float,
                    "total_pieces": int,
                    "paid": bool,
                    "finished": bool,
                    "create_time": datetime,
                    "finish_time": Optional[datetime],
                },
                ...
            ]
        """
        # Формируем XML запрос
        only_opened_attr = '1' if only_opened else '0'
        xml_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<RK7Query>
    <RK7CMD CMD="GetOrderList" onlyOpened="{only_opened_attr}" needIdents="1" needCodes="1" needNames="1"/>
</RK7Query>'''

        root = await self._send_request(xml_request)

        # Парсим ответ
        orders = []
        for visit_elem in root.findall(".//Visit"):
            visit_id = visit_elem.get("VisitID", "")

            # Проходим по всем заказам в визите
            orders_elem = visit_elem.find("Orders")
            if orders_elem is not None:
                for order_elem in orders_elem.findall("Order"):
                    # Получаем атрибуты заказа
                    order_ident = order_elem.get("OrderID", "")  # В GetOrderList возвращается OrderID
                    order_sum_kopeks = int(order_elem.get("OrderSum", 0))
                    order_sum = order_sum_kopeks / 100.0
                    total_pieces = int(order_elem.get("TotalPieces", 0))
                    paid = order_elem.get("Finished", "0") == "1"  # В GetOrderList нет paid, используем Finished
                    finished = order_elem.get("Finished", "0") == "1"

                    # Парсим даты
                    create_time_str = order_elem.get("CreateTime")
                    finish_time_str = order_elem.get("FinishTime")

                    create_time = None
                    if create_time_str:
                        try:
                            create_time = datetime.fromisoformat(create_time_str.replace("Z", "+00:00"))
                        except:
                            pass

                    finish_time = None
                    if finish_time_str:
                        try:
                            finish_time = datetime.fromisoformat(finish_time_str.replace("Z", "+00:00"))
                        except:
                            pass

                    # Получаем код и название стола
                    table_code = order_elem.get("TableCode", "")
                    table_name = order_elem.get("TableName", table_code)

                    orders.append({
                        "visit_id": visit_id,
                        "order_ident": order_ident,
                        "table_code": table_code,
                        "table_name": table_name,
                        "order_sum": order_sum,
                        "total_pieces": total_pieces,
                        "paid": paid,
                        "finished": finished,
                        "create_time": create_time,
                        "finish_time": finish_time,
                    })

        logger.info(f"📋 Fetched {len(orders)} orders from RKeeper")
        return orders

    async def get_order(self, visit_id: str, order_ident: str) -> Dict[str, any]:
        """
        Получает детальную информацию о заказе включая блюда

        Args:
            visit_id: ID визита
            order_ident: ID заказа

        Returns:
            Dict с полной информацией о заказе и блюдах
        """
        xml_request = f'''<?xml version="1.0" encoding="UTF-8"?>
<RK7Query>
    <RK7CMD CMD="GetOrder" visit="{visit_id}" orderIdent="{order_ident}"/>
</RK7Query>'''

        root = await self._send_request(xml_request)

        # DEBUG: Логируем полный XML ответ
        import xml.etree.ElementTree as ET
        xml_response = ET.tostring(root, encoding='unicode')
        logger.info(f"🔍 GetOrder XML response for visit={visit_id}, order={order_ident}:\n{xml_response}")

        # Парсим Order элемент
        order_elem = root.find(".//Order")
        if order_elem is None:
            raise ValueError(f"Order not found: visit={visit_id}, order={order_ident}")

        # Основная информация о заказе
        table_elem = order_elem.find("Table")
        table_code = table_elem.get("code", "") if table_elem is not None else ""
        table_name = table_elem.get("name", table_code) if table_elem is not None else table_code

        order_sum_kopeks = int(order_elem.get("orderSum", 0))
        order_sum = order_sum_kopeks / 100.0

        total_pieces = int(order_elem.get("totalPieces", 0))
        paid = order_elem.get("paid", "0") == "1"
        finished = order_elem.get("finished", "0") == "1"

        # Собираем блюда из Session
        dishes = []
        session_elem = order_elem.find(".//Session")
        if session_elem is not None:
            for dish_elem in session_elem.findall("Dish"):
                dish_id = dish_elem.get("id", "")
                dish_code = dish_elem.get("code", "")
                dish_name = dish_elem.get("name", "")
                quantity_g = int(dish_elem.get("quantity", 0))
                quantity = quantity_g // 1000  # Конвертируем граммы в порции (1000г = 1 порция)

                logger.info(
                    f"📦 GetOrder dish parsed: name='{dish_name}', code={dish_code}, "
                    f"quantity_raw={quantity_g}, quantity_portions={quantity}"
                )

                dishes.append({
                    "dish_id": dish_id,
                    "dish_code": dish_code,
                    "dish_name": dish_name,
                    "quantity": quantity,
                    "quantity_g": quantity_g,  # Сохраняем граммы для renderer
                })

        return {
            "visit_id": visit_id,
            "order_ident": order_ident,
            "table_code": table_code,
            "table_name": table_name,
            "order_sum": order_sum,
            "total_pieces": total_pieces,
            "paid": paid,
            "finished": finished,
            "dishes": dishes,
        }


# Singleton instance
_rkeeper_client = None


def get_rkeeper_client() -> RKeeperClient:
    """Возвращает singleton инстанс RKeeper клиента"""
    global _rkeeper_client
    if _rkeeper_client is None:
        _rkeeper_client = RKeeperClient()
    return _rkeeper_client
