import secrets
import os

def generate_secret_key():
    """Генерирует случайный секретный ключ длиной 32 символа."""
    return secrets.token_urlsafe(32)

if __name__ == "__main__":
    key = generate_secret_key()
    print(key)  # Выводит сгенерированный ключ в консоль
    with open(".env", "w") as f:
        f.write(f"{key}") 