/**
 * API Client для взаимодействия с backend
 */

import type {
  User,
  AuthResponse,
  Order,
  OrderListItem,
  Setting,
  TableFilter,
  SystemInfo,
  PrinterInfo,
} from '../types'

const API_BASE_URL = '/api'

// ============================================================================
// Helper Functions
// ============================================================================

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include', // Важно для cookie
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

// ============================================================================
// Auth API
// ============================================================================

export const authApi = {
  login: (login: string, password: string) =>
    fetchApi<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ login, password }),
    }),

  logout: () =>
    fetchApi('/auth/logout', {
      method: 'POST',
    }),

  checkAuth: () =>
    fetchApi<{ authenticated: boolean; user: User | null }>('/auth/check'),

  getCurrentUser: () => fetchApi<User>('/auth/me'),
}

// ============================================================================
// Orders API
// ============================================================================

export const ordersApi = {
  getAll: (params?: {
    status?: string
    table_code?: string
    limit?: number
    offset?: number
  }) => {
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.table_code) query.set('table_code', params.table_code)
    if (params?.limit) query.set('limit', params.limit.toString())
    if (params?.offset) query.set('offset', params.offset.toString())

    return fetchApi<OrderListItem[]>(`/orders/?${query.toString()}`)
  },

  getById: (id: number) => fetchApi<Order>(`/orders/${id}`),

  delete: (id: number) =>
    fetchApi(`/orders/${id}`, {
      method: 'DELETE',
    }),

  cancel: (id: number) =>
    fetchApi(`/orders/${id}/cancel`, {
      method: 'POST',
    }),

  reprint: (orderItemId: number, quantity?: number) =>
    fetchApi('/orders/reprint', {
      method: 'POST',
      body: JSON.stringify({
        order_item_id: orderItemId,
        quantity,
      }),
    }),

  cleanup: (days: number = 7) =>
    fetchApi(`/orders/cleanup?days=${days}`, {
      method: 'DELETE',
    }),
}

// ============================================================================
// Print API
// ============================================================================

export const printApi = {
  testPrint: () =>
    fetchApi('/print/test', {
      method: 'POST',
    }),

  printDish: (rkCode: string, quantity: number = 1) =>
    fetchApi('/print/dish', {
      method: 'POST',
      body: JSON.stringify({
        rk_code: rkCode,
        quantity,
      }),
    }),

  getPrinterStatus: () => fetchApi('/print/status'),
}

// ============================================================================
// Settings API
// ============================================================================

