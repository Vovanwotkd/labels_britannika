/**
 * Table Selector Modal
 * Модальное окно для выбора столов из RKeeper
 */

import { useState, useEffect } from 'react'
import { rkeeperApi } from '../api/client'

interface Table {
  code: string
  name: string
}

interface TableSelectorModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (selectedTables: Table[]) => Promise<void>
}

export default function TableSelectorModal({
  isOpen,
  onClose,
  onSave,
}: TableSelectorModalProps) {
  const [tables, setTables] = useState<Table[]>([])
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Загрузка столов из RKeeper
  useEffect(() => {
    if (isOpen) {
      loadTables()
      loadSelectedTables()
    }
  }, [isOpen])

  const loadTables = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await rkeeperApi.getTables()
      setTables(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки столов')
    } finally {
      setLoading(false)
    }
  }

  const loadSelectedTables = async () => {
    try {
      const data = await rkeeperApi.getSelectedTables()
      setSelectedCodes(new Set(data.map((t: Table) => t.code)))
    } catch (err) {
      console.error('Failed to load selected tables:', err)
    }
  }

  const handleToggle = (code: string) => {
    setSelectedCodes((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(code)) {
        newSet.delete(code)
      } else {
        newSet.add(code)
      }
      return newSet
    })
  }

  const handleSelectAll = () => {
    setSelectedCodes(new Set(filteredTables.map((t) => t.code)))
  }

  const handleDeselectAll = () => {
    setSelectedCodes(new Set())
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      const selectedTables = tables.filter((t) => selectedCodes.has(t.code))
      await onSave(selectedTables)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  // Фильтрация столов по поисковому запросу
  const filteredTables = tables.filter(
    (table) =>
      table.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      table.code.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-medium text-gray-900">
                Выбор столов из RKeeper
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-500"
              >
                <span className="text-2xl">&times;</span>
              </button>
            </div>

            {/* Search */}
            <div className="mt-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Поиск по названию или коду..."
                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>

            {/* Actions */}
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleSelectAll}
                disabled={loading}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
              >
                Выбрать все
              </button>
              <button
                onClick={handleDeselectAll}
                disabled={loading}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
              >
                Снять все
              </button>
              <div className="flex-1 text-sm text-gray-600 flex items-center justify-end">
                Выбрано: {selectedCodes.size} из {filteredTables.length}
              </div>
            </div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {loading && (
              <div className="text-center py-8 text-gray-600">
                Загрузка столов из RKeeper...
              </div>
            )}

            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <div className="text-sm text-red-800">{error}</div>
                <button
                  onClick={loadTables}
                  className="mt-2 text-sm text-red-600 underline"
                >
                  Повторить
                </button>
              </div>
            )}

            {!loading && !error && filteredTables.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                {searchQuery
                  ? 'Столы не найдены'
                  : 'Нет активных столов в RKeeper'}
              </div>
            )}

            {!loading && !error && filteredTables.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {filteredTables.map((table) => (
                  <label
                    key={table.code}
                    className={`
                      flex items-center p-3 rounded border cursor-pointer transition-colors
                      ${
                        selectedCodes.has(table.code)
                          ? 'bg-primary-50 border-primary-500'
                          : 'bg-white border-gray-300 hover:bg-gray-50'
                      }
                    `}
                  >
                    <input
                      type="checkbox"
                      checked={selectedCodes.has(table.code)}
                      onChange={() => handleToggle(table.code)}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-900">
                      {table.name}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              Отмена
            </button>
            <button
              onClick={handleSave}
              disabled={saving || loading}
              className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
            >
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
