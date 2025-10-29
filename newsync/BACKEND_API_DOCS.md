# Backend API документация - Система печати этикеток

## Описание системы

Система потоковой печати этикеток для ресторанов с фильтрацией по подразделениям (departments).

**Архитектура:**
- Backend: FastAPI + SQLite
- Frontend: React UI с выбором подразделений
- База данных: `dishes_full.sqlite` (26,942+ блюд)

**Основные возможности:**
- Поиск блюд по коду RKeeper
- Фильтрация по одному или нескольким подразделениям (departments)
- Получение полной информации: блюдо + состав + БЖУ + дополнительные этикетки
- Потоковая печать нескольких этикеток

---

## Важные особенности данных

### 1. Дубли RKeeper кодов
**Проблема:** Один RKeeper код может встречаться в разных ресторанах/подразделениях.

**Решение:** Всегда фильтровать по `level_2_name` (department):

```sql
SELECT * FROM dishes
WHERE rkeeper_code = '2538'
  AND level_2_name = 'Британника 1';  -- Фильтр по подразделению!
```

### 2. Иерархия (6 уровней)
- **level_1** - Ресторан/Меню (например: "01 Меню Британника")
- **level_2** - Подразделение (например: "Британника 1", "Британника 2")
- **level_3** - Категория (например: "Холодные закуски")
- **level_4** - Подкатегория
- **level_5** - Дополнительный уровень
- **level_6** - Дополнительный уровень

**Для UI фильтрации используем level_2 (department)**

### 3. Состав блюд
База содержит **базовые ингредиенты**, а не полуфабрикаты:
- ✅ "Мука пшеничная" 0.15 кг
- ✅ "Соль" 0.001403 кг
- ❌ "ПФ 123 Тесто дрожжевое" (таких нет!)

---

## REST API Endpoints

### 1. Получить список подразделений (для UI фильтра)

**Endpoint:** `GET /api/departments`

**SQL запрос:**
```sql
SELECT DISTINCT
    level_1_name AS restaurant,
    level_2_rid AS department_rid,
    level_2_name AS department_name,
    COUNT(*) AS dishes_count
FROM dishes
WHERE level_2_name IS NOT NULL
GROUP BY level_1_name, level_2_rid, level_2_name
ORDER BY level_1_name, level_2_name;
```

**Ответ:**
```json
{
  "departments": [
    {
      "restaurant": "01 Меню Британника",
      "department_rid": 12345,
      "department_name": "Британника 1",
      "dishes_count": 245
    },
    {
      "restaurant": "01 Меню Британника",
      "department_rid": 12346,
      "department_name": "Британника 2",
      "dishes_count": 198
    }
  ]
}
```

**FastAPI код:**
```python
from fastapi import FastAPI, HTTPException
from typing import List, Optional
import sqlite3

app = FastAPI()

@app.get("/api/departments")
async def get_departments():
    """Получить список всех подразделений для UI фильтра"""
    conn = sqlite3.connect("dishes_full.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT
            level_1_name AS restaurant,
            level_2_rid AS department_rid,
            level_2_name AS department_name,
            COUNT(*) AS dishes_count
        FROM dishes
        WHERE level_2_name IS NOT NULL
        GROUP BY level_1_name, level_2_rid, level_2_name
        ORDER BY level_1_name, level_2_name
    """

    cursor.execute(query)
    departments = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"departments": departments}
```

---

### 2. Поиск блюда по RKeeper коду (с фильтром по подразделениям)

**Endpoint:** `GET /api/dish/search`

**Query параметры:**
- `rkeeper_code` (required) - код RKeeper
- `departments` (optional) - список подразделений через запятую

**Примеры запросов:**
```
GET /api/dish/search?rkeeper_code=2538
GET /api/dish/search?rkeeper_code=2538&departments=Британника 1
GET /api/dish/search?rkeeper_code=2538&departments=Британника 1,Британника 2
```

**SQL запрос (один department):**
```sql
SELECT
    d.rid,
    d.name,
    d.rkeeper_code,
    d.level_1_name AS restaurant,
    d.level_2_name AS department,
    d.weight_g,
    d.calculated_weight_g,
    d.protein,
    d.fat,
    d.carbs,
    d.calories,
    d.has_extra_labels
FROM dishes d
WHERE d.rkeeper_code = ?
  AND d.level_2_name = ?
LIMIT 1;
```