export const settingsApi = {
  getAll: () => fetchApi<Setting[]>('/settings/'),

  getByKey: (key: string) => fetchApi<Setting>(`/settings/${key}`),

  update: (key: string, value: string) =>
    fetchApi('/settings/', {
      method: 'PUT',
      body: JSON.stringify({ key, value }),
    }),

  batchUpdate: (settings: Array<{ key: string; value: string }>) =>
    fetchApi('/settings/batch', {
      method: 'POST',
      body: JSON.stringify(settings),
    }),

  getFilters: () => fetchApi<TableFilter[]>('/settings/filters/'),

  getFilterById: (id: number) => fetchApi<TableFilter>(`/settings/filters/${id}`),

  createFilter: (data: {
    filter_type: 'include' | 'exclude'
    table_codes: string[]
    is_active?: boolean
    description?: string
  }) =>
    fetchApi<TableFilter>('/settings/filters/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateFilter: (
    id: number,
    data: {
      filter_type?: 'include' | 'exclude'
      table_codes?: string[]
      is_active?: boolean
      description?: string
    }
  ) =>
    fetchApi<TableFilter>(`/settings/filters/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteFilter: (id: number) =>
    fetchApi(`/settings/filters/${id}`, {
      method: 'DELETE',
    }),

  getSystemInfo: () => fetchApi<SystemInfo>('/settings/system/info'),

  updateSettingsBatch: (settings: Array<{ key: string; value: string }>) =>
    fetchApi('/settings/batch', {
      method: 'POST',
      body: JSON.stringify(settings),
    }),
}

// ============================================================================
// Test Connection API
// ============================================================================

export interface TestConnectionResponse {
  success: boolean
  message: string
  details?: Record<string, any>
}

export const testConnectionApi = {
  testPrinter: () =>
    fetchApi<TestConnectionResponse>('/test/printer', {
      method: 'POST',
    }),

  testStorehouse: () =>
    fetchApi<TestConnectionResponse>('/test/storehouse', {
      method: 'POST',
    }),

  testRKeeper: () =>
    fetchApi<TestConnectionResponse>('/test/rkeeper', {
      method: 'POST',
    }),
}

// ============================================================================
// RKeeper API
// ============================================================================

interface RKeeperTable {
  code: string
  name: string
  ident?: string
  status?: string
  hall?: string
}

export const rkeeperApi = {
  getTables: () => fetchApi<RKeeperTable[]>('/rkeeper/tables'),

  getSelectedTables: () => fetchApi<RKeeperTable[]>('/rkeeper/tables/selected'),

  saveTables: (tables: Array<{ code: string; name: string }>) =>
    fetchApi('/rkeeper/tables/save', {
      method: 'POST',
      body: JSON.stringify({ tables }),
    }),
}

// ============================================================================
// Templates API
// ============================================================================

import type { Template } from '../components/TemplateEditor/types'

export const templatesApi = {
  getAll: () => fetchApi<Template[]>('/templates/'),

  getById: (id: number) => fetchApi<Template>(`/templates/${id}`),

  create: (template: Omit<Template, 'id' | 'created_at' | 'updated_at'>) =>
    fetchApi<Template>('/templates/', {
      method: 'POST',
      body: JSON.stringify(template),
    }),

  update: (id: number, template: Partial<Template>) =>
    fetchApi<Template>(`/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(template),
    }),

  delete: (id: number) =>
    fetchApi(`/templates/${id}`, {
      method: 'DELETE',
    }),

  setDefault: (id: number) =>
    fetchApi(`/templates/${id}/set-default`, {
      method: 'POST',
    }),

  testPrint: (id: number) =>
    fetchApi(`/templates/${id}/test-print`, {
      method: 'POST',
    }),
}

// ============================================================================
// Sync API
// ============================================================================

export interface SyncStatus {
  last_sync: string | null
  last_error: string | null
  interval_hours: number
}

export interface SyncTriggerResponse {
  status: string
  message: string
  pid: number
  started_at: string
}

export interface SyncOrdersResponse {
  status: 'success' | 'error'
  fetched_from_rkeeper: number
  orders_created: number
  orders_updated: number
  orders_marked_done: number
  orders_marked_cancelled: number
  message: string
  synced_at: string
}

export const syncApi = {
  getStatus: () => fetchApi<SyncStatus>('/sync/status'),

  getProgress: () => fetchApi<any>('/sync/progress'),

  trigger: () =>
    fetchApi<SyncTriggerResponse>('/sync/trigger', {
      method: 'POST',
    }),

  syncOrders: () =>
    fetchApi<SyncOrdersResponse>('/sync/orders', {
      method: 'POST',
    }),
}

// ============================================================================
// Printers API
// ============================================================================

export interface PrintersListResponse {
  printers: string[]  // Backend returns array of printer names
  count: number
}

export const printersApi = {
  getList: () => fetchApi<PrintersListResponse>('/printers/list'),

  getStatus: (printerName: string) =>
    fetchApi<PrinterInfo>(`/printers/${encodeURIComponent(printerName)}/status`),
}

// ============================================================================
// Departments API
// ============================================================================

export interface TreeNode {
  name: string
  count: number
  level: number
  children?: TreeNode[]
}

export interface DepartmentsTreeResponse {
  tree: TreeNode[]
  error?: string
}

export const departmentsApi = {
  getTree: () => fetchApi<DepartmentsTreeResponse>('/departments/tree'),
}
