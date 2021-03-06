# ZotaFox2MQTT
Прежде всего выражаю благодарность [Tomasz Król](https://github.com/twkrol), его проекту [econetanalyze](https://github.com/twkrol/econetanalyze) и пользователям форума elektroda.pl в [этой](https://www.elektroda.pl/rtvforum/topic3346727.html) ветке. Без них у меня бы мозгов не хватило на все это))
***
Предисловие

Плюмовские контроллеры работают со своими периферийными устройствами по шине RS485. С комнатными термостатами, панелями, эконетами и прочими. Все идет через RS485. Сам контроллер раз в пару секунд шлет типа броадкастного пакета в шину с данными о своем состоянии. Ну и собственно можно получить эти данные, распарсить и куда-то перегнать. В теории можно прикинуться панелькой или эконетом и попробовать самому отправить данные в контроллер для изменения параметров. Но мне удаленное управление совсем не критично, а вот мониторинг горелки в едином умном доме вместе с остальными устройствами прям в тему.

***
Данный скрипт позволяет получить и опубликовать в mqtt некоторые данные с пеллетной горелки Zota Fox, которая сделана на базе контроллера Plum Ecomax850P2.
У Tomasz Król анализатор для контроллера Ecomax860, а в Ecomax850 немного другой протокол, поэтому пришлось посниффить что там гуляет по RS485 и удалось получить следующие данные:
1. Состояние котла: Выключен, Розжиг, Работа, Тушение, Ожидание, Очистка. (Моя горелка переходит только между этими режимами, "Надзора" нет, может быть еще чего-то не хватает)
2. Температура горелки
3. Установленная максимальная температура теплоносителя (это температура, до которой горелка будет нагонять теплоноситель. Если включено погодное управление, то этот параметр плавает в зависимости от уличной температуры)
4. Температура теплоносителя
5. Температура улицы (если подключен уличный датчик)
6. Уровень топлива
7. Текущая мощность горелки
8. Уровень пламени
9. Количество розжигов
***
Что надо сделать для получения данных:

Необходимо подключить какой-либо преобразователь RS485-to-RS232 к контроллеру и уже с преобразователя получать данные. Преобразователь может быть usb, com, wi-fi и т.д. Главное чтоб у преобразователя на выходе был serial порт к которому можно подключиться. В моем случае я выбрал RS485-to-WiFi конвертер Elfin-EW11A (лютый китай), стоит недорого, работает стабильно. Первый раз пробовал конвертер RS485-to-TTL подключить к esp8266 с прошивкой ESPEasy, но почему-то большие пакеты такая связка неправильно переводила из RS485 в Serial. Может быть конвертер кривой был, может дело было в прошивке ESPEasy, я не стал разбираться. С Elfin-EW11A взлетело все с первого раза.
***
Как подключить конвертер Elfin-EW11A к контроллеру:

Снимаем верхнюю крышку с контроллера, в левом верхнем углу платы контроллера отсоединяем понель от разъема RJ-11. Чуть ниже этого разъема видим шесть винтовых клемм. Нас интересуют первые четыре: +5В,D+,D-,GND. Выводим с этих клемм четыре провода и подключаем к Elfin-EW11A, питание к питанию, D+ к A+, D- к B-. Подключение к другим конвертерам аналогично: питание если надо к питанию, дата к дате. Втыкаем обратно панель и все закрываем. Далее настраиваем конвертер для подключения к Wi-Fi и настраиваем чтоб он работал как tcp сервер. Если используется конвертер, подключаемый к компьютеру, то настраиваем его чтоб он был com-портом.
***
Как работает скрипт:

Для работы скрипта нужен установленный python, для отправки в mqtt нужен установленный mosquitto_pub.<br>
В скрипте надо указать адрес и порт конвертера (или com-порт если используется конверт, подключенный к компьютеру напрямую, типа RS485-to-USB к примеру), можно выбрать печатать/не печатать данные в консоль, отправлять/не отправлять в mqtt, путь к mosquitto_pub, хост mqtt и имя топика.<br>
Логика работы скрипта очень простая: подключение к конвертеру, ожидание данных от контроллера, получение данных, вывод на экран, отправка в mqtt, завершение работы. Если при запуске из консоли все работает и видно полученные данные, то можно отключить вывод в консоль, запихнуть скрипт в крон и получать данные хоть каждую минуту.
***
Home Assistant:

В файле configuration.yaml прикинуто как можно загнать эти данные в HA. В HA выглядит как-то так:

![](https://github.com/Begemoty-shli/ZotaFox2MQTT/raw/main/images/ZotaFoxHA.jpg)



