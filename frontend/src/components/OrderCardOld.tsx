/**
 * Order Card Component
 * Карточка заказа для доски
 */

import type { OrderListItem } from '../types'

interface OrderCardProps {
  order: OrderListItem
  onCancel: () => void
  onDelete: () => void
}

export default function OrderCard({ order, onCancel, onDelete }: OrderCardProps) {
  const getStatusBadge = (status: string) => {
    const badges = {
      NOT_PRINTED: 'bg-orange-100 text-orange-800',
      PRINTING: 'bg-blue-100 text-blue-800',
      DONE: 'bg-green-100 text-green-800',
      FAILED: 'bg-red-100 text-red-800',
      CANCELLED: 'bg-gray-100 text-gray-800',
    }

    const labels = {
      NOT_PRINTED: 'Не напечатано',
      PRINTING: 'Печатается',
      DONE: 'Готово',
      FAILED: 'Ошибка',
      CANCELLED: 'Отменено',
    }

    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
          badges[status as keyof typeof badges] || 'bg-gray-100 text-gray-800'
        }`}
      >
        {labels[status as keyof typeof labels] || status}
      </span>
    )
  }

  const progressPercent = order.jobs_count > 0
    ? Math.round((order.jobs_done / order.jobs_count) * 100)
    : 0

  return (
    <div className="bg-white shadow rounded-lg overflow-hidden hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex justify-between items-start">
          <div>
            <div className="text-lg font-semibold text-gray-900">
              {order.table_name}
            </div>
            <div className="text-sm text-gray-600">
              Заказ #{order.order_ident}
            </div>
          </div>
          <div>{getStatusBadge(order.status)}</div>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-3">
        {/* Info */}
        <div className="text-sm text-gray-600 space-y-1">
          <div>Visit: {order.visit_id}</div>
          <div>Столов: {order.table_code}</div>
          <div>Блюд: {order.items_count}</div>
        </div>

        {/* Progress */}
        <div>
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Печать</span>
            <span>
              {order.jobs_done} / {order.jobs_count}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                order.jobs_failed > 0
                  ? 'bg-red-600'
                  : order.jobs_done === order.jobs_count
                  ? 'bg-green-600'
                  : 'bg-blue-600'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          {order.jobs_failed > 0 && (
            <div className="text-xs text-red-600 mt-1">
              Ошибок: {order.jobs_failed}
            </div>
          )}
        </div>

        {/* Time */}
        <div className="text-xs text-gray-500">
          Создан: {new Date(order.created_at).toLocaleString('ru-RU')}
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex space-x-2">
        {order.status !== 'CANCELLED' && (
          <button
            onClick={onCancel}
            className="flex-1 px-3 py-2 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            Отменить
          </button>
        )}

        <button
          onClick={onDelete}
          className="flex-1 px-3 py-2 text-sm text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          Удалить
        </button>
      </div>
    </div>
  )
}
