-- ============================================================================
-- SQL QUERIES FOR dishes_full.sqlite
-- Для использования в DBViewer или другом SQL клиенте
-- ============================================================================

-- 1. ПОИСК БЛЮДА ПО КОДУ RKEEPER
-- Получить полную информацию о блюде по коду RKeeper
SELECT
    rid,
    name,
    rkeeper_code,
    type,
    -- Иерархия групп (6 уровней)
    level_1_name AS restaurant,        -- Уровень 1 (ресторан/меню)
    level_2_name AS department,        -- Уровень 2 (подразделение)
    level_3_name AS category,          -- Уровень 3 (категория)
    level_4_name AS subcategory,       -- Уровень 4 (подкатегория)
    level_5_name AS level_5,
    level_6_name AS level_6,
    -- БЖУ и калории
    protein,
    fat,
    carbs,
    calories,
    weight_g,
    calculated_weight_g,
    -- Технология приготовления
    technology,
    has_extra_labels,
    created_at
FROM dishes
WHERE rkeeper_code = '2538';  -- ЗАМЕНИТЕ НА НУЖНЫЙ КОД


-- 2. ПОИСК ВСЕХ БЛЮД С ОДИНАКОВЫМ КОДОМ RKEEPER (для решения проблемы дублей)
-- Показывает все блюда с одним RK кодом из разных ресторанов/отделов
SELECT
    rid,
    name,
    rkeeper_code,
    level_1_name AS restaurant,
    level_2_name AS department,
    level_3_name AS category,
    protein,
    fat,
    carbs,
    calories,
    weight_g
FROM dishes
WHERE rkeeper_code = '2538'
ORDER BY level_1_name, level_2_name;


-- 3. ПОЛУЧИТЬ БЛЮДО С ИНГРЕДИЕНТАМИ
-- Блюдо + состав (ингредиенты)
SELECT
    d.rid,
    d.name AS dish_name,
    d.rkeeper_code,
    d.level_1_name || ' > ' || d.level_2_name AS location,
    d.protein,
    d.fat,
    d.carbs,
    d.calories,
    d.weight_g,
    -- Ингредиенты
    i.name AS ingredient_name,
    i.yield_value,
    i.unit
FROM dishes d
LEFT JOIN ingredients i ON d.rid = i.dish_rid
WHERE d.rkeeper_code = '2538'
ORDER BY d.rid, i.name;


-- 4. ПОЛУЧИТЬ БЛЮДО С ДОПОЛНИТЕЛЬНЫМИ ЭТИКЕТКАМИ
-- Блюдо + дополнительные этикетки (соусы, гарниры и т.д.)
SELECT
    d.rid AS main_dish_rid,
    d.name AS main_dish_name,
    d.rkeeper_code AS main_rk_code,
    d.level_1_name AS restaurant,
    d.weight_g AS main_weight,
    -- Дополнительные товары
    el.extra_dish_rid,
    el.extra_dish_name,
    el.extra_dish_weight_g,
    el.extra_dish_protein,
    el.extra_dish_fat,
    el.extra_dish_carbs,
    el.sort_order
FROM dishes d
LEFT JOIN dish_extra_labels el ON d.rid = el.main_dish_rid
WHERE d.rkeeper_code = '2538'
ORDER BY d.rid, el.sort_order;


-- 5. ПОЛНАЯ ИНФОРМАЦИЯ О БЛЮДЕ ДЛЯ ПЕЧАТИ ЭТИКЕТКИ
-- Все данные для печати: блюдо + состав + доп. этикетки + состав доп. товаров
WITH main_dish AS (
    SELECT
        d.rid,
        d.name,
        d.rkeeper_code,
        d.level_1_name,
        d.level_2_name,
        d.level_3_name,
        d.protein,
        d.fat,
        d.carbs,
        d.calories,
        d.weight_g,
        d.technology
    FROM dishes d
    WHERE d.rkeeper_code = '2538'
)
SELECT
    'MAIN' AS item_type,
    md.rid,
    md.name,
    md.rkeeper_code,
    md.level_1_name || ' > ' || md.level_2_name AS location,
    md.protein,
    md.fat,
    md.carbs,
    md.calories,
    md.weight_g,
    NULL AS extra_rid,
    NULL AS extra_name,
    i.name AS ingredient_name,
    i.yield_value,
    i.unit
