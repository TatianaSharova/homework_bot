import logging
import os
import sys
import time
from logging import StreamHandler

import requests
from dotenv import load_dotenv
from telegram.bot import Bot

from exceptions import CustomMessageException, CustomRequestException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Проверка доступности необходимых переменных окружения."""
    logger.debug('Проверка доступности переменных окружения.')

    if (
        PRACTICUM_TOKEN is None
        or TELEGRAM_TOKEN is None
        or TELEGRAM_CHAT_ID is None
    ):
        logger.critical("Отсутствие обязательных переменных окружения.")
        sys.exit(
            'Завершение программы. Отсутствуют переменные окружения.'
        )
    logger.debug('Проверка успешно пройдена.')
    return True


def send_message(bot, message):
    """Отправляем сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение успешно отправлено.')
    except CustomMessageException as error:
        logger.error(f'Ошибка при отправке сообщения: {error}.')
        raise CustomMessageException(error)


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    logger.debug(f'Попытка запроса к эндпоинту API-сервиса {ENDPOINT}'
                 F'с параметрами {params}.')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        status = response.status_code
        logger.debug(f'Эндпоинт API доступен. '
                     f'Ответ API: {response.text}. '
                     f'Статус ответа {status}.')
    except requests.RequestException as error:
        logger.error(f'Эндпоинт API недоступен: {error}.')
        raise CustomRequestException(str(error))
    else:
        status = response.status_code
        if status != requests.codes.ok:
            logger.debug(f'Ошибка при запросе к эндпоинту. '
                         f'Ответ API: {response.text}. '
                         f'Статус ответа {status}.')
            raise requests.HTTPError(f'Статус ответа {status}.')
    return response.json()
 

def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    logger.debug('Проверка ответа API на соответствие документации.')
    if not isinstance(response, dict):
        error = 'Неверный тип данных у элемента response.'
        logger.error(error)
        raise TypeError(error)
    elif 'homeworks' not in response:
        error = 'Ожидаемый ключ отсутствует в ответе API.'
        logger.error(error)
        raise KeyError(error)
    elif not isinstance(response["homeworks"], list):
        error = 'Неверный тип данных у элемента homeworks.'
        logger.error(error)
        raise TypeError(error)
    else:
        logger.debug('Ожидаемые ключи присутствуют в ответе API.')
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о конкретной домашке статус этой работы."""
    logger.debug('Попытка извлечь статус проверки работы.')

    try:
        'status' in homework
        homework_status = homework["status"]
        logger.debug('У работы есть статус.')
    except KeyError as error:
        logger.error(f'У домашки нет статуса. {error}')
        raise KeyError(error)

    try:
        'homework_name' in homework
        homework_name = homework["homework_name"]
        logger.debug(f'Домашка {homework_name} присутствует в ответе API.')
    except KeyError as error:
        logger.error(error)
        raise KeyError(error)
    
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        logger.error(f'Недокументированный статус домашки: {homework_status}.')
        raise ValueError(
            f'Недокументированный статус домашки: {homework_status}.'
        )

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if len(response['homeworks']) >0:
                homework = response['homeworks'][0]
                message = parse_status(homework)
                if message != last_message:
                    send_message(bot, message)
                    last_message = message
                    timestamp = int(time.time())
            else:
                logger.debug('Отсутствие нового статуса.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
