@"
import socket

tspl = '''SIZE 58 mm, 60 mm
GAP 2 mm, 0 mm
DIRECTION 1
CLS
TEXT 50,30,"DEJAVU.TTF",0,14,14,"Тест шрифта"
TEXT 50,70,"DEJAVU.TTF",0,12,12,"Оладьи Лосось"
TEXT 50,110,"DEJAVU.TTF",0,10,10,"Вес: 350г  Ккал: 298"
TEXT 50,150,"DEJAVU.TTF",0,8,8,"Б: 15г Ж: 20г У: 30г"
PRINT 1
'''

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)
sock.connect(('10.55.3.254', 9100))
sock.sendall(tspl.encode('utf-8'))
sock.close()
print('✅ Test label sent')
"@ | Out-File -Encoding utf8 test_print.py

python test_print.py