**SQL запрос (несколько departments):**
```sql
SELECT
    d.rid,
    d.name,
    d.rkeeper_code,
    d.level_1_name AS restaurant,
    d.level_2_name AS department,
    d.weight_g,
    d.calculated_weight_g,
    d.protein,
    d.fat,
    d.carbs,
    d.calories,
    d.has_extra_labels
FROM dishes d
WHERE d.rkeeper_code = ?
  AND d.level_2_name IN ('Британника 1', 'Британника 2')
LIMIT 1;
```

**Ответ:**
```json
{
  "dish": {
    "rid": 123456,
    "name": "Лепешка узбекская",
    "rkeeper_code": "2538",
    "restaurant": "01 Меню Британника",
    "department": "Британника 1",
    "weight_g": 250.0,
    "calculated_weight_g": 248.5,
    "protein": 8.5,
    "fat": 3.2,
    "carbs": 45.6,
    "calories": 245.8,
    "has_extra_labels": 0
  }
}
```

**FastAPI код:**
```python
from fastapi import Query

@app.get("/api/dish/search")
async def search_dish(
    rkeeper_code: str,
    departments: Optional[str] = None  # "Британника 1,Британника 2"
):
    """Поиск блюда по RKeeper коду с фильтрацией по подразделениям"""
    conn = sqlite3.connect("dishes_full.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if departments:
        # Фильтр по нескольким подразделениям
        dept_list = [d.strip() for d in departments.split(',')]
        placeholders = ','.join(['?'] * len(dept_list))

        query = f"""
            SELECT
                d.rid, d.name, d.rkeeper_code,
                d.level_1_name AS restaurant,
                d.level_2_name AS department,
                d.weight_g, d.calculated_weight_g,
                d.protein, d.fat, d.carbs, d.calories,
                d.has_extra_labels
            FROM dishes d
            WHERE d.rkeeper_code = ?
              AND d.level_2_name IN ({placeholders})
            LIMIT 1
        """
        cursor.execute(query, [rkeeper_code] + dept_list)
    else:
        # Без фильтра (первое найденное)
        query = """
            SELECT
                d.rid, d.name, d.rkeeper_code,
                d.level_1_name AS restaurant,
                d.level_2_name AS department,
                d.weight_g, d.calculated_weight_g,
                d.protein, d.fat, d.carbs, d.calories,
                d.has_extra_labels
            FROM dishes d
            WHERE d.rkeeper_code = ?
            LIMIT 1
        """
        cursor.execute(query, [rkeeper_code])

    dish = cursor.fetchone()
    conn.close()

    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    return {"dish": dict(dish)}
```

---

### 3. Получить полную информацию о блюде (для печати этикетки)

**Endpoint:** `GET /api/dish/{rid}/full`

**Возвращает:**
- Основная информация о блюде
- Состав (базовые ингредиенты)
- Дополнительные этикетки (если есть)
- Состав дополнительных этикеток

**SQL запросы:**

```sql
-- 1. Основное блюдо
SELECT
    d.rid, d.name, d.rkeeper_code,
    d.level_1_name AS restaurant,
    d.level_2_name AS department,
    d.level_3_name AS category,
    d.weight_g, d.calculated_weight_g,
    d.protein, d.fat, d.carbs, d.calories,
    d.technology, d.has_extra_labels
FROM dishes d
WHERE d.rid = ?;

-- 2. Состав основного блюда
SELECT
    i.name AS ingredient,
    ROUND(i.yield_value, 6) AS quantity,
    i.unit
FROM ingredients i
WHERE i.dish_rid = ?
ORDER BY i.name;

-- 3. Дополнительные этикетки
SELECT
    el.extra_dish_rid,
    el.extra_dish_name,
    el.extra_dish_weight_g,
    el.extra_dish_protein,
    el.extra_dish_fat,
    el.extra_dish_carbs,
    el.extra_dish_calories,
    el.sort_order
FROM dish_extra_labels el
WHERE el.main_dish_rid = ?
ORDER BY el.sort_order;

-- 4. Состав дополнительных этикеток
SELECT
    ei.extra_dish_rid,
    ei.name AS ingredient,
    ROUND(ei.yield_value, 6) AS quantity,
    ei.unit
FROM extra_dish_ingredients ei
WHERE ei.extra_dish_rid IN (
    SELECT extra_dish_rid
    FROM dish_extra_labels
    WHERE main_dish_rid = ?
)
ORDER BY ei.extra_dish_rid, ei.name;
```

