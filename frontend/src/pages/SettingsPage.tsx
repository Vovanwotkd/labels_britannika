/**
 * Settings Page
 * Страница настроек (только для админов)
 */

import { useState, useEffect } from 'react'
import { settingsApi } from '../api/client'
import type { SystemInfo } from '../types'

export default function SettingsPage() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSystemInfo()
  }, [])

  const loadSystemInfo = async () => {
    try {
      setLoading(true)
      const data = await settingsApi.getSystemInfo()
      setSystemInfo(data)
    } catch (error) {
      console.error('Failed to load system info:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-xl text-gray-600">Загрузка...</div>
      </div>
    )
  }

  if (!systemInfo) {
    return (
      <div className="rounded-md bg-red-50 p-4">
        <div className="text-sm text-red-800">Ошибка загрузки информации о системе</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">Настройки</h1>

      {/* System Info */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Информация о системе
        </h2>

        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Приложение</dt>
            <dd className="mt-1 text-sm text-gray-900">{systemInfo.app_name}</dd>
          </div>

          <div>
            <dt className="text-sm font-medium text-gray-500">Версия</dt>
            <dd className="mt-1 text-sm text-gray-900">{systemInfo.version}</dd>
          </div>

          <div>
            <dt className="text-sm font-medium text-gray-500">Окружение</dt>
            <dd className="mt-1 text-sm text-gray-900">{systemInfo.environment}</dd>
          </div>

          <div>
            <dt className="text-sm font-medium text-gray-500">Часовой пояс</dt>
            <dd className="mt-1 text-sm text-gray-900">{systemInfo.timezone}</dd>
          </div>
        </dl>
      </div>

      {/* Printer */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Принтер</h2>

        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">IP адрес</dt>
            <dd className="mt-1 text-sm text-gray-900 font-mono">
              {systemInfo.printer.ip}
            </dd>
          </div>

          <div>
            <dt className="text-sm font-medium text-gray-500">Порт</dt>
            <dd className="mt-1 text-sm text-gray-900 font-mono">
              {systemInfo.printer.port}
            </dd>
          </div>
        </dl>
      </div>

      {/* Database Stats */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Статистика базы данных
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Заказов</div>
            <div className="text-2xl font-bold text-gray-900">
              {systemInfo.database.orders}
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Блюд</div>
            <div className="text-2xl font-bold text-gray-900">
              {systemInfo.database.order_items}
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Заданий печати</div>
            <div className="text-2xl font-bold text-gray-900">
              {systemInfo.database.print_jobs.total}
            </div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
          <div className="text-center p-2 bg-yellow-50 rounded">
            <div className="text-xs text-gray-600">В очереди</div>
            <div className="text-lg font-semibold text-yellow-700">
              {systemInfo.database.print_jobs.queued}
            </div>
          </div>

          <div className="text-center p-2 bg-blue-50 rounded">
            <div className="text-xs text-gray-600">Печатается</div>
            <div className="text-lg font-semibold text-blue-700">
              {systemInfo.database.print_jobs.printing}
            </div>
          </div>

          <div className="text-center p-2 bg-green-50 rounded">
            <div className="text-xs text-gray-600">Готово</div>
            <div className="text-lg font-semibold text-green-700">
              {systemInfo.database.print_jobs.done}
            </div>
          </div>

          <div className="text-center p-2 bg-red-50 rounded">
            <div className="text-xs text-gray-600">Ошибок</div>
            <div className="text-lg font-semibold text-red-700">
              {systemInfo.database.print_jobs.failed}
            </div>
          </div>
        </div>
      </div>

      {/* WebSocket */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">WebSocket</h2>

        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">
              Подключенных клиентов
            </dt>
            <dd className="mt-1 text-sm text-gray-900">
              {systemInfo.websocket.connections}
            </dd>
          </div>

          <div>
            <dt className="text-sm font-medium text-gray-500">
              В комнате "orders"
            </dt>
            <dd className="mt-1 text-sm text-gray-900">
              {systemInfo.websocket.rooms.orders}
            </dd>
          </div>
        </dl>
      </div>

      {/* Actions */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Действия</h2>

        <div className="flex space-x-4">
          <button
            onClick={loadSystemInfo}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            Обновить информацию
          </button>
        </div>
      </div>
    </div>
  )
}
