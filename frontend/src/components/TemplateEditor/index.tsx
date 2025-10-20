/**
 * Template Editor
 * Визуальный редактор шаблонов этикеток
 */

import { useState } from 'react'
import Canvas from './Canvas'
import Toolbar from './Toolbar'
import PropertiesPanel from './PropertiesPanel'
import {
  Template,
  TemplateElement,
  ElementType,
  Position,
  TemplateConfig,
} from './types'

interface TemplateEditorProps {
  template: Template
  onSave: (config: TemplateConfig) => void
  onCancel: () => void
  onTestPrint: () => void
}

export default function TemplateEditor({
  template,
  onSave,
  onCancel,
  onTestPrint,
}: TemplateEditorProps) {
  const [config, setConfig] = useState<TemplateConfig>(
    template.config || {
      paper_width_mm: 58,
      paper_height_mm: 60,
      paper_gap_mm: 2,
      elements: [],
    }
  )

  const [selectedElementId, setSelectedElementId] = useState<string | null>(null)

  const selectedElement = config.elements.find((el) => el.id === selectedElementId)

  const generateId = () => {
    return `el_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  const createDefaultElement = (type: ElementType): TemplateElement => {
    const base = {
      id: generateId(),
      type,
      position: { x: 10, y: 10 },
      size: { width: 40, height: 10 },
      visible: true,
    }

    switch (type) {
      case 'logo':
        return { ...base, type: 'logo' }
      case 'text':
        return {
          ...base,
          type: 'text',
          content: 'Текст',
          fontSize: 14,
          fontFamily: 'Arial',
          fontWeight: 'normal',
          color: '#000000',
          align: 'left',
        }
      case 'composition':
        return {
          ...base,
          type: 'composition',
          fontSize: 10,
          fontFamily: 'Arial',
          color: '#000000',
          maxLines: 3,
        }
      case 'bju':
        return {
          ...base,
          type: 'bju',
          fontSize: 10,
          fontFamily: 'Arial',
          color: '#000000',
          showProteins: true,
          showFats: true,
          showCarbs: true,
          showCalories: true,
        }
      case 'weight':
        return {
          ...base,
          type: 'weight',
          fontSize: 12,
          fontFamily: 'Arial',
          color: '#000000',
          showUnit: true,
        }
      case 'datetime':
        return {
          ...base,
          type: 'datetime',
          fontSize: 10,
          fontFamily: 'Arial',
          color: '#000000',
          format: 'datetime',
          label: 'Дата производства:',
        }
      case 'shelf_life':
        return {
          ...base,
          type: 'shelf_life',
          fontSize: 10,
          fontFamily: 'Arial',
          color: '#000000',
          hours: 6,
        }
      default:
        return base as any
    }
  }

  const handleAddElement = (type: ElementType) => {
    const newElement = createDefaultElement(type)
    setConfig({
      ...config,
      elements: [...config.elements, newElement],
    })
    setSelectedElementId(newElement.id)
  }

  const handleElementMove = (id: string, position: Position) => {
    setConfig({
      ...config,
      elements: config.elements.map((el) =>
        el.id === id ? { ...el, position } : el
      ),
    })
  }

  const handleElementResize = (id: string, width: number, height: number) => {
    setConfig({
      ...config,
      elements: config.elements.map((el) =>
        el.id === id ? { ...el, size: { width, height } } : el
      ),
    })
  }

  const handleElementUpdate = (updates: Partial<TemplateElement>) => {
    if (!selectedElementId) return

    setConfig({
      ...config,
      elements: config.elements.map((el) =>
        el.id === selectedElementId ? { ...el, ...updates } : el
      ),
    })
  }

  const handleElementDelete = () => {
    if (!selectedElementId) return

    setConfig({
      ...config,
      elements: config.elements.filter((el) => el.id !== selectedElementId),
    })
    setSelectedElementId(null)
  }

  const handleSave = () => {
    onSave(config)
  }

  return (
    <div className="fixed inset-0 z-50 bg-white flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Редактор шаблона: {template.name}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Перетаскивайте элементы и настраивайте их свойства
            </p>
          </div>
          <div className="flex gap-3">
            {template.id !== 0 && (
              <button
                onClick={onTestPrint}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
              >
                🖨️ Тестовая печать
              </button>
            )}
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Отмена
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700"
            >
              Сохранить
            </button>
          </div>
        </div>

        {/* Paper size settings */}
        <div className="mt-4 flex gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Ширина (мм)
            </label>
            <input
              type="number"
              value={config.paper_width_mm}
              onChange={(e) =>
                setConfig({
                  ...config,
                  paper_width_mm: parseInt(e.target.value) || 58,
                })
              }
              className="block w-20 px-2 py-1 text-sm border border-gray-300 rounded"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Высота (мм)
            </label>
            <input
              type="number"
              value={config.paper_height_mm}
              onChange={(e) =>
                setConfig({
                  ...config,
                  paper_height_mm: parseInt(e.target.value) || 60,
                })
              }
              className="block w-20 px-2 py-1 text-sm border border-gray-300 rounded"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Отступ (мм)
            </label>
            <input
              type="number"
              value={config.paper_gap_mm}
              onChange={(e) =>
                setConfig({
                  ...config,
                  paper_gap_mm: parseInt(e.target.value) || 2,
                })
              }
              className="block w-20 px-2 py-1 text-sm border border-gray-300 rounded"
            />
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar - Toolbar */}
        <div className="w-64 flex-shrink-0 bg-white border-r overflow-y-auto">
          <Toolbar onAddElement={handleAddElement} />
        </div>

        {/* Canvas area */}
        <div className="flex-1 bg-gray-100 p-8 overflow-auto flex items-center justify-center">
          <Canvas
            width={config.paper_width_mm}
            height={config.paper_height_mm}
            elements={config.elements}
            selectedElementId={selectedElementId}
            onElementSelect={setSelectedElementId}
            onElementMove={handleElementMove}
            onElementResize={handleElementResize}
          />
        </div>

        {/* Right sidebar - Properties */}
        <div className="w-80 flex-shrink-0 bg-white border-l overflow-y-auto">
          <PropertiesPanel
            element={selectedElement || null}
            onUpdate={handleElementUpdate}
            onDelete={handleElementDelete}
          />
        </div>
      </div>
    </div>
  )
}
