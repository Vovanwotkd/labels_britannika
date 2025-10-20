/**
 * Templates Page
 * Страница управления шаблонами этикеток
 */

import { useState, useEffect } from 'react'
import { templatesApi } from '../api/client'
import TemplateEditor from '../components/TemplateEditor'
import type { Template, TemplateConfig } from '../components/TemplateEditor/types'

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
        paper_width_mm: 58,
        paper_height_mm: 60,
        paper_gap_mm: 2,
        elements: [],
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

  const handleSave = async (config: TemplateConfig) => {
    if (!selectedTemplate) return

    try {
      const updatedTemplate: Template = {
        ...selectedTemplate,
        config,
      }

      if (updatedTemplate.id === 0) {
        await templatesApi.create(updatedTemplate)
      } else {
        await templatesApi.update(updatedTemplate.id, updatedTemplate)
      }
      await loadTemplates()
      setIsEditorOpen(false)
      setSelectedTemplate(null)
    } catch (err) {
      alert('Ошибка сохранения шаблона')
      console.error(err)
    }
  }

  const handleTestPrint = async () => {
    if (!selectedTemplate || selectedTemplate.id === 0) {
      alert('Сначала сохраните шаблон')
      return
    }

    try {
      await templatesApi.testPrint(selectedTemplate.id)
      alert('Тестовая этикетка отправлена на печать!')
    } catch (err) {
      alert('Ошибка печати: ' + (err instanceof Error ? err.message : 'Unknown error'))
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
                <div>Элементов: {template.config.elements?.length || 0}</div>
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

      {/* Visual Template Editor */}
      {isEditorOpen && selectedTemplate && (
        <TemplateEditor
          template={selectedTemplate}
          onSave={handleSave}
          onCancel={() => {
            setIsEditorOpen(false)
            setSelectedTemplate(null)
          }}
          onTestPrint={handleTestPrint}
        />
      )}
    </div>
  )
}
