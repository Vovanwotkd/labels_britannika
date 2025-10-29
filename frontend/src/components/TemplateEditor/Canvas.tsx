/**
 * Template Canvas Component
 * Canvas для визуального редактирования шаблона этикетки
 */

import { useRef, useState } from 'react'
import { TemplateElement, Position } from './types'

interface CanvasProps {
  width: number // мм
  height: number // мм
  elements: TemplateElement[]
  selectedElementId: string | null
  onElementSelect: (id: string | null) => void
  onElementMove: (id: string, position: Position) => void
  onElementResize: (id: string, width: number, height: number) => void
}

// Масштаб совпадает с принтером: 203 DPI / 25.4 mm/inch ≈ 8 px/mm
// Для увеличения используйте зум в интерфейсе редактора
const MM_TO_PX = 8

export default function Canvas({
  width,
  height,
  elements,
  selectedElementId,
  onElementSelect,
  onElementMove,
  onElementResize,
}: CanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const [dragging, setDragging] = useState<{
    elementId: string
    startX: number
    startY: number
    startPosX: number
    startPosY: number
  } | null>(null)

  const [resizing, setResizing] = useState<{
    elementId: string
    startX: number
    startY: number
    startWidth: number
    startHeight: number
  } | null>(null)

  const canvasWidthPx = width * MM_TO_PX
  const canvasHeightPx = height * MM_TO_PX

  const handleMouseDown = (e: React.MouseEvent, elementId: string) => {
    e.stopPropagation()
    onElementSelect(elementId)

    const element = elements.find((el) => el.id === elementId)
    if (!element) return

    setDragging({
      elementId,
      startX: e.clientX,
      startY: e.clientY,
      startPosX: element.position.x,
      startPosY: element.position.y,
    })
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (dragging) {
      const deltaX = (e.clientX - dragging.startX) / MM_TO_PX
      const deltaY = (e.clientY - dragging.startY) / MM_TO_PX

      const newX = Math.max(0, Math.min(width, dragging.startPosX + deltaX))
      const newY = Math.max(0, Math.min(height, dragging.startPosY + deltaY))

      onElementMove(dragging.elementId, { x: newX, y: newY })
    }

    if (resizing) {
      const deltaX = (e.clientX - resizing.startX) / MM_TO_PX
      const deltaY = (e.clientY - resizing.startY) / MM_TO_PX

      const newWidth = Math.max(5, resizing.startWidth + deltaX)
      const newHeight = Math.max(5, resizing.startHeight + deltaY)

      onElementResize(resizing.elementId, newWidth, newHeight)
    }
  }

  const handleMouseUp = () => {
    setDragging(null)
    setResizing(null)
  }

  const handleCanvasClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onElementSelect(null)
    }
  }

  const handleResizeMouseDown = (
    e: React.MouseEvent,
    elementId: string,
    element: TemplateElement
  ) => {
    e.stopPropagation()
    onElementSelect(elementId)

    setResizing({
      elementId,
      startX: e.clientX,
      startY: e.clientY,
      startWidth: element.size.width,
      startHeight: element.size.height,
    })
  }

  // Проверка пересечения двух элементов
  const checkOverlap = (el1: TemplateElement, el2: TemplateElement): boolean => {
    const left1 = el1.position.x
    const right1 = el1.position.x + el1.size.width
    const top1 = el1.position.y
    const bottom1 = el1.position.y + el1.size.height

    const left2 = el2.position.x
    const right2 = el2.position.x + el2.size.width
    const top2 = el2.position.y
    const bottom2 = el2.position.y + el2.size.height

    // Проверяем пересечение по обеим осям
    return !(right1 <= left2 || right2 <= left1 || bottom1 <= top2 || bottom2 <= top1)
  }

  // Проверка, накладывается ли элемент на другие
  const hasOverlap = (element: TemplateElement): boolean => {
    return elements.some(
      (other) =>
        other.id !== element.id &&
        other.visible &&
        element.visible &&
        checkOverlap(element, other)
    )
  }

  const renderElement = (element: TemplateElement) => {
    const isSelected = element.id === selectedElementId
    const isOverlapping = hasOverlap(element)
    const left = element.position.x * MM_TO_PX
    const top = element.position.y * MM_TO_PX
    const width = element.size.width * MM_TO_PX
    const height = element.size.height * MM_TO_PX

    let content = ''
    let bgColor = '#ffffff'

    // Расчёт реальной высоты для многострочных элементов
    let realHeight = height
    if (element.type === 'dish_name' || element.type === 'text' || element.type === 'composition') {
      const fontSize = 'fontSize' in element ? element.fontSize : 14
      const lineSpacing = 'lineSpacing' in element ? (element.lineSpacing ?? 1.4) : 1.4

      // Примерное количество строк (ширина 50мм, ~10 символов на строку для русского)
      let estimatedLines = 1
      if (element.type === 'dish_name') {
        estimatedLines = 2 // Название обычно 2 строки
      } else if (element.type === 'composition') {
        estimatedLines = 'maxLines' in element ? element.maxLines : 3
      } else if (element.type === 'text') {
        const textLength = 'content' in element ? (element.content?.length ?? 0) : 0
        estimatedLines = Math.max(1, Math.ceil(textLength / 30)) // ~30 символов на строку
      }

      // Реальная высота = количество строк * высота строки * lineSpacing
      // fontSize в пунктах, конвертируем в мм: 1pt ≈ 0.35mm
      const lineHeightMm = (fontSize * 0.35) * lineSpacing
      realHeight = lineHeightMm * estimatedLines * MM_TO_PX
    }

    switch (element.type) {
      case 'logo':
        content = element.imageUrl ? '🖼️' : 'Логотип'
        bgColor = '#e3f2fd'
        break
      case 'dish_name':
        content = 'Борщ с говядиной и сметаной'
        bgColor = '#fff8e1'
        break
      case 'text':
        content = element.content || element.fieldName || 'Текст'
        bgColor = '#fff3e0'
        break
      case 'composition':
        content = 'Состав: ...'
        bgColor = '#f3e5f5'
        break
      case 'bju':
        content = 'белки Xг, жиры Yг, углеводы Zг'
        bgColor = '#e8f5e9'
        break
      case 'weight':
        content = 'Вес: 155.0г'
        bgColor = '#fce4ec'
        break
      case 'energy_value':
        content = '41,1 ккал / 172,1 кДж'
        bgColor = '#e1f5fe'
        break
      case 'datetime':
        content = element.label || 'Дата:'
        bgColor = '#fff9c4'
        break
      case 'shelf_life':
        content = `Годен до: ${element.hours}ч`
        bgColor = '#ffe0b2'
        break
    }

    return (
      <div
        key={element.id}
        onMouseDown={(e) => handleMouseDown(e, element.id)}
        style={{
          position: 'absolute',
          left: `${left}px`,
          top: `${top}px`,
          width: `${width}px`,
          height: `${height}px`,
          border: isSelected
            ? '2px solid #2196F3'
            : isOverlapping
            ? '2px solid #ff9800'
            : '1px solid #ccc',
          backgroundColor: isOverlapping ? '#fff3e0' : bgColor,
          cursor: 'move',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '11px',
          overflow: 'hidden',
          userSelect: 'none',
          boxShadow: isSelected
            ? '0 0 8px rgba(33, 150, 243, 0.5)'
            : isOverlapping
            ? '0 0 6px rgba(255, 152, 0, 0.5)'
            : 'none',
          // Всегда используем тёмный текст на canvas для видимости
          color: '#333',
          fontWeight: 500,
          padding: '2px',
        }}
      >
        <span style={{
          maxWidth: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {content}
        </span>

        {/* Real height indicator - показывает реальную высоту многострочного текста */}
        {realHeight > height && (
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: `${height}px`,
              width: '100%',
              height: `${realHeight - height}px`,
              border: '1px dashed #9c27b0',
              backgroundColor: 'rgba(156, 39, 176, 0.05)',
              pointerEvents: 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '9px',
              color: '#9c27b0',
              fontWeight: 600,
            }}
          >
            Реальная высота текста
          </div>
        )}

        {/* Resize handle */}
        {isSelected && (
          <div
            onMouseDown={(e) => handleResizeMouseDown(e, element.id, element)}
            style={{
              position: 'absolute',
              right: '-4px',
              bottom: '-4px',
              width: '8px',
              height: '8px',
              backgroundColor: '#2196F3',
              cursor: 'nwse-resize',
              borderRadius: '50%',
            }}
          />
        )}
      </div>
    )
  }

  return (
    <div
      ref={canvasRef}
      onClick={handleCanvasClick}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{
        position: 'relative',
        width: `${canvasWidthPx}px`,
        height: `${canvasHeightPx}px`,
        backgroundColor: '#ffffff',
        border: '2px solid #333',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        overflow: 'hidden',
        cursor: dragging || resizing ? 'grabbing' : 'default',
      }}
    >
      {/* Grid lines */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `
            linear-gradient(to right, #e0e0e0 1px, transparent 1px),
            linear-gradient(to bottom, #e0e0e0 1px, transparent 1px)
          `,
          backgroundSize: `${10 * MM_TO_PX}px ${10 * MM_TO_PX}px`,
          pointerEvents: 'none',
        }}
      />

      {/* Elements */}
      {elements.filter((el) => el.visible).map((element) => renderElement(element))}

      {/* Dimensions label */}
      <div
        style={{
          position: 'absolute',
          top: '4px',
          right: '4px',
          fontSize: '10px',
          color: '#666',
          backgroundColor: 'rgba(255,255,255,0.8)',
          padding: '2px 6px',
          borderRadius: '3px',
          pointerEvents: 'none',
        }}
      >
        {width} × {height} мм
      </div>

      {/* Overlap warning */}
      {elements.filter((el) => el.visible && hasOverlap(el)).length > 0 && (
        <div
          style={{
            position: 'absolute',
            bottom: '4px',
            left: '50%',
            transform: 'translateX(-50%)',
            fontSize: '11px',
            color: '#f57c00',
            backgroundColor: 'rgba(255, 243, 224, 0.95)',
            padding: '4px 10px',
            borderRadius: '4px',
            border: '1px solid #ff9800',
            pointerEvents: 'none',
            fontWeight: 600,
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          }}
        >
          ⚠️ Элементы накладываются друг на друга
        </div>
      )}
    </div>
  )
}