**Ответ:**
```json
{
  "dish": {
    "rid": 123456,
    "name": "Лепешка узбекская",
    "rkeeper_code": "2538",
    "restaurant": "01 Меню Британника",
    "department": "Британника 1",
    "category": "Хлеб и выпечка",
    "weight_g": 250.0,
    "calculated_weight_g": 248.5,
    "protein": 8.5,
    "fat": 3.2,
    "carbs": 45.6,
    "calories": 245.8,
    "technology": "Выпекать при 220°C 15 минут",
    "has_extra_labels": 1
  },
  "ingredients": [
    {"ingredient": "Вода", "quantity": 0.210442, "unit": "кг"},
    {"ingredient": "Дрожжи", "quantity": 0.003, "unit": "кг"},
    {"ingredient": "Масло подсолнечное", "quantity": 0.015, "unit": "кг"},
    {"ingredient": "Мука пшеничная", "quantity": 0.15, "unit": "кг"},
    {"ingredient": "Соль", "quantity": 0.001403, "unit": "кг"}
  ],
  "extra_labels": [
    {
      "extra_dish_rid": 789012,
      "extra_dish_name": "Соус чесночный",
      "extra_dish_weight_g": 30.0,
      "extra_dish_protein": 1.2,
      "extra_dish_fat": 15.3,
      "extra_dish_carbs": 2.1,
      "extra_dish_calories": 145.2,
      "sort_order": 0,
      "ingredients": [
        {"ingredient": "Майонез", "quantity": 0.025, "unit": "кг"},
        {"ingredient": "Чеснок", "quantity": 0.005, "unit": "кг"}
      ]
    }
  ]
}
```

**FastAPI код:**
```python
@app.get("/api/dish/{rid}/full")
async def get_dish_full(rid: int):
    """Получить полную информацию о блюде для печати этикетки"""
    conn = sqlite3.connect("dishes_full.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Основное блюдо
    cursor.execute("""
        SELECT
            d.rid, d.name, d.rkeeper_code,
            d.level_1_name AS restaurant,
            d.level_2_name AS department,
            d.level_3_name AS category,
            d.weight_g, d.calculated_weight_g,
            d.protein, d.fat, d.carbs, d.calories,
            d.technology, d.has_extra_labels
        FROM dishes d
        WHERE d.rid = ?
    """, [rid])

    dish = cursor.fetchone()
    if not dish:
        conn.close()
        raise HTTPException(status_code=404, detail="Dish not found")

    dish_dict = dict(dish)

    # 2. Состав основного блюда
    cursor.execute("""
        SELECT
            i.name AS ingredient,
            ROUND(i.yield_value, 6) AS quantity,
            i.unit
        FROM ingredients i
        WHERE i.dish_rid = ?
        ORDER BY i.name
    """, [rid])

    ingredients = [dict(row) for row in cursor.fetchall()]

    # 3. Дополнительные этикетки
    cursor.execute("""
        SELECT
            el.extra_dish_rid,
            el.extra_dish_name,
            el.extra_dish_weight_g,
            el.extra_dish_protein,
            el.extra_dish_fat,
            el.extra_dish_carbs,
            el.extra_dish_calories,
            el.sort_order
        FROM dish_extra_labels el
        WHERE el.main_dish_rid = ?
        ORDER BY el.sort_order
    """, [rid])

    extra_labels = []
    for label_row in cursor.fetchall():
        label_dict = dict(label_row)

        # 4. Состав дополнительной этикетки
        cursor.execute("""
            SELECT
                ei.name AS ingredient,
                ROUND(ei.yield_value, 6) AS quantity,
                ei.unit
            FROM extra_dish_ingredients ei
            WHERE ei.extra_dish_rid = ?
            ORDER BY ei.name
        """, [label_dict['extra_dish_rid']])

        label_dict['ingredients'] = [dict(row) for row in cursor.fetchall()]
        extra_labels.append(label_dict)

    conn.close()

    return {
        "dish": dish_dict,
        "ingredients": ingredients,
        "extra_labels": extra_labels
    }
```

