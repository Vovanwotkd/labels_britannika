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

const MM_TO_PX = 8 // Увеличенный масштаб для удобства редактирования

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

  const renderElement = (element: TemplateElement) => {
    const isSelected = element.id === selectedElementId
    const left = element.position.x * MM_TO_PX
    const top = element.position.y * MM_TO_PX
    const width = element.size.width * MM_TO_PX
    const height = element.size.height * MM_TO_PX

    let content = ''
    let bgColor = '#ffffff'

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
        content = 'Б/Ж/У/Ккал'
        bgColor = '#e8f5e9'
        break
      case 'weight':
        content = 'Вес: 250г'
        bgColor = '#fce4ec'
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
          border: isSelected ? '2px solid #2196F3' : '1px solid #ccc',
          backgroundColor: bgColor,
          cursor: 'move',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '12px',
          overflow: 'hidden',
          userSelect: 'none',
          boxShadow: isSelected ? '0 0 8px rgba(33, 150, 243, 0.5)' : 'none',
        }}
      >
        {content}

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
    </div>
  )
}
