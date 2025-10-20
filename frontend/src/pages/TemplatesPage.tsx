/**
 * Templates Page
 * Страница управления шаблонами этикеток
 */

import { useState, useEffect } from 'react'
import { templatesApi } from '../api/client'

interface Template {
  id: number
  name: string
  brand_id: string
  is_default: boolean
  config: TemplateConfig
  created_at?: string
  updated_at?: string
}

interface TemplateConfig {
  paper_width_mm: number
  paper_height_mm: number
  paper_gap_mm: number
  shelf_life_hours: number
  logo?: {
    enabled: boolean
    path?: string
    x: number
    y: number
  }
  title?: {
    font: string
    x: number
    y: number
  }
  weight_calories?: {
    font: string
    x: number
    y: number
  }
  bju?: {
    enabled: boolean
    font: string
    x: number
    y: number
  }
  ingredients?: {
    enabled: boolean
    font: string
    x: number
    y: number
    max_lines?: number
  }
  datetime_shelf?: {
    font: string
    x: number
    y: number
  }
  barcode?: {
    type: string
    x: number
    y: number
    height: number
    narrow_bar: number
  }
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [isEditorOpen, setIsEditorOpen] = useState(false)

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      setLoading(true)
      const data = await templatesApi.getAll()
      setTemplates(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки шаблонов')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    const newTemplate: Template = {
      id: 0,
      name: 'Новый шаблон',
      brand_id: '',
      is_default: false,
      config: {
        paper_width_mm: 60,
        paper_height_mm: 60,
        paper_gap_mm: 2,
        shelf_life_hours: 6,
        logo: { enabled: false, x: 5, y: 5 },
        title: { font: '3', x: 10, y: 30 },
        weight_calories: { font: '2', x: 10, y: 60 },
        bju: { enabled: true, font: '2', x: 10, y: 80 },
        ingredients: { enabled: true, font: '1', x: 10, y: 100, max_lines: 3 },
        datetime_shelf: { font: '2', x: 10, y: 140 },
        barcode: { type: '128', x: 10, y: 170, height: 50, narrow_bar: 2 },
      },
    }
    setSelectedTemplate(newTemplate)
    setIsEditorOpen(true)
  }

  const handleEdit = (template: Template) => {
    setSelectedTemplate(template)
    setIsEditorOpen(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить шаблон?')) return

    try {
      await templatesApi.delete(id)
      await loadTemplates()
    } catch (err) {
      alert('Ошибка удаления шаблона')
      console.error(err)
    }
  }

  const handleSave = async (template: Template) => {
    try {
      if (template.id === 0) {
        await templatesApi.create(template)
      } else {
        await templatesApi.update(template.id, template)
      }
      await loadTemplates()
      setIsEditorOpen(false)
      setSelectedTemplate(null)
    } catch (err) {
      alert('Ошибка сохранения шаблона')
      console.error(err)
    }
  }

  const handleSetDefault = async (id: number) => {
    try {
      await templatesApi.setDefault(id)
      await loadTemplates()
    } catch (err) {
      alert('Ошибка установки шаблона по умолчанию')
      console.error(err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-xl text-gray-600">Загрузка шаблонов...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <div className="text-sm text-red-800">{error}</div>
        <button
          onClick={loadTemplates}
          className="mt-2 text-sm text-red-600 underline"
        >
          Повторить
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Шаблоны этикеток</h1>

        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          Создать шаблон
        </button>
      </div>

      {/* Templates Grid */}
      {templates.length === 0 ? (
        <div className="text-center py-12 bg-white shadow rounded-lg">
          <div className="text-gray-500">Шаблонов нет</div>
          <button
            onClick={handleCreate}
            className="mt-4 text-primary-600 hover:text-primary-700"
          >
            Создать первый шаблон
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((template) => (
            <div
              key={template.id}
              className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {template.name}
                  </h3>
                  {template.brand_id && (
                    <p className="text-sm text-gray-500">{template.brand_id}</p>
                  )}
                </div>
                {template.is_default && (
                  <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                    По умолчанию
                  </span>
                )}
              </div>

              <div className="space-y-2 mb-4 text-sm text-gray-600">
                <div>
                  Размер: {template.config.paper_width_mm} × {template.config.paper_height_mm} мм
                </div>
                <div>Срок годности: {template.config.shelf_life_hours} ч</div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => handleEdit(template)}
                  className="flex-1 px-3 py-2 text-sm bg-primary-50 text-primary-700 rounded hover:bg-primary-100"
                >
                  Редактировать
                </button>
                {!template.is_default && (
                  <button
                    onClick={() => handleSetDefault(template.id)}
                    className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    title="Установить по умолчанию"
                  >
                    ⭐
                  </button>
                )}
                <button
                  onClick={() => handleDelete(template.id)}
                  className="px-3 py-2 text-sm bg-red-50 text-red-700 rounded hover:bg-red-100"
                  disabled={template.is_default}
                  title={template.is_default ? 'Нельзя удалить шаблон по умолчанию' : 'Удалить'}
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Template Editor Modal */}
      {isEditorOpen && selectedTemplate && (
        <TemplateEditorModal
          template={selectedTemplate}
          onSave={handleSave}
          onClose={() => {
            setIsEditorOpen(false)
            setSelectedTemplate(null)
          }}
        />
      )}
    </div>
  )
}

// Template Editor Modal Component
interface TemplateEditorModalProps {
  template: Template
  onSave: (template: Template) => void
  onClose: () => void
}

function TemplateEditorModal({ template, onSave, onClose }: TemplateEditorModalProps) {
  const [editedTemplate, setEditedTemplate] = useState<Template>(template)
  const [printing, setPrinting] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(editedTemplate)
  }

  const handleTestPrint = async () => {
    if (editedTemplate.id === 0) {
      alert('Сначала сохраните шаблон')
      return
    }

    try {
      setPrinting(true)
      await templatesApi.testPrint(editedTemplate.id)
      alert('Тестовая этикетка отправлена на печать!')
    } catch (err) {
      alert('Ошибка печати: ' + (err instanceof Error ? err.message : 'Unknown error'))
      console.error(err)
    } finally {
      setPrinting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">
                {template.id === 0 ? 'Создание шаблона' : 'Редактирование шаблона'}
              </h3>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
                <span className="text-2xl">&times;</span>
              </button>
            </div>
          </div>

          {/* Body */}
          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-6 py-4">
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Название шаблона *
                  </label>
                  <input
                    type="text"
                    required
                    value={editedTemplate.name}
                    onChange={(e) =>
                      setEditedTemplate({ ...editedTemplate, name: e.target.value })
                    }
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    ID бренда
                  </label>
                  <input
                    type="text"
                    value={editedTemplate.brand_id}
                    onChange={(e) =>
                      setEditedTemplate({ ...editedTemplate, brand_id: e.target.value })
                    }
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    placeholder="britannica_pizza"
                  />
                </div>
              </div>

              {/* Paper Settings */}
              <div>
                <h4 className="text-md font-medium text-gray-900 mb-3">Размер этикетки</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Ширина (мм)
                    </label>
                    <input
                      type="number"
                      required
                      value={editedTemplate.config.paper_width_mm}
                      onChange={(e) =>
                        setEditedTemplate({
                          ...editedTemplate,
                          config: {
                            ...editedTemplate.config,
                            paper_width_mm: parseInt(e.target.value),
                          },
                        })
                      }
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Высота (мм)
                    </label>
                    <input
                      type="number"
                      required
                      value={editedTemplate.config.paper_height_mm}
                      onChange={(e) =>
                        setEditedTemplate({
                          ...editedTemplate,
                          config: {
                            ...editedTemplate.config,
                            paper_height_mm: parseInt(e.target.value),
                          },
                        })
                      }
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Отступ (мм)
                    </label>
                    <input
                      type="number"
                      required
                      value={editedTemplate.config.paper_gap_mm}
                      onChange={(e) =>
                        setEditedTemplate({
                          ...editedTemplate,
                          config: {
                            ...editedTemplate.config,
                            paper_gap_mm: parseInt(e.target.value),
                          },
                        })
                      }
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md"
                    />
                  </div>
                </div>
              </div>

              {/* Shelf Life */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Срок годности (часы)
                </label>
                <input
                  type="number"
                  required
                  value={editedTemplate.config.shelf_life_hours}
                  onChange={(e) =>
                    setEditedTemplate({
                      ...editedTemplate,
                      config: {
                        ...editedTemplate.config,
                        shelf_life_hours: parseInt(e.target.value),
                      },
                    })
                  }
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>

              {/* Note */}
              <div className="rounded-md bg-blue-50 p-4">
                <p className="text-sm text-blue-700">
                  Дополнительные настройки позиционирования элементов (логотип, текст, штрихкод)
                  будут добавлены в следующих версиях
                </p>
              </div>
            </div>
          </form>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
            <div>
              {editedTemplate.id !== 0 && (
                <button
                  type="button"
                  onClick={handleTestPrint}
                  disabled={printing}
                  className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
                >
                  {printing ? 'Печать...' : '🖨️ Тестовая печать'}
                </button>
              )}
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Отмена
              </button>
              <button
                type="submit"
                onClick={handleSubmit}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700"
              >
                Сохранить
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
