#!/usr/bin/env python3
"""
Upload TTF font to TSC printer
Загрузка TTF шрифта в принтер TSC PC-365B
"""

import sys
import socket
import os
from pathlib import Path

def upload_font_to_printer(font_path: str, printer_ip: str, printer_port: int = 9100, font_name: str = None):
    """
    Upload TTF font to TSC printer

    Args:
        font_path: Path to TTF font file
        printer_ip: Printer IP address
        printer_port: Printer port (default 9100)
        font_name: Font name in printer memory (default: filename)
    """

    # Check file exists
    if not os.path.exists(font_path):
        print(f"❌ Font file not found: {font_path}")
        return False

    # Get file size
    file_size = os.path.getsize(font_path)
    print(f"📁 Font file: {font_path}")
    print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

    # Read font file
    with open(font_path, 'rb') as f:
        font_data = f.read()

    # Use filename if font_name not specified
    if not font_name:
        font_name = Path(font_path).name

    print(f"📝 Font name in printer: {font_name}")

    # Prepare TSPL DOWNLOAD command
    # Format: DOWNLOAD "filename",size,data
    tspl_header = f'DOWNLOAD "{font_name}",{file_size},'.encode('ascii')

    print(f"📤 Connecting to printer {printer_ip}:{printer_port}...")

    try:
        # Connect to printer
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)  # 30 seconds timeout
        sock.connect((printer_ip, printer_port))

        print(f"✅ Connected")
        print(f"📤 Uploading font...")

        # Send DOWNLOAD command + font data
        sock.sendall(tspl_header + font_data)

        # Wait for response
        sock.settimeout(5)
        try:
            response = sock.recv(1024)
            print(f"📥 Printer response: {response}")
        except socket.timeout:
            print(f"⏱️  No response (timeout - likely OK for large file)")

        sock.close()

        print(f"✅ Font uploaded successfully!")
        print(f"")
        print(f"You can now use the font in TSPL commands:")
        print(f'TEXT 50,50,"{font_name}",0,12,12,"Test Text"')

        return True

    except Exception as e:
        print(f"❌ Error uploading font: {e}")
        return False


def test_font(printer_ip: str, font_name: str, printer_port: int = 9100):
    """
    Test uploaded font by printing a label
    """

    tspl = f'''SIZE 58 mm, 60 mm
GAP 2 mm, 0 mm
DIRECTION 1
CLS
TEXT 50,30,"{font_name}",0,14,14,"Тест шрифта"
TEXT 50,70,"{font_name}",0,12,12,"Оладьи Лосось"
TEXT 50,110,"{font_name}",0,10,10,"Вес: 350г  Ккал: 298"
TEXT 50,150,"{font_name}",0,8,8,"Б: 15г Ж: 20г У: 30г"
PRINT 1
'''

    print(f"🖨️  Testing font {font_name}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((printer_ip, printer_port))
        sock.sendall(tspl.encode('utf-8'))
        sock.close()

        print(f"✅ Test label sent to printer")
        return True

    except Exception as e:
        print(f"❌ Error testing font: {e}")
        return False


if __name__ == "__main__":
    # Default values
    FONT_PATH = "../fonts/DejaVuSans.ttf"
    FONT_NAME = "DEJAVU.TTF"
    PRINTER_IP = "10.55.3.253"
    PRINTER_PORT = 9100

    # Parse command line arguments
    if len(sys.argv) > 1:
        PRINTER_IP = sys.argv[1]

    if len(sys.argv) > 2:
        FONT_PATH = sys.argv[2]

    # Get absolute path
    script_dir = Path(__file__).parent
    font_path = (script_dir / FONT_PATH).resolve()

    print("=" * 70)
    print("BRITANNICA LABELS - Upload Font to Printer")
    print("=" * 70)
    print()

    # Upload font
    success = upload_font_to_printer(
        font_path=str(font_path),
        printer_ip=PRINTER_IP,
        printer_port=PRINTER_PORT,
        font_name=FONT_NAME
    )

    if success:
        print()
        print("=" * 70)
        print("Do you want to test the font? (y/n)")
        print("=" * 70)

        # In Docker, skip interactive prompt
        if os.environ.get('DOCKER_CONTAINER'):
            response = 'y'
        else:
            response = input().lower().strip()

        if response == 'y':
            print()
            test_font(PRINTER_IP, FONT_NAME, PRINTER_PORT)

    print()
    print("=" * 70)
    print("Done!")
    print("=" * 70)
