import asyncio
import random
import requests
from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from uuid import uuid4
from sqlalchemy import ForeignKey
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from tonutils.client import TonapiClient
from tonutils.wallet import WalletV3R1

from check_transactions import check_transactions
from create_wallets import create_wallet
from tonutils_api import api_key

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
# Инициализирует библиотеку для того что бы хэшировать пароль и не хранить его в чистом виде
bcrypt = Bcrypt(app)

class Users(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    # Значение по умолчанию это генерация UUID
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=str(uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    # Столбцы для данных кошелька
    wallet_address = db.Column(db.String(50), nullable=True)
    public_key = db.Column(db.String(128), nullable=True)
    private_key = db.Column(db.String(128), nullable=True)
    mnemonic = db.Column(MutableList.as_mutable(db.JSON), nullable=True)  # Используется тип данных JSON

    # Связь с таблицей Transactions
    transactions = relationship("Transactions", backref="user", lazy=True)


class Transactions(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)  # Внешний ключ для связи с Users
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())


@app.route('/register', methods=['GET', 'POST'])
def register():
    # POST запрос означает что на адрес был отправлен запрос с html страницы в котором должны передаваться данные из полей ввода
    if request.method == 'POST':
        # Извлекает данные из полей с сайта
        username = request.form.get('username')
        password = request.form.get('password')

        # Если одно из полей пустое или оба пустые
        if not username or not password:
            return jsonify({"error": "Требуется имя пользователя и пароль"}), 400

        # Сравнивает данные из переменной с данными из бд
        existing_user = Users.query.filter_by(username=username).first()

        # Если данные сходятся, то регистрации не происходит и выводится ошибка
        if existing_user:
            return jsonify({"error": "Имя пользователя занято"}), 400

        # Берет пароль из переменной и хеширует его с помощью generate_password_hash и записывает хэш в переменную
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Назначает столбцам из бд данные из переменных (пароль в виде хэша)
        new_user = Users(username=username, password=hashed_password)

        # Добавляет новые данные в сессию
        db.session.add(new_user)
        # Сохраняет изменения в базе данных
        db.session.commit()

        # Создаем кошелек и получаем его данные
        wallet_data = create_wallet()  # Вызов функции для создания кошелька

        # Сохраняем данные кошелька в базу данных
        new_user.wallet_address = wallet_data["address"]
        new_user.public_key = wallet_data["public_key"]
        new_user.private_key = wallet_data["private_key"]
        new_user.mnemonic = wallet_data["mnemonic"]

        db.session.commit()  # Сохраняем изменения

        # Если все действия выше были выполнены удачно и пользователь зарегистрирован, то переадресация на страницу авторизации
        return redirect(url_for('login'))
    # Это если GET запрос, то есть если просто переход по ссылке в браузере
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Получение данных из полей ввода
        username = request.form.get('username')
        password = request.form.get('password')

        # Если одно или оба поля ввода пустые
        if not username or not password:
            return jsonify({"error": "Требуется имя пользователя и пароль"}), 400

        # Сравнивает введённое имя пользователя с данными в базе данных
        user = Users.query.filter_by(username=username).first()

        # Если пользователь найден, то сравнивает его пароль в виде хэша с паролем из поля ввода
        if user and bcrypt.check_password_hash(user.password, password):
            # Записывает в сессию, внутрь ключа user_id ид из столбца в базе данных
            session['user_id'] = user.id
            return redirect(url_for('profile'))

        return jsonify({"error": "Неправильное имя пользователя или пароль"}), 401

    return render_template('login.html')


# Выход из сессии
@app.route('/logout', methods=['POST'])
def logout():
    # Отчищает сессию от ключа с ид пользователя и ставит значение None
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/profile')
def profile():
    # Проверяем, что пользователь авторизован
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Получаем данные пользователя
    user = Users.query.get(session['user_id'])

    wallet_address = user.wallet_address
    balance_url = f'https://testnet.tonapi.io/v2/accounts/{wallet_address}'

    # Отправляем GET-запрос на API для получения баланса
    headers = {'X-API-KEY': api_key}
    response = requests.get(balance_url, headers=headers)

    if response.status_code == 200:
        # Извлекаем баланс и преобразуем его в TON
        data = response.json()
        balance = data.get('balance') / 1000000000  # Преобразуем в TON
    else:
        balance = "Ошибка при получении баланса"

    # Передаём баланс и данные пользователя на страницу
    return render_template('profile.html', username=user.username, uuid=user.uuid, wallet_address=user.wallet_address,
                           balance=balance)

@app.route('/transfer', methods=['POST'])
def transfer():
    # Получаем данные из формы
    amount = float(request.form.get('amount'))
    destination_address = request.form.get('destination_address')
    user_id = session.get('user_id')  # Получаем user_id из сессии

    # Проверка наличия user_id в сессии
    if not user_id:
        return jsonify({"error": "Пользователь не найден"}), 401

    # Извлекаем сид-фразу пользователя из базы данных
    user = Users.query.get(user_id)
    seed = user.mnemonic  # Сид-фраза из базы данных

    # Запуск функции перевода
    tx_hash = asyncio.run(execute_transfer(seed, amount, destination_address))
    return jsonify({"message": "Перевод выполнен", "tx_hash": tx_hash})


async def execute_transfer(seed, amount, destination_address):
    client = TonapiClient(api_key=api_key, is_testnet=True)
    wallet, public_key, private_key, mnemonic = WalletV3R1.from_mnemonic(client, seed)
    tx_hash = await wallet.transfer(destination=destination_address, amount=amount, body="Перевод с профиля")
    return tx_hash


@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    # Извлекаем UUID из заголовков запроса
    uuid = request.headers.get('Authorization')
    if not uuid:
        return jsonify({"error": "UUID не предоставлен"}), 400

    # Ищем пользователя с этим UUID в базе данных
    user = Users.query.filter_by(uuid=uuid).first()
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Извлекаем данные из запроса и записываем в переменную
    data = request.json
    # Запись суммы из ключа amount
    amount = data.get('amount')
    # Добавляем небольшое случайное значение от 0.00001 до 0.00011
    random_increment = random.uniform(0.00001, 0.00999)
    amount = round(amount + random_increment, 5)
    if amount is None:
        return jsonify({"error": "Сумма не предоставлена"}), 400

    # Создаем новую заявку и добавляем в базу данных
    transaction = Transactions(user_id=user.id, amount=amount)
    db.session.add(transaction)
    db.session.commit()

    # Возвращаем ответ с суммой и ID транзакции
    return jsonify({"transaction_id": transaction.id, "amount": transaction.amount, "wallets": user.wallet_address}), 201


@app.route('/check_transaction', methods=['POST'])
def check_transaction():
    # Извлекаем UUID из заголовков запроса
    uuid = request.headers.get('Authorization')
    if not uuid:
        return jsonify({"error": "UUID не предоставлен"}), 400

    # Ищем пользователя с этим UUID в базе данных
    user = Users.query.filter_by(uuid=uuid).first()
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Извлекаем данные из запроса и записываем в переменную
    data = request.json
    transaction_id = data.get('transaction_id')

    if transaction_id is None:
        return jsonify({"error": "ID транзакции не предоставлен"}), 400

    # Ищем транзакцию по ID и user_id
    transaction = Transactions.query.filter_by(id=transaction_id, user_id=user.id).first()
    if not transaction:
        return jsonify({"error": "Транзакция не найдена"}), 404

    # Получаем сумму и адрес кошелька из данных пользователя и транзакции
    amount = transaction.amount
    wallet_address = user.wallet_address

    # Вызываем функцию для проверки транзакции
    result = check_transactions(amount, wallet_address)

    # Возвращаем ответ на основе результата проверки
    if result['status'] == "success":
        return jsonify({"status": "success"}), 200
    elif result['status'] == "not_found":
        return jsonify({"status": "not_found"}), 404
    elif result['status'] == "no_transactions":
        return jsonify({"status": "message"}), 404
    else:
        return jsonify({"status": "error"}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="localhost", port="5000", debug=True)
