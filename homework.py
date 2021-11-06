import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s',
    filemode='a',
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


class NegativeError(Exception):
    """Кастомное исключение."""

    pass


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка: {error}')


def get_api_answer(url, current_timestamp):
    """Запрос информации от сервера."""
    current_timestamp = current_timestamp or int(time.time())
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=headers, params=payload)
        if response.status_code != 200:
            raise NegativeError('Ошибка при получении ответа с сервера')
        logger.info('Сервер на связи')
        return response.json()
    except requests.RequestException as request_error:
        msg = f'Код ответа API (RequestException): {request_error}'
        logger.error(msg)
        raise NegativeError(msg)
    except ValueError as value_error:
        msg = f'Код ответа API (ValueError): {value_error}'
        logger.error(msg)
        raise NegativeError(msg)


def parse_status(homework):
    """Парсим статус домашки."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise NegativeError('У домашки нет имени')
    status = homework.get('status')
    if status is None:
        raise NegativeError('Нет статуса работы')
    verdict = HOMEWORK_STATUSES[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Проверяем запрос."""
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise NegativeError("Нет списка 'homework'")
    if not isinstance(homeworks, list):
        raise NegativeError("Неверный формат 'homework'")
    if not homeworks:
        return False
    for homework in homeworks:
        status = homework.get('status')
        if status in HOMEWORK_STATUSES:
            return homework
        else:
            raise NegativeError('Нет статуса работы')


def main():
    """Главный цикл работы."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_time = int(time.time())
    errors = False
    while True:
        try:
            get_result = get_api_answer(ENDPOINT, current_time)
            check_result = check_response(get_result)
            if check_result:
                message = parse_status(check_result)
                send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Бот недеесспособен, ошибка: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logger.critical(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