---

### 4. Batch поиск блюд (для потоковой печати)

**Endpoint:** `POST /api/dish/batch`

**Body:**
```json
{
  "rkeeper_codes": ["2538", "1234", "5678"],
  "departments": ["Британника 1", "Британника 2"]
}
```

**SQL запрос:**
```sql
SELECT
    d.rid, d.name, d.rkeeper_code,
    d.level_1_name AS restaurant,
    d.level_2_name AS department,
    d.weight_g, d.protein, d.fat, d.carbs, d.calories,
    d.has_extra_labels
FROM dishes d
WHERE d.rkeeper_code IN ('2538', '1234', '5678')
  AND d.level_2_name IN ('Британника 1', 'Британника 2')
ORDER BY d.rkeeper_code;
```

**Ответ:**
```json
{
  "dishes": [
    {
      "rid": 123456,
      "name": "Лепешка узбекская",
      "rkeeper_code": "2538",
      "department": "Британника 1",
      "weight_g": 250.0,
      ...
    },
    {
      "rid": 123457,
      "name": "Салат Цезарь",
      "rkeeper_code": "1234",
      "department": "Британника 1",
      "weight_g": 180.0,
      ...
    }
  ],
  "found": 2,
  "not_found": ["5678"]
}
```

**FastAPI код:**
```python
from pydantic import BaseModel

class BatchSearchRequest(BaseModel):
    rkeeper_codes: List[str]
    departments: Optional[List[str]] = None

@app.post("/api/dish/batch")
async def batch_search(request: BatchSearchRequest):
    """Batch поиск блюд по нескольким RKeeper кодам"""
    conn = sqlite3.connect("dishes_full.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    codes_placeholders = ','.join(['?'] * len(request.rkeeper_codes))

    if request.departments:
        dept_placeholders = ','.join(['?'] * len(request.departments))
        query = f"""
            SELECT
                d.rid, d.name, d.rkeeper_code,
                d.level_1_name AS restaurant,
                d.level_2_name AS department,
                d.weight_g, d.calculated_weight_g,
                d.protein, d.fat, d.carbs, d.calories,
                d.has_extra_labels
            FROM dishes d
            WHERE d.rkeeper_code IN ({codes_placeholders})
              AND d.level_2_name IN ({dept_placeholders})
            GROUP BY d.rkeeper_code
        """
        cursor.execute(query, request.rkeeper_codes + request.departments)
    else:
        query = f"""
            SELECT
                d.rid, d.name, d.rkeeper_code,
                d.level_1_name AS restaurant,
                d.level_2_name AS department,
                d.weight_g, d.calculated_weight_g,
                d.protein, d.fat, d.carbs, d.calories,
                d.has_extra_labels
            FROM dishes d
            WHERE d.rkeeper_code IN ({codes_placeholders})
            GROUP BY d.rkeeper_code
        """
        cursor.execute(query, request.rkeeper_codes)

    dishes = [dict(row) for row in cursor.fetchall()]
    conn.close()

    found_codes = {dish['rkeeper_code'] for dish in dishes}
    not_found = [code for code in request.rkeeper_codes if code not in found_codes]

    return {
        "dishes": dishes,
        "found": len(dishes),
        "not_found": not_found
    }
```

---

## SQL запросы для прямого тестирования

Скопируйте эти запросы в DBViewer для тестирования.

### Поиск по RKeeper коду с фильтром по department

```sql
-- Один department
SELECT
    d.rid, d.name, d.rkeeper_code,
    d.level_2_name AS department,
    d.weight_g, d.protein, d.fat, d.carbs, d.calories
FROM dishes d
WHERE d.rkeeper_code = '2538'
  AND d.level_2_name = 'Британника 1';

-- Несколько departments
SELECT
    d.rid, d.name, d.rkeeper_code,
    d.level_2_name AS department,
    d.weight_g, d.protein, d.fat, d.carbs, d.calories
FROM dishes d
WHERE d.rkeeper_code = '2538'
  AND d.level_2_name IN ('Британника 1', 'Британника 2', 'Британника 3');
```

