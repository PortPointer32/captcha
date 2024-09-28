import logging
import asyncio
import pytz
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types, filters
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from robot import database
import aiohttp
from aiohttp import ClientSession
import json
import os
import re
from crypto import periodic_crypto_update
import subprocess
from io import StringIO
from robot.start import start_main, restart_main

logging.basicConfig(level=logging.INFO)

API_TOKEN = '7233911716:AAFV-NKYt6jTtkJZHbWzOo88SsGtFn--Io8'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

database.initialize()

class Form(StatesGroup):
    token = State()

class OrderNumberState(StatesGroup):
    waiting_for_order_number = State()

class SettingsStates(StatesGroup):
    help_text = State()
    cooperation_text = State()
    rules_text = State()
    preorder_text = State()
    edit_card = State()
    edit_btc = State()

class MailingStates(StatesGroup):
    mailing_text = State()
    mailing_photo = State()
    daily_mailing_time = State()

class ProductAddStates(StatesGroup):
    city = State()
    product_name = State()
    product_price = State()
    
async def daily_mailing_task():
    moscow_tz = pytz.timezone('Europe/Moscow')
    while True:
        now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
        now_msk = now_utc.astimezone(moscow_tz)
        mailings = database.get_daily_mailings()
        for mailing in mailings:
            mailing_time = datetime.strptime(mailing[1], "%H:%M").time()
            current_time_msk = now_msk.time()
            if current_time_msk >= mailing_time and (datetime.combine(datetime.today(), current_time_msk) - datetime.combine(datetime.today(), mailing_time)) < timedelta(minutes=1):
                tokens = database.get_tokens()
                for token in tokens:
                    bot_child = Bot(token=token[0])
                    users = database.get_users_by_token(token[0])
                    for user in users:
                        user_id = user[0]
                        try:
                            if mailing[3]:  
                                absolute_photo_path = os.path.abspath(mailing[3])
                                with open(absolute_photo_path, 'rb') as photo_file:
                                    await bot_child.send_photo(user_id, photo=photo_file, caption=mailing[2], parse_mode='HTML')
                            else:
                                await bot_child.send_message(user_id, text=mailing[2], parse_mode='HTML')
                        except Exception as e:
                            logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
                        await bot_child.close()
        await asyncio.sleep(60)  

main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.add(KeyboardButton("➕Добавить Бота"), KeyboardButton("🤖 Текущие Боты"))
main_keyboard.add(KeyboardButton("🧑🏼‍💻Настройки"))

cancel_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
cancel_keyboard.add(KeyboardButton("❌ Отмена"))

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer("Привет, я создан для управления твоим Ботом.", reply_markup=main_keyboard)

@dp.message_handler(lambda message: message.text == "➕Добавить Бота", state="*")
async def add_bot(message: types.Message, state: FSMContext):
    await state.finish()  
    await Form.token.set()
    await message.answer("Отправь мне токен бота:", reply_markup=cancel_keyboard)

