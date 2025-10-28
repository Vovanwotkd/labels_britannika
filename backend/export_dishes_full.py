#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ПОЛНЫЙ ЭКСПОРТ ТОВАРОВ С ИЕРАРХИЕЙ ГРУПП И ДОПОЛНИТЕЛЬНЫМИ ЭТИКЕТКАМИ
Вариант 2: Полная база + многоуровневая иерархия групп + фильтр в UI
Использует: GGroupsTree + asyncio + aiohttp + кеширование
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
MAX_CONCURRENT = 100
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAYS = [0.5, 1, 2]

# SQLite
DB_FILE = "/app/data/dishes_full.sqlite"  # В Docker volume
BATCH_SIZE = 500
PRAGMA_JOURNAL = "WAL"
PRAGMA_SYNC = "NORMAL"
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
CHECKPOINT_FILE = "export_full_checkpoint.json"

# ЛОГИРОВАНИЕ
ERROR_LOG = "export_full_errors.log"
STATS_LOG = "export_full_stats.log"

# ИЕРАРХИЯ ГРУПП
MAX_GROUP_LEVELS = 6  # Максимум уровней иерархии для сохранения

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
    "unique_groups": 0,
    "max_hierarchy_depth": 0,
    "start_time": 0,
    "current_workers": MAX_CONCURRENT,
}

processed_rids: Set[int] = set()
shutdown_requested = False
extra_dishes_cache: Dict[int, Optional[Dict]] = {}

# Дерево групп (загружается один раз)
groups_dict: Dict[int, Dict] = {}

# ============================================================================
# ЗАГРУЗКА НАСТРОЕК ИЗ БД
# ============================================================================

def load_settings_from_db():
    """
    Загрузить настройки StoreHouse из SQLite БД backend
    Возвращает tuple: (sh_url, sh_user, sh_pass)
    """
    import os

    # Путь к БД backend (монтируется в docker как volume)
    db_path = os.environ.get("BACKEND_DB_PATH", "/app/data/britannica_labels.db")

    # Если файл не существует, используем fallback
    if not Path(db_path).exists():
        logging.warning(f"[WARN] DB not found at {db_path}, using defaults")
        return SH_URL, SH_USER, SH_PASS

    try:
        # Подключаемся к SQLite БД backend
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()

        # Получаем настройки из таблицы settings
        cursor.execute("SELECT key, value FROM settings WHERE key IN ('sh5_url', 'sh5_user', 'sh5_pass')")
        rows = cursor.fetchall()
        settings = dict(rows)

        cursor.close()
        conn.close()

        sh_url = settings.get('sh5_url', '').strip() or SH_URL
        sh_user = settings.get('sh5_user', '').strip() or SH_USER
        sh_pass = settings.get('sh5_pass', '').strip() or SH_PASS

        if settings:
            logging.info("[OK] StoreHouse settings loaded from DB")
            logging.info(f"   URL: {sh_url}")
            logging.info(f"   User: {sh_user}")
        else:
            logging.warning("[WARN] Settings not found in DB, using defaults")

        return sh_url, sh_user, sh_pass

    except Exception as e:
        logging.error(f"[ERROR] Failed to load settings from DB: {e}")
        logging.warning("[WARN] Using default values")
        return SH_URL, SH_USER, SH_PASS

