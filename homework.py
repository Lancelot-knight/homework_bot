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
    filemode='a'
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
        logging.error(f'Ошибка: {error}')


def get_api_answer(url, current_timestamp):
    """Запрос информации от сервера."""
    current_timestamp = current_timestamp or int(time.time())
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=headers, params=payload)
        if response.status_code != 200:
            raise NegativeError('Ошибка при получении ответа с сервера')
        logging.info('Сервер на связи')
        return response.json()
    except requests.RequestException as error:
        logging.error(f'Ошибка запроса: {error}')
        return False
    except ValueError as error:
        logging.error(f'У функции несоответствующее значение : {error}')
        return False


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
    old_error = None
    while True:
        try:
            get_result = get_api_answer(ENDPOINT, current_time)
            check_result = check_response(get_result)
            if check_result:
                for homework in check_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            current_time = get_result.get('current_date')
            time.sleep(RETRY_TIME)
        except Exception as error:
            if error != old_error:
                old_error = error
                send_message(bot, f'Сбой в работе: {error}')
                logging.error(f'Бот недееспособен, ошибка: {error}')
                time.sleep(RETRY_TIME)
            else:
                logging.error(f'Бот недееспособен, ошибка: {error}')
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