FROM main_dish md
LEFT JOIN ingredients i ON md.rid = i.dish_rid

UNION ALL

SELECT
    'EXTRA' AS item_type,
    md.rid AS main_rid,
    md.name AS main_name,
    md.rkeeper_code,
    md.level_1_name || ' > ' || md.level_2_name AS location,
    el.extra_dish_protein,
    el.extra_dish_fat,
    el.extra_dish_carbs,
    el.extra_dish_calories,
    el.extra_dish_weight_g,
    el.extra_dish_rid,
    el.extra_dish_name,
    ei.name AS ingredient_name,
    ei.yield_value,
    ei.unit
FROM main_dish md
INNER JOIN dish_extra_labels el ON md.rid = el.main_dish_rid
LEFT JOIN extra_dish_ingredients ei ON el.extra_dish_rid = ei.extra_dish_rid
ORDER BY item_type DESC, extra_rid, ingredient_name;


-- 6. ПОИСК ПО КОДУ RKEEPER + ФИЛЬТР ПО РЕСТОРАНУ
-- Для решения проблемы дублей: выбор блюда из конкретного ресторана
SELECT
    rid,
    name,
    rkeeper_code,
    level_1_name AS restaurant,
    level_2_name AS department,
    protein,
    fat,
    carbs,
    calories,
    weight_g
FROM dishes
WHERE rkeeper_code = '2538'
  AND level_1_name = '01 Меню Британника'  -- ЗАМЕНИТЕ НА НУЖНЫЙ РЕСТОРАН
  AND level_2_name = 'Британника 1';       -- ЗАМЕНИТЕ НА НУЖНОЕ ПОДРАЗДЕЛЕНИЕ


-- 7. ПОИСК БЛЮДА ПО ЧАСТИЧНОМУ СОВПАДЕНИЮ НАЗВАНИЯ
SELECT
    rid,
    name,
    rkeeper_code,
    level_1_name AS restaurant,
    level_2_name AS department,
    weight_g,
    calories
FROM dishes
WHERE name LIKE '%Лепешка%'  -- ЗАМЕНИТЕ НА НУЖНУЮ ПОДСТРОКУ
ORDER BY level_1_name, level_2_name, name;


-- 8. СПИСОК ВСЕХ РЕСТОРАНОВ (УРОВЕНЬ 1)
SELECT DISTINCT
    level_1_rid,
    level_1_name AS restaurant_name,
    COUNT(*) AS dishes_count
FROM dishes
WHERE level_1_name IS NOT NULL
GROUP BY level_1_rid, level_1_name
ORDER BY level_1_name;


-- 9. СПИСОК ВСЕХ ПОДРАЗДЕЛЕНИЙ РЕСТОРАНА (УРОВЕНЬ 2)
SELECT DISTINCT
    level_1_name AS restaurant,
    level_2_rid,
    level_2_name AS department,
    COUNT(*) AS dishes_count
FROM dishes
WHERE level_1_name = '01 Меню Британника'  -- ЗАМЕНИТЕ НА НУЖНЫЙ РЕСТОРАН
  AND level_2_name IS NOT NULL
GROUP BY level_1_name, level_2_rid, level_2_name
ORDER BY level_2_name;


-- 10. ПРОВЕРКА: НАЙТИ ВСЕ ДУБЛИ КОДОВ RKEEPER
-- Показывает коды, которые встречаются в разных местах
SELECT
    rkeeper_code,
    COUNT(*) AS count,
    COUNT(DISTINCT level_1_name) AS restaurants_count,
    GROUP_CONCAT(DISTINCT level_1_name, ', ') AS restaurants
FROM dishes
WHERE rkeeper_code IS NOT NULL
GROUP BY rkeeper_code
HAVING COUNT(*) > 1
ORDER BY count DESC;


