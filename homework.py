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

TOKENS = [
    PRACTICUM_TOKEN,
    TELEGRAM_TOKEN,
    CHAT_ID
]


class NegativeError(Exception):
    pass


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as error:
        print(error)


def get_api_answer(url, current_timestamp):
    """Запрос информации от сервера."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=headers, params=payload)
    except requests.RequestException as error:
        print(error)
    except ValueError as error:
        print(error)

    if response.status_code != 200:
        raise NegativeError('Ошибка при получении ответа с сервера')

    logging.info('Сервер на связи')
    return response.json()


def parse_status(homework):
    """Парсим статус домашки."""
    status = homework.get('status')
    if status is None:
        raise NegativeError('Нет статуса работы')
    verdict = HOMEWORK_STATUSES[homework.get('status')]
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise NegativeError('У домашки нет имени')
    if verdict is None:
        raise NegativeError('Нет статуса работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Проверяем запрос."""
    homeworks = response.get('homeworks')
    for homework in homeworks:
        status = homework.get('status')
        if status in HOMEWORK_STATUSES:
            return homeworks
        else:
            raise NegativeError('Нет статуса работы')
    return homeworks


def main():
    """Главный цикл работы."""
    if not all(TOKENS):
        logging.critical('Отсутствуют переменные окружения')
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    except Exception as error:
        logging.critical('Бот не инициализирован: '
                         f'{error}')

    current_timestamp = int(time.time())
    while True:
        try:
            get_result = get_api_answer(ENDPOINT, current_timestamp)
            check_result = check_response(get_result)
            if check_result:
                for homework in check_result:
                    parse_status_result = parse_status(homework)
                    send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logging.error('Бот недееспособен')
            send_message(
                chat_id=CHAT_ID, text=f'Сбой в работе программы: {error}'
            )
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
