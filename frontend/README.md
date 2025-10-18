# Britannica Labels - Frontend

React + TypeScript + Vite + Tailwind CSS фронтенд для системы печати этикеток.

## Технологии

- **React 18** - UI библиотека
- **TypeScript** - Типизация
- **Vite** - Сборщик и dev сервер
- **Tailwind CSS** - Стилизация
- **React Router** - Маршрутизация
- **WebSocket** - Real-time обновления

## Установка

```bash
npm install
```

## Запуск dev сервера

```bash
npm run dev
```

Приложение запустится на http://localhost:3000

## Сборка для production

```bash
npm run build
```

Файлы будут собраны в директорию `dist/`

## Структура проекта

```
src/
├── api/              # API клиенты
│   └── client.ts     # REST API client
├── components/       # React компоненты
│   ├── Layout.tsx
│   ├── ProtectedRoute.tsx
│   └── OrderCard.tsx
├── contexts/         # React контексты
│   ├── AuthContext.tsx      # Аутентификация
│   └── WebSocketContext.tsx # WebSocket
├── pages/            # Страницы
│   ├── LoginPage.tsx
│   ├── OrdersBoard.tsx
│   └── SettingsPage.tsx
├── types/            # TypeScript типы
│   └── index.ts
├── App.tsx           # Главный компонент
├── main.tsx          # Entry point
└── index.css         # Глобальные стили
```

## Особенности

### Real-time обновления

Приложение использует WebSocket для получения обновлений в реальном времени:

- Новые заказы от RKeeper
- Изменения статуса печати
- Обновления статуса принтера

```typescript
// Пример использования WebSocket
import { useWebSocketMessage } from '../contexts/WebSocketContext'

useWebSocketMessage<WSOrderUpdate>('order_update', (message) => {
  console.log('Order update:', message)
})
```

### Аутентификация

Cookie-based аутентификация:

- Логин/логаут
- Защищённые роуты
- Проверка прав доступа (operator/admin)

```typescript
// Пример защищённого роута
<ProtectedRoute>
  <OrdersBoard />
</ProtectedRoute>
```

### API клиент

Типизированный API клиент с автоматической обработкой ошибок:

```typescript
import { ordersApi } from '../api/client'

// Получить все заказы
const orders = await ordersApi.getAll({ status: 'NOT_PRINTED' })

// Отменить заказ
await ordersApi.cancel(orderId)
```

## Конфигурация

### Vite Proxy

В dev режиме Vite проксирует запросы к backend:

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
  '/ws': {
    target: 'ws://localhost:8000',
    ws: true,
  },
}
```

### Tailwind CSS

Кастомизация цветов в `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        500: '#0ea5e9',
        600: '#0284c7',
        700: '#0369a1',
      },
    },
  },
}
```

## Тестовый пользователь

- **Логин:** admin
- **Пароль:** admin

## Production deployment

1. Собрать frontend:
```bash
npm run build
```

2. Настроить nginx для раздачи статики и проксирования API:

```nginx
server {
    listen 80;
    server_name labels.local;

    # Frontend статика
    location / {
        root /path/to/frontend/dist;
        try_files $uri /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Дополнительная информация

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vite.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [TypeScript Documentation](https://www.typescriptlang.org/)
