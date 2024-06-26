# Homework bot
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/)

Телеграм бот, который работает в качестве нотифаера: когда меняется статус проверки домашки от яндексПрактикума, приходит уведомление с новым статусом работы. В боте подключено логгирование, а в случае ошибки бот присылает сообщение с текстом ошибки.

В зависимости от ответа API, приходит 1 из 3 уведомлений:  
1. Работа проверена: ревьюеру всё понравилось. Ура!  
2. Работа взята на проверку ревьюером.  
3. Работа проверена: у ревьюера есть замечания.



### Локальный запуск бота:

**_Склонировать репозиторий к себе_**
```
git@github.com:TatianaSharova/homework_bot.git
```
**_В директории проекта создать файл .env и заполнить своими данными:_**
```
PRACTICUM_TOKEN        - токен от API яндекса
TELEGRAM_TOKEN         - токен вашего телеграм бота
TELEGRAM_CHAT_ID       - id вашего аккаунта в телеграме
```
**_Создать и активировать виртуальное окружение:_**

Для Linux/macOS:
```
python3 -m venv venv
```
```
source venv/bin/activate
```
Для Windows:
```
python -m venv venv
```
```
source venv/Scripts/activate
```
**_Установить зависимости из файла requirements.txt:_**
```
pip install -r requirements.txt
```
**_Запустить бот:_**
```
python bot.py
```

### Автор
[Татьяна Шарова](https://github.com/TatianaSharova)