-- 11. ПРОСТОЙ ЗАПРОС ДЛЯ API: БЛЮДО ПО RK + РЕСТОРАН + ОТДЕЛ
-- Минимальная выборка для FastAPI endpoint
SELECT
    rid,
    name,
    rkeeper_code,
    protein,
    fat,
    carbs,
    calories,
    weight_g,
    technology,
    has_extra_labels
FROM dishes
WHERE rkeeper_code = ?  -- Параметр 1: RK код
  AND (level_1_name = ? OR ? IS NULL)  -- Параметр 2 и 3: Ресторан (опционально)
  AND (level_2_name = ? OR ? IS NULL)  -- Параметр 4 и 5: Отдел (опционально)
LIMIT 1;


-- 12. ПОЛУЧИТЬ ВСЕ БЛЮДА С ДОПОЛНИТЕЛЬНЫМИ ЭТИКЕТКАМИ
SELECT
    d.rid,
    d.name,
    d.rkeeper_code,
    d.level_1_name,
    COUNT(el.extra_dish_rid) AS extra_labels_count
FROM dishes d
INNER JOIN dish_extra_labels el ON d.rid = el.main_dish_rid
GROUP BY d.rid, d.name, d.rkeeper_code, d.level_1_name
ORDER BY extra_labels_count DESC;


-- 13. СТАТИСТИКА ПО БАЗЕ
SELECT
    'Total dishes' AS metric,
    COUNT(*) AS value
FROM dishes

UNION ALL

SELECT
    'Dishes with RKeeper code',
    COUNT(*)
FROM dishes
WHERE rkeeper_code IS NOT NULL

UNION ALL

SELECT
    'Dishes with extra labels',
    COUNT(*)
FROM dishes
WHERE has_extra_labels = 1

UNION ALL

SELECT
    'Total ingredients',
    COUNT(*)
FROM ingredients

UNION ALL

SELECT
    'Total extra labels',
    COUNT(*)
FROM dish_extra_labels

UNION ALL

SELECT
    'Unique restaurants (level 1)',
    COUNT(DISTINCT level_1_name)
FROM dishes
WHERE level_1_name IS NOT NULL

UNION ALL

SELECT
    'Unique departments (level 2)',
    COUNT(DISTINCT level_2_name)
FROM dishes
WHERE level_2_name IS NOT NULL;


-- ============================================================================
-- ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ В FASTAPI
-- ============================================================================

/*
Пример 1: Получить блюдо по RK коду (с учетом ресторана)
Endpoint: GET /dish?rk_code=2538&restaurant=Британника

query = """
SELECT rid, name, rkeeper_code, protein, fat, carbs, calories, weight_g
FROM dishes
WHERE rkeeper_code = ?
  AND level_1_name LIKE ?
LIMIT 1
"""
cursor.execute(query, (rk_code, f'%{restaurant}%'))


Пример 2: Получить блюдо с ингредиентами
Endpoint: GET /dish/{rid}/full

query = """
SELECT
    d.rid, d.name, d.rkeeper_code, d.protein, d.fat, d.carbs,
    d.calories, d.weight_g, d.technology,
    i.name as ingredient, i.yield_value, i.unit
FROM dishes d
LEFT JOIN ingredients i ON d.rid = i.dish_rid
WHERE d.rid = ?
"""
cursor.execute(query, (rid,))


Пример 3: Получить блюдо с доп. этикетками
Endpoint: GET /dish/{rid}/labels

query = """
SELECT
    el.extra_dish_rid, el.extra_dish_name, el.extra_dish_protein,
    el.extra_dish_fat, el.extra_dish_carbs, el.extra_dish_calories,
    el.extra_dish_weight_g
FROM dish_extra_labels el
WHERE el.main_dish_rid = ?
ORDER BY el.sort_order
"""
cursor.execute(query, (rid,))
*/


-- ============================================================================
-- ПРОВЕРОЧНЫЕ ЗАПРОСЫ ДЛЯ ТЕСТИРОВАНИЯ ОБНОВЛЁННОГО СКРИПТА
-- ============================================================================

