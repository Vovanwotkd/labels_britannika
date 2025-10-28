/**
 * DepartmentTreeSelect Component
 * Иерархический multi-select для выбора подразделений с каскадной фильтрацией
 */

import { useState, useEffect, useMemo } from 'react'
import { departmentsApi } from '../api/client'

interface TreeNode {
  name: string
  count: number
  level: number
  children?: TreeNode[]
}

interface DepartmentsTreeResponse {
  tree: TreeNode[]
  error?: string
}

interface DepartmentTreeSelectProps {
  value: Record<string, string[]>
  onChange: (value: Record<string, string[]>) => void
}

export default function DepartmentTreeSelect({ value, onChange }: DepartmentTreeSelectProps) {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadTree()
  }, [])

  const loadTree = async () => {
    try {
      setLoading(true)
      const data: DepartmentsTreeResponse = await departmentsApi.getTree()
      setTree(data.tree || [])
      setError(data.error || null)
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки подразделений')
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = (level: number, name: string, checked: boolean) => {
    const levelKey = `level_${level}`
    const levelValues = value[levelKey] || []

    const newValues = checked
      ? [...levelValues, name]
      : levelValues.filter((v) => v !== name)

    const newValue = {
      ...value,
      [levelKey]: newValues,
    }

    // Если снимаем галочку с родителя - очищаем всех детей этого родителя
    if (!checked) {
      // Очищаем выборы на всех нижних уровнях которые зависят от этого родителя
      for (let i = level + 1; i <= 6; i++) {
        const childLevelKey = `level_${i}`
        if (newValue[childLevelKey]) {
          // Фильтруем детей: оставляем только тех, кто не принадлежит снятому родителю
          const validChildren = getValidChildrenForLevel(i, newValue, tree)
          newValue[childLevelKey] = newValue[childLevelKey].filter((child: string) =>
            validChildren.some((node) => node.name === child)
          )
        }
      }
    }

    onChange(newValue)
  }

  const isChecked = (level: number, name: string) => {
    const levelKey = `level_${level}`
    return (value[levelKey] || []).includes(name)
  }

  // Получить список валидных узлов для уровня с учётом выбранных родителей
  const getValidChildrenForLevel = (level: number, selections: Record<string, string[]>, nodes: TreeNode[]): TreeNode[] => {
    if (level === 1) {
      return nodes
    }

    const parentLevel = level - 1
    const parentKey = `level_${parentLevel}`
    const selectedParents = selections[parentKey] || []

    // Если ничего не выбрано на предыдущем уровне - показываем всё
    if (selectedParents.length === 0) {
      return getAllNodesAtLevel(nodes, level)
    }

    // Собираем детей только от выбранных родителей
    const validNodes: TreeNode[] = []

    function traverse(currentNodes: TreeNode[], currentLevel: number) {
      for (const node of currentNodes) {
        if (currentLevel === parentLevel && selectedParents.includes(node.name)) {
          // Нашли выбранного родителя - добавляем его детей
          if (node.children) {
            validNodes.push(...node.children)
          }
        } else if (node.children && currentLevel < parentLevel) {
          // Продолжаем спускаться вниз
          traverse(node.children, currentLevel + 1)
        }
      }
    }

    traverse(nodes, 1)
    return validNodes
  }

  // Получить все узлы на определённом уровне (без фильтрации по родителям)
  const getAllNodesAtLevel = (nodes: TreeNode[], targetLevel: number): TreeNode[] => {
    const result: TreeNode[] = []

    function traverse(currentNodes: TreeNode[], currentLevel: number) {
      for (const node of currentNodes) {
        if (currentLevel === targetLevel) {
          result.push(node)
        } else if (node.children && currentLevel < targetLevel) {
          traverse(node.children, currentLevel + 1)
        }
      }
    }

    traverse(nodes, 1)
    return result
  }

  // Группируем узлы по уровням с учётом выбора
  const levelGroups = useMemo(() => {
    const groups: { level: number; label: string; nodes: TreeNode[] }[] = []

    for (let level = 1; level <= 6; level++) {
      const nodes = getValidChildrenForLevel(level, value, tree)

      if (nodes.length > 0) {
        const labels: Record<number, string> = {
          1: 'Уровень 1 (Рестораны/Меню)',
          2: 'Уровень 2 (Подразделения)',
          3: 'Уровень 3 (Категории)',
          4: 'Уровень 4',
          5: 'Уровень 5',
          6: 'Уровень 6',
        }

        groups.push({
          level,
          label: labels[level],
          nodes,
        })
      }
    }

    return groups
  }, [tree, value])

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

  if (tree.length === 0) {
    return (
      <div className="text-gray-500 text-sm">
        Нет данных. Выполните синхронизацию с StoreHouse.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-600 mb-2">
        Выберите подразделения из которых берутся блюда. Используется для фильтрации дублей по RKeeper кодам из разных ресторанов.
      </div>

      {levelGroups.map((group) => (
        <div key={group.level} className="border border-gray-200 rounded-md p-4">
          <h4 className="font-medium text-gray-900 mb-3">{group.label}</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {group.nodes.map((node) => (
              <label
                key={node.name}
                className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
              >
                <input
                  type="checkbox"
                  checked={isChecked(group.level, node.name)}
                  onChange={(e) => handleToggle(group.level, node.name, e.target.checked)}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-2 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700">
                  {node.name}{' '}
                  <span className="text-gray-400 text-xs">({node.count})</span>
                </span>
              </label>
            ))}
          </div>
        </div>
      ))}

      {/* Показываем что выбрано */}
      {Object.keys(value).some((k) => value[k]?.length > 0) && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <div className="text-sm font-medium text-blue-900 mb-2">✓ Выбрано:</div>
          <div className="text-sm text-blue-700 space-y-1">
            {Object.entries(value)
              .filter(([_, items]) => items && items.length > 0)
              .map(([level, items]) => (
                <div key={level}>
                  <span className="font-medium">{level}:</span> {items.join(', ')}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
