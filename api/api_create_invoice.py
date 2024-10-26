import requests

UUID = 'd1fced81-9cb5-4843-8b7b-0887dfc35827'
# URL API
URL = 'http://127.0.0.1:5000/create_invoice'

# Данные для создания инвойса
data = {
    'amount': 2.0,
}

# Заголовки для запроса
headers = {
    'Authorization': UUID,
    'Content-Type': 'application/json'
}

# Отправляем запрос
response = requests.post(URL, headers=headers, json=data)

print(response.json())
