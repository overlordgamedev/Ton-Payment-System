from tonutils.client import TonapiClient
from tonutils.wallet import WalletV3R1
from tonutils_api import api_key


# Функция создания кошелька с параметром означающим работу в тестовой сети
def create_wallet(is_testnet=True):
    client = TonapiClient(api_key=api_key, is_testnet=is_testnet)
    # Создание кошелька
    wallet, public_key, private_key, mnemonic = WalletV3R1.create(client)

    # Конвертация ключей в hex формат
    public_key_hex = public_key.hex()
    private_key_hex = private_key.hex()

    # Возвращает данные от кошелька в виде словаря json
    return {
        "address": wallet.address.to_str(),
        "public_key": public_key_hex,
        "private_key": private_key_hex,
        "mnemonic": mnemonic
    }
