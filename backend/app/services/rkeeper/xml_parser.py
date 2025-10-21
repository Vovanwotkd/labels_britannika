"""
RKeeper XML Parser
Парсер XML webhook от RKeeper (новый формат событий)
"""

import logging
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET
from datetime import datetime

logger = logging.getLogger(__name__)


class RKeeperXMLParser:
    """
    Парсер XML webhook от RKeeper (новый формат)

    RKeeper отправляет события в формате:
    ```xml
    <a name="Order Changed" DateTime="..." Situation="3" ...>
        <Order visit="617707056" orderIdent="256" ...>
            <Table id="1011163" code="5" name="5"/>
            <Waiter id="1000634" code="7764" name="Ассар"/>
            <Session uni="101" ...>
                <Dish id="1004496" code="2714" name="..." uni="4" quantity="1000" price="29800"/>
            </Session>
        </Order>
        <ChangeLog>
            <Dish id="1004496" code="2714" uni="4" oldvalue="0" newvalue="1000" new="1"/>
        </ChangeLog>
    </a>
    ```

    События (name):
    - "New Order" - создание нового заказа
    - "Open Order" - открытие существующего заказа
    - "Order Changed" - изменение заказа (добавление/удаление блюд)
    - "Save Order" - сохранение заказа (закрытие сессии)
    - "Quit Order" - выход из заказа/закрытие
    - "Order recalc" - пересчет заказа

    ChangeLog содержит изменения:
    - oldvalue="0" newvalue="1000" new="1" - добавлено блюдо
    - oldvalue="1000" newvalue="0" - удалено блюдо
    - oldvalue="1000" newvalue="2000" - изменено количество
    """

    def parse(self, xml_data: str) -> Optional[Dict]:
        """
        Парсить XML webhook от RKeeper

        Args:
            xml_data: XML строка от RKeeper

        Returns:
            {
                "event_type": str,  # "New Order", "Order Changed", "Save Order", "Quit Order"
                "visit_id": str,
                "order_ident": str,
                "table_code": str,
                "table_name": str,
                "waiter_code": Optional[str],
                "waiter_name": Optional[str],
                "order_sum": float,  # Общая сумма заказа
                "paid": bool,  # Оплачен ли заказ
                "finished": bool,  # Завершен ли заказ
                "changes": [  # Изменения из ChangeLog
                    {
                        "rk_code": str,
                        "rk_id": str,
                        "name": str,
                        "uni": int,
                        "old_quantity": int,  # Старое количество порций
                        "new_quantity": int,  # Новое количество порций
                        "delta": int,  # Изменение (+1, -1, +2 и т.д.)
                        "price": float,
                        "is_new": bool,  # True если блюдо только добавлено
                        "is_deleted": bool,  # True если блюдо удалено
                    }
                ]
            }
            или None при ошибке
        """
        try:
            # Парсим XML
            root = ET.fromstring(xml_data)

            # Получаем тип события
            event_type = root.get('name', '')
            if not event_type:
                logger.error("Атрибут 'name' не найден в корневом элементе")
                return None

            logger.info(f"📨 RKeeper event: {event_type}")

            # Получаем Order
            order_elem = root.find('Order')
            if order_elem is None:
                logger.warning(f"⚠️ Элемент <Order> не найден для события '{event_type}'")
                # Некоторые события могут не содержать Order (например чисто служебные)
                return None

            visit_id = order_elem.get('visit', '')
            order_ident = order_elem.get('orderIdent', '')
            order_sum_kopeks = int(order_elem.get('orderSum', 0))
            order_sum = order_sum_kopeks / 100.0
            paid = order_elem.get('paid', '0') == '1'
            finished = order_elem.get('finished', '0') == '1'

            if not visit_id or not order_ident:
                logger.error("visit_id или order_ident отсутствуют")
                return None

            # Получаем Table
            table_elem = order_elem.find('Table')
            table_code = table_elem.get('code', '') if table_elem is not None else ''
            table_name = table_elem.get('name', table_code) if table_elem is not None else ''

            # Получаем Waiter (опционально)
            waiter_elem = order_elem.find('Waiter')
            waiter_code = waiter_elem.get('code') if waiter_elem is not None else None
            waiter_name = waiter_elem.get('name') if waiter_elem is not None else None

            # Парсим изменения из ChangeLog
            changes = self._parse_changelog(root, order_elem)

            result = {
                "event_type": event_type,
                "visit_id": visit_id,
                "order_ident": order_ident,
                "table_code": table_code,
                "table_name": table_name,
                "waiter_code": waiter_code,
                "waiter_name": waiter_name,
                "order_sum": order_sum,
                "paid": paid,
                "finished": finished,
                "changes": changes,
            }

            logger.info(
                f"✅ Parsed: event={event_type}, visit={visit_id}, order={order_ident}, "
                f"table={table_code}, changes={len(changes)}, sum={order_sum:.2f}₽, "
                f"paid={paid}, finished={finished}"
            )

            return result

        except ET.ParseError as e:
            logger.error(f"❌ XML parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing RKeeper XML: {e}", exc_info=True)
            return None

    def _parse_changelog(self, root: ET.Element, order_elem: ET.Element) -> List[Dict]:
        """
        Парсить изменения из ChangeLog

        Args:
            root: Корневой элемент <a>
            order_elem: Элемент <Order>

        Returns:
            Список изменений блюд
        """
        changes = []

        # Ищем ChangeLog
        changelog_elem = root.find('ChangeLog')
        if changelog_elem is None:
            # Нет изменений
            return changes

        # Парсим все Dish элементы в ChangeLog
        for dish_change in changelog_elem.findall('Dish'):
            rk_id = dish_change.get('id', '')
            rk_code = dish_change.get('code', rk_id)
            name = dish_change.get('name', '')
            uni = int(dish_change.get('uni', 0))

            # Старое и новое значение (в граммах)
            old_value_g = int(dish_change.get('oldvalue', 0))
            new_value_g = int(dish_change.get('newvalue', 0))

            # Количество порций (1000г = 1 порция)
            old_quantity = old_value_g // 1000
            new_quantity = new_value_g // 1000
            delta = new_quantity - old_quantity

            # Цена в рублях
            price_kopeks = int(dish_change.get('price', 0))
            price = price_kopeks / 100.0

            # Флаги
            is_new = dish_change.get('new') == '1'
            is_deleted = (new_value_g == 0 and old_value_g > 0)

            # Если нет имени в ChangeLog, ищем в Order/Session
            if not name:
                name = self._find_dish_name(order_elem, uni)

            change = {
                "rk_code": rk_code,
                "rk_id": rk_id,
                "name": name,
                "uni": uni,
                "old_quantity": old_quantity,
                "new_quantity": new_quantity,
                "delta": delta,
                "price": price,
                "is_new": is_new,
                "is_deleted": is_deleted,
            }

            changes.append(change)

            # Логируем для отладки
            action_str = "➕ ADD" if is_new else ("➖ DELETE" if is_deleted else "🔄 CHANGE")
            logger.debug(
                f"{action_str} dish: uni={uni}, code={rk_code}, "
                f"qty: {old_quantity}→{new_quantity} (Δ{delta:+d}), "
                f"price={price:.2f}₽"
            )

        return changes

    def _find_dish_name(self, order_elem: ET.Element, uni: int) -> str:
        """
        Найти название блюда по uni в Order/Session

        Args:
            order_elem: Элемент <Order>
            uni: Уникальный номер позиции

        Returns:
            Название блюда или пустая строка
        """
        # Ищем все Session/Dish с данным uni
        for session in order_elem.findall('.//Session'):
            for dish in session.findall('Dish'):
                dish_uni = int(dish.get('uni', 0))
                if dish_uni == uni:
                    return dish.get('name', '')

        return ''


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_rkeeper_xml(xml_data: str) -> Optional[Dict]:
    """
    Удобная функция для парсинга RKeeper XML

    Args:
        xml_data: XML строка

    Returns:
        Parsed data или None
    """
    parser = RKeeperXMLParser()
    return parser.parse(xml_data)
