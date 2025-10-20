/**
 * Toolbar Component
 * Панель инструментов для добавления элементов
 */

import { ElementType } from './types'

interface ToolbarProps {
  onAddElement: (type: ElementType) => void
}

const tools = [
  { type: 'logo' as ElementType, icon: '🖼️', label: 'Логотип' },
  { type: 'text' as ElementType, icon: '📝', label: 'Текст' },
  { type: 'composition' as ElementType, icon: '📋', label: 'Состав' },
  { type: 'bju' as ElementType, icon: '🥗', label: 'БЖУ' },
  { type: 'weight' as ElementType, icon: '⚖️', label: 'Вес' },
  { type: 'datetime' as ElementType, icon: '📅', label: 'Дата/Время' },
  { type: 'shelf_life' as ElementType, icon: '⏰', label: 'Срок годности' },
]

export default function Toolbar({ onAddElement }: ToolbarProps) {
  return (
    <div className="p-4 bg-gray-50 border-b">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Добавить элемент:
      </h3>
      <div className="flex flex-col gap-2">
        {tools.map((tool) => (
          <button
            key={tool.type}
            onClick={() => onAddElement(tool.type)}
            className="flex items-center gap-3 px-3 py-2.5 text-sm bg-white border border-gray-300 rounded hover:bg-primary-50 hover:border-primary-500 transition-colors text-left"
          >
            <span className="text-xl flex-shrink-0">{tool.icon}</span>
            <span className="font-medium text-gray-700">{tool.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
