"""
RKeeper XML Parser
Парсер XML webhook от RKeeper
"""

import logging
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET
from datetime import datetime

logger = logging.getLogger(__name__)


class RKeeperXMLParser:
    """
    Парсер XML webhook от RKeeper

    Формат webhook:
    ```xml
    <RK7Query>
        <a name="Save Order">
            <Order visit="123456" orderIdent="7890">
                <Table code="101" name="Стол 1"/>
                <Waiter code="5" name="Иван"/>
                <Session>
                    <Dish id="2538" code="2538" name="Борщ" uni="1" quantity="1000" price="45000"/>
                    <Dish id="2539" code="2539" name="Котлета" uni="2" quantity="2000" price="35000">
                        <Modi id="123" name="С гарниром"/>
                    </Dish>
                </Session>
                <ChangeLog>
                    <Dish id="2538" uni="1" oldvalue="0" newvalue="1000" price="45000"/>
                    <Dish id="2539" uni="2" oldvalue="0" newvalue="2000" price="35000"/>
                    <Modi id="123"/>
                </ChangeLog>
            </Order>
        </a>
    </RK7Query>
    ```

    Параметры:
    - visit: ID визита (заказа в RKeeper)
    - orderIdent: Идентификатор заказа
    - code: Код блюда в RKeeper
    - quantity: Количество в граммах (1000 = 1 порция)
    - price: Цена в копейках (45000 = 450 руб)
    - uni: Уникальный номер позиции в заказе
    """

    def parse(self, xml_data: str) -> Optional[Dict]:
        """
        Парсить XML webhook от RKeeper

        Args:
            xml_data: XML строка от RKeeper

        Returns:
            {
                "action": str,  # "Save Order", "Print Receipt", etc.
                "visit_id": str,
                "order_ident": str,
                "table_code": str,
                "table_name": str,
                "waiter_code": Optional[str],
                "waiter_name": Optional[str],
                "items": [
                    {
                        "rk_code": str,  # Код блюда в RKeeper
                        "rk_id": str,    # ID блюда в RKeeper
                        "name": str,
                        "uni": int,      # Уникальный номер позиции
                        "quantity": int,  # Количество порций
                        "price": float,  # Цена в рублях
                        "modifier_id": Optional[str],
                        "modifier_name": Optional[str],
                    }
                ],
                "prepay": Optional[float],  # Предоплата в рублях
                "discount": Optional[float],  # Скидка в рублях
            }
            или None при ошибке
        """
        try:
            # Парсим XML
            root = ET.fromstring(xml_data)

            # Получаем action
            action_elem = root.find('.//a')
            if action_elem is None:
                logger.error("Элемент <a> не найден в XML")
                return None

            action = action_elem.get('name', '')

            # Получаем Order
            order_elem = action_elem.find('Order')
            if order_elem is None:
                logger.error("Элемент <Order> не найден в XML")
                return None

            visit_id = order_elem.get('visit', '')
            order_ident = order_elem.get('orderIdent', '')

            # Получаем Table
            table_elem = order_elem.find('Table')
            table_code = table_elem.get('code', '') if table_elem is not None else ''
            table_name = table_elem.get('name', '') if table_elem is not None else ''

            # Получаем Waiter (опционально)
            waiter_elem = order_elem.find('Waiter')
            waiter_code = waiter_elem.get('code') if waiter_elem is not None else None
            waiter_name = waiter_elem.get('name') if waiter_elem is not None else None

            # Парсим items из Session
            items = self._parse_items(order_elem)

            # Парсим Prepay (предоплата)
            prepay = self._parse_prepay(action_elem)

            # Парсим Discount (скидка)
            discount = self._parse_discount(order_elem)

            result = {
                "action": action,
                "visit_id": visit_id,
                "order_ident": order_ident,
                "table_code": table_code,
                "table_name": table_name,
                "waiter_code": waiter_code,
                "waiter_name": waiter_name,
                "items": items,
                "prepay": prepay,
                "discount": discount,
            }

            logger.info(
                f"✅ Parsed RKeeper XML: action={action}, visit={visit_id}, "
                f"order={order_ident}, table={table_code}, items={len(items)}"
            )

            return result

        except ET.ParseError as e:
            logger.error(f"❌ XML parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing RKeeper XML: {e}", exc_info=True)
            return None

    def _parse_items(self, order_elem: ET.Element) -> List[Dict]:
        """
        Парсить items из Session

        Args:
            order_elem: Элемент <Order>

        Returns:
            Список items
        """
        items = []

        # Ищем все Session элементы
        sessions = order_elem.findall('.//Session')

        for session in sessions:
            # Ищем все Dish элементы
            dishes = session.findall('Dish')

            for dish in dishes:
                rk_id = dish.get('id', '')
                rk_code = dish.get('code', rk_id)  # code может отсутствовать, используем id
                name = dish.get('name', '')
                uni = int(dish.get('uni', 0))
                quantity_g = int(dish.get('quantity', 0))  # В граммах (1000 = 1 порция)
                price_kopeks = int(dish.get('price', 0))  # В копейках

                # Количество порций (1000г = 1 порция)
                quantity = quantity_g // 1000

                # Цена в рублях
                price = price_kopeks / 100.0

                # Модификатор (опционально)
                modifier_elem = dish.find('Modi')
                modifier_id = modifier_elem.get('id') if modifier_elem is not None else None
                modifier_name = modifier_elem.get('name') if modifier_elem is not None else None

                items.append({
                    "rk_code": rk_code,
                    "rk_id": rk_id,
                    "name": name,
                    "uni": uni,
                    "quantity": quantity,
                    "price": price,
                    "modifier_id": modifier_id,
                    "modifier_name": modifier_name,
                })

        return items

    def _parse_prepay(self, action_elem: ET.Element) -> Optional[float]:
        """
        Парсить Prepay (предоплату)

        Args:
            action_elem: Элемент <a>

        Returns:
            Предоплата в рублях или None
        """
        prepay_elem = action_elem.find('.//ChangeLog/Prepay')

        if prepay_elem is not None:
            amount_kopeks = int(prepay_elem.get('amount', 0))
            return amount_kopeks / 100.0

        return None

    def _parse_discount(self, order_elem: ET.Element) -> Optional[float]:
        """
        Парсить Discount (скидку)

        Args:
            order_elem: Элемент <Order>

        Returns:
            Скидка в рублях или None
        """
        # Скидка может быть в Session/Discount
        discount_elem = order_elem.find('.//Session/Discount')

        if discount_elem is not None:
            amount_kopeks = int(discount_elem.get('amount', 0))
            return abs(amount_kopeks) / 100.0  # Модуль, т.к. может быть отрицательной

        return None


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
