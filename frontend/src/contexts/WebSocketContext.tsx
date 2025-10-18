/**
 * WebSocket Context
 * Управление WebSocket соединением для real-time обновлений
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  ReactNode,
  useCallback,
} from 'react'
import type { WSMessage } from '../types'

type MessageHandler = (message: WSMessage) => void

interface WebSocketContextType {
  connected: boolean
  subscribe: (type: string, handler: MessageHandler) => () => void
  send: (message: any) => void
  joinRoom: (room: string) => void
  leaveRoom: (room: string) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${
  window.location.host
}/ws/?room=orders`

const RECONNECT_INTERVAL = 3000 // 3 секунды
const MAX_RECONNECT_ATTEMPTS = 10

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map())
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  const subscribe = useCallback((type: string, handler: MessageHandler) => {
    if (!handlersRef.current.has(type)) {
      handlersRef.current.set(type, new Set())
    }
    handlersRef.current.get(type)!.add(handler)

    // Return unsubscribe function
    return () => {
      const handlers = handlersRef.current.get(type)
      if (handlers) {
        handlers.delete(handler)
        if (handlers.size === 0) {
          handlersRef.current.delete(type)
        }
      }
    }
  }, [])

  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected, cannot send message:', message)
    }
  }, [])

  const joinRoom = useCallback(
    (room: string) => {
      send({ action: 'join_room', room })
    },
    [send]
  )

  const leaveRoom = useCallback(
    (room: string) => {
      send({ action: 'leave_room', room })
    },
    [send]
  )

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WSMessage = JSON.parse(event.data)
      console.log('📨 WebSocket message:', message)

      // Вызываем все обработчики для этого типа сообщения
      const handlers = handlersRef.current.get(message.type)
      if (handlers) {
        handlers.forEach((handler) => handler(message))
      }

      // Вызываем обработчики для wildcard '*'
      const wildcardHandlers = handlersRef.current.get('*')
      if (wildcardHandlers) {
        wildcardHandlers.forEach((handler) => handler(message))
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }, [])

  const connect = useCallback(() => {
    console.log('🔌 Connecting to WebSocket...')

    try {
      const ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        console.log('✅ WebSocket connected')
        setConnected(true)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = handleMessage

      ws.onclose = (event) => {
        console.log('🔌 WebSocket closed:', event.code, event.reason)
        setConnected(false)

        // Автоматический реконнект
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++
          console.log(
            `⏳ Reconnecting in ${RECONNECT_INTERVAL}ms (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})...`
          )

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, RECONNECT_INTERVAL)
        } else {
          console.error('❌ Max reconnect attempts reached')
        }
      }

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
    }
  }, [handleMessage])

  useEffect(() => {
    connect()

    return () => {
      // Cleanup
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }

      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  // Ping-pong для поддержания соединения
  useEffect(() => {
    if (!connected) return

    const pingInterval = setInterval(() => {
      send({ action: 'ping' })
    }, 30000) // Каждые 30 секунд

    return () => clearInterval(pingInterval)
  }, [connected, send])

  return (
    <WebSocketContext.Provider
      value={{
        connected,
        subscribe,
        send,
        joinRoom,
        leaveRoom,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

// Хуки для конкретных типов сообщений
export function useWebSocketMessage<T extends WSMessage>(
  type: string,
  handler: (message: T) => void
) {
  const { subscribe } = useWebSocket()

  useEffect(() => {
    return subscribe(type, handler as MessageHandler)
  }, [subscribe, type, handler])
}
