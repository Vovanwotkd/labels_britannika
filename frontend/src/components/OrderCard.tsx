/**
 * Order Card Component - New Design
 * Карточка заказа 220×220px с цветовой индикацией статуса
 */

import { useState } from 'react'
import type { OrderListItem } from '../types'

interface OrderCardProps {
  order: OrderListItem
  onPrintAll: () => void
  onOpenDetails: () => void
}

export default function OrderCard({ order, onPrintAll, onOpenDetails }: OrderCardProps) {
  const [isAnimating, setIsAnimating] = useState(false)

  // Мапим статусы на цвета
  const getStatusColor = (status: string) => {
    if (status === 'DONE') {
      return 'bg-[#D8F7D0]' // Зелёный - напечатан
    } else if (status === 'FAILED') {
      return 'bg-[#FFD6D6]' // Красный - ошибка
    } else {
      // NOT_PRINTED, PRINTING - голубой (новый)
      return 'bg-[#D6E8FF]'
    }
  }

  // Иконка в зависимости от статуса
  const getStatusIcon = (status: string) => {
    if (status === 'DONE') {
      return '✓' // Галочка для готовых
    } else if (status === 'FAILED') {
      return '✕' // Крестик для ошибок
    } else {
      return '🍽️' // Блюдо для новых
    }
  }

  // Прогресс печати
  const progressPercent = order.jobs_count > 0
    ? Math.round((order.jobs_done / order.jobs_count) * 100)
    : 0

  const isPrinting = order.status === 'PRINTING'

  // Клик на карточку - печатать все
  const handleCardClick = () => {
    setIsAnimating(true)
    onPrintAll()
    // Анимация мигания 500мс
    setTimeout(() => setIsAnimating(false), 500)
  }

  // Клик на кнопку "Открыть" - не должен триггерить печать
  const handleOpenClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onOpenDetails()
  }

  // Форматирование суммы
  const formatSum = (sum: number | null) => {
    if (!sum) return '0 ₽'
    return `${sum.toFixed(0)} ₽`
  }

  return (
    <div
      onClick={handleCardClick}
      className={`
        relative w-[220px] h-[220px] rounded-lg shadow-md
        flex flex-col items-center justify-between p-4
        cursor-pointer transition-all duration-300
        hover:shadow-xl hover:scale-105
        ${getStatusColor(order.status)}
        ${isAnimating ? 'animate-pulse' : ''}
      `}
    >
      {/* Иконка статуса */}
      <div className="text-4xl mb-2">
        {getStatusIcon(order.status)}
      </div>

      {/* Номер заказа (visit_id) */}
      <div className="text-2xl font-bold text-gray-900 mb-1">
        #{order.visit_id}
      </div>

      {/* Сумма заказа */}
      <div className="text-xl font-semibold text-gray-800 mb-2">
        {formatSum(order.order_total)}
      </div>

      {/* Стол и количество блюд */}
      <div className="text-sm text-gray-700 text-center mb-3">
        Стол {order.table_code} • {order.items_count} блюд{order.items_count !== 1 && 'а'}
      </div>

      {/* Полоска прогресса (если печатается) */}
      {isPrinting && (
        <div className="w-full h-1 bg-gray-300 rounded-full overflow-hidden mb-3">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      )}

      {/* Кнопка "Открыть" */}
      <button
        onClick={handleOpenClick}
        className="
          w-[80%] py-2 px-4
          bg-white/80 hover:bg-white
          text-gray-800 text-sm font-medium
          rounded-md shadow-sm
          transition-all duration-200
          flex items-center justify-center gap-2
        "
      >
        Открыть
        <span className="text-gray-600">→</span>
      </button>
    </div>
  )
}
