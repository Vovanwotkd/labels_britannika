/**
 * Order Card Component - New Design
 * Карточка заказа 220×220px с цветовой индикацией статуса
 */

import { useState, useRef, useEffect } from 'react'
import type { OrderListItem } from '../types'

interface OrderCardProps {
  order: OrderListItem
  onPrintAll: () => void
  onOpenDetails: () => void
  onDelete: () => void
}

export default function OrderCard({ order, onPrintAll, onOpenDetails, onDelete }: OrderCardProps) {
  const [isAnimating, setIsAnimating] = useState(false)
  const [showDeleteIcon, setShowDeleteIcon] = useState(false)
  const [isLongPress, setIsLongPress] = useState(false)
  const longPressTimer = useRef<NodeJS.Timeout | null>(null)
  const deleteIconTimer = useRef<NodeJS.Timeout | null>(null)

  // Мапим статусы на цвета
  const getStatusColor = (status: string) => {
    if (status === 'DONE') {
      return 'bg-[#D8F7D0]' // Зелёный - напечатан
    } else if (status === 'FAILED') {
      return 'bg-[#FFD6D6]' // Красный - ошибка
    } else if (status === 'CANCELLED') {
      return 'bg-[#E9D5FF]' // Фиолетовый - отменён
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
    } else if (status === 'CANCELLED') {
      return '⊘' // Перечёркнутый круг для отменённых
    } else {
      return '🍽️' // Блюдо для новых
    }
  }

  // Прогресс печати
  const progressPercent = order.jobs_count > 0
    ? Math.round((order.jobs_done / order.jobs_count) * 100)
    : 0

  const isPrinting = order.status === 'PRINTING'

  // Очистка таймеров при размонтировании
  useEffect(() => {
    return () => {
      if (longPressTimer.current) {
        clearTimeout(longPressTimer.current)
      }
      if (deleteIconTimer.current) {
        clearTimeout(deleteIconTimer.current)
      }
    }
  }, [])

  // Автоматическое скрытие иконки удаления через 2 секунды
  useEffect(() => {
    if (showDeleteIcon) {
      deleteIconTimer.current = setTimeout(() => {
        setShowDeleteIcon(false)
      }, 2000) // 2 секунды

      return () => {
        if (deleteIconTimer.current) {
          clearTimeout(deleteIconTimer.current)
        }
      }
    }
  }, [showDeleteIcon])

  // Долгое нажатие - показать иконку удаления
  const handleMouseDown = () => {
    setIsLongPress(false)
    longPressTimer.current = setTimeout(() => {
      setIsLongPress(true)
      setShowDeleteIcon(true)
    }, 800) // 800ms для долгого нажатия
  }

  const handleMouseUp = () => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
    // Сброс флага долгого нажатия через небольшую задержку
    setTimeout(() => setIsLongPress(false), 100)
  }

  const handleTouchStart = () => {
    setIsLongPress(false)
    longPressTimer.current = setTimeout(() => {
      setIsLongPress(true)
      setShowDeleteIcon(true)
    }, 800)
  }

  const handleTouchEnd = () => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
    setTimeout(() => setIsLongPress(false), 100)
  }

  // Клик на карточку - печатать все
  const handleCardClick = () => {
    // Если было долгое нажатие или показана иконка удаления, игнорируем клик
    if (isLongPress || showDeleteIcon) return

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

  // Клик на иконку удаления
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm(`Удалить заказ #${order.visit_id}?`)) {
      onDelete()
    }
    setShowDeleteIcon(false)
  }

  // Форматирование суммы
  const formatSum = (sum: number | null) => {
    if (!sum) return '0 ₽'
    return `${sum.toFixed(0)} ₽`
  }

  return (
    <div
      onClick={handleCardClick}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      className={`
        relative w-[220px] h-[220px] rounded-lg shadow-md
        flex flex-col items-center justify-between p-4
        cursor-pointer transition-all duration-300
        hover:shadow-xl hover:scale-105
        ${getStatusColor(order.status)}
        ${isAnimating ? 'animate-pulse' : ''}
      `}
    >
      {/* Иконка удаления (при долгом нажатии) */}
      {showDeleteIcon && (
        <button
          onClick={handleDeleteClick}
          className="absolute top-2 right-2 w-8 h-8 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center shadow-lg z-10 transition-all"
        >
          🗑️
        </button>
      )}

      {/* Иконка статуса */}
      <div className="text-4xl mb-2">
        {getStatusIcon(order.status)}
      </div>

      {/* Сумма заказа (ВВЕРХУ, ЖИРНЫМ) */}
      <div className="text-3xl font-bold text-gray-900 mb-1">
        {formatSum(order.order_total)}
      </div>

      {/* Номер заказа visit_id (обычным шрифтом) */}
      <div className="text-lg text-gray-700 mb-2">
        #{order.visit_id}
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