-- 14. ПОЛНАЯ ИНФОРМАЦИЯ О БЛЮДЕ ПО КОДУ RKEEPER
-- Выводит основное блюдо, его состав, доп. этикетки и их состав
-- Используйте этот запрос для проверки правильности экспорта

-- Часть 1: Основное блюдо
SELECT
    '=== OSNOVNOE BLYUDO ===' AS section,
    d.rid,
    d.name,
    d.rkeeper_code,
    d.level_1_name AS restaurant,
    d.level_2_name AS department,
    d.level_3_name AS category,
    d.protein,
    d.fat,
    d.carbs,
    d.calories,
    d.weight_g,
    d.calculated_weight_g,
    d.has_extra_labels,
    d.technology
FROM dishes d
WHERE d.rkeeper_code = '2538';  -- ЗАМЕНИТЕ НА НУЖНЫЙ КОД

-- Часть 2: Состав основного блюда (должны быть базовые ингредиенты, не полуфабрикаты!)
SELECT
    '=== SOSTAV OSNOVNOGO BLYUDA ===' AS section,
    i.name AS ingredient,
    ROUND(i.yield_value, 6) AS quantity,
    i.unit
FROM dishes d
INNER JOIN ingredients i ON d.rid = i.dish_rid
WHERE d.rkeeper_code = '2538'  -- ЗАМЕНИТЕ НА НУЖНЫЙ КОД
ORDER BY i.name;

-- Часть 3: Дополнительные этикетки
SELECT
    '=== DOPOLNITELNYE ETIKETKI ===' AS section,
    el.extra_dish_rid AS rid,
    el.extra_dish_name AS name,
    el.extra_dish_protein AS protein,
    el.extra_dish_fat AS fat,
    el.extra_dish_carbs AS carbs,
    el.extra_dish_calories AS calories,
    el.extra_dish_weight_g AS weight_g,
    el.sort_order
FROM dishes d
INNER JOIN dish_extra_labels el ON d.rid = el.main_dish_rid
WHERE d.rkeeper_code = '2538'  -- ЗАМЕНИТЕ НА НУЖНЫЙ КОД
ORDER BY el.sort_order;

-- Часть 4: Состав дополнительных этикеток
SELECT
    '=== SOSTAV DOP. ETIKЕТOK ===' AS section,
    el.extra_dish_name AS extra_label,
    ei.name AS ingredient,
    ROUND(ei.yield_value, 6) AS quantity,
    ei.unit
FROM dishes d
INNER JOIN dish_extra_labels el ON d.rid = el.main_dish_rid
INNER JOIN extra_dish_ingredients ei ON el.extra_dish_rid = ei.extra_dish_rid
WHERE d.rkeeper_code = '2538'  -- ЗАМЕНИТЕ НА НУЖНЫЙ КОД
ORDER BY el.sort_order, ei.name;


-- 15. ПОЛНАЯ ИНФОРМАЦИЯ О БЛЮДЕ ПО RID
-- Такой же запрос, но поиск по RID вместо RKeeper кода

-- Часть 1: Основное блюдо
SELECT
    '=== OSNOVNOE BLYUDO ===' AS section,
    d.rid,
    d.name,
    d.rkeeper_code,
    d.level_1_name AS restaurant,
    d.level_2_name AS department,
    d.level_3_name AS category,
    d.protein,
    d.fat,
    d.carbs,
    d.calories,
    d.weight_g,
    d.calculated_weight_g,
    d.has_extra_labels,
    d.technology
FROM dishes d
WHERE d.rid = 12345;  -- ЗАМЕНИТЕ НА НУЖНЫЙ RID

-- Часть 2: Состав основного блюда
SELECT
    '=== SOSTAV OSNOVNOGO BLYUDA ===' AS section,
    i.name AS ingredient,
    ROUND(i.yield_value, 6) AS quantity,
    i.unit
FROM dishes d
INNER JOIN ingredients i ON d.rid = i.dish_rid
WHERE d.rid = 12345  -- ЗАМЕНИТЕ НА НУЖНЫЙ RID
ORDER BY i.name;

