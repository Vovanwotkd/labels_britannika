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
  const [saving, setSaving] = useState(false)

  // Редактируемые настройки
  const [printerIp, setPrinterIp] = useState('')
  const [printerPort, setPrinterPort] = useState('')
  const [sh5Url, setSh5Url] = useState('')
  const [sh5User, setSh5User] = useState('')
  const [sh5Pass, setSh5Pass] = useState('')
  const [rkUrl, setRkUrl] = useState('')
  const [rkUser, setRkUser] = useState('')
  const [rkPass, setRkPass] = useState('')
  const [defaultTemplateId, setDefaultTemplateId] = useState('')

  useEffect(() => {
    loadSystemInfo()
  }, [])

  const loadSystemInfo = async () => {
    try {
      setLoading(true)
      const data = await settingsApi.getSystemInfo()
      setSystemInfo(data)

      // Заполняем поля текущими значениями
      setPrinterIp(data.printer.ip)
      setPrinterPort(data.printer.port.toString())
      setSh5Url(data.storehouse.url)
      setSh5User(data.storehouse.user)
      setSh5Pass(data.storehouse.pass)
      setRkUrl(data.rkeeper.url)
      setRkUser(data.rkeeper.user)
      setRkPass(data.rkeeper.pass)
      setDefaultTemplateId(data.default_template_id.toString())
    } catch (error) {
      console.error('Failed to load system info:', error)
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async () => {
    try {
      setSaving(true)

      const settings = [
        { key: 'printer_ip', value: printerIp },
        { key: 'printer_port', value: printerPort },
        { key: 'sh5_url', value: sh5Url },
        { key: 'sh5_user', value: sh5User },
        { key: 'sh5_pass', value: sh5Pass },
        { key: 'rkeeper_url', value: rkUrl },
        { key: 'rkeeper_user', value: rkUser },
        { key: 'rkeeper_pass', value: rkPass },
        { key: 'default_template_id', value: defaultTemplateId },
      ]

      await settingsApi.updateSettingsBatch(settings)

      alert('Настройки сохранены успешно!')
      loadSystemInfo()
    } catch (error) {
      console.error('Failed to save settings:', error)
      alert('Ошибка сохранения настроек')
    } finally {
      setSaving(false)
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

      {/* System Info (Read-only) */}
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

      {/* Printer Settings (Editable) */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Принтер</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              IP адрес
            </label>
            <input
              type="text"
              value={printerIp}
              onChange={(e) => setPrinterIp(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
              placeholder="192.168.1.10"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Порт
            </label>
            <input
              type="text"
              value={printerPort}
              onChange={(e) => setPrinterPort(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
              placeholder="9100"
            />
          </div>
        </div>
      </div>

      {/* StoreHouse 5 Settings (Editable) */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">StoreHouse 5</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              URL API
            </label>
            <input
              type="text"
              value={sh5Url}
              onChange={(e) => setSh5Url(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
              placeholder="http://10.0.0.141:9797/api/sh5exec"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Логин
              </label>
              <input
                type="text"
                value={sh5User}
                onChange={(e) => setSh5User(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Admin"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Пароль
              </label>
              <input
                type="password"
                value={sh5Pass}
                onChange={(e) => setSh5Pass(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="••••••••"
              />
            </div>
          </div>
        </div>
      </div>

      {/* RKeeper Settings (Editable) */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">RKeeper</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              URL API
            </label>
            <input
              type="text"
              value={rkUrl}
              onChange={(e) => setRkUrl(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 font-mono"
              placeholder="http://10.0.0.141:8443/rkeeper-api"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Логин
              </label>
              <input
                type="text"
                value={rkUser}
                onChange={(e) => setRkUser(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="admin"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Пароль
              </label>
              <input
                type="password"
                value={rkPass}
                onChange={(e) => setRkPass(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="••••••••"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Template Settings (Editable) */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Шаблон по умолчанию</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Шаблон
          </label>
          <select
            value={defaultTemplateId}
            onChange={(e) => setDefaultTemplateId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {systemInfo.templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name} {template.brand_id !== 'default' && `(${template.brand_id})`}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Save Button */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex space-x-4">
          <button
            onClick={saveSettings}
            disabled={saving}
            className="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Сохранение...' : 'Сохранить настройки'}
          </button>

          <button
            onClick={loadSystemInfo}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400"
          >
            Отменить
          </button>
        </div>
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
    </div>
  )
}
