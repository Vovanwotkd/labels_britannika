/**
 * Type definitions for Britannica Labels
 */

// ============================================================================
// User & Auth
// ============================================================================

export interface User {
  id: number
  login: string
  role: 'operator' | 'admin'
  full_name: string | null
}

export interface AuthResponse {
  success: boolean
  message: string
  user?: User
}

// ============================================================================
// Orders & Items
// ============================================================================

export interface PrintJob {
  id: number
  status: 'QUEUED' | 'PRINTING' | 'DONE' | 'FAILED' | 'CANCELLED'
  created_at: string
  started_at: string | null
  printed_at: string | null
  retry_count: number
  error_message: string | null
}

export interface OrderItem {
  id: number
  rk_code: string
  name: string
  uni: number
  quantity: number
  price: number
  modifier_id: string | null
  modifier_name: string | null
  created_at: string
  print_jobs: PrintJob[]
}

export interface Order {
  id: number
  visit_id: string
  order_ident: string
  table_code: string
  table_name: string
  waiter_code: string | null
  waiter_name: string | null
  status: 'NOT_PRINTED' | 'PRINTING' | 'DONE' | 'FAILED' | 'CANCELLED'
  created_at: string
  updated_at: string
  items: OrderItem[]
}

export interface OrderListItem {
  id: number
  visit_id: string
  order_ident: string
  table_code: string
  table_name: string
  order_total: number | null
  status: 'NOT_PRINTED' | 'PRINTING' | 'DONE' | 'FAILED' | 'CANCELLED'
  created_at: string
  updated_at: string
  items_count: number
  jobs_count: number
  jobs_done: number
  jobs_failed: number
}

// ============================================================================
// Settings
// ============================================================================

export interface Setting {
  key: string
  value: string
  description: string | null
}

export interface TableFilter {
  id: number
  filter_type: 'include' | 'exclude'
  table_codes: string[]
  is_active: boolean
  description: string | null
}

// ============================================================================
// WebSocket Messages
// ============================================================================

export interface WSMessage {
  type: string
  [key: string]: any
}

export interface WSOrderUpdate extends WSMessage {
  type: 'order_update'
  event: 'new_order' | 'order_updated' | 'order_cancelled'
  order_id: number
  data: any
}

export interface WSPrintJobUpdate extends WSMessage {
  type: 'print_job_update'
  job_id: number
  status: 'QUEUED' | 'PRINTING' | 'DONE' | 'FAILED'
  order_item_id: number | null
}

export interface WSPrinterStatus extends WSMessage {
  type: 'printer_status'
  online: boolean
  error: string | null
}

// ============================================================================
// API Responses
// ============================================================================

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
}

export interface Template {
  id: number
  name: string
  brand_id: string
  is_default: boolean
}

export interface SystemInfo {
  app_name: string
  version: string
  environment: string
  timezone: string
  printer: {
    ip: string
    port: number
  }
  label: {
    width: number
    height: number
    gap: number
  }
  storehouse: {
    url: string
    user: string
    pass: string
  }
  rkeeper: {
    url: string
    user: string
    pass: string
    logging: boolean
  }
  default_template_id: number
  templates: Template[]
  database: {
    orders: number
    order_items: number
    print_jobs: {
      total: number
      queued: number
      printing: number
      done: number
      failed: number
    }
  }
  websocket: {
    connections: number
    rooms: {
      orders: number
    }
  }
}
