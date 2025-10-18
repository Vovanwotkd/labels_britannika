/**
 * Layout Component
 * Основной layout с навигацией
 */

import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useWebSocket } from '../contexts/WebSocketContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const { connected } = useWebSocket()

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">
                Britannica Labels
              </h1>
            </div>

            {/* Navigation */}
            <nav className="flex space-x-4">
              <NavLink
                to="/orders"
                className={({ isActive }) =>
                  `px-3 py-2 rounded-md text-sm font-medium ${
                    isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`
                }
              >
                Заказы
              </NavLink>

              {user?.role === 'admin' && (
                <NavLink
                  to="/settings"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium ${
                      isActive
                        ? 'bg-primary-100 text-primary-700'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`
                  }
                >
                  Настройки
                </NavLink>
              )}
            </nav>

            {/* User info */}
            <div className="flex items-center space-x-4">
              {/* WebSocket status */}
              <div className="flex items-center space-x-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    connected ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  title={connected ? 'Подключено' : 'Отключено'}
                />
                <span className="text-sm text-gray-600">
                  {connected ? 'Online' : 'Offline'}
                </span>
              </div>

              <div className="text-sm text-gray-700">
                {user?.full_name || user?.login}
                <span className="ml-2 text-gray-500">({user?.role})</span>
              </div>

              <button
                onClick={handleLogout}
                className="px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md"
              >
                Выход
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