### Получить полные данные по RID

```sql
-- Основное блюдо
SELECT * FROM dishes WHERE rid = 12345;

-- Состав
SELECT
    i.name AS ingredient,
    ROUND(i.yield_value, 6) AS quantity,
    i.unit
FROM ingredients i
WHERE i.dish_rid = 12345
ORDER BY i.name;

-- Дополнительные этикетки
SELECT * FROM dish_extra_labels
WHERE main_dish_rid = 12345
ORDER BY sort_order;

-- Состав дополнительных этикеток
SELECT
    ei.extra_dish_rid,
    ei.name AS ingredient,
    ROUND(ei.yield_value, 6) AS quantity,
    ei.unit
FROM extra_dish_ingredients ei
WHERE ei.extra_dish_rid IN (
    SELECT extra_dish_rid
    FROM dish_extra_labels
    WHERE main_dish_rid = 12345
)
ORDER BY ei.extra_dish_rid, ei.name;
```

### Проверка дублей

```sql
-- Найти все дубли RKeeper кодов
SELECT
    rkeeper_code,
    COUNT(*) AS count,
    GROUP_CONCAT(DISTINCT level_2_name, ', ') AS departments
FROM dishes
WHERE rkeeper_code = '2538'
GROUP BY rkeeper_code;

-- Показать все варианты дубля
SELECT
    rid, name, rkeeper_code,
    level_1_name AS restaurant,
    level_2_name AS department
FROM dishes
WHERE rkeeper_code = '2538'
ORDER BY level_1_name, level_2_name;
```

---

## React UI - Пример компонентов

### Фильтр по подразделениям

```typescript
import { useState, useEffect } from 'react';

interface Department {
  restaurant: string;
  department_rid: number;
  department_name: string;
  dishes_count: number;
}

function DepartmentFilter() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDepts, setSelectedDepts] = useState<string[]>([]);

  useEffect(() => {
    // Загрузка списка подразделений
    fetch('/api/departments')
      .then(res => res.json())
      .then(data => setDepartments(data.departments));
  }, []);

  const handleToggle = (deptName: string) => {
    setSelectedDepts(prev =>
      prev.includes(deptName)
        ? prev.filter(d => d !== deptName)
        : [...prev, deptName]
    );
  };

  return (
    <div>
      <h3>Выберите подразделения:</h3>
      {departments.map(dept => (
        <label key={dept.department_rid}>
          <input
            type="checkbox"
            checked={selectedDepts.includes(dept.department_name)}
            onChange={() => handleToggle(dept.department_name)}
          />
          {dept.restaurant} - {dept.department_name} ({dept.dishes_count} блюд)
        </label>
      ))}
    </div>
  );
}
```

### Поиск и печать блюда

```typescript
interface SearchFormProps {
  selectedDepartments: string[];
}

function SearchForm({ selectedDepartments }: SearchFormProps) {
  const [rkeeperCode, setRkeeperCode] = useState('');
  const [dish, setDish] = useState(null);

  const handleSearch = async () => {
    const params = new URLSearchParams({
      rkeeper_code: rkeeperCode,
      departments: selectedDepartments.join(',')
    });

    const response = await fetch(`/api/dish/search?${params}`);
    const data = await response.json();
    setDish(data.dish);
  };

  const handlePrint = async () => {
    if (!dish) return;

    // Получаем полные данные для печати
    const response = await fetch(`/api/dish/${dish.rid}/full`);
    const fullData = await response.json();

    // Отправляем на печать
    printLabel(fullData);
  };

  return (
    <div>
      <input
        type="text"
        value={rkeeperCode}
        onChange={e => setRkeeperCode(e.target.value)}
        placeholder="Введите код RKeeper"
      />
      <button onClick={handleSearch}>Найти</button>

      {dish && (
        <div>
          <h3>{dish.name}</h3>
          <p>Вес: {dish.weight_g} г</p>
          <p>Калории: {dish.calories} ккал</p>
          <p>Подразделение: {dish.department}</p>
          <button onClick={handlePrint}>Печать этикетки</button>
        </div>
      )}
    </div>
  );
}
```

