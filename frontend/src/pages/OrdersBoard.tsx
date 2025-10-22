/**
 * Orders Board Page - New Design
 * Доска заказов с real-time обновлениями и новым дизайном карточек
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { ordersApi } from '../api/client'
import { useWebSocketMessage } from '../contexts/WebSocketContext'
import type {
  OrderListItem,
  WSOrderUpdate,
  WSPrintJobUpdate,
} from '../types'
import OrderCard from '../components/OrderCard'
import TableSelectorModal from '../components/TableSelectorModal'

export default function OrdersBoard() {
  const [orders, setOrders] = useState<OrderListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<{
    status?: string
    table_code?: string
  }>({})
  const [isTableModalOpen, setIsTableModalOpen] = useState(false)
  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false)
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Закрытие dropdown при клике вне его области
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsStatusDropdownOpen(false)
      }
    }

    if (isStatusDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isStatusDropdownOpen])

  // Загрузка заказов
  const loadOrders = useCallback(async () => {
    try {
      setLoading(true)
      const data = await ordersApi.getAll({
        ...filter,
        limit: 100,
      })
      setOrders(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки заказов')
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    loadOrders()
  }, [loadOrders])

  // WebSocket: обновления заказов
  useWebSocketMessage<WSOrderUpdate>('order_update', (message) => {
    console.log('Order update:', message)

    if (message.event === 'new_order') {
      // Перезагружаем список
      loadOrders()
    } else if (message.event === 'order_updated') {
      // Обновляем конкретный заказ
      loadOrders()
    } else if (message.event === 'order_cancelled') {
      // Удаляем отмененный заказ из списка
      setOrders((prev) => prev.filter((order) => order.id !== message.order_id))
    }
  })

  // WebSocket: обновления print jobs
  useWebSocketMessage<WSPrintJobUpdate>('print_job_update', (message) => {
    console.log('Print job update:', message)

    // Можно также перезагрузить весь список для точности
    if (message.status === 'DONE' || message.status === 'FAILED') {
      loadOrders()
    }
  })

  // Фильтрация и сортировка заказов
  const sortedOrders = useMemo(() => {
    // 1. Фильтруем CANCELLED заказы (скрываем их)
    let filtered = orders.filter((order) => order.status !== 'CANCELLED')

    // 2. Сортируем по приоритету статусов
    const statusPriority: Record<string, number> = {
      'NOT_PRINTED': 1,  // Новые - вверху
      'PRINTING': 1,     // Печатаются - тоже новые
      'FAILED': 2,       // Ошибки - посередине
      'DONE': 3,         // Готовые - внизу
    }

    filtered.sort((a, b) => {
      const priorityA = statusPriority[a.status] || 999
      const priorityB = statusPriority[b.status] || 999

      // Сначала по приоритету статуса
      if (priorityA !== priorityB) {
        return priorityA - priorityB
      }

      // Внутри одного статуса - по времени создания (новые первые)
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })

    return filtered
  }, [orders])

  // Печать всего заказа
  const handlePrintAll = async (orderId: number) => {
    try {
      // TODO: вызвать API для печати всего заказа
      console.log('Print all labels for order:', orderId)
      // await ordersApi.printOrder(orderId)
    } catch (err) {
      console.error('Failed to print order:', err)
    }
  }

  // Открыть детальный вид заказа
  const handleOpenDetails = (orderId: number) => {
    setSelectedOrderId(orderId)
    // TODO: открыть модальное окно с деталями
    console.log('Open order details:', orderId)
  }

  // Удаление заказа
  const handleDeleteOrder = async (orderId: number) => {
    try {
      await ordersApi.delete(orderId)
      // Удаляем из списка
      setOrders((prev) => prev.filter((order) => order.id !== orderId))
    } catch (err) {
      console.error('Failed to delete order:', err)
      alert('Не удалось удалить заказ')
    }
  }

  // Сохранение выбранных столов
  const handleSaveTables = async () => {
    // Перезагружаем заказы после изменения фильтра столов
    await loadOrders()
    setIsTableModalOpen(false)
  }

  if (loading && orders.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">Загрузка заказов...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="text-red-800 font-medium">Ошибка</div>
          <div className="text-red-600 text-sm mt-1">{error}</div>
          <button
            onClick={loadOrders}
            className="mt-2 text-sm text-red-600 underline"
          >
            Повторить
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with Filters */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-6">
          <h1 className="text-3xl font-bold text-gray-900">Заказы</h1>

          {/* Status Filter */}
          <div className="flex items-center gap-2 relative">
            <label className="text-sm font-medium text-gray-700">Статус</label>
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setIsStatusDropdownOpen(!isStatusDropdownOpen)}
                className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white min-w-[180px] text-left flex justify-between items-center"
              >
                <span className="text-gray-900">
                  {filter.status === 'NOT_PRINTED' ? 'Новые' :
                   filter.status === 'DONE' ? 'Напечатаны' :
                   filter.status === 'FAILED' ? 'Ошибки' :
                   'Все'}
                </span>
                <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {isStatusDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-full bg-white border-2 border-gray-400 rounded-md shadow-xl z-50">
                  {[
                    { value: '', label: 'Все' },
                    { value: 'NOT_PRINTED', label: 'Новые' },
                    { value: 'DONE', label: 'Напечатаны' },
                    { value: 'FAILED', label: 'Ошибки' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setFilter((prev) => ({
                          ...prev,
                          status: option.value || undefined,
                        }))
                        setIsStatusDropdownOpen(false)
                      }}
                      className={`w-full text-left px-3 py-2 text-sm border-b border-gray-200 last:border-b-0 hover:bg-gray-100 ${
                        (filter.status || '') === option.value ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-900'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => setIsTableModalOpen(true)}
            className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            Выбрать столы
          </button>
          <button
            onClick={loadOrders}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            Обновить
          </button>
        </div>
      </div>

      {/* Orders Grid - 3 columns on desktop, 2 on tablet, 1 on mobile */}
      {sortedOrders.length === 0 ? (
        <div className="text-center py-12 bg-white shadow rounded-lg">
          <div className="text-gray-500">Заказов нет</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-y-6 gap-x-6 justify-items-center">
          {sortedOrders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              onPrintAll={() => handlePrintAll(order.id)}
              onOpenDetails={() => handleOpenDetails(order.id)}
              onDelete={() => handleDeleteOrder(order.id)}
            />
          ))}
        </div>
      )}

      {/* Table Selector Modal */}
      <TableSelectorModal
        isOpen={isTableModalOpen}
        onClose={() => setIsTableModalOpen(false)}
        onSave={handleSaveTables}
      />

      {/* TODO: Order Details Modal */}
      {selectedOrderId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
            <h2 className="text-2xl font-bold mb-4">Детали заказа #{selectedOrderId}</h2>
            <p className="text-gray-600 mb-4">Модальное окно в разработке...</p>
            <button
              onClick={() => setSelectedOrderId(null)}
              className="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              Закрыть
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
