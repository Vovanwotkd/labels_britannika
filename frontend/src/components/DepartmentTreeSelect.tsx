/**
 * DepartmentTreeSelect Component
 * Multi-select для выбора подразделений на разных уровнях иерархии
 */

import { useState, useEffect } from 'react'
import { departmentsApi, type DepartmentsTreeResponse } from '../api/client'

interface DepartmentTreeSelectProps {
  value: Record<string, string[]>
  onChange: (value: Record<string, string[]>) => void
}

export default function DepartmentTreeSelect({ value, onChange }: DepartmentTreeSelectProps) {
  const [tree, setTree] = useState<DepartmentsTreeResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadTree()
  }, [])

  const loadTree = async () => {
    try {
      setLoading(true)
      const data = await departmentsApi.getTree()
      setTree(data)
      setError(data.error || null)
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки подразделений')
    } finally {
      setLoading(false)
    }
  }

  const handleLevelChange = (level: string, departmentName: string, checked: boolean) => {
    const levelValues = value[level] || []
    const newValues = checked
      ? [...levelValues, departmentName]
      : levelValues.filter((v) => v !== departmentName)

    onChange({
      ...value,
      [level]: newValues,
    })
  }

  const isChecked = (level: string, departmentName: string) => {
    return (value[level] || []).includes(departmentName)
  }

  if (loading) {
    return <div className="text-gray-500 text-sm">Загрузка подразделений...</div>
  }

  if (error) {
    return (
      <div className="text-red-600 text-sm">
        Ошибка: {error}
        <button onClick={loadTree} className="ml-2 underline">
          Повторить
        </button>
      </div>
    )
  }

  if (!tree) {
    return <div className="text-gray-500 text-sm">Нет данных</div>
  }

  const levels = [
    { key: 'level_1', label: 'Уровень 1 (Рестораны/Меню)', items: tree.level_1 },
    { key: 'level_2', label: 'Уровень 2 (Подразделения)', items: tree.level_2 },
    { key: 'level_3', label: 'Уровень 3 (Категории)', items: tree.level_3 },
    { key: 'level_4', label: 'Уровень 4', items: tree.level_4 },
    { key: 'level_5', label: 'Уровень 5', items: tree.level_5 },
    { key: 'level_6', label: 'Уровень 6', items: tree.level_6 },
  ]

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-600 mb-2">
        Выберите подразделения для фильтрации блюд. Можно выбрать несколько на разных
        уровнях.
      </div>

      {levels.map((level) => {
        if (level.items.length === 0) return null

        return (
          <div key={level.key} className="border border-gray-200 rounded-md p-4">
            <h4 className="font-medium text-gray-900 mb-3">{level.label}</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {level.items.map((item) => (
                <label
                  key={item.name}
                  className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                >
                  <input
                    type="checkbox"
                    checked={isChecked(level.key, item.name)}
                    onChange={(e) =>
                      handleLevelChange(level.key, item.name, e.target.checked)
                    }
                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-2 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-700">
                    {item.name}{' '}
                    <span className="text-gray-400">({item.count})</span>
                  </span>
                </label>
              ))}
            </div>
          </div>
        )
      })}

      {/* Показываем что выбрано */}
      {Object.keys(value).some((k) => value[k]?.length > 0) && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <div className="text-sm font-medium text-blue-900 mb-2">Выбрано:</div>
          <div className="text-sm text-blue-700 space-y-1">
            {Object.entries(value).map(([level, items]) => {
              if (!items || items.length === 0) return null
              return (
                <div key={level}>
                  <span className="font-medium">{level}:</span> {items.join(', ')}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
