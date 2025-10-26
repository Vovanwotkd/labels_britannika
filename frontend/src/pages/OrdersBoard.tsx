/**
 * Orders Board Page - New Design
 * Доска заказов с real-time обновлениями и новым дизайном карточек
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { ordersApi, syncApi } from '../api/client'
import { useWebSocketMessage } from '../contexts/WebSocketContext'
import type {
  OrderListItem,
  Order,
  WSOrderUpdate,
  WSPrintJobUpdate,
} from '../types'
import OrderCard from '../components/OrderCard'
import TableSelectorModal from '../components/TableSelectorModal'
import OrderDetailsModal from '../components/OrderDetailsModal'

export default function OrdersBoard() {
  const [orders, setOrders] = useState<OrderListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [filter, setFilter] = useState<{
    status?: string
    table_code?: string
  }>({})
  const [isTableModalOpen, setIsTableModalOpen] = useState(false)
  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false)
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null)
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false)
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

  // Синхронизация с RKeeper и загрузка заказов
  const loadOrders = useCallback(async (withSync: boolean = false) => {
    try {
      setLoading(true)

      // Если withSync=true, сначала синхронизируемся с RKeeper
      if (withSync) {
        setSyncing(true)
        try {
          const syncResult = await syncApi.syncOrders()
          console.log('Sync result:', syncResult)
        } catch (syncErr) {
          console.error('Sync error:', syncErr)
          // Продолжаем загрузку заказов даже если синхронизация не удалась
        } finally {
          setSyncing(false)
        }
      }

      // Загружаем заказы из нашей БД
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
    loadOrders(false)
  }, [loadOrders])

  // WebSocket: обновления заказов
  useWebSocketMessage<WSOrderUpdate>('order_update', (message) => {
    console.log('Order update:', message)

    if (message.event === 'new_order') {
      // Перезагружаем список
      loadOrders(false)
    } else if (message.event === 'order_updated') {
      // Обновляем конкретный заказ
      loadOrders(false)
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
      loadOrders(false)
    }
  })

  // Фильтрация и сортировка заказов
  const sortedOrders = useMemo(() => {
    // 1. Фильтруем CANCELLED заказы (скрываем их только если не выбран фильтр CANCELLED)
    let filtered = orders.filter((order) => {
      // Если выбран конкретный статус в фильтре - не скрываем CANCELLED
      if (filter.status) {
        return true
      }
      // Если фильтр "Все" - скрываем CANCELLED по умолчанию
      return order.status !== 'CANCELLED'
    })

    // 2. Сортируем по приоритету статусов
    const statusPriority: Record<string, number> = {
      'NOT_PRINTED': 1,  // Новые - вверху
      'PRINTING': 1,     // Печатаются - тоже новые
      'FAILED': 2,       // Ошибки - посередине
      'DONE': 3,         // Готовые - внизу
      'CANCELLED': 4,    // Отменённые - самый низ
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
  }, [orders, filter.status])

  // Печать всего заказа
  const handlePrintAll = async (orderId: number) => {
    try {
      const order = await ordersApi.getById(orderId)

      if (!order.items || order.items.length === 0) {
        alert('В заказе нет блюд для печати')
        return
      }

      // Печатаем каждое блюдо
      for (const item of order.items) {
        await ordersApi.reprint(item.id, item.quantity)
      }

      // Перезагружаем заказы для обновления статусов
      await loadOrders(false)
    } catch (err) {
      console.error('Failed to print order:', err)
      alert('Не удалось напечатать заказ')
    }
  }

  // Открыть детальный вид заказа
  const handleOpenDetails = async (orderId: number) => {
    try {
      const orderData = await ordersApi.getById(orderId)
      setSelectedOrder(orderData)
      setIsDetailsModalOpen(true)
    } catch (err) {
      console.error('Failed to load order details:', err)
      alert('Не удалось загрузить детали заказа')
    }
  }

  // Печать отдельного блюда
  const handlePrintDish = async (dishId: number, quantity: number) => {
    try {
      await ordersApi.reprint(dishId, quantity)
      // Успех - checkmark уже показывается в модалке
    } catch (err) {
      console.error('Failed to print dish:', err)
      alert('Не удалось напечатать блюдо')
    }
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
    await loadOrders(false)
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
            onClick={() => loadOrders(false)}
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
                   filter.status === 'CANCELLED' ? 'Отменённые' :
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
                    { value: 'CANCELLED', label: 'Отменённые' },
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
            onClick={() => loadOrders(true)}
            disabled={syncing}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {syncing && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
            )}
            {syncing ? 'Синхронизация...' : 'Обновить'}
          </button>
        </div>
      </div>

      {/* Orders Grid - 3 columns on desktop, 2 on tablet, 1 on mobile */}
      {sortedOrders.length === 0 ? (
        <div className="text-center py-12 bg-white shadow rounded-lg">
          <div className="text-gray-500">Заказов нет</div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-6 justify-center">
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

      {/* Order Details Modal */}
      {isDetailsModalOpen && selectedOrder && (
        <OrderDetailsModal
          order={selectedOrder}
          onClose={() => {
            setIsDetailsModalOpen(false)
            setSelectedOrder(null)
          }}
          onPrintDish={handlePrintDish}
        />
      )}
    </div>
  )
}