---

## Рекомендации по производительности

### 1. Индексы (уже созданы скриптом)
```sql
CREATE INDEX idx_rkeeper_code ON dishes(rkeeper_code);
CREATE INDEX idx_level_2_name ON dishes(level_2_name);
CREATE INDEX idx_ingredients_dish_rid ON ingredients(dish_rid);
CREATE INDEX idx_extra_labels_main_dish ON dish_extra_labels(main_dish_rid);
```

### 2. Connection pooling
Используйте пул подключений для FastAPI:

```python
import sqlite3
from contextlib import contextmanager

DB_PATH = "dishes_full.sqlite"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

@app.get("/api/dish/{rid}")
async def get_dish(rid: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dishes WHERE rid = ?", [rid])
        return dict(cursor.fetchone())
```

### 3. Кэширование списка подразделений
Список departments меняется редко - кэшируйте его:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_departments_cached():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT
                level_1_name AS restaurant,
                level_2_name AS department_name
            FROM dishes
            WHERE level_2_name IS NOT NULL
            ORDER BY level_1_name, level_2_name
        """)
        return [dict(row) for row in cursor.fetchall()]

@app.get("/api/departments")
async def departments():
    return {"departments": get_departments_cached()}
```

---

## Тестирование API

### cURL примеры:

```bash
# Получить список подразделений
curl http://localhost:8000/api/departments

# Поиск блюда по RKeeper коду
curl "http://localhost:8000/api/dish/search?rkeeper_code=2538"

# Поиск с фильтром по department
curl "http://localhost:8000/api/dish/search?rkeeper_code=2538&departments=Британника%201"

# Получить полную информацию
curl http://localhost:8000/api/dish/123456/full

# Batch поиск
curl -X POST http://localhost:8000/api/dish/batch \
  -H "Content-Type: application/json" \
  -d '{
    "rkeeper_codes": ["2538", "1234"],
    "departments": ["Британника 1"]
  }'
```

---

## Обработка ошибок

### Типичные ошибки:

**1. Блюдо не найдено (404)**
```json
{
  "detail": "Dish not found"
}
```
**Причины:**
- Неверный RKeeper код
- Код существует, но не в указанных departments
- База данных устарела

**2. Дубли RKeeper кодов**
```json
{
  "detail": "Multiple dishes found. Please specify department filter.",
  "dishes": [
    {"rid": 12345, "department": "Британника 1"},
    {"rid": 12346, "department": "Британника 2"}
  ]
}
```
**Решение:** Добавить фильтр по department

**3. Пустой состав**
```json
{
  "dish": {...},
  "ingredients": []
}
```
**Причина:** В Store House 5 нет калькуляции для блюда на текущую дату

---

## Лог структуры БД

```
dishes (26,942 записи)
├── rid (PRIMARY KEY)
├── rkeeper_code (INDEX) ← Поиск по этому полю
├── level_1_name (INDEX)
└── level_2_name (INDEX) ← Фильтр по этому полю

ingredients (~350,000 записей)
└── dish_rid (INDEX) ← JOIN с dishes

dish_extra_labels (~2,500 записей)
└── main_dish_rid (INDEX) ← JOIN с dishes

extra_dish_ingredients (~15,000 записей)
└── extra_dish_rid (INDEX) ← JOIN с dish_extra_labels
```

---

## Чеклист перед запуском

- [ ] База данных `dishes_full.sqlite` актуальная (перезапущен export_dishes_full.py)
- [ ] Проверены индексы: `PRAGMA index_list('dishes');`
- [ ] Тестовый запрос работает: `SELECT COUNT(*) FROM dishes;`
- [ ] FastAPI сервер поднимается: `uvicorn main:app --reload`
- [ ] Endpoint `/api/departments` возвращает данные
- [ ] Поиск по RKeeper коду работает с фильтром по department
- [ ] Frontend получает данные через API

---

## Контакты и поддержка

**База данных:** `dishes_full.sqlite` (обновляется через `export_dishes_full.py`)

**Скрипт экспорта:** См. `EXPORT_SCRIPT_DOCS.md`

**SQL запросы:** См. `sql_queries.sql` (18 готовых запросов)
