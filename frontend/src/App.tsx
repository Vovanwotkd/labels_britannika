import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { WebSocketProvider } from './contexts/WebSocketContext'
import LoginPage from './pages/LoginPage'
import OrdersBoard from './pages/OrdersBoard'
import TemplatesPage from './pages/TemplatesPage'
import SettingsPage from './pages/SettingsPage'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <WebSocketProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/orders" replace />} />
              <Route path="orders" element={<OrdersBoard />} />
              <Route path="templates" element={<TemplatesPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </WebSocketProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
