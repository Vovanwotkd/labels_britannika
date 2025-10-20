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
  LogoElement,
  TextElement,
  CompositionElement,
  BJUElement,
  WeightElement,
  DateTimeElement,
  ShelfLifeElement,
} from './types'

interface TemplateEditorProps {
  template: Template
  onSave: (config: TemplateConfig, name: string, brandId: string) => void
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
  const [zoom, setZoom] = useState<number>(100) // Масштаб в процентах
  const [templateName, setTemplateName] = useState<string>(template.name)
  const [brandId, setBrandId] = useState<string>(template.brand_id || '')

  const selectedElement = config.elements.find((el) => el.id === selectedElementId)

  const generateId = () => {
    return `el_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  const createDefaultElement = (type: ElementType): TemplateElement => {
    const id = generateId()
    const position = { x: 10, y: 10 }
    const size = { width: 40, height: 10 }
    const visible = true

    switch (type) {
      case 'logo':
        return { id, type: 'logo', position, size, visible } as LogoElement
      case 'text':
        return {
          id,
          type: 'text',
          position,
          size,
          visible,
          content: 'Текст',
          fontSize: 14,
          fontFamily: 'Arial',
          fontWeight: 'normal',
          color: '#000000',
          align: 'left',
        } as TextElement
      case 'composition':
        return {
          id,
          type: 'composition',
          position,
          size,
          visible,
          fontSize: 10,
          fontFamily: 'Arial',
          color: '#000000',
          maxLines: 3,
        } as CompositionElement
      case 'bju':
        return {
          id,
          type: 'bju',
          position,
          size,
          visible,
          fontSize: 10,
          fontFamily: 'Arial',
          color: '#000000',
          showProteins: true,
          showFats: true,
          showCarbs: true,
          showCalories: true,
        } as BJUElement
      case 'weight':
        return {
          id,
          type: 'weight',
          position,
          size,
          visible,
          fontSize: 12,
          fontFamily: 'Arial',
          color: '#000000',
          showUnit: true,
        } as WeightElement
      case 'datetime':
        return {
          id,
          type: 'datetime',
          position,
          size,
          visible,
          fontSize: 10,
          fontFamily: 'Arial',
          color: '#000000',
          format: 'datetime',
          label: 'Дата производства:',
        } as DateTimeElement
      case 'shelf_life':
        return {
          id,
          type: 'shelf_life',
          position,
          size,
          visible,
          fontSize: 10,
          fontFamily: 'Arial',
          color: '#000000',
          hours: 6,
        } as ShelfLifeElement
      default:
        return {
          id,
          type: 'text',
          position,
          size,
          visible,
          content: '',
          fontSize: 12,
          fontFamily: 'Arial',
          fontWeight: 'normal',
          color: '#000000',
          align: 'left',
        } as TextElement
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
        el.id === selectedElementId ? ({ ...el, ...updates } as TemplateElement) : el
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
    if (!templateName.trim()) {
      alert('Укажите название шаблона')
      return
    }
    onSave(config, templateName, brandId)
  }

  return (
    <div className="fixed inset-0 z-50 bg-white flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex-1 max-w-xl">
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Название шаблона *
            </label>
            <input
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Например: Britannica Pizza"
            />
          </div>
          <div className="flex-1 max-w-xs ml-4">
            <label className="block text-xs font-medium text-gray-700 mb-1">
              ID бренда (опционально)
            </label>
            <input
              type="text"
              value={brandId}
              onChange={(e) => setBrandId(e.target.value)}
              className="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="britannica_pizza"
            />
          </div>
          <div className="flex gap-3 ml-4">
            <button
              onClick={onTestPrint}
              disabled={template.id === 0}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              title={template.id === 0 ? 'Сначала сохраните шаблон' : 'Тестовая печать'}
            >
              🖨️ Тест
            </button>
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
        <p className="text-xs text-gray-500 mt-2">
          Перетаскивайте элементы и настраивайте их свойства
        </p>

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
          <div className="ml-auto flex items-center gap-2">
            <label className="block text-xs font-medium text-gray-700">
              Масштаб:
            </label>
            <button
              onClick={() => setZoom(Math.max(50, zoom - 25))}
              className="px-2 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50"
            >
              -
            </button>
            <span className="text-sm font-medium text-gray-700 min-w-[50px] text-center">
              {zoom}%
            </span>
            <button
              onClick={() => setZoom(Math.min(200, zoom + 25))}
              className="px-2 py-1 text-sm bg-white border border-gray-300 rounded hover:bg-gray-50"
            >
              +
            </button>
            <button
              onClick={() => setZoom(100)}
              className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50"
            >
              100%
            </button>
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
          <div style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'center' }}>
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
