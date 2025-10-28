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
  dish_name: string | null
  quantity: number
  weight_g: number | null
  printed_count: number
  last_printed_at: string | null
  print_jobs: PrintJob[]
}

export interface Order {
  id: number
  visit_id: string
  order_ident: string
  table_code: string
  order_total: number | null
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

export interface PrinterInfo {
  name: string
  online: boolean
  status: string
}

export interface SystemInfo {
  app_name: string
  version: string
  environment: string
  timezone: string
  printer: {
    type: string  // "tcp" or "cups"
    ip: string
    port: number
    name: string  // CUPS printer name
    cups_darkness: number  // CUPS darkness level (0-15)
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
  default_extra_template_id: number | null
  selected_departments: Record<string, string[]> | null
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
