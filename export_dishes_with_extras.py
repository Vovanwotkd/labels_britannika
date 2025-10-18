#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЭКСПОРТ ТОВАРОВ С ДОПОЛНИТЕЛЬНЫМИ ЭТИКЕТКАМИ (AddListSauce)
Использует: asyncio + aiohttp + кеширование доп. товаров
"""

import asyncio
import aiohttp
import sqlite3
import json
import time
import signal
import sys
import re
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from datetime import datetime
import logging

# ============================================================================
# НАСТРОЙКИ
# ============================================================================

# API
SH_URL = "http://10.0.0.141:9797/api/sh5exec"
SH_USER = "Admin"
SH_PASS = "776417"

# ПРОИЗВОДИТЕЛЬНОСТЬ
MAX_CONCURRENT = 300        # Параллельных запросов
REQUEST_TIMEOUT = 30        # Таймаут запроса (сек)
MAX_RETRIES = 3             # Попытки при ошибке
RETRY_DELAYS = [0.5, 1, 2]  # Задержки между попытками

# SQLite
DB_FILE = "dishes_with_extras.sqlite"
BATCH_SIZE = 500            # Размер батча для SQLite
PRAGMA_JOURNAL = "WAL"      # Write-Ahead Logging
PRAGMA_SYNC = "NORMAL"      # Баланс скорость/надёжность
PRAGMA_CACHE = 10000

# ФИЛЬТРЫ
ONLY_WITH_RKEEPER = True
EXCLUDE_SEMIFINISHED = True

# ОТКАЗОУСТОЙЧИВОСТЬ
MAX_CONSECUTIVE_ERRORS = 100
ERROR_RATE_THRESHOLD = 0.5
ERROR_RATE_PAUSE = 15
ENABLE_ADAPTIVE_THROTTLING = True
MIN_WORKERS = 25

# CHECKPOINT
ENABLE_CHECKPOINT = True
CHECKPOINT_INTERVAL = 1000
CHECKPOINT_FILE = "export_extras_checkpoint.json"

# ЛОГИРОВАНИЕ
ERROR_LOG = "export_extras_errors.log"
STATS_LOG = "export_extras_stats.log"

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

stats = {
    "total": 0,
    "processed": 0,
    "saved": 0,
    "errors": 0,
    "consecutive_errors": 0,
    "skipped": 0,
    "extra_labels_found": 0,
    "extra_labels_processed": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "start_time": 0,
    "current_workers": MAX_CONCURRENT,
}

processed_rids: Set[int] = set()
shutdown_requested = False

# Кеш для дополнительных товаров (чтобы не загружать один соус 100 раз)
extra_dishes_cache: Dict[int, Optional[Dict]] = {}

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

def setup_logging():
    """Настроить логирование"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(ERROR_LOG, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def log_error(rid: int, error: str, details: str = ""):
    """Логировать ошибку"""
    with open(ERROR_LOG, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now()}] RID={rid} | {error}\n")
        if details:
            f.write(f"  Details: {details}\n")

def log_stats():
    """Логировать статистику"""
    elapsed = time.time() - stats["start_time"]
    speed = stats["processed"] / elapsed if elapsed > 0 else 0

    with open(STATS_LOG, 'a', encoding='utf-8') as f:
        f.write(f"\n[{datetime.now()}] Статистика:\n")
        f.write(f"  Обработано: {stats['processed']}/{stats['total']}\n")
        f.write(f"  Сохранено: {stats['saved']}\n")
        f.write(f"  Ошибок: {stats['errors']}\n")
        f.write(f"  Пропущено: {stats['skipped']}\n")
        f.write(f"  Доп. этикеток найдено: {stats['extra_labels_found']}\n")
        f.write(f"  Доп. этикеток обработано: {stats['extra_labels_processed']}\n")
        f.write(f"  Cache hits: {stats['cache_hits']}\n")
        f.write(f"  Cache misses: {stats['cache_misses']}\n")
        f.write(f"  Скорость: {speed:.1f} товар/сек\n")
        f.write(f"  Воркеров: {stats['current_workers']}\n")

# ============================================================================
# CHECKPOINT СИСТЕМА
# ============================================================================

