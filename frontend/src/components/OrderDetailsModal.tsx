import React, { useState } from 'react'
import type { Order } from '../types'

interface OrderDetailsModalProps {
  order: Order
  onClose: () => void
  onPrintDish: (dishId: number, quantity: number) => void
}

export default function OrderDetailsModal({ order, onClose, onPrintDish }: OrderDetailsModalProps) {
  const [printingDishId, setPrintingDishId] = useState<number | null>(null)

  const handlePrintDish = async (dishId: number, quantity: number) => {
    setPrintingDishId(dishId)
    await onPrintDish(dishId, quantity)

    // Show checkmark briefly
    setTimeout(() => {
      setPrintingDishId(null)
    }, 1000)
  }

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  // Close on ESC key
  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl w-[600px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="bg-[#D6E8FF] rounded-t-lg px-6 py-4 flex justify-between items-start">
          <div>
            <div className="text-2xl text-gray-900 mb-1">
              #{order.visit_id}
            </div>
            <div className="text-sm text-gray-700">
              Стол {order.table_code} • {order.order_total ? `${order.order_total} ₽` : 'Сумма неизвестна'}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-900 text-2xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Dishes List */}
        <div className="flex-1 overflow-y-auto">
          {order.items && order.items.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {order.items.map((item) => (
                <div
                  key={item.id}
                  className="px-6 py-4 hover:bg-gray-50 transition-colors flex items-center justify-between"
                >
                  <div className="flex-1">
                    <span className="text-gray-900">{item.dish_name || item.rk_code}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-bold text-gray-700">× {item.quantity}</span>
                    <button
                      onClick={() => handlePrintDish(item.id, item.quantity)}
                      disabled={printingDishId === item.id}
                      className={`px-4 py-2 rounded-md transition-all ${
                        printingDishId === item.id
                          ? 'bg-green-500 text-white'
                          : 'bg-blue-500 text-white hover:bg-blue-600'
                      }`}
                    >
                      {printingDishId === item.id ? '✓' : 'Печать →'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-6 py-8 text-center text-gray-500">
              Нет блюд в заказе
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
