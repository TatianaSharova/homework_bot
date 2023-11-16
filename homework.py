import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (CustomHTTPException, CustomJSONDecodeError,
                        CustomMessageException, CustomRequestException)

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
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens() -> None:
    """Проверка доступности необходимых переменных окружения."""
    logger.info('Проверка доступности переменных окружения.')
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(tokens):
        raise KeyError('Отсутствует переменная окружения.')
    logger.info('Проверка успешно пройдена.')


def send_message(bot: telegram.Bot, message: str) -> telegram.Message:
    """Отправляем сообщение."""
    logger.info('Пытаемся отправить сообщение.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        raise CustomMessageException(error)
    else:
        logger.debug('Сообщение успешно отправлено.')


def get_api_answer(timestamp: int) -> dict:
    """Запрос к эндпоинту API-сервиса."""
    params = {
        'url': ENDPOINT,
        'params': {'from_date': timestamp},
        'headers': HEADERS
    }
    logger.info(f'Попытка запроса к эндпоинту API-сервиса {ENDPOINT}'
                f'с параметрами {params}.')
    try:
        response = requests.get(**params)
    except requests.RequestException as error:
        raise CustomRequestException(f'Эндпоинт API недоступен: {error}. '
                                     f'url запроса: {ENDPOINT}. '
                                     f'Заголовок: {HEADERS}.')
    else:
        if response.status_code != HTTPStatus.OK:
            logger.debug(f'Ошибка при запросе к эндпоинту. '
                         f'Ответ API: {response.text}. '
                         f'Статус ответа {response.status_code}.')
            raise CustomHTTPException(f'Статус ответа {response.status_code}.')
    finally:
        logger.info(f'Эндпоинт API доступен. '
                    f'Ответ API: {response.text}. '
                    f'Статус ответа {response.status_code}.')

    try:
        response = response.json()
    except requests.JSONDecodeError as error:
        raise CustomJSONDecodeError(error)
    else:
        return response


def check_response(response: dict) -> list:
    """Проверяет ответ API на соответствие документации."""
    logger.info('Проверка ответа API на соответствие документации.')
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных у элемента response.')
    elif 'homeworks' not in response:
        raise KeyError('Ожидаемый ключ отсутствует в ответе API.')
    elif not isinstance(response["homeworks"], list):
        raise TypeError('Неверный тип данных у элемента homeworks.')
    else:
        logger.info('Ожидаемые ключи присутствуют в ответе API.')
    return response["homeworks"]


def parse_status(homework: dict) -> str:
    """Извлекает из информации о конкретной домашке статус этой работы."""
    logger.info('Попытка извлечь статус проверки работы.')
    if 'status' not in homework:
        raise KeyError('У домашки нет статуса.')
    elif 'homework_name' not in homework:
        raise KeyError('Домашка не найдена.')
    else:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        logger.info('Домашка найдена, у неё есть статус.')

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        raise ValueError(
            f'Недокументированный статус домашки: {homework_status}.'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:  # noqa: C901
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    last_message = ''

    try:
        check_tokens()
    except KeyError as error:
        logger.critical(
            f'Отсутствуют необходимые переменные окружения. {error}'
        )
        sys.exit(1)

    while True:
        try:
            try:
                response = get_api_answer(timestamp)
            except CustomRequestException as error:
                logger.error(error)
            except CustomHTTPException as error:
                logger.error(error)
            except CustomJSONDecodeError as error:
                logger.error(error)

            try:
                homework = check_response(response)
            except TypeError as error:
                logger.error(error)
            except KeyError as error:
                logger.error(error)

            if len(response['homeworks']) > 0:
                homework = response['homeworks'][0]
                try:
                    message = parse_status(homework)
                except KeyError as error:
                    logger.error(error)
                except ValueError as error:
                    logger.error(error)
                if message != last_message:
                    try:
                        send_message(bot, message)
                    except CustomMessageException as error:
                        logger.error(
                            f'Ошибка при отправке сообщения: {error}.'
                        )
                    last_message = message
                    timestamp = int(time.time())
            else:
                logger.debug('Отсутствие нового статуса.')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
            if message != last_message:
                send_message(bot, message)
            last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
