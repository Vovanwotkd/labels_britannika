/**
 * Template Editor Types
 * Типы для визуального редактора шаблонов
 */

export type ElementType =
  | 'logo'
  | 'dish_name'
  | 'text'
  | 'composition'
  | 'bju'
  | 'weight'
  | 'datetime'
  | 'shelf_life'

export type FontFamily = 'Calibri' | 'Arial' | 'Times New Roman'

export interface Position {
  x: number
  y: number
}

export interface Size {
  width: number
  height: number
}

export interface BaseElement {
  id: string
  type: ElementType
  position: Position
  size: Size
  visible: boolean
}

export interface LogoElement extends BaseElement {
  type: 'logo'
  imageUrl?: string
  imageData?: string // base64
}

export interface TextElement extends BaseElement {
  type: 'text'
  content: string
  fontSize: number
  fontFamily: FontFamily
  fontWeight: 'normal' | 'bold'
  color: string
  align: 'left' | 'center' | 'right'
  fieldName?: string // для динамических полей (dish_name, weight_g и т.д.)
}

export interface DishNameElement extends BaseElement {
  type: 'dish_name'
  fontSize: number
  fontFamily: FontFamily
  fontWeight: 'normal' | 'bold'
  color: string
  align: 'left' | 'center' | 'right'
}

export interface CompositionElement extends BaseElement {
  type: 'composition'
  fontSize: number
  fontFamily: FontFamily
  fontWeight: 'normal' | 'bold'
  color: string
  maxLines: number
}

export interface BJUElement extends BaseElement {
  type: 'bju'
  fontSize: number
  fontFamily: FontFamily
  fontWeight: 'normal' | 'bold'
  color: string
  showProteins: boolean
  showFats: boolean
  showCarbs: boolean
  showCalories: boolean
}

export interface WeightElement extends BaseElement {
  type: 'weight'
  fontSize: number
  fontFamily: FontFamily
  fontWeight: 'normal' | 'bold'
  color: string
  showUnit: boolean // показывать "г" или нет
}

export interface DateTimeElement extends BaseElement {
  type: 'datetime'
  fontSize: number
  fontFamily: FontFamily
  fontWeight: 'normal' | 'bold'
  color: string
  format: 'datetime' | 'date' | 'time'
  label: string // "Дата производства:", "Годен до:" и т.д.
}

export interface ShelfLifeElement extends BaseElement {
  type: 'shelf_life'
  fontSize: number
  fontFamily: FontFamily
  fontWeight: 'normal' | 'bold'
  color: string
  hours: number // срок годности в часах
}

export type TemplateElement =
  | LogoElement
  | DishNameElement
  | TextElement
  | CompositionElement
  | BJUElement
  | WeightElement
  | DateTimeElement
  | ShelfLifeElement

export interface TemplateConfig {
  paper_width_mm: number
  paper_height_mm: number
  paper_gap_mm: number
  shelf_life_hours?: number  // Срок годности (часы)
  bitmap_width?: number  // Ширина BITMAP изображений для оптимизации (px), по умолчанию 280
  elements: TemplateElement[]
}

export interface Template {
  id: number
  name: string
  brand_id: string
  is_default: boolean
  config: TemplateConfig
  created_at?: string
  updated_at?: string
}
