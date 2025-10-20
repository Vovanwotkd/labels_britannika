"""
RKeeper 7 XML API Client
Модуль для работы с RKeeper API
"""
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..models.setting import Setting
from ..core.database import SessionLocal


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


# Singleton instance
_rkeeper_client = None


def get_rkeeper_client() -> RKeeperClient:
    """Возвращает singleton инстанс RKeeper клиента"""
    global _rkeeper_client
    if _rkeeper_client is None:
        _rkeeper_client = RKeeperClient()
    return _rkeeper_client