def update_sync_timestamp():
    """
    Обновить время последней синхронизации в БД backend
    """
    import os
    from datetime import datetime

    db_path = os.environ.get("BACKEND_DB_PATH", "/app/data/britannica_labels.db")

    if not Path(db_path).exists():
        logging.warning(f"[WARN] Cannot update sync timestamp: DB not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()

        # Получаем текущее время в ISO формате
        now = datetime.now().isoformat()

        # Проверяем существует ли запись
        cursor.execute("SELECT COUNT(*) FROM settings WHERE key = 'sh5_sync_last'")
        exists = cursor.fetchone()[0] > 0

        if exists:
            # Обновляем существующую запись
            cursor.execute("UPDATE settings SET value = ? WHERE key = 'sh5_sync_last'", (now,))
        else:
            # Создаём новую запись
            cursor.execute("INSERT INTO settings (key, value) VALUES ('sh5_sync_last', ?)", (now,))

        # Очищаем ошибку если была
        cursor.execute("UPDATE settings SET value = NULL WHERE key = 'sh5_sync_error'")

        conn.commit()
        cursor.close()
        conn.close()

        logging.info(f"[OK] Updated sh5_sync_last: {now}")
        print(f"[OK] Sync timestamp updated: {now}")

    except Exception as e:
        logging.error(f"[ERROR] Failed to update sync timestamp: {e}")
        print(f"[ERROR] Failed to update sync timestamp: {e}")

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
        f.write(f"  Уникальных групп: {stats['unique_groups']}\n")
        f.write(f"  Макс. глубина иерархии: {stats['max_hierarchy_depth']}\n")
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
        logging.info(f"[CHECKPOINT] Saved: {len(processed_rids)} items")
    except Exception as e:
        logging.error(f"Checkpoint save error: {e}")

def load_checkpoint() -> Optional[Set[int]]:
    """Загрузить прогресс"""
    if not ENABLE_CHECKPOINT or not Path(CHECKPOINT_FILE).exists():
        return None

    try:
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)

        rids = set(checkpoint.get("processed_rids", []))
        logging.info(f"[CHECKPOINT] Loaded: {len(rids)} items already processed")
        return rids
    except Exception as e:
        logging.error(f"Checkpoint load error: {e}")
        return None

# ============================================================================
# GRACEFUL SHUTDOWN
# ============================================================================

def signal_handler(sig, frame):
    """Обработчик сигнала остановки"""
    global shutdown_requested
    logging.info("\n\n[WARN] Shutdown signal received. Graceful shutdown...")
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

    # Таблица товаров (с многоуровневой иерархией!)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS dishes (
            rid INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            rkeeper_code TEXT,
            type INTEGER,

            -- Многоуровневая иерархия групп (до {MAX_GROUP_LEVELS} уровней)
            level_1_rid INTEGER,
            level_1_name TEXT,
            level_2_rid INTEGER,
            level_2_name TEXT,
            level_3_rid INTEGER,
            level_3_name TEXT,
            level_4_rid INTEGER,
            level_4_name TEXT,
            level_5_rid INTEGER,
            level_5_name TEXT,
            level_6_rid INTEGER,
            level_6_name TEXT,

            -- Для совместимости (последний уровень)
            group_rid INTEGER,
            group_name TEXT,

            -- Данные товара
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

    # Таблица дополнительных этикеток
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

    # Таблица настроек приложения
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    return conn