def save_checkpoint():
    """Сохранить прогресс"""
    if not ENABLE_CHECKPOINT:
        return

    checkpoint = {
        "timestamp": datetime.now().isoformat(),
        "processed_rids": list(processed_rids),
        "stats": stats.copy(),
        "cache_size": len(extra_dishes_cache),
    }

    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        logging.info(f"💾 Checkpoint сохранён: {len(processed_rids)} товаров")
    except Exception as e:
        logging.error(f"Ошибка сохранения checkpoint: {e}")

def load_checkpoint() -> Optional[Set[int]]:
    """Загрузить прогресс"""
    if not ENABLE_CHECKPOINT or not Path(CHECKPOINT_FILE).exists():
        return None

    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)

        rids = set(checkpoint.get("processed_rids", []))
        logging.info(f"📂 Checkpoint загружен: {len(rids)} товаров уже обработано")
        return rids
    except Exception as e:
        logging.error(f"Ошибка загрузки checkpoint: {e}")
        return None

# ============================================================================
# GRACEFUL SHUTDOWN
# ============================================================================

def signal_handler(sig, frame):
    """Обработчик сигнала остановки"""
    global shutdown_requested
    logging.info("\n\n⚠️  Получен сигнал остановки. Корректное завершение...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============================================================================
# SQLite
# ============================================================================

def init_database():
    """Инициализировать БД"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Оптимизация SQLite
    cursor.execute(f"PRAGMA journal_mode = {PRAGMA_JOURNAL}")
    cursor.execute(f"PRAGMA synchronous = {PRAGMA_SYNC}")
    cursor.execute(f"PRAGMA cache_size = {PRAGMA_CACHE}")
    cursor.execute("PRAGMA temp_store = MEMORY")

    # Таблица товаров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dishes (
            rid INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            rkeeper_code TEXT,
            type INTEGER,
            protein REAL,
            fat REAL,
            carbs REAL,
            calories REAL,
            weight_g REAL,
            calculated_weight_g REAL,
            technology TEXT,
            has_extra_labels INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица ингредиентов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dish_rid INTEGER NOT NULL,
            name TEXT NOT NULL,
            yield_value REAL,
            unit TEXT,
            FOREIGN KEY (dish_rid) REFERENCES dishes(rid)
        )
    """)

    # НОВАЯ ТАБЛИЦА: дополнительные этикетки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dish_extra_labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_dish_rid INTEGER NOT NULL,
            extra_dish_rid INTEGER NOT NULL,
            extra_dish_name TEXT NOT NULL,
            extra_dish_rkeeper_code TEXT,
            extra_dish_type INTEGER,
            extra_dish_protein REAL,
            extra_dish_fat REAL,
            extra_dish_carbs REAL,
            extra_dish_calories REAL,
            extra_dish_weight_g REAL,
            extra_dish_calculated_weight_g REAL,
            extra_dish_technology TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (main_dish_rid) REFERENCES dishes(rid),
            UNIQUE (main_dish_rid, extra_dish_rid)
        )
    """)

    # Таблица ингредиентов для дополнительных товаров
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extra_dish_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            extra_dish_rid INTEGER NOT NULL,
            name TEXT NOT NULL,
            yield_value REAL,
            unit TEXT,
            FOREIGN KEY (extra_dish_rid) REFERENCES dish_extra_labels(extra_dish_rid)
        )
    """)

    conn.commit()
    return conn

