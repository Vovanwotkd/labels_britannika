/**
 * Settings Page
 * Страница настроек (только для админов)
 */

import { useState, useEffect } from 'react'
import { settingsApi, testConnectionApi, syncApi, printersApi } from '../api/client'
import type { SystemInfo, PrinterInfo } from '../types'
import type { SyncStatus } from '../api/client'

export default function SettingsPage() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Состояния тестирования подключения
  const [testingPrinter, setTestingPrinter] = useState(false)
  const [testingStorehouse, setTestingStorehouse] = useState(false)
  const [testingRKeeper, setTestingRKeeper] = useState(false)

  // Состояния синхронизации
  const [syncing, setSyncing] = useState(false)
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)

  // Редактируемые настройки
  const [printerType, setPrinterType] = useState('tcp')
  const [printerIp, setPrinterIp] = useState('')
  const [printerPort, setPrinterPort] = useState('')
  const [printerName, setPrinterName] = useState('')
  const [cupsPrinters, setCupsPrinters] = useState<PrinterInfo[]>([])
  const [loadingPrinters, setLoadingPrinters] = useState(false)
  const [sh5Url, setSh5Url] = useState('')
  const [sh5User, setSh5User] = useState('')
  const [sh5Pass, setSh5Pass] = useState('')
  const [rkUrl, setRkUrl] = useState('')
  const [rkUser, setRkUser] = useState('')
  const [rkPass, setRkPass] = useState('')
  const [rkLogging, setRkLogging] = useState(false)
  const [defaultTemplateId, setDefaultTemplateId] = useState('')
  const [syncIntervalHours, setSyncIntervalHours] = useState('')

  useEffect(() => {
    loadSystemInfo()
    loadSyncStatus()
  }, [])

  const loadSystemInfo = async () => {
    try {
      setLoading(true)
      const data = await settingsApi.getSystemInfo()
      setSystemInfo(data)

      // Заполняем поля текущими значениями
      setPrinterType(data.printer.type || 'tcp')
      setPrinterIp(data.printer.ip)
      setPrinterPort(data.printer.port.toString())
      setPrinterName(data.printer.name || '')
      setSh5Url(data.storehouse.url)
      setSh5User(data.storehouse.user)
      setSh5Pass(data.storehouse.pass)
      setRkUrl(data.rkeeper.url)
      setRkUser(data.rkeeper.user)
      setRkPass(data.rkeeper.pass)
      setRkLogging(data.rkeeper.logging)
      setDefaultTemplateId(data.default_template_id.toString())
    } catch (error) {
      console.error('Failed to load system info:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSyncStatus = async () => {
    try {
      const data = await syncApi.getStatus()
      setSyncStatus(data)
      setSyncIntervalHours(data.interval_hours.toString())
    } catch (error) {
      console.error('Failed to load sync status:', error)
    }
  }

  const loadCupsPrinters = async () => {
    try {
      setLoadingPrinters(true)
      const data = await printersApi.getList()
      setCupsPrinters(data.printers)
    } catch (error) {
      console.error('Failed to load CUPS printers:', error)
      alert('Ошибка загрузки списка CUPS принтеров. Убедитесь, что CUPS настроен на сервере.')
    } finally {
      setLoadingPrinters(false)
    }
  }

  // Загружаем список CUPS принтеров при переключении на CUPS режим
  useEffect(() => {
    if (printerType === 'cups' && cupsPrinters.length === 0) {
      loadCupsPrinters()
    }
  }, [printerType])

  const saveSettings = async () => {
    try {
      setSaving(true)

      const settings = [
        { key: 'printer_type', value: printerType },
        { key: 'printer_ip', value: printerIp },
        { key: 'printer_port', value: printerPort },
        { key: 'printer_name', value: printerName },
        { key: 'sh5_url', value: sh5Url },
        { key: 'sh5_user', value: sh5User },
        { key: 'sh5_pass', value: sh5Pass },
        { key: 'rkeeper_url', value: rkUrl },
        { key: 'rkeeper_user', value: rkUser },
        { key: 'rkeeper_pass', value: rkPass },
        { key: 'rkeeper_logging', value: rkLogging ? 'true' : 'false' },
        { key: 'default_template_id', value: defaultTemplateId },
        { key: 'sync_interval_hours', value: syncIntervalHours },
      ]

      await settingsApi.updateSettingsBatch(settings)

      alert('Настройки сохранены успешно!')
      loadSystemInfo()
      loadSyncStatus()
    } catch (error) {
      console.error('Failed to save settings:', error)
      alert('Ошибка сохранения настроек')
    } finally {
      setSaving(false)
    }
  }

  const triggerSync = async () => {
    if (!confirm('Запустить синхронизацию с StoreHouse 5?')) {
      return
    }

    try {
      setSyncing(true)
      const result = await syncApi.trigger()
      alert(`Синхронизация запущена!\n${result.message}`)
      loadSyncStatus()
    } catch (error: any) {
      alert(`Ошибка: ${error.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const testPrinterConnection = async () => {
    try {
      setTestingPrinter(true)
      const result = await testConnectionApi.testPrinter()
      alert(result.message)
    } catch (error: any) {
      alert(`Ошибка: ${error.message}`)
    } finally {
      setTestingPrinter(false)
    }
  }

  const testStorehouseConnection = async () => {
    try {
      setTestingStorehouse(true)
      const result = await testConnectionApi.testStorehouse()
      alert(result.message)
    } catch (error: any) {
      alert(`Ошибка: ${error.message}`)
    } finally {
      setTestingStorehouse(false)
    }
  }

  const testRKeeperConnection = async () => {
    try {
      setTestingRKeeper(true)
      const result = await testConnectionApi.testRKeeper()
      alert(result.message)
    } catch (error: any) {
      alert(`Ошибка: ${error.message}`)
    } finally {
      setTestingRKeeper(false)
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

        {/* Printer Type Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Тип подключения
          </label>
          <div className="flex gap-6">
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                value="tcp"
                checked={printerType === 'tcp'}
                onChange={(e) => setPrinterType(e.target.value)}
                className="w-4 h-4 text-primary-600 border-gray-300 focus:ring-2 focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-gray-700">
                TCP (Raw TSPL)
              </span>
            </label>
            <label className="flex items-center cursor-pointer">
              <input
                type="radio"
                value="cups"
                checked={printerType === 'cups'}
                onChange={(e) => setPrinterType(e.target.value)}
                className="w-4 h-4 text-primary-600 border-gray-300 focus:ring-2 focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-gray-700">
                CUPS (Драйвер)
              </span>
            </label>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            {printerType === 'tcp'
              ? 'Прямая отправка TSPL команд на IP:Port принтера (legacy режим)'
              : 'Печать через CUPS драйвер (рекомендуется, поддерживает кириллицу)'}
          </p>
        </div>

        {/* TCP Mode Settings */}
        {printerType === 'tcp' && (
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
                placeholder="10.55.3.254"
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
        )}

        {/* CUPS Mode Settings */}
        {printerType === 'cups' && (
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">
                  CUPS принтер
                </label>
                <button
                  onClick={loadCupsPrinters}
                  disabled={loadingPrinters}
                  className="text-xs text-primary-600 hover:text-primary-700 disabled:opacity-50"
                >
                  {loadingPrinters ? 'Загрузка...' : 'Обновить список'}
                </button>
              </div>
              <select
                value={printerName}
                onChange={(e) => setPrinterName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                disabled={loadingPrinters}
              >
                <option value="">-- Выберите принтер --</option>
                {cupsPrinters.map((printer) => (
                  <option key={printer.name} value={printer.name}>
                    {printer.name} {printer.online ? '(online)' : '(offline)'}
                  </option>
                ))}
              </select>
              {cupsPrinters.length === 0 && !loadingPrinters && (
                <p className="mt-1 text-xs text-red-600">
                  Принтеры не найдены. Убедитесь, что CUPS настроен на сервере.
                </p>
              )}
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
              <p className="text-xs text-blue-800">
                <strong>Требуется:</strong> CUPS установлен на хост-сервере и настроен принтер.
                <br />
                См. <code className="bg-white px-1 py-0.5 rounded">INSTALL.md</code> для инструкций.
              </p>
            </div>
          </div>
        )}

        <div className="mt-4">
          <button
            onClick={testPrinterConnection}
            disabled={testingPrinter}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {testingPrinter ? 'Проверка...' : 'Проверить связь'}
          </button>
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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Интервал синхронизации (часы)
            </label>
            <input
              type="number"
              value={syncIntervalHours}
              onChange={(e) => setSyncIntervalHours(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="24"
              min="1"
              max="168"
            />
            <p className="mt-1 text-xs text-gray-500">
              Как часто автоматически синхронизировать товары (от 1 до 168 часов)
            </p>
          </div>

          {syncStatus && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Статус синхронизации</h3>
              <dl className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-600">Последняя синхронизация:</dt>
                  <dd className="text-gray-900">
                    {syncStatus.last_sync
                      ? new Date(syncStatus.last_sync).toLocaleString('ru-RU')
                      : 'Никогда'}
                  </dd>
                </div>
                {syncStatus.last_error && (
                  <div className="flex justify-between">
                    <dt className="text-red-600">Последняя ошибка:</dt>
                    <dd className="text-red-900 text-xs">{syncStatus.last_error}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
        </div>

        <div className="mt-4 flex gap-3">
          <button
            onClick={testStorehouseConnection}
            disabled={testingStorehouse}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {testingStorehouse ? 'Проверка...' : 'Проверить связь'}
          </button>

          <button
            onClick={triggerSync}
            disabled={syncing}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {syncing ? 'Синхронизация...' : 'Синхронизировать сейчас'}
          </button>
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

          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={rkLogging}
                onChange={(e) => setRkLogging(e.target.checked)}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-2 focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Включить логирование webhook событий
              </span>
            </label>
            <p className="mt-1 ml-6 text-xs text-gray-500">
              Записывать все входящие webhook события от RKeeper в файл для отладки
            </p>
            {rkLogging && (
              <div className="mt-2 ml-6 p-3 bg-blue-50 rounded-md">
                <p className="text-xs text-blue-800 font-mono">
                  Для просмотра логов используйте команду:
                </p>
                <code className="block mt-1 text-xs text-blue-900 bg-white p-2 rounded border border-blue-200 overflow-x-auto">
                  sudo docker exec britannica-backend tail -f /app/data/rkeeper_logs/webhook_$(date +%Y%m%d).log
                </code>
              </div>
            )}
          </div>
        </div>

        <div className="mt-4">
          <button
            onClick={testRKeeperConnection}
            disabled={testingRKeeper}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {testingRKeeper ? 'Проверка...' : 'Проверить связь'}
          </button>
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
