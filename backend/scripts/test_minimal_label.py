#!/usr/bin/env python3
"""
Тест минимальной этикетки с оптимизированным BITMAP
"""

import sys
from pathlib import Path

# Добавляем путь к app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.printer.bitmap_renderer import BitmapRenderer
import socket


def create_minimal_label():
    """
    Создаем минимальную этикетку с оптимизированными bitmap
    """

    tspl_commands = []

    # Настройки бумаги
    tspl_commands.append("SIZE 58 mm, 60 mm")
    tspl_commands.append("GAP 2 mm, 0 mm")
    tspl_commands.append("DIRECTION 1")
    tspl_commands.append("CLS")

    # НАЗВАНИЕ - уменьшаем шрифт и ширину
    title_bitmap = BitmapRenderer.text_to_bitmap_tspl(
        text="Оладьи Лосось",
        x=10,
        y=20,
        font_size=18,  # Было 24, стало 18
        width=300      # Было 400, стало 300
    )
    tspl_commands.append(title_bitmap)

    # ВЕС И КАЛОРИИ - мелкий шрифт
    wc_bitmap = BitmapRenderer.text_to_bitmap_tspl(
        text="Вес: 350г | 298 ккал",
        x=10,
        y=45,
        font_size=12,  # Было 16, стало 12
        width=250      # Было 400, стало 250
    )
    tspl_commands.append(wc_bitmap)

    # БЖУ - мелкий шрифт
    bju_bitmap = BitmapRenderer.text_to_bitmap_tspl(
        text="Б:15г Ж:20г У:30г",
        x=10,
        y=65,
        font_size=12,  # Было 16, стало 12
        width=250      # Было 400, стало 250
    )
    tspl_commands.append(bju_bitmap)

    # ДАТА - без "Изготовлено", только дата
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%d.%m %H:%M")

    date_bitmap = BitmapRenderer.text_to_bitmap_tspl(
        text=f"Изг: {date_str}",
        x=10,
        y=85,
        font_size=10,  # Было 16, стало 10
        width=200      # Было 400, стало 200
    )
    tspl_commands.append(date_bitmap)

    # СРОК ГОДНОСТИ
    shelf_str = (now.replace(hour=now.hour + 6)).strftime("%d.%m %H:%M")
    shelf_bitmap = BitmapRenderer.text_to_bitmap_tspl(
        text=f"До: {shelf_str}",
        x=10,
        y=100,
        font_size=10,  # Было 16, стало 10
        width=200      # Было 400, стало 200
    )
    tspl_commands.append(shelf_bitmap)

    # Печать
    tspl_commands.append("PRINT 1")

    return "\n".join(tspl_commands)


def send_to_printer(tspl_data: str, printer_ip: str = "10.55.3.254", port: int = 9100):
    """
    Отправляет TSPL на принтер
    """
    print(f"📊 TSPL размер: {len(tspl_data)} байт ({len(tspl_data)/1024:.1f} KB)")
    print(f"📤 Отправка на {printer_ip}:{port}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((printer_ip, port))
        sock.sendall(tspl_data.encode('utf-8'))
        sock.close()

        print("✅ Отправлено успешно!")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("BRITANNICA LABELS - Тест минимальной этикетки")
    print("=" * 70)
    print()

    # Создаем этикетку
    print("🏗️  Генерация TSPL...")
    tspl = create_minimal_label()

    # Показываем превью
    print()
    print("=" * 70)
    print("TSPL КОМАНДЫ:")
    print("=" * 70)
    print(tspl[:500] + "..." if len(tspl) > 500 else tspl)
    print("=" * 70)
    print()

    # Отправляем на принтер
    printer_ip = sys.argv[1] if len(sys.argv) > 1 else "10.55.3.254"
    send_to_printer(tspl, printer_ip)

    print()
    print("=" * 70)
    print("Готово!")
    print("=" * 70)