@dp.message_handler(state=Form.token)
async def process_token(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Добавление бота отменено.", reply_markup=main_keyboard)
        return

    tokens = message.text.split('\n')
    for token in tokens:
        try:
            temp_bot = Bot(token=token)
            bot_user = await temp_bot.get_me()
            username = bot_user.username
            await temp_bot.close()

            database.add_token(token, username)
            await message.answer(f"Бот @{username} успешно добавлен.", reply_markup=main_keyboard)
        except Exception as e:
            await message.answer(f"Ошибка с токеном {token}: {e}", reply_markup=main_keyboard)

    restart_main()
    await state.finish()
    
@dp.message_handler(commands=['get'])
async def get_database_info(message: types.Message):
    database_info = database.get_full_database_info()
    link = await upload_text(database_info)
    await message.answer(f"Вот ссылка на данные из базы данных: {link}")

@dp.message_handler(commands=['delcity'])
async def command_delete_city(message: types.Message):
    city_ids = message.get_args().replace(" ", "").split(",")
    deleted_ids = []
    for city_id in city_ids:
        if city_id.isdigit():
            database.delete_city(int(city_id))
            deleted_ids.append(city_id)
    if deleted_ids:
        await message.reply(f"Города с ID {', '.join(deleted_ids)} и все связанные с ними категории и товары удалены.")
    else:
        await message.reply("Пожалуйста, укажите корректные ID городов.")

@dp.message_handler(commands=['delcategory'])
async def command_delete_category(message: types.Message):
    category_ids = message.get_args().replace(" ", "").split(",")
    deleted_ids = []
    for category_id in category_ids:
        if category_id.isdigit():
            database.delete_category(int(category_id))
            deleted_ids.append(category_id)
    if deleted_ids:
        await message.reply(f"Категории с ID {', '.join(deleted_ids)} и все связанные с ними товары удалены.")
    else:
        await message.reply("Пожалуйста, укажите корректные ID категорий.")

@dp.message_handler(commands=['delproduct'])
async def command_delete_product(message: types.Message):
    product_ids = message.get_args().replace(" ", "").split(",")
    deleted_ids = []
    for product_id in product_ids:
        if product_id.isdigit():
            database.delete_product(int(product_id))
            deleted_ids.append(product_id)
    if deleted_ids:
        await message.reply(f"Товары с ID {', '.join(deleted_ids)} удалены.")
    else:
        await message.reply("Пожалуйста, укажите корректные ID товаров.")

@dp.message_handler(lambda message: message.text == "🤖 Текущие Боты", state="*")
async def current_bots(message: types.Message, state: FSMContext):
    await state.finish()
    bots = database.get_tokens()
    bots_info = StringIO()

    for index, bot in enumerate(bots, start=1):
        token, username = bot
        bots_info.write(f"{index}. Юзернейм: @{username}, Токен:\n{token}\n\n")

    bots_info.seek(0)
    await message.answer_document(types.InputFile(bots_info, filename="bots_info.txt"))

@dp.callback_query_handler(filters.Text(startswith="delete_"))
@dp.message_handler(commands=['delbot'])
async def delete_bot(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Пожалуйста, используйте команду в формате: /delete <token>")
        return

    token = parts[1]
    database.delete_token(token)
    await message.reply("Бот успешно удален.")
    restart_main()
                           
@dp.message_handler(commands=['delete'])
async def delete_everything(message: types.Message):
    database.clear_database()

    await message.answer("База данных очищена.")

@dp.message_handler(lambda message: message.text == "🧑🏼‍💻Настройки", state="*")
async def settings(message: types.Message, state: FSMContext):
    await state.finish()
    total_users_count = database.get_total_users_count()  

    inline_kb = InlineKeyboardMarkup(row_width=2)
    inline_kb.add(
        InlineKeyboardButton("Добавить товары", callback_data="settings_products"),
        InlineKeyboardButton("Рассылка", callback_data="settings_mailing"),
        InlineKeyboardButton("Ежедневные рассылки", callback_data="daily_mailing_check"),
        InlineKeyboardButton("Номер заказа", callback_data="settings_order_number")
    )
    settings_text = "Выберите, что хотите сделать:\n\nОбщее количество пользователей: " + str(total_users_count)
    await message.answer(settings_text, reply_markup=inline_kb)

@dp.callback_query_handler(lambda c: c.data == "settings_order_number", state="*")
async def handle_order_number_setting(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    current_order_value = database.get_order_value()

    order_text = f"Введите новое значение для номера заказа:\n\nТекущее: <b>{current_order_value}</b>"
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

    await bot.send_message(callback_query.from_user.id, order_text, reply_markup=markup, parse_mode='HTML')

    await OrderNumberState.waiting_for_order_number.set()

@dp.message_handler(lambda message: message.text.isdigit(), state=OrderNumberState.waiting_for_order_number)
async def set_new_order_number(message: types.Message, state: FSMContext):
    new_order_number = int(message.text)

    database.set_order_value(new_order_number)

    await state.finish()
    await message.answer(f"Номер заказа успешно обновлен на <b>{new_order_number}</b>.", parse_mode='HTML')

@dp.message_handler(lambda message: not message.text.isdigit(), state=OrderNumberState.waiting_for_order_number)
async def invalid_order_number_input(message: types.Message, state: FSMContext):
    await message.answer("Ошибка: пожалуйста, введите числовое значение для номера заказа.")

@dp.callback_query_handler(lambda c: c.data == 'settings_products')
async def add_product_start(callback_query: types.CallbackQuery):
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    await bot.send_message(callback_query.from_user.id, "Введите название города:", reply_markup=markup)
    await ProductAddStates.city.set()

@dp.message_handler(state=ProductAddStates.city, content_types=types.ContentTypes.TEXT)
async def process_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['city'] = message.text
    await bot.send_message(message.chat.id, "Введите название товара:", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel")))
    await ProductAddStates.product_name.set()

@dp.message_handler(state=ProductAddStates.product_name, content_types=types.ContentTypes.TEXT)
async def process_product_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['product_name'] = message.text
    await bot.send_message(message.chat.id, "Введите цену и районы для товара в формате 'цена(район1,район2)' каждый с новой строки:", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel")))
    await ProductAddStates.product_price.set()

@dp.message_handler(state=ProductAddStates.product_price, content_types=types.ContentTypes.TEXT)
async def process_product_price(message: types.Message, state: FSMContext):
    price_data = message.text
    price_entries = price_data.split('\n')

    async with state.proxy() as data:
        city_id = database.add_city_if_not_exists(data['city'])
        product_name_id = database.add_product(data['product_name'], city_id)

        for entry in price_entries:
            try:
                price, districts = entry.split('(')
                districts = districts.strip(')').strip()
                price = float(price.strip())

                database.add_product_details(product_name_id, price, districts)

                await message.answer(f"Добавлен товар: {price} руб., Районы: {districts}")
            except ValueError as e:
                await message.answer(f"Ошибка при обработке строки '{entry}': {e}")
                continue

        await message.answer("Все товары успешно добавлены.")
        await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'settings_mailing')
async def mailing_start(callback_query: types.CallbackQuery):
    await bot.send_message(
        callback_query.from_user.id,
        "Введите текст сообщения для рассылки (поддерживается HTML разметка):",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    )
    await MailingStates.mailing_text.set()

@dp.message_handler(state=MailingStates.mailing_text, content_types=types.ContentTypes.TEXT)
async def process_mailing_text(message: types.Message, state: FSMContext):
    await state.update_data(mailing_text=message.text)
    skip_photo_button = InlineKeyboardMarkup().add(InlineKeyboardButton("Пропустить", callback_data="skip_photo"))
    await message.answer("Теперь отправьте фотографию для рассылки или нажмите 'Пропустить'", reply_markup=skip_photo_button)
    await MailingStates.next()

@dp.callback_query_handler(lambda c: c.data == 'skip_photo', state=MailingStates.mailing_photo)
async def skip_photo(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(mailing_photo=None)
    data = await state.get_data()
    mailing_text = data['mailing_text']
    await bot.send_message(
        callback_query.from_user.id,
        "Вы пропустили добавление фото.\n\n" + mailing_text,
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton("✅ Отправить", callback_data="confirm_send"),
            InlineKeyboardButton("🕝 Ежедневная рассылка", callback_data="daily_mailing")
        ).add(InlineKeyboardButton("❌ Отменить", callback_data="cancel")),
        parse_mode='HTML'
    )

@dp.message_handler(content_types=['photo'], state=MailingStates.mailing_photo)
async def process_mailing_photo(message: types.Message, state: FSMContext):
    file_info = await bot.get_file(message.photo[-1].file_id)
    file_url = f'https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}'
    file_name = f"temp_{message.photo[-1].file_id}.jpg"
    await download_file(file_url, file_name)
    await state.update_data(mailing_photo=file_name)
    data = await state.get_data()
    mailing_text = data['mailing_text']
    await message.answer(
        "Все верно?\n\n" + mailing_text,
        reply_markup=InlineKeyboardMarkup().row(
            InlineKeyboardButton("✅ Отправить", callback_data="confirm_send"),
            InlineKeyboardButton("🕝 Ежедневная рассылка", callback_data="daily_mailing")
        ).add(InlineKeyboardButton("❌ Отменить", callback_data="cancel")),
        parse_mode='HTML'
    )

@dp.callback_query_handler(lambda c: c.data == 'confirm_send', state=MailingStates.mailing_photo)
async def confirm_and_send_mailing(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mailing_text = data['mailing_text']
    mailing_photo = data.get('mailing_photo')

    tokens = database.get_tokens()
    for token in tokens:
        bot_token = token[0]
        users = database.get_users_by_token(bot_token)
        bot_child = Bot(token=bot_token)

        for user in users:
            user_id = user[0]
            try:
                if mailing_photo:
                    absolute_photo_path = os.path.abspath(mailing_photo)
                    with open(absolute_photo_path, 'rb') as photo_file:
                        await bot_child.send_photo(user_id, photo=photo_file, caption=mailing_text, parse_mode='HTML')
                else:
                    await bot_child.send_message(user_id, text=mailing_text, parse_mode='HTML')
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

        await bot_child.close()

    if mailing_photo:
        os.remove(mailing_photo)  

    await bot.answer_callback_query(callback_query.id, "Рассылка выполнена.")
    await state.finish()
   
@dp.callback_query_handler(lambda c: c.data == 'daily_mailing', state=MailingStates.mailing_photo)
async def request_daily_mailing_time(callback_query: CallbackQuery, state: FSMContext):
    await bot.send_message(
        callback_query.from_user.id,
        "Введите время для ежедневной рассылки в формате ЧЧ:ММ (например, 17:00):"
    )
    await MailingStates.daily_mailing_time.set()

@dp.message_handler(state=MailingStates.daily_mailing_time, content_types=types.ContentTypes.TEXT)
async def set_daily_mailing_time(message: Message, state: FSMContext):
    time = message.text

    
    if not re.match(r"^(2[0-3]|[01]?[0-9]):([0-5]?[0-9])$", time):
        await message.reply("Пожалуйста, введите время в правильном формате (например, 17:00).")
        return

    data = await state.get_data()
    mailing_text = data['mailing_text']
    mailing_photo = data.get('mailing_photo', None)
    mailing_photo_path = os.path.abspath(mailing_photo) if mailing_photo else None

    
    database.add_daily_mailing(time, mailing_text, mailing_photo_path)

    await bot.send_message(
        message.chat.id,
        f"Ежедневная рассылка задана на {time}."
    )
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'cancel_mail', state=MailingStates.mailing_text)
async def cancel_mailing(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await bot.answer_callback_query(callback_query.id, "Рассылка отменена.")
    await bot.send_message(callback_query.from_user.id, "Рассылка отменена.")

@dp.callback_query_handler(lambda c: c.data == 'daily_mailing_check')
async def check_daily_mailings(callback_query: types.CallbackQuery):
    mailings = database.get_daily_mailings()
    if not mailings:
        await bot.send_message(callback_query.from_user.id, "Ежедневные рассылки отсутствуют.")
        return

    markup = InlineKeyboardMarkup()
    for mailing in mailings:
        button_text = f"{mailing[1]} - {mailing[2][:10]}..."  
        callback_data = f"view_{mailing[0]}"  
        markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))

    await bot.send_message(callback_query.from_user.id, "Вот текущие ежедневные рассылки:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('view_'))
async def view_daily_mailing(callback_query: types.CallbackQuery):
    mailing_id = int(callback_query.data.split('_')[1])
    mailing = database.get_daily_mailing_by_id(mailing_id)
    
    if not mailing:
        await bot.answer_callback_query(callback_query.id, "Рассылка не найдена.")
        return

    text = f"Текст: {mailing[2]}\nВремя: {mailing[1]}"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🗑 Удалить", callback_data=f"deletemail_{mailing[0]}"))

    if mailing[3]:
        with open(os.path.abspath(mailing[3]), 'rb') as photo_file:
            await bot.send_photo(callback_query.from_user.id, photo=photo_file, caption=text, reply_markup=markup)
    else:
        await bot.send_message(callback_query.from_user.id, text, reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data.startswith('deletemail_'))
async def delete_daily_mailing_handler(callback_query: types.CallbackQuery):
    mailing_id = int(callback_query.data.split('_')[1])
    mailing = database.get_daily_mailing_by_id(mailing_id)

    if mailing and mailing[3]:
        try:
            os.remove(os.path.abspath(mailing[3]))  
        except Exception as e:
            logging.error(f"Ошибка при удалении файла: {e}")

    database.delete_daily_mailing(mailing_id)

    
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)

    
    mailings = database.get_daily_mailings()
    if not mailings:
        await bot.send_message(callback_query.from_user.id, "Ежедневные рассылки отсутствуют.")
        return

    markup = InlineKeyboardMarkup()
    for mailing in mailings:
        button_text = f"{mailing[1]} - {mailing[2][:10]}..."  
        callback_data = f"view_{mailing[0]}"  
        markup.add(InlineKeyboardButton(button_text, callback_data=callback_data))

    await bot.send_message(callback_query.from_user.id, "Вот текущие ежедневные рассылки:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data == 'edit_help')
async def edit_help(callback_query: types.CallbackQuery):
    current_text = database.get_help_text()
    await bot.send_message(
        callback_query.from_user.id,
        f"Введите новый текст для помощи:\n\nТекущий:\n{current_text}",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    )
    await SettingsStates.help_text.set()

@dp.message_handler(state=SettingsStates.help_text)
async def process_new_help_text(message: types.Message, state: FSMContext):
    new_text = message.text
    database.set_help_text(new_text)
    await message.answer("Текст помощи обновлен.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'edit_cooperation')
async def edit_cooperation(callback_query: types.CallbackQuery):
    current_text = database.get_cooperation_text()
    await bot.send_message(
        callback_query.from_user.id,
        f"Введите новый текст для Сотруднчество:\n\nТекущий:\n{current_text}",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    )
    await SettingsStates.cooperation_text.set()

@dp.message_handler(state=SettingsStates.cooperation_text)
async def process_new_cooperation_text(message: types.Message, state: FSMContext):
    new_text = message.text
    database.set_cooperation_text(new_text)
    await message.answer("Текст Сотруднчество обновлен.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'edit_rules')
async def edit_rules(callback_query: types.CallbackQuery):
    current_text = database.get_rules_text()
    await bot.send_message(
        callback_query.from_user.id,
        f"Введите новый текст для помощи:\n\nТекущий:\n{current_text}",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    )
    await SettingsStates.rules_text.set()

@dp.message_handler(state=SettingsStates.rules_text)
async def process_new_rules_text(message: types.Message, state: FSMContext):
    new_text = message.text
    database.set_rules_text(new_text)
    await message.answer("Текст помощи обновлен.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'payment')
async def payment_options(callback_query: types.CallbackQuery):
    inline_kb = InlineKeyboardMarkup()
    inline_kb.add(
        InlineKeyboardButton("Карта", callback_data="edit_card"),
        InlineKeyboardButton("BTC", callback_data="edit_btc")
    )
    await callback_query.message.edit_text(
        "Что вы хотите изменить:",
        reply_markup=inline_kb
    )

@dp.callback_query_handler(lambda c: c.data == 'edit_card')
async def edit_card(callback_query: types.CallbackQuery):
    
    current_text = database.get_payment_details('card')
    await callback_query.message.edit_text(
        f"Введите новую карту для оплаты:\n\nТекущий:\n{current_text}",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    )
    await SettingsStates.edit_card.set()


@dp.message_handler(state=SettingsStates.edit_card)
async def process_new_card_details(message: types.Message, state: FSMContext):
    new_text = message.text
    database.set_payment_details('card', new_text)  
    await message.answer("Реквизиты карты обновлены.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'edit_btc')
async def edit_btc(callback_query: types.CallbackQuery):
    current_text = database.get_payment_details('btc')
    await callback_query.message.edit_text(
        f"Введите новый BTC адрес для оплаты:\n\nТекущий:\n{current_text}",
        reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    )
    await SettingsStates.edit_btc.set()

@dp.message_handler(state=SettingsStates.edit_btc)
async def process_new_btc_details(message: types.Message, state: FSMContext):
    new_text = message.text
    database.set_payment_details('btc', new_text)
    await message.answer("BTC адрес для оплаты обновлен.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'cancel', state="*")
async def cancel_editing(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await bot.answer_callback_query(callback_query.id, "Редактирование отменено.")
    await bot.send_message(callback_query.from_user.id, "Редактирование отменено.", reply_markup=main_keyboard)

async def download_file(file_url, file_name):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            if resp.status == 200:
                with open(file_name, 'wb') as f:
                    f.write(await resp.read())

async def upload_text(get_text) -> str:
    async with ClientSession() as session:
        
        try:
            response = await session.post(
                "http://pastie.org/pastes/create",
                data={"language": "plaintext", "content": get_text}
            )
            get_link = response.url
            if "create" in str(get_link):
                raise Exception("Не удалось загрузить на первый хостинг")
        except Exception as e:
            
            response = await session.post(
                "https://www.friendpaste.com",
                json={"language": "text", "title": "", "snippet": get_text}
            )
            get_link = json.loads(await response.read())['url']

    return get_link

async def on_startup(_):
    start_main()
    asyncio.create_task(daily_mailing_task())
    asyncio.create_task(periodic_crypto_update())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