def create_indexes(conn: sqlite3.Connection):
    """Создать индексы (в конце)"""
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rkeeper_code ON dishes(rkeeper_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dish_name ON dishes(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_extra ON dishes(has_extra_labels)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredients_dish ON ingredients(dish_rid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_extra_labels_main ON dish_extra_labels(main_dish_rid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_extra_labels_extra ON dish_extra_labels(extra_dish_rid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_extra_ingredients ON extra_dish_ingredients(extra_dish_rid)")
    conn.commit()

def save_batch_to_db(conn: sqlite3.Connection, batch: List[Dict]):
    """Сохранить пачку товаров"""
    if not batch:
        return

    cursor = conn.cursor()

    try:
        # Сохраняем основные товары
        dishes_data = [
            (
                d["rid"], d["name"], d["rkeeper_code"], d["type"],
                d["nutrition"]["protein"], d["nutrition"]["fat"],
                d["nutrition"]["carbs"], d["nutrition"]["calories"],
                d["weight_g"], d["calculated_weight_g"], d["technology"],
                1 if d.get("extra_labels") else 0
            )
            for d in batch
        ]

        cursor.executemany("""
            INSERT OR REPLACE INTO dishes
            (rid, name, rkeeper_code, type, protein, fat, carbs, calories,
             weight_g, calculated_weight_g, technology, has_extra_labels)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dishes_data)

        # Удаляем старые ингредиенты
        rids = [d["rid"] for d in batch]
        placeholders = ','.join('?' * len(rids))
        cursor.execute(f"DELETE FROM ingredients WHERE dish_rid IN ({placeholders})", rids)

        # Сохраняем ингредиенты основных блюд
        all_ingredients = []
        for d in batch:
            for ing in d["ingredients"]:
                all_ingredients.append((
                    d["rid"], ing["name"], ing["yield"], ing["unit"]
                ))

        if all_ingredients:
            cursor.executemany("""
                INSERT INTO ingredients (dish_rid, name, yield_value, unit)
                VALUES (?, ?, ?, ?)
            """, all_ingredients)

        # Удаляем старые дополнительные этикетки
        cursor.execute(f"DELETE FROM dish_extra_labels WHERE main_dish_rid IN ({placeholders})", rids)

        # Сохраняем дополнительные этикетки
        all_extra_labels = []
        for d in batch:
            for idx, extra in enumerate(d.get("extra_labels", [])):
                all_extra_labels.append((
                    d["rid"], extra["rid"], extra["name"], extra.get("rkeeper_code"),
                    extra.get("type"), extra["nutrition"]["protein"], extra["nutrition"]["fat"],
                    extra["nutrition"]["carbs"], extra["nutrition"]["calories"],
                    extra["weight_g"], extra["calculated_weight_g"],
                    extra.get("technology"), idx
                ))

        if all_extra_labels:
            cursor.executemany("""
                INSERT INTO dish_extra_labels
                (main_dish_rid, extra_dish_rid, extra_dish_name, extra_dish_rkeeper_code,
                 extra_dish_type, extra_dish_protein, extra_dish_fat, extra_dish_carbs,
                 extra_dish_calories, extra_dish_weight_g, extra_dish_calculated_weight_g,
                 extra_dish_technology, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, all_extra_labels)

        # Удаляем старые ингредиенты дополнительных товаров
        extra_rids = [extra["rid"] for d in batch for extra in d.get("extra_labels", [])]
        if extra_rids:
            placeholders_extra = ','.join('?' * len(extra_rids))
            cursor.execute(f"DELETE FROM extra_dish_ingredients WHERE extra_dish_rid IN ({placeholders_extra})", extra_rids)

            # Сохраняем ингредиенты дополнительных товаров
            all_extra_ingredients = []
            for d in batch:
                for extra in d.get("extra_labels", []):
                    for ing in extra.get("ingredients", []):
                        all_extra_ingredients.append((
                            extra["rid"], ing["name"], ing["yield"], ing["unit"]
                        ))

            if all_extra_ingredients:
                cursor.executemany("""
                    INSERT INTO extra_dish_ingredients (extra_dish_rid, name, yield_value, unit)
                    VALUES (?, ?, ?, ?)
                """, all_extra_ingredients)

        conn.commit()
        stats["saved"] += len(batch)

    except Exception as e:
        logging.error(f"Ошибка сохранения батча: {e}")
        conn.rollback()
        raise

# ============================================================================
# API ФУНКЦИИ
# ============================================================================

async def call_procedure(session: aiohttp.ClientSession, proc_name: str,
                        inputs: List[Dict], retry: int = 0) -> Optional[Dict]:
    """Вызов процедуры SH5 с retry"""
    payload = {
        "UserName": SH_USER,
        "Password": SH_PASS,
        "procName": proc_name
    }
    if inputs:
        payload["Input"] = inputs

    try:
        async with session.post(
            SH_URL,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        ) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")

            data = await resp.json()

            if data.get("errorCode") != 0:
                raise Exception(f"SH5 error: {data.get('errMessage')}")

            return data

    except asyncio.TimeoutError:
        if retry < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAYS[retry])
            return await call_procedure(session, proc_name, inputs, retry + 1)
        raise Exception("Timeout after retries")

    except Exception as e:
        if retry < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAYS[retry])
            return await call_procedure(session, proc_name, inputs, retry + 1)
        raise

def parse_table(table: Dict) -> List[Dict]:
    """Преобразовать колоночный формат в строки"""
    fields = table.get("fields", [])
    cols = table.get("values", [])
    rec_count = table.get("recCount", 0)

    if not fields or not cols or rec_count <= 0:
        return []

    rows = []
    for i in range(rec_count):
        row = {}
        for j, field in enumerate(fields):
            if j < len(cols) and i < len(cols[j]):
                row[field] = cols[j][i]
        rows.append(row)
    return rows

def find_table(data: Dict, head: str) -> Optional[Dict]:
    """Найти таблицу по head"""
    for t in data.get("shTable", []):
        if t.get("head") == head:
            return t
    return None

async def get_goods_tree(session: aiohttp.ClientSession) -> List[Dict]:
    """Получить все товары через GoodsTree"""
    logging.info("📦 Загрузка всех товаров (GoodsTree)...")

    data = await call_procedure(session, "GoodsTree", [
        {"head": "209", "original": ["1"], "values": [[1]]}
    ])

    t210 = find_table(data, "210")
    if not t210:
        raise RuntimeError("Таблица 210 не найдена")

    goods = parse_table(t210)
    logging.info(f"✓ Загружено товаров: {len(goods)}")

    return goods

async def get_dish_details(session: aiohttp.ClientSession, rid: int) -> Dict:
    """Получить детали товара (GoodsItem)"""
    data = await call_procedure(session, "GoodsItem", [
        {"head": "210", "original": ["1"], "values": [[rid]]}
    ])

    t210 = find_table(data, "210")
    if not t210:
        return {}

    rows = parse_table(t210)
    if not rows:
        return {}

    row = rows[0]
    return {
        "protein": row.get("20"),
        "fat": row.get("21"),
        "carbs": row.get("22"),
        "calories": row.get("67"),
        "output": row.get("6\\DishOutput"),
        "technology": row.get("6\\Сompound") or row.get("6\\Compound"),
        "add_list_sauce": row.get("6\\AddListSauce"),  # НОВОЕ ПОЛЕ!
    }

async def get_dish_composition(session: aiohttp.ClientSession, rid: int) -> List[Dict]:
    """Получить состав товара (GoodsItemCompDetail)"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    data = await call_procedure(session, "GoodsItemCompDetail", [
        {
            "head": "210#1",
            "original": ["1", "106\\1", "110\\31"],
            "values": [[rid], [None], [current_date]]
        }
    ])

    t218 = find_table(data, "218")
    if not t218:
        return []

    return parse_table(t218)

def calculate_weight(composition: List[Dict]) -> float:
    """Рассчитать вес из состава"""
    total_grams = 0.0

    for ing in composition:
        parent = ing.get("218#3\\1")
        if parent is not None:
            continue

        yield_value = ing.get("53") or 0
        unit = ing.get("210\\206\\3", "")

        if not yield_value:
            continue

        try:
            yield_float = float(str(yield_value).replace(",", "."))
        except (ValueError, TypeError):
            continue

        unit_lower = unit.strip().lower()
        if unit_lower.startswith("кг") or unit_lower.startswith("kg"):
            total_grams += yield_float * 1000
        elif unit_lower.startswith("литр") or unit_lower.startswith("l"):
            total_grams += yield_float * 1000
        else:
            total_grams += yield_float

    return total_grams

def parse_add_list_sauce(value: Any) -> List[int]:
    """
    Парсить поле AddListSauce в список RID'ов
    Формат: "123, 456, 789" или "123,456,789" или "123" или пустая строка
    """
    if not value:
        return []

    # Приводим к строке
    value_str = str(value).strip()
    if not value_str:
        return []

    # Разбиваем по запятой
    parts = value_str.split(',')

    rids = []
    for part in parts:
        part = part.strip()
        if part:
            try:
                rid = int(part)
                if rid > 0:
                    rids.append(rid)
            except ValueError:
                logging.warning(f"Не удалось распарсить RID: '{part}' в AddListSauce")
                continue

    return rids

# ============================================================================
# ОБРАБОТКА ДОПОЛНИТЕЛЬНЫХ ТОВАРОВ (С КЕШИРОВАНИЕМ)
# ============================================================================

async def fetch_extra_dish(session: aiohttp.ClientSession, rid: int) -> Optional[Dict]:
    """
    Получить полные данные о дополнительном товаре
    С кешированием - если товар уже загружен, вернуть из кеша
    """
    # Проверяем кеш
    if rid in extra_dishes_cache:
        stats["cache_hits"] += 1
        return extra_dishes_cache[rid]

    stats["cache_misses"] += 1

    try:
        # Запрос 1: GoodsItem (детали)
        details = await get_dish_details(session, rid)

        # Запрос 2: GoodsItemCompDetail (состав)
        composition = await get_dish_composition(session, rid)

        # Рассчитываем вес
        calc_weight = calculate_weight(composition)

        # Собираем ингредиенты
        ingredients = []
        for ing in composition:
            if ing.get("218#3\\1") is not None:
                continue

            yield_val = ing.get("53", 0)
            try:
                yield_float = float(str(yield_val).replace(",", "."))
                if yield_float <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            ing_name = ing.get("210\\3", "")
            ing_name = re.sub(r'^ПФ\s+\d+\s+', '', ing_name)

            ingredients.append({
                "name": ing_name,
                "yield": yield_float,
                "unit": ing.get("210\\206\\3"),
            })

        result = {
            "rid": rid,
            "name": details.get("name", f"Extra dish {rid}"),
            "rkeeper_code": None,  # У дополнительных товаров обычно нет RK кода
            "type": None,
            "nutrition": {
                "protein": details.get("protein"),
                "fat": details.get("fat"),
                "carbs": details.get("carbs"),
                "calories": details.get("calories"),
            },
            "weight_g": details.get("output") or calc_weight,
            "calculated_weight_g": calc_weight,
            "ingredients": ingredients,
            "technology": details.get("technology"),
        }

        # Сохраняем в кеш
        extra_dishes_cache[rid] = result
        stats["extra_labels_processed"] += 1

        return result

    except Exception as e:
        logging.error(f"Ошибка загрузки дополнительного товара RID={rid}: {e}")
        extra_dishes_cache[rid] = None  # Кешируем неудачу чтобы не пытаться снова
        return None

# ============================================================================
# ОБРАБОТКА ТОВАРА
# ============================================================================

async def process_dish(session: aiohttp.ClientSession, goods_item: Dict,
                      semaphore: asyncio.Semaphore) -> Optional[Dict]:
    """Обработать один товар"""
    async with semaphore:
        if shutdown_requested:
            return None

        rid = goods_item.get("1")
        name = goods_item.get("3", "")
        rkeeper_code = goods_item.get("241")
        goods_type = goods_item.get("25")

        try:
            # Запрос 1: GoodsItem (детали)
            details = await get_dish_details(session, rid)

            # Запрос 2: GoodsItemCompDetail (состав)
            composition = await get_dish_composition(session, rid)

            # Рассчитываем вес
            calc_weight = calculate_weight(composition)

            # Собираем ингредиенты
            ingredients = []
            for ing in composition:
                if ing.get("218#3\\1") is not None:
                    continue

                yield_val = ing.get("53", 0)
                try:
                    yield_float = float(str(yield_val).replace(",", "."))
                    if yield_float <= 0:
                        continue
                except (ValueError, TypeError):
                    continue

                ing_name = ing.get("210\\3", "")
                ing_name = re.sub(r'^ПФ\s+\d+\s+', '', ing_name)

                ingredients.append({
                    "name": ing_name,
                    "yield": yield_float,
                    "unit": ing.get("210\\206\\3"),
                })

            # НОВОЕ: Обработка дополнительных этикеток
            extra_labels = []
            add_list_sauce = details.get("add_list_sauce")

            if add_list_sauce:
                extra_rids = parse_add_list_sauce(add_list_sauce)

                if extra_rids:
                    stats["extra_labels_found"] += len(extra_rids)
                    logging.debug(f"RID={rid} ({name}): найдено {len(extra_rids)} доп. этикеток: {extra_rids}")

                    # Загружаем данные о каждом дополнительном товаре
                    for extra_rid in extra_rids:
                        extra_data = await fetch_extra_dish(session, extra_rid)
                        if extra_data:
                            extra_labels.append(extra_data)

            # Сбрасываем счётчик последовательных ошибок
            stats["consecutive_errors"] = 0

            return {
                "rid": rid,
                "name": name,
                "rkeeper_code": rkeeper_code,
                "type": goods_type,
                "nutrition": {
                    "protein": details.get("protein"),
                    "fat": details.get("fat"),
                    "carbs": details.get("carbs"),
                    "calories": details.get("calories"),
                },
                "weight_g": details.get("output") or calc_weight,
                "calculated_weight_g": calc_weight,
                "ingredients": ingredients,
                "technology": details.get("technology"),
                "extra_labels": extra_labels,  # НОВОЕ!
            }

        except Exception as e:
            stats["errors"] += 1
            stats["consecutive_errors"] += 1
            log_error(rid, str(e), f"Name: {name}")
            return None

# ============================================================================
# АДАПТИВНАЯ РЕГУЛИРОВКА
# ============================================================================

def check_and_adjust_workers(semaphore: asyncio.Semaphore):
    """Проверить error rate и отрегулировать нагрузку"""
    if not ENABLE_ADAPTIVE_THROTTLING:
        return False

    total = stats["processed"]
    if total < 100:
        return False

    error_rate = stats["errors"] / total

    if error_rate > ERROR_RATE_THRESHOLD:
        new_workers = max(MIN_WORKERS, stats["current_workers"] // 2)
        if new_workers != stats["current_workers"]:
            stats["current_workers"] = new_workers
            logging.warning(f"⚠️  High error rate ({error_rate:.1%}). Снижаем до {new_workers} воркеров")
            return True

    elif error_rate < 0.1 and stats["current_workers"] < MAX_CONCURRENT:
        new_workers = min(MAX_CONCURRENT, stats["current_workers"] + 10)
        stats["current_workers"] = new_workers
        logging.info(f"✓ Error rate низкий. Увеличиваем до {new_workers} воркеров")

    return False

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

async def main():
    """Главная функция"""
    global shutdown_requested

    setup_logging()

    print("="*70)
    print("   ЭКСПОРТ ТОВАРОВ С ДОПОЛНИТЕЛЬНЫМИ ЭТИКЕТКАМИ (AddListSauce)")
    print("="*70)
    print(f"\n⚙️  Настройки:")
    print(f"  Параллельных запросов: {MAX_CONCURRENT}")
    print(f"  Размер батча SQLite: {BATCH_SIZE}")
    print(f"  Таймаут: {REQUEST_TIMEOUT}с")
    print(f"  Попытки при ошибке: {MAX_RETRIES}")
    print(f"  База данных: {DB_FILE}")
    print(f"  Кеширование доп. товаров: ДА")

    # Загрузить checkpoint если есть
    checkpoint_rids = load_checkpoint()
    if checkpoint_rids:
        processed_rids.update(checkpoint_rids)

    # Инициализация БД
    conn = init_database()

    # Создаём connector с пулом соединений
    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT,
        limit_per_host=50,
        ttl_dns_cache=300,
        keepalive_timeout=60
    )

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Получаем все товары
        all_goods = await get_goods_tree(session)

        # Фильтруем
        filtered_goods = []
        for g in all_goods:
            rid = g.get("1")

            # Пропускаем уже обработанные
            if rid in processed_rids:
                continue

            name = str(g.get("3", ""))
            rkeeper_code = g.get("241")

            if ONLY_WITH_RKEEPER and not rkeeper_code:
                continue

            if EXCLUDE_SEMIFINISHED and name.startswith("ПФ "):
                continue

            filtered_goods.append(g)

        stats["total"] = len(filtered_goods)
        stats["start_time"] = time.time()

        print(f"\n📊 После фильтрации: {stats['total']} товаров")
        print(f"  С кодом RKeeper: {ONLY_WITH_RKEEPER}")
        print(f"  Без полуфабрикатов: {EXCLUDE_SEMIFINISHED}")

        if checkpoint_rids:
            print(f"  Уже обработано: {len(checkpoint_rids)} (пропущено)")

        print(f"\n{'='*70}")
        print("🚀 Начинаем обработку...")
        print(f"{'='*70}\n")

        # Семафор для ограничения параллелизма
        semaphore = asyncio.Semaphore(stats["current_workers"])

        # Батч для SQLite
        batch = []

        # Создаём задачи
        tasks = [process_dish(session, item, semaphore) for item in filtered_goods]

        # Обрабатываем по мере завершения
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            if shutdown_requested:
                logging.info("🛑 Остановка по запросу пользователя...")
                break

            result = await coro

            stats["processed"] += 1

            if result:
                batch.append(result)
                processed_rids.add(result["rid"])
            else:
                stats["skipped"] += 1

            # Прогресс
            elapsed = time.time() - stats["start_time"]
            speed = stats["processed"] / elapsed if elapsed > 0 else 0
            remaining = (stats["total"] - stats["processed"]) / speed if speed > 0 else 0
            progress = stats["processed"] / stats["total"] * 100

            bar_length = 30
            filled = int(bar_length * stats["processed"] / stats["total"])
            bar = "█" * filled + "░" * (bar_length - filled)

            print(f"\r[{stats['processed']}/{stats['total']}] {bar} {progress:.1f}% | "
                  f"{speed:.1f} товар/сек | ETA: {remaining/60:.1f}мин | "
                  f"Ошибок: {stats['errors']} | Доп.этикеток: {stats['extra_labels_found']} | "
                  f"Cache: {stats['cache_hits']}/{stats['cache_hits']+stats['cache_misses']}",
                  end="", flush=True)

            # Сохраняем батч
            if len(batch) >= BATCH_SIZE:
                save_batch_to_db(conn, batch)
                batch = []

            # Checkpoint
            if ENABLE_CHECKPOINT and stats["processed"] % CHECKPOINT_INTERVAL == 0:
                save_checkpoint()
                log_stats()

            # Проверка error rate
            if stats["processed"] % 100 == 0:
                needs_pause = check_and_adjust_workers(semaphore)
                if needs_pause:
                    logging.warning(f"⏸️  Пауза {ERROR_RATE_PAUSE}с из-за высокого error rate...")
                    await asyncio.sleep(ERROR_RATE_PAUSE)

            # Проверка consecutive errors
            if stats["consecutive_errors"] >= MAX_CONSECUTIVE_ERRORS:
                logging.error(f"\n❌ КРИТИЧНО: {MAX_CONSECUTIVE_ERRORS}+ ошибок подряд. Остановка.")
                break

        # Сохраняем остатки
        if batch:
            save_batch_to_db(conn, batch)

        # Финальный checkpoint
        save_checkpoint()

    print("\n")

    # Создаём индексы
    print("📇 Создание индексов...")
    create_indexes(conn)

    # Статистика БД
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM dishes")
    total_dishes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ingredients")
    total_ingredients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM dishes WHERE rkeeper_code IS NOT NULL")
    dishes_with_rk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM dishes WHERE has_extra_labels = 1")
    dishes_with_extras = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM dish_extra_labels")
    total_extra_labels = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT extra_dish_rid) FROM dish_extra_labels")
    unique_extra_dishes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM extra_dish_ingredients")
    total_extra_ingredients = cursor.fetchone()[0]

    conn.close()

    # Финальная статистика
    elapsed_total = time.time() - stats["start_time"]

    print(f"\n{'='*70}")
    print("✅ ЭКСПОРТ ЗАВЕРШЁН!")
    print(f"{'='*70}")
    print(f"⏱️  Время: {elapsed_total/60:.1f} минут ({elapsed_total:.0f} секунд)")
    print(f"📊 Производительность: {stats['saved']/elapsed_total:.1f} товаров/секунду")
    print(f"📦 Обработано: {stats['processed']}")
    print(f"💾 Сохранено: {stats['saved']}")
    print(f"❌ Ошибок: {stats['errors']}")
    print(f"⏭️  Пропущено: {stats['skipped']}")
    print(f"\n🏷️  Дополнительные этикетки:")
    print(f"  Найдено связей: {stats['extra_labels_found']}")
    print(f"  Обработано товаров: {stats['extra_labels_processed']}")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Cache misses: {stats['cache_misses']}")
    print(f"\n📂 База данных: {DB_FILE}")
    print(f"  Товаров: {total_dishes}")
    print(f"  С кодом RKeeper: {dishes_with_rk}")
    print(f"  С доп. этикетками: {dishes_with_extras}")
    print(f"  Ингредиентов: {total_ingredients}")
    print(f"  Доп. этикеток (связей): {total_extra_labels}")
    print(f"  Уникальных доп. товаров: {unique_extra_dishes}")
    print(f"  Ингредиентов доп. товаров: {total_extra_ingredients}")
    print(f"  Средний состав: {total_ingredients/total_dishes:.1f} ингр/товар")
    print(f"{'='*70}")

    log_stats()

# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        save_checkpoint()
        print(f"💾 Прогресс сохранён. Обработано: {stats['processed']}")
    except Exception as e:
        logging.error(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        save_checkpoint()
        sys.exit(1)
