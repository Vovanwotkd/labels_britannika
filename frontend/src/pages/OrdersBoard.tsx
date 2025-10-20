/**
 * Orders Board Page
 * Доска заказов с real-time обновлениями
 */

import { useState, useEffect, useCallback } from 'react'
import { ordersApi, rkeeperApi } from '../api/client'
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
      // Обновляем статус заказа
      setOrders((prev) =>
        prev.map((order) =>
          order.id === message.order_id
            ? { ...order, status: 'CANCELLED' }
            : order
        )
      )
    }
  })

  // WebSocket: обновления print jobs
  useWebSocketMessage<WSPrintJobUpdate>('print_job_update', (message) => {
    console.log('Print job update:', message)

    // Обновляем статистику заказа
    setOrders((prev) =>
      prev.map((order) => {
        // Нужно пересчитать jobs_done, jobs_failed
        // Для простоты - перезагружаем весь заказ
        return order
      })
    )

    // Можно также перезагрузить весь список для точности
    if (message.status === 'DONE' || message.status === 'FAILED') {
      loadOrders()
    }
  })

  const handleCancelOrder = async (orderId: number) => {
    if (!confirm('Отменить заказ?')) return

    try {
      await ordersApi.cancel(orderId)
      // Обновим локально
      setOrders((prev) =>
        prev.map((order) =>
          order.id === orderId ? { ...order, status: 'CANCELLED' } : order
        )
      )
    } catch (err) {
      alert('Ошибка отмены заказа')
      console.error(err)
    }
  }

  const handleDeleteOrder = async (orderId: number) => {
    if (!confirm('Удалить заказ из списка?')) return

    try {
      await ordersApi.delete(orderId)
      // Удалим локально
      setOrders((prev) => prev.filter((order) => order.id !== orderId))
    } catch (err) {
      alert('Ошибка удаления заказа')
      console.error(err)
    }
  }

  const handleSaveTables = async (
    selectedTables: Array<{ code: string; name: string }>
  ) => {
    await rkeeperApi.saveTables(selectedTables)
    alert(`Сохранено ${selectedTables.length} столов`)
  }

  if (loading && orders.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-xl text-gray-600">Загрузка заказов...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <div className="text-sm text-red-800">{error}</div>
        <button
          onClick={loadOrders}
          className="mt-2 text-sm text-red-600 underline"
        >
          Повторить
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with Status filter */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-6">
          <h1 className="text-3xl font-bold text-gray-900">Заказы</h1>

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Статус</label>
            <select
              value={filter.status || ''}
              onChange={(e) =>
                setFilter((prev) => ({
                  ...prev,
                  status: e.target.value || undefined,
                }))
              }
              className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white"
            >
              <option value="">Все</option>
              <option value="NOT_PRINTED">Не напечатано</option>
              <option value="PRINTING">Печатается</option>
              <option value="DONE">Готово</option>
              <option value="FAILED">Ошибка</option>
              <option value="CANCELLED">Отменено</option>
            </select>
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

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-600">Всего заказов</div>
          <div className="text-2xl font-bold text-gray-900">{orders.length}</div>
        </div>

        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-600">Не напечатано</div>
          <div className="text-2xl font-bold text-orange-600">
            {orders.filter((o) => o.status === 'NOT_PRINTED').length}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-600">Готово</div>
          <div className="text-2xl font-bold text-green-600">
            {orders.filter((o) => o.status === 'DONE').length}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-4">
          <div className="text-sm text-gray-600">Ошибки</div>
          <div className="text-2xl font-bold text-red-600">
            {orders.filter((o) => o.status === 'FAILED').length}
          </div>
        </div>
      </div>

      {/* Orders Grid */}
      {orders.length === 0 ? (
        <div className="text-center py-12 bg-white shadow rounded-lg">
          <div className="text-gray-500">Заказов нет</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {orders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              onCancel={() => handleCancelOrder(order.id)}
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
    </div>
  )
}
