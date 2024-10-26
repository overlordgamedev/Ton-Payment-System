import requests

# Замените на фактический токен аутентификации пользователя
UUID = 'd1fced81-9cb5-4843-8b7b-0887dfc35827'
# URL вашего сервера
URL = 'http://127.0.0.1:5000/check_transaction'

# Данные для создания инвойса
data = {
    'transaction_id': 1,
}

# Заголовки для запроса
headers = {
    'Authorization': UUID,
    'Content-Type': 'application/json'
}

# Отправляем запрос
response = requests.post(URL, headers=headers, json=data)

print(response.json())
