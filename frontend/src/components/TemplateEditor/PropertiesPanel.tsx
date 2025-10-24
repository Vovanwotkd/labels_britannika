/**
 * Properties Panel Component
 * Панель свойств выбранного элемента
 */

import { TemplateElement, FontFamily } from './types'

interface PropertiesPanelProps {
  element: TemplateElement | null
  onUpdate: (updates: Partial<TemplateElement>) => void
  onDelete: () => void
}

const fontFamilies: FontFamily[] = ['Calibri', 'Arial', 'Times New Roman']

export default function PropertiesPanel({
  element,
  onUpdate,
  onDelete,
}: PropertiesPanelProps) {
  if (!element) {
    return (
      <div className="p-4 text-center text-gray-500">
        Выберите элемент для редактирования
      </div>
    )
  }

  const hasFont =
    element.type === 'dish_name' ||
    element.type === 'text' ||
    element.type === 'composition' ||
    element.type === 'bju' ||
    element.type === 'weight' ||
    element.type === 'datetime' ||
    element.type === 'shelf_life'

  const hasFontWeight =
    element.type === 'dish_name' ||
    element.type === 'text' ||
    element.type === 'composition' ||
    element.type === 'bju' ||
    element.type === 'weight' ||
    element.type === 'datetime' ||
    element.type === 'shelf_life'

  return (
    <div className="p-4 space-y-4">
      <div className="flex justify-between items-center pb-2 border-b">
        <h3 className="font-semibold text-gray-900">
          {element.type === 'logo' && 'Логотип'}
          {element.type === 'dish_name' && 'Название блюда'}
          {element.type === 'text' && 'Текстовый блок'}
          {element.type === 'composition' && 'Состав'}
          {element.type === 'bju' && 'БЖУ'}
          {element.type === 'weight' && 'Вес'}
          {element.type === 'datetime' && 'Дата/Время'}
          {element.type === 'shelf_life' && 'Срок годности'}
        </h3>
        <button
          onClick={onDelete}
          className="text-red-600 hover:text-red-700 text-sm"
        >
          🗑️ Удалить
        </button>
      </div>

      {/* Position */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Позиция (мм)
        </label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <input
              type="number"
              value={Math.round(element.position.x)}
              onChange={(e) =>
                onUpdate({
                  position: {
                    ...element.position,
                    x: parseFloat(e.target.value) || 0,
                  },
                })
              }
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
              placeholder="X"
            />
          </div>
          <div>
            <input
              type="number"
              value={Math.round(element.position.y)}
              onChange={(e) =>
                onUpdate({
                  position: {
                    ...element.position,
                    y: parseFloat(e.target.value) || 0,
                  },
                })
              }
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
              placeholder="Y"
            />
          </div>
        </div>
      </div>

      {/* Size */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Размер (мм)
        </label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <input
              type="number"
              value={Math.round(element.size.width)}
              onChange={(e) =>
                onUpdate({
                  size: {
                    ...element.size,
                    width: parseFloat(e.target.value) || 5,
                  },
                })
              }
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
              placeholder="Ширина"
            />
          </div>
          <div>
            <input
              type="number"
              value={Math.round(element.size.height)}
              onChange={(e) =>
                onUpdate({
                  size: {
                    ...element.size,
                    height: parseFloat(e.target.value) || 5,
                  },
                })
              }
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
              placeholder="Высота"
            />
          </div>
        </div>
      </div>

      {/* Logo specific */}
      {element.type === 'logo' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Изображение
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) {
                const reader = new FileReader()
                reader.onload = (ev) => {
                  onUpdate({ imageData: ev.target?.result as string })
                }
                reader.readAsDataURL(file)
              }
            }}
            className="block w-full text-sm"
          />
          {element.imageData && (
            <img
              src={element.imageData}
              alt="Logo preview"
              className="mt-2 max-w-full h-20 object-contain border"
            />
          )}
        </div>
      )}

      {/* DishName specific */}
      {element.type === 'dish_name' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Выравнивание
          </label>
          <select
            value={element.align}
            onChange={(e) =>
              onUpdate({ align: e.target.value as 'left' | 'center' | 'right' })
            }
            className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
          >
            <option value="left">Слева</option>
            <option value="center">По центру</option>
            <option value="right">Справа</option>
          </select>
        </div>
      )}

      {/* Text specific */}
      {element.type === 'text' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Текст / Поле
            </label>
            <input
              type="text"
              value={element.content}
              onChange={(e) => onUpdate({ content: e.target.value })}
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
              placeholder="Введите текст или {dish_name}"
            />
            <p className="mt-1 text-xs text-gray-500">
              Используйте: {'{dish_name}'}, {'{weight_g}'}, {'{calories}'}
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Выравнивание
            </label>
            <select
              value={element.align}
              onChange={(e) =>
                onUpdate({ align: e.target.value as 'left' | 'center' | 'right' })
              }
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
            >
              <option value="left">Слева</option>
              <option value="center">По центру</option>
              <option value="right">Справа</option>
            </select>
          </div>
        </>
      )}

      {/* Composition specific */}
      {element.type === 'composition' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Максимум строк
          </label>
          <input
            type="number"
            value={element.maxLines}
            onChange={(e) =>
              onUpdate({ maxLines: parseInt(e.target.value) || 3 })
            }
            className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
            min="1"
            max="10"
          />
        </div>
      )}

      {/* BJU specific */}
      {element.type === 'bju' && (
        <div className="space-y-3">
          <div className="text-sm font-medium text-gray-700 mb-2">
            Отображаемые элементы:
          </div>
          <label className="flex items-center text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={element.showProteins}
              onChange={(e) => onUpdate({ showProteins: e.target.checked })}
              className="mr-3 w-4 h-4"
            />
            <span className="text-gray-700">Белки</span>
          </label>
          <label className="flex items-center text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={element.showFats}
              onChange={(e) => onUpdate({ showFats: e.target.checked })}
              className="mr-3 w-4 h-4"
            />
            <span className="text-gray-700">Жиры</span>
          </label>
          <label className="flex items-center text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={element.showCarbs}
              onChange={(e) => onUpdate({ showCarbs: e.target.checked })}
              className="mr-3 w-4 h-4"
            />
            <span className="text-gray-700">Углеводы</span>
          </label>
          <label className="flex items-center text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={element.showCalories}
              onChange={(e) => onUpdate({ showCalories: e.target.checked })}
              className="mr-3 w-4 h-4"
            />
            <span className="text-gray-700">Калории</span>
          </label>
        </div>
      )}

      {/* DateTime specific */}
      {element.type === 'datetime' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Подпись
            </label>
            <input
              type="text"
              value={element.label}
              onChange={(e) => onUpdate({ label: e.target.value })}
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
              placeholder="Дата производства:"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Формат
            </label>
            <select
              value={element.format}
              onChange={(e) =>
                onUpdate({
                  format: e.target.value as 'datetime' | 'date' | 'time',
                })
              }
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
            >
              <option value="datetime">Дата и время</option>
              <option value="date">Только дата</option>
              <option value="time">Только время</option>
            </select>
          </div>
        </>
      )}

      {/* ShelfLife specific */}
      {element.type === 'shelf_life' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Срок годности (часы)
          </label>
          <input
            type="number"
            value={element.hours}
            onChange={(e) => onUpdate({ hours: parseInt(e.target.value) || 6 })}
            className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
            min="1"
          />
        </div>
      )}

      {/* Font settings */}
      {hasFont && 'fontSize' in element && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Шрифт
            </label>
            <select
              value={element.fontFamily}
              onChange={(e) =>
                onUpdate({ fontFamily: e.target.value as FontFamily })
              }
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
            >
              {fontFamilies.map((font) => (
                <option key={font} value={font}>
                  {font}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Размер шрифта
            </label>
            <input
              type="number"
              value={element.fontSize}
              onChange={(e) =>
                onUpdate({ fontSize: parseInt(e.target.value) || 12 })
              }
              className="block w-full px-2 py-1 text-sm border border-gray-300 rounded"
              min="6"
              max="72"
            />
          </div>
          {hasFontWeight && 'fontWeight' in element && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Жирность: {element.fontWeight}
              </label>
              <input
                type="range"
                min="100"
                max="900"
                step="100"
                value={element.fontWeight}
                onChange={(e) =>
                  onUpdate({ fontWeight: parseInt(e.target.value) as 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 })
                }
                className="block w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>100 (тонкий)</span>
                <span>400 (норма)</span>
                <span>700 (жирный)</span>
                <span>900 (очень жирный)</span>
              </div>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Цвет
            </label>
            <input
              type="color"
              value={element.color}
              onChange={(e) => onUpdate({ color: e.target.value })}
              className="block w-full h-8 border border-gray-300 rounded"
            />
          </div>
        </>
      )}

      {/* Visibility */}
      <div>
        <label className="flex items-center text-sm">
          <input
            type="checkbox"
            checked={element.visible}
            onChange={(e) => onUpdate({ visible: e.target.checked })}
            className="mr-2"
          />
          Отображать элемент
        </label>
      </div>
    </div>
  )
}
