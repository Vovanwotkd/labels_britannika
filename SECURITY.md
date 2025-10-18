# 🔒 Безопасность и Учётные Данные

## ⚠️ ВАЖНО: Credentials НЕ должны попадать в git!

Этот проект использует чувствительные данные (пароли, API ключи), которые **НЕ должны** храниться в репозитории.

---

## 📋 Файлы с credentials (НЕ в git)

### ❌ Что НЕ должно быть в репозитории:

1. **`.env`** - файл с переменными окружения (пароли, ключи)
2. **`export_dishes_with_extras.py`** - скрипт с hardcoded credentials
3. **Любые файлы с паролями или API ключами**

### ✅ Что ЕСТЬ в репозитории:

1. **`.env.example`** - пример конфигурации (без реальных паролей)
2. **`export_dishes_with_extras.py.example`** - пример скрипта
3. **`.gitignore`** - правила игнорирования чувствительных файлов

---

## 🚀 Первоначальная Настройка

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/Vovanwotkd/-labels_britannika.git
cd -labels_britannika
```

### 2. Создайте файл .env

```bash
# Скопируйте пример
cp .env.example .env

# Отредактируйте своими данными
nano .env
```

**Укажите реальные значения:**

```env
# Store House 5
SH5_URL=http://10.0.0.141:9797/api/sh5exec
SH5_USER=Admin
SH5_PASS=ВАШ_РЕАЛЬНЫЙ_ПАРОЛЬ

# Принтер
PRINTER_IP=192.168.1.10

# Секретный ключ (сгенерируйте новый!)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

### 3. Создайте скрипт экспорта

```bash
# Скопируйте пример
cp export_dishes_with_extras.py.example export_dishes_with_extras.py

# Отредактируйте (укажите credentials или используйте .env)
nano export_dishes_with_extras.py
```

**Вариант 1: Использовать .env (рекомендуется)**

Скрипт автоматически прочитает credentials из `.env`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

SH_URL = os.getenv("SH5_URL")
SH_USER = os.getenv("SH5_USER")
SH_PASS = os.getenv("SH5_PASS")
```

**Вариант 2: Hardcoded (не рекомендуется)**

Укажите напрямую в коде:

```python
SH_URL = "http://10.0.0.141:9797/api/sh5exec"
SH_USER = "Admin"
SH_PASS = "ваш_пароль"
```

⚠️ **Важно:** При hardcoded credentials файл `export_dishes_with_extras.py` **НЕ должен** попадать в git!

---

## 🔐 Генерация Секретных Ключей

### SECRET_KEY для сессий

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Скопируйте результат в `.env`:

```env
SECRET_KEY=a1b2c3d4e5f6...
```

---

## 🛡️ Проверка Безопасности

### Перед commit - убедитесь:

```bash
# 1. Проверьте .gitignore
cat .gitignore | grep -E "(\.env|export_dishes)"

# Должно вывести:
# .env
# export_dishes_with_extras.py

# 2. Проверьте что файлы НЕ в git
git ls-files | grep -E "(\.env|export_dishes_with_extras\.py)$"

# Ничего не должно вывести!

# 3. Проверьте staged файлы
git status

# .env и export_dishes_with_extras.py НЕ должны быть в списке!
```

---

## 🚨 Если Credentials Попали в Git

### Если вы случайно закоммитили credentials:

#### 1. Немедленно удалите из git

```bash
# Удалить файл из индекса
git rm --cached .env
git rm --cached export_dishes_with_extras.py

# Добавить в .gitignore (если ещё не добавлено)
echo ".env" >> .gitignore
echo "export_dishes_with_extras.py" >> .gitignore

# Закоммитить изменения
git add .gitignore
git commit -m "Remove credentials from git"
```

#### 2. Переписать историю (если уже запушили)

⚠️ **ВНИМАНИЕ:** Это изменит историю git!

```bash
# Удалить файл из ВСЕЙ истории
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch export_dishes_with_extras.py" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (перезапишет историю на сервере!)
git push origin --force --all
```

#### 3. Смените пароли!

Если credentials попали в публичный репозиторий:
- ✅ Смените пароль Store House 5
- ✅ Смените SECRET_KEY
- ✅ Проверьте логи на подозрительную активность

---

## 📝 Checklist Безопасности

### Перед началом разработки:

- [ ] Создан файл `.env` из `.env.example`
- [ ] Все пароли указаны корректно
- [ ] Сгенерирован новый `SECRET_KEY`
- [ ] Создан `export_dishes_with_extras.py` из примера
- [ ] Файлы `.env` и `export_dishes_with_extras.py` **НЕ в git**

### Перед каждым commit:

- [ ] `git status` не показывает `.env` или скрипты с паролями
- [ ] В коде нет hardcoded паролей
- [ ] Все credentials загружаются из переменных окружения

### Production deployment:

- [ ] `.env` файл создан на сервере (не копируется из репозитория!)
- [ ] Права доступа к `.env`: `chmod 600 .env`
- [ ] `export_dishes_with_extras.py` имеет права: `chmod 600`
- [ ] Логи не содержат паролей

---

## 📞 Что делать при утечке?

1. **Немедленно смените все пароли**
2. **Удалите credentials из git истории** (см. выше)
3. **Проверьте логи доступа** к Store House 5
4. **Уведомите администратора**

---

## 🔗 Полезные Ссылки

- [12-Factor App: Config](https://12factor.net/config)
- [OWASP: Storing Secrets](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub: Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

**Версия**: 1.0
**Дата**: 19.10.2025