-- Часть 3: Дополнительные этикетки
SELECT
    '=== DOPOLNITELNYE ETIKETKI ===' AS section,
    el.extra_dish_rid AS rid,
    el.extra_dish_name AS name,
    el.extra_dish_protein AS protein,
    el.extra_dish_fat AS fat,
    el.extra_dish_carbs AS carbs,
    el.extra_dish_calories AS calories,
    el.extra_dish_weight_g AS weight_g,
    el.sort_order
FROM dishes d
INNER JOIN dish_extra_labels el ON d.rid = el.main_dish_rid
WHERE d.rid = 12345  -- ЗАМЕНИТЕ НА НУЖНЫЙ RID
ORDER BY el.sort_order;

-- Часть 4: Состав дополнительных этикеток
SELECT
    '=== SOSTAV DOP. ETIKЕТOK ===' AS section,
    el.extra_dish_name AS extra_label,
    ei.name AS ingredient,
    ROUND(ei.yield_value, 6) AS quantity,
    ei.unit
FROM dishes d
INNER JOIN dish_extra_labels el ON d.rid = el.main_dish_rid
INNER JOIN extra_dish_ingredients ei ON el.extra_dish_rid = ei.extra_dish_rid
WHERE d.rid = 12345  -- ЗАМЕНИТЕ НА НУЖНЫЙ RID
ORDER BY el.sort_order, ei.name;


-- 16. БЫСТРАЯ ПРОВЕРКА: СКОЛЬКО ИНГРЕДИЕНТОВ У БЛЮДА
-- Используйте для быстрой проверки количества ингредиентов
SELECT
    d.rid,
    d.name,
    d.rkeeper_code,
    COUNT(i.name) AS ingredients_count
FROM dishes d
LEFT JOIN ingredients i ON d.rid = i.dish_rid
WHERE d.rkeeper_code = '2538'  -- ЗАМЕНИТЕ НА НУЖНЫЙ КОД
GROUP BY d.rid, d.name, d.rkeeper_code;


-- 17. СРАВНИТЬ ДВА БЛЮДА (для проверки до/после обновления скрипта)
-- Показывает количество ингредиентов для каждого блюда
SELECT
    d.rid,
    d.name,
    d.rkeeper_code,
    COUNT(DISTINCT i.name) AS unique_ingredients,
    COUNT(i.name) AS total_ingredient_records,
    GROUP_CONCAT(i.name, ', ') AS ingredients_list
FROM dishes d
LEFT JOIN ingredients i ON d.rid = i.dish_rid
WHERE d.rkeeper_code IN ('2538', '1234')  -- ЗАМЕНИТЕ НА НУЖНЫЕ КОДЫ
GROUP BY d.rid, d.name, d.rkeeper_code
ORDER BY d.rkeeper_code;


-- ============================================================================
-- 18. ПОЛНАЯ ИНФОРМАЦИЯ ПО RID - КОМПАКТНЫЙ ВАРИАНТ
-- Основное блюдо + состав + БЖУ + вес + доп. этикетки (если есть)
-- ============================================================================

-- Основное блюдо с БЖУ и весом
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
WHERE d.rid = 12345;  -- ЗАМЕНИТЕ НА НУЖНЫЙ RID

-- Состав (ингредиенты) основного блюда
SELECT
    i.name AS ingredient,
    ROUND(i.yield_value, 6) AS quantity,
    i.unit
FROM ingredients i
WHERE i.dish_rid = 12345  -- ЗАМЕНИТЕ НА НУЖНЫЙ RID
ORDER BY i.name;

-- Дополнительные этикетки (если has_extra_labels = 1)
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
WHERE el.main_dish_rid = 12345  -- ЗАМЕНИТЕ НА НУЖНЫЙ RID
ORDER BY el.sort_order;

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
    WHERE main_dish_rid = 12345  -- ЗАМЕНИТЕ НА НУЖНЫЙ RID
)
ORDER BY ei.extra_dish_rid, ei.name;
*/
