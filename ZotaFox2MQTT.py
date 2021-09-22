import functools
import math
import socket
import struct
import sys
import struct
import subprocess

#Выбираем источник. По сети или локально через com-port
SOURCE = 'STREAM'
streamIP = '192.168.10.124'
streamPORT = 23
# SOURCE = 'SERIAL'
serialPORT = "/dev/ttyUSB0"
serialBAUDRATE = 115200

#Для вывода данных в консоль устанавливаем переменную PrintToConsole в 1. При других значениях в консоль не выводим.
PrintToConsole = "1"

#Для отправки данных в mqtt устанавливаем переменную SendToMQTT в 1, определяем путь к mosquitto_pub, топик и хост.
SendToMQTT = "1"
mosquitto_path = "/usr/bin/mosquitto_pub"
mosquitto_topic = "/ZotaFox"
mosquitto_host = "localhost"

RAMKA_START = 0x68
RAMKA_STOP = 0x16

NADAWCA_ECOMAX = 0x45

def parseFrame(message):
    if message[0] == 0x08:
        parseFrame08(message)

def parseFrame08(message):
    OPERATING_STATUS_byte = 27
    FIRE_float = 72
    TEMP_CO_float = 80
    TEMP_CO_MAX_SET_short = 154
    TEMP_CWU_float = 84
    TEMP_WEATHER_float = 92
    FUEL_LEVEL_byte=199
    POWERKW_FLOAT=235
    IGNITIONS_short = 252

    OPERATION_STATUSES = {0:'Выключено', 1:'Розжиг', 2:'Работа', 4:'Тушение', 5:'Ожидание', 8:'Очистка', 10:'Alarm'}
    if message[OPERATING_STATUS_byte] in OPERATION_STATUSES:
      OperStatus = OPERATION_STATUSES[message[OPERATING_STATUS_byte]]
    else:
      OperStatus = str(message[OPERATING_STATUS_byte])
    tempCWU = struct.unpack("f", bytes(message[TEMP_CWU_float:TEMP_CWU_float+4]))[0]
    tempCO = struct.unpack("f", bytes(message[TEMP_CO_float:TEMP_CO_float+4]))[0]
    tempCOmaxset = struct.unpack("h", bytes(message[TEMP_CO_MAX_SET_short:TEMP_CO_MAX_SET_short+2]))[0]
    tempOut= struct.unpack("f", bytes(message[TEMP_WEATHER_float:TEMP_WEATHER_float+4]))[0]
    PowerKW = struct.unpack("f", bytes(message[POWERKW_FLOAT:POWERKW_FLOAT+4])) [0]
    Fire = struct.unpack("f", bytes(message[FIRE_float:FIRE_float+4])) [0]
    igns = struct.unpack("H", bytes(message[IGNITIONS_short:IGNITIONS_short+2])) [0]
    
    if PrintToConsole == "1":
        print(f"Состояние: {OperStatus}")
        print(f"Температура горелки: {tempCWU:.1f}")
        print(f"Температура теплоносителя: {tempCO:.1f}")
        print(f"Установленная max температура теплоносителя: {tempCOmaxset:.1f}")
        print(f"Температура улицы: {tempOut:.1f}")
        print(f"Уровень топлива: {message[FUEL_LEVEL_byte]}%")
        print(f"Мощность котла: {PowerKW:.1f}")
        print(f"Пламя: {Fire:.1f}")
        print(f"Количество розжигов: {igns}")

    if SendToMQTT == "1":
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/State","-m", OperStatus])
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/TempBurner","-m", str(f"{tempCWU:.1f}")])
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/TempCO","-m", str(f"{tempCO:.1f}")])
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/TempCOmaxset","-m", str(f"{tempCOmaxset:.1f}")])
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/TempOut","-m", str(f"{tempOut:.1f}")])
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/FuelLevel","-m", str(f"{message[FUEL_LEVEL_byte]}")])
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/PowerKW","-m", str(f"{PowerKW:.1f}")])
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/Fire","-m", str(f"{Fire:.1f}")])
        subprocess.run([mosquitto_path, "-h", mosquitto_host,"-t", mosquitto_topic+"/Ignitions","-m", str(f"{igns:.1f}")])

    exit()


try:
  SOURCE
except:
  print("Источник данных не выбран! Исправьте конфигурацию в начале этого файла.")
  exit()


if SOURCE == 'STREAM':
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((streamIP, streamPORT))

elif SOURCE == 'SERIAL':
  ser = serial.Serial(serialPORT, serialBAUDRATE)
  ser.bytesize = serial.EIGHTBITS
  ser.parity = serial.PARITY_NONE
  ser.stopbits = serial.STOPBITS_ONE
  ser.open()
else:
  print("Неизвестный тип источника данных. Исправьте конфигурацию в начале этого файла.")
  exit()


bajtCzytany = 0 # bajt aktualnie przetwarzany
bajtPoprzedni = 0
ramka = []
#mapa ramki
START_BYTE = 0              #[0]
ROZMIAR_RAMKI_SHORT = 1     #[1,2]
ADRES_ODBIORCY_BYTE = 3     #[3]
ADRES_NADAWCY_BYTE = 4      #[4]
TYP_NADAWCY_BYTE = 5        #[5]
WERSJA_ECONET_BYTE = 6      #[6]
TYP_RAMKI = 7               #[7]
CRC_BYTE = -2               #[przedostatni bajt]
MESSAGE_START = 7           #od-do [7:-2]


while True:

  if SOURCE == 'STREAM':
    chunk = s.recv(1)
  elif SOURCE == 'SERIAL':
    chunk = ser.read(1)

  bajtCzytany = ord(chunk)


  if bajtCzytany == RAMKA_START and bajtPoprzedni == RAMKA_STOP:

    if len(ramka) > 0:

      ramkaCRC = ramka[-2]
      myCRC = functools.reduce(lambda x,y: x^y, ramka[:-2])

      if myCRC == ramkaCRC:

        ramkaHEX = [f'{ramka[i]:02X}' for i in range(0, len(ramka))]

        message = ramka[MESSAGE_START:CRC_BYTE]
        messageHEX = ramkaHEX[MESSAGE_START:CRC_BYTE]


        if len(message) > 1 and ramka[ADRES_NADAWCY_BYTE] == NADAWCA_ECOMAX and PrintToConsole == "1":
          print("")
          print(f"== [ramka] [Тип кадра: 0x{ramka[TYP_RAMKI]:02X}] [Размер кадра:{len(ramka)}] [Отправитель: 0x{ramka[ADRES_NADAWCY_BYTE]:02X}] [Получатель: 0x{ramka[ADRES_ODBIORCY_BYTE]:02X}] [CRC:0x{ramkaCRC:02X}] ==")
          rowsize=12
          for row in range(math.ceil(len(message)/rowsize)):
            od = row*rowsize
            do = od+rowsize if len(message) >= od+rowsize else len(message)
            print(f"{od:03d}-{do-1:03d} \t{' '.join(messageHEX[od:do])}", end='')
            print('   ' * ((od+rowsize)-do), end='')
            print(f" \t{message[od:do]}")

        if ramka[ADRES_NADAWCY_BYTE] == NADAWCA_ECOMAX:
          parseFrame(message)

    ramka = []


  ramka.append(bajtCzytany)

  bajtPoprzedni = bajtCzytany