def create_indexes(conn: sqlite3.Connection):
    """Создать индексы (в конце)"""
    cursor = conn.cursor()

    # Индексы для поиска товаров
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rkeeper_code ON dishes(rkeeper_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dish_name ON dishes(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_has_extra ON dishes(has_extra_labels)")

    # Индексы для уровней иерархии
    for level in range(1, MAX_GROUP_LEVELS + 1):
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_level_{level}_name ON dishes(level_{level}_name)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_level_{level}_rid ON dishes(level_{level}_rid)")

    # Комбинированные индексы (для фильтрации по ресторану + группе)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rk_level1 ON dishes(rkeeper_code, level_1_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rk_level2 ON dishes(rkeeper_code, level_2_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_level1_level2 ON dishes(level_1_name, level_2_name)")

    # Индексы для связанных таблиц
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
        # Сохраняем основные товары (с иерархией!)
        dishes_data = []
        for d in batch:
            hierarchy = d.get("hierarchy", {})

            row = [
                d["rid"], d["name"], d["rkeeper_code"], d["type"],
            ]

            # Добавляем все уровни иерархии
            for level in range(1, MAX_GROUP_LEVELS + 1):
                level_data = hierarchy.get(f"level_{level}", {})
                row.append(level_data.get("rid"))
                row.append(level_data.get("name"))

            # Для совместимости
            row.extend([
                d.get("group_rid"),
                d.get("group_name"),
                d["nutrition"]["protein"],
                d["nutrition"]["fat"],
                d["nutrition"]["carbs"],
                d["nutrition"]["calories"],
                d["weight_g"],
                d["calculated_weight_g"],
                d["technology"],
                1 if d.get("extra_labels") else 0
            ])

            dishes_data.append(tuple(row))

        # Генерируем SQL с правильным количеством placeholder
        level_fields = ", ".join([f"level_{i}_rid, level_{i}_name" for i in range(1, MAX_GROUP_LEVELS + 1)])
        placeholders = ", ".join(["?"] * (4 + MAX_GROUP_LEVELS * 2 + 10))

        cursor.executemany(f"""
            INSERT OR REPLACE INTO dishes
            (rid, name, rkeeper_code, type,
             {level_fields},
             group_rid, group_name,
             protein, fat, carbs, calories,
             weight_g, calculated_weight_g, technology, has_extra_labels)
            VALUES ({placeholders})
        """, dishes_data)

        # Удаляем старые ингредиенты
        rids = [d["rid"] for d in batch]
        placeholders_rids = ','.join('?' * len(rids))
        cursor.execute(f"DELETE FROM ingredients WHERE dish_rid IN ({placeholders_rids})", rids)

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
        cursor.execute(f"DELETE FROM dish_extra_labels WHERE main_dish_rid IN ({placeholders_rids})", rids)

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

async def get_groups_tree(session: aiohttp.ClientSession) -> Dict[int, Dict]:
    """
    Получить дерево товарных групп через GGroupsTree
    Возвращает словарь: {group_rid: {name, parent_rid, parent_name}}
    """
    logging.info("[GROUPS] Loading groups tree (GGroupsTree)...")

    data = await call_procedure(session, "GGroupsTree", [
        {"head": "209#1", "original": ["1"], "values": [[1]]}  # Root group
    ])

    t209 = find_table(data, "209")
    if not t209:
        logging.warning("Таблица 209 не найдена в GGroupsTree")
        return {}

    groups = parse_table(t209)
    groups_dict = {}

    for group in groups:
        rid = group.get("1")
        name = group.get("3")
        parent_rid = group.get("209#1\\1")
        parent_name = group.get("209#1\\3")

        if rid:
            groups_dict[rid] = {
                "rid": rid,
                "name": name or f"Group {rid}",
                "parent_rid": parent_rid,
                "parent_name": parent_name,
            }

    logging.info(f"[OK] Loaded groups: {len(groups_dict)}")
    return groups_dict

def build_group_hierarchy(group_rid: int, groups_dict: Dict[int, Dict]) -> Dict:
    """
    Построить иерархию от корня до указанной группы
    Возвращает: {
        "level_1": {"rid": ..., "name": ...},
        "level_2": {"rid": ..., "name": ...},
        ...
    }
    """
    if not group_rid or group_rid not in groups_dict:
        return {}

    # Собираем путь от товара к корню
    path = []
    current_rid = group_rid
    max_iterations = 20  # Защита от зацикливания

    for _ in range(max_iterations):
        if not current_rid or current_rid == 1:  # Корень
            break

        group_info = groups_dict.get(current_rid)
        if not group_info:
            break

        path.append({
            "rid": current_rid,
            "name": group_info["name"]
        })

        # Переходим к родителю
        current_rid = group_info.get("parent_rid")

    # Разворачиваем (от корня к товару)
    path.reverse()

    # Формируем словарь с уровнями
    hierarchy = {}
    for level, group_info in enumerate(path, start=1):
        if level <= MAX_GROUP_LEVELS:
            hierarchy[f"level_{level}"] = group_info

    return hierarchy

async def get_goods_tree(session: aiohttp.ClientSession) -> List[Dict]:
    """Получить все товары через GoodsTree"""
    logging.info("[GOODS] Loading all goods (GoodsTree)...")

    data = await call_procedure(session, "GoodsTree", [
        {"head": "209", "original": ["1"], "values": [[1]]}
    ])

    t210 = find_table(data, "210")
    if not t210:
        raise RuntimeError("Table 210 not found")

    goods = parse_table(t210)
    logging.info(f"[OK] Loaded goods: {len(goods)}")

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
        "add_list_sauce": row.get("6\\AddListSauce"),
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
    """Парсить поле AddListSauce в список RID'ов"""
    if not value:
        return []

    value_str = str(value).strip()
    if not value_str:
        return []

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
    """Получить полные данные о дополнительном товаре (с кешированием)"""
    if rid in extra_dishes_cache:
        stats["cache_hits"] += 1
        return extra_dishes_cache[rid]

    stats["cache_misses"] += 1

    try:
        details = await get_dish_details(session, rid)
        composition = await get_dish_composition(session, rid)
        calc_weight = calculate_weight(composition)

        # Собираем ингредиенты (АГРЕГИРОВАННЫЕ базовые ингредиенты)
        from collections import defaultdict

        # Шаг 1: Находим все RID'ы, которые являются родителями
        parent_rids = set()
        for ing in composition:
            parent_rid = ing.get("218#3\\1")
            if parent_rid is not None:
                parent_rids.add(parent_rid)

        # Шаг 2: Берём только листья и агрегируем по названиям
        aggregated = defaultdict(lambda: {"yield": 0.0, "unit": ""})

        for ing in composition:
            # Получаем RID этого ингредиента
            ingredient_rid = ing.get("1")

            # Если этот RID является родителем - пропускаем
            if ingredient_rid in parent_rids:
                continue

            # Используем поле "9" (количество) вместо "53" (выход)
            yield_val = ing.get("9", 0)
            try:
                yield_float = float(str(yield_val).replace(",", "."))
                if yield_float <= 0:
                    continue
            except (ValueError, TypeError):
                continue

            ing_name = ing.get("210\\3", "")
            ing_name = re.sub(r'^ПФ\s+\d+\s+', '', ing_name)

            unit = ing.get("210\\206\\3", "")

            # СУММИРУЕМ по имени
            aggregated[ing_name]["yield"] += yield_float
            aggregated[ing_name]["unit"] = unit

        # Преобразуем в список
        ingredients = [
            {"name": name, "yield": data["yield"], "unit": data["unit"]}
            for name, data in sorted(aggregated.items())
        ]

        result = {
            "rid": rid,
            "name": details.get("name", f"Extra dish {rid}"),
            "rkeeper_code": None,
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

        extra_dishes_cache[rid] = result
        stats["extra_labels_processed"] += 1

        return result

    except Exception as e:
        logging.error(f"Ошибка загрузки дополнительного товара RID={rid}: {e}")
        extra_dishes_cache[rid] = None
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

        # Читаем группу из GoodsTree (последний уровень)
        group_rid = goods_item.get("209\\1")
        group_name = goods_item.get("209\\3")

        # Строим полную иерархию от корня
        hierarchy = build_group_hierarchy(group_rid, groups_dict)

        # Обновляем статистику
        depth = len(hierarchy)
        if depth > stats["max_hierarchy_depth"]:
            stats["max_hierarchy_depth"] = depth

        try:
            # Запрос 1: GoodsItem (детали)
            details = await get_dish_details(session, rid)

            # Запрос 2: GoodsItemCompDetail (состав)
            composition = await get_dish_composition(session, rid)

            # Рассчитываем вес
            calc_weight = calculate_weight(composition)

            # Собираем ингредиенты (АГРЕГИРОВАННЫЕ базовые ингредиенты)
            from collections import defaultdict

            # Шаг 1: Находим все RID'ы, которые являются родителями
            parent_rids = set()
            for ing in composition:
                parent_rid = ing.get("218#3\\1")
                if parent_rid is not None:
                    parent_rids.add(parent_rid)

            # Шаг 2: Берём только листья и агрегируем по названиям
            aggregated = defaultdict(lambda: {"yield": 0.0, "unit": ""})

            for ing in composition:
                # Получаем RID этого ингредиента
                ingredient_rid = ing.get("1")

                # Если этот RID является родителем - пропускаем
                if ingredient_rid in parent_rids:
                    continue

                # Используем поле "9" (количество) вместо "53" (выход)
                yield_val = ing.get("9", 0)
                try:
                    yield_float = float(str(yield_val).replace(",", "."))
                    if yield_float <= 0:
                        continue
                except (ValueError, TypeError):
                    continue

                ing_name = ing.get("210\\3", "")
                ing_name = re.sub(r'^ПФ\s+\d+\s+', '', ing_name)

                unit = ing.get("210\\206\\3", "")

                # СУММИРУЕМ по имени
                aggregated[ing_name]["yield"] += yield_float
                aggregated[ing_name]["unit"] = unit

            # Преобразуем в список
            ingredients = [
                {"name": name, "yield": data["yield"], "unit": data["unit"]}
                for name, data in sorted(aggregated.items())
            ]

            # Обработка дополнительных этикеток
            extra_labels = []
            add_list_sauce = details.get("add_list_sauce")

            if add_list_sauce:
                extra_rids = parse_add_list_sauce(add_list_sauce)

                if extra_rids:
                    stats["extra_labels_found"] += len(extra_rids)
                    logging.debug(f"RID={rid} ({name}): найдено {len(extra_rids)} доп. этикеток: {extra_rids}")

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
                "group_rid": group_rid,
                "group_name": group_name,
                "hierarchy": hierarchy,  # НОВОЕ! Полная иерархия
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
                "extra_labels": extra_labels,
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
            logging.warning(f"[WARN] High error rate ({error_rate:.1%}). Reducing to {new_workers} workers")
            return True

    elif error_rate < 0.1 and stats["current_workers"] < MAX_CONCURRENT:
        new_workers = min(MAX_CONCURRENT, stats["current_workers"] + 10)
        stats["current_workers"] = new_workers
        logging.info(f"[OK] Error rate low. Increasing to {new_workers} workers")

    return False

# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

async def main():
    """Главная функция"""
    global shutdown_requested, groups_dict, SH_URL, SH_USER, SH_PASS

    setup_logging()

    # Загружаем настройки из БД
    sh_url_loaded, sh_user_loaded, sh_pass_loaded = load_settings_from_db()
    SH_URL = sh_url_loaded
    SH_USER = sh_user_loaded
    SH_PASS = sh_pass_loaded

    print("="*70)
    print("   POLNYJ EKSPORT S MNOGOUROVNEVOJ IERARHIEJ GRUPP")
    print("="*70)
    print(f"\n[*] Nastrojki:")
    print(f"  Parallel'nyh zaprosov: {MAX_CONCURRENT}")
    print(f"  Razmer batcha SQLite: {BATCH_SIZE}")
    print(f"  Tajmaut: {REQUEST_TIMEOUT}s")
    print(f"  Popytki pri oshibke: {MAX_RETRIES}")
    print(f"  Baza dannyh: {DB_FILE}")
    print(f"  Maks. urovnej ierarhii: {MAX_GROUP_LEVELS}")
    print(f"  StoreHouse URL: {SH_URL}")
    print(f"  StoreHouse User: {SH_USER}")

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
        # НОВОЕ: Сначала загружаем дерево групп
        groups_dict = await get_groups_tree(session)
        stats["unique_groups"] = len(groups_dict)

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

        print(f"\n[*] Posle fil'tracii: {stats['total']} tovarov")
        print(f"  S kodom RKeeper: {ONLY_WITH_RKEEPER}")
        print(f"  Bez polufabrikatov: {EXCLUDE_SEMIFINISHED}")
        print(f"  Zagruzheno grupp: {stats['unique_groups']}")

        if checkpoint_rids:
            print(f"  Uzhe obrabotano: {len(checkpoint_rids)} (propushcheno)")

        print(f"\n{'='*70}")
        print("[>] Nachinaem obrabotku...")
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
                logging.info("[STOP] Shutdown requested by user...")
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
            bar = "#" * filled + "." * (bar_length - filled)

            print(f"\r[{stats['processed']}/{stats['total']}] {bar} {progress:.1f}% | "
                  f"{speed:.1f} item/sec | ETA: {remaining/60:.1f}min | "
                  f"Errors: {stats['errors']} | Extra: {stats['extra_labels_found']} | "
                  f"MaxDepth: {stats['max_hierarchy_depth']}",
                  end="", flush=True)

            # Записываем прогресс в файл для API
            try:
                progress_data = {
                    "progress": round(progress, 1),
                    "current": stats["processed"],
                    "total": stats["total"],
                    "speed": round(speed, 1),
                    "eta_minutes": round(remaining / 60, 1),
                    "errors": stats["errors"],
                    "extra_labels": stats["extra_labels_found"]
                }
                with open("/app/data/sync_progress.json", "w") as f:
                    json.dump(progress_data, f)
            except Exception:
                pass  # Не ломаем синхронизацию если не удалось записать прогресс

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
                    logging.warning(f"[PAUSE] Pausing {ERROR_RATE_PAUSE}s due to high error rate...")
                    await asyncio.sleep(ERROR_RATE_PAUSE)

            # Проверка consecutive errors
            if stats["consecutive_errors"] >= MAX_CONSECUTIVE_ERRORS:
                logging.error(f"\n[CRITICAL] {MAX_CONSECUTIVE_ERRORS}+ consecutive errors. Stopping.")
                break

        # Сохраняем остатки
        if batch:
            save_batch_to_db(conn, batch)

        # Финальный checkpoint
        save_checkpoint()

    print("\n")

    # Создаём индексы
    print("[*] Creating indexes...")
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

    # Статистика по уровням иерархии
    for level in range(1, MAX_GROUP_LEVELS + 1):
        cursor.execute(f"SELECT COUNT(DISTINCT level_{level}_name) FROM dishes WHERE level_{level}_name IS NOT NULL")
        unique_level = cursor.fetchone()[0]
        if unique_level > 0:
            print(f"  Level {level}: {unique_level} unique groups")

    conn.close()

    # Обновляем время последней синхронизации в backend БД
    update_sync_timestamp()

    # Удаляем файл прогресса (синхронизация завершена)
    try:
        import os
        progress_file = "/app/data/sync_progress.json"
        if os.path.exists(progress_file):
            os.remove(progress_file)
    except Exception:
        pass

    # Финальная статистика
    elapsed_total = time.time() - stats["start_time"]

    print(f"\n{'='*70}")
    print("[OK] EXPORT COMPLETED!")
    print(f"{'='*70}")
    print(f"[TIME] {elapsed_total/60:.1f} minutes ({elapsed_total:.0f} seconds)")
    print(f"[PERFORMANCE] {stats['saved']/elapsed_total:.1f} items/second")
    print(f"[PROCESSED] {stats['processed']}")
    print(f"[SAVED] {stats['saved']}")
    print(f"[ERRORS] {stats['errors']}")
    print(f"[SKIPPED] {stats['skipped']}")
    print(f"\n[EXTRA LABELS]")
    print(f"  Found connections: {stats['extra_labels_found']}")
    print(f"  Processed items: {stats['extra_labels_processed']}")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  Cache misses: {stats['cache_misses']}")
    print(f"\n[HIERARCHY]")
    print(f"  Total groups: {stats['unique_groups']}")
    print(f"  Max depth: {stats['max_hierarchy_depth']}")
    print(f"\n[DATABASE] {DB_FILE}")
    print(f"  Dishes: {total_dishes}")
    print(f"  With RKeeper code: {dishes_with_rk}")
    print(f"  With extra labels: {dishes_with_extras}")
    print(f"  Ingredients: {total_ingredients}")
    print(f"  Extra labels (connections): {total_extra_labels}")
    print(f"  Unique extra items: {unique_extra_dishes}")
    print(f"  Extra ingredients: {total_extra_ingredients}")
    print(f"  Avg composition: {total_ingredients/total_dishes:.1f} ing/item")
    print(f"{'='*70}")

    log_stats()

# ============================================================================
# ЗАПУСК
# ============================================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrupted by user")
        save_checkpoint()
        print(f"[CHECKPOINT] Progress saved. Processed: {stats['processed']}")
    except Exception as e:
        logging.error(f"\n\n[ERROR] Critical error: {e}")
        import traceback
        traceback.print_exc()
        save_checkpoint()
        sys.exit(1)
