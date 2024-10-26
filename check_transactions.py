import requests
from tonutils_api import api_key


def check_transactions(amount, wallet_address):
    # URL для получения списка транзакций
    transactions_url = f'https://testnet.tonapi.io/v2/blockchain/accounts/{wallet_address}/transactions'

    # Заголовки для запроса, включая API ключ
    headers = {
        'X-API-KEY': api_key
    }

    # Отправляем GET запрос
    response = requests.get(transactions_url, headers=headers)

    # Если ответ положительный
    if response.status_code == 200:
        # Запись ответа в переменную data
        data = response.json()

        # Проходим по всем транзакциям и извлекаем значение
        if 'transactions' in data:
            for transaction in data['transactions']:
                if 'in_msg' in transaction and 'value' in transaction['in_msg']:
                    value = transaction['in_msg']['value']
                    value_in_ton = value / 1000000000  # Перевод в TON

                    # Сравнение каждого значения с заданной суммой
                    if value_in_ton == amount:
                        return {"status": "success"}
            return {"status": "not_found"}
        else:
            return {"status": "no_transactions"}
    else:
        return {"status": "error"}