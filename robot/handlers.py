import os
import sys
from aiogram import Bot, Dispatcher, types
import database
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BotCommand
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.callback_data import CallbackData
import aiohttp
import random
import logging
import base64
import json
from start import restart_main
import re
from aiogram.utils.exceptions import TelegramAPIError
import string

logging.basicConfig(level=logging.INFO)

class CaptchaState(StatesGroup):
    input = State()

class ActivateState(StatesGroup):
    waiting_for_referral_code = State()

class CheckOrderState(StatesGroup):
    waiting_for_order_number = State()
    waiting_for_order_comment = State()

class TicketState(StatesGroup):
    waiting_for_city = State()
    waiting_for_ticket_subject = State()

class PaymentState(StatesGroup):
    choosing_method = State()

class ReviewState(StatesGroup):
    waiting_for_review_text = State()
    waiting_for_review_rating = State()

class SimPayState(StatesGroup):
    entering_amount = State()
    waiting_for_payment_confirmation = State()

class PayState(StatesGroup):
    choosing_method = State()
    entering_amount = State()

class CardPayState(StatesGroup):
    entering_amount = State()
    waiting_for_payment_confirmation = State()

class CouponPayState(StatesGroup):
    entering_coupon = State()

class PaymentSelectionState(StatesGroup):
    choosing_payment_method = State()

class CitySelectionState(StatesGroup):
    choosing_city = State()
    choosing_product = State()
    choosing_district = State()

async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Главная страница"),
        BotCommand(command="/poll", description="Голосования"),
        BotCommand(command="/ref", description="Реферальная система"),
        BotCommand(command="/balance", description="Просмотр баланса"),
        BotCommand(command="/check", description="Проверка заказа"),
        BotCommand(command="/help", description="Получить помощь"),
        BotCommand(command="/connect", description="Информация о тикетах, перезакладах и зависших платежах"),
        BotCommand(command="/reviews", description="Список отзывов"),
        BotCommand(command="/addreview", description="Добавить отзыв"),
        BotCommand(command="/history", description="История пополнений и расходов"),
        BotCommand(command="/lastorder", description="Просмотр информации о последнем заказе"),
        BotCommand(command="/pay", description="Пополнить баланс"),
        BotCommand(command="/trans", description="Список заявок на обмен"),
        BotCommand(command="/issue", description="Создать заявку на перезаклад"),
        BotCommand(command="/myissues", description="Список Ваших заявок на перезаклад"),
        BotCommand(command="/ticket", description="Создать обращение в магазин"),
        BotCommand(command="/mytickets", description="Список Ваших обращений в магазин"),
        BotCommand(command="/exticket", description="Создать обращение по зависшему платежу"),
        BotCommand(command="/myextickets", description="Список Ваших обращений по зависшим платежам"),
        BotCommand(command="/mybots", description="Список Ваших персональных ботов"),
        BotCommand(command="/addbot", description="Добавить персонального бота"),
        BotCommand(command="/editbot", description="Редактирование персонального бота"),
        BotCommand(command="/removebot", description="Удаление персонального бота"),
    ]
    await bot.set_my_commands(commands)

async def register_handlers(dp: Dispatcher, bot_token):
    @dp.message_handler(lambda message: message.text.lower() in ["@"], state="*")
    async def send_welcome(message: types.Message, state: FSMContext):
        await state.finish()
        user_id = message.from_user.id
        user_username = message.from_user.username if message.from_user.username else str(user_id)

    
        await set_default_commands(message.bot)
    
        if not database.check_user_exists(user_id, bot_token):
            if await send_random_captcha(message, state):
                await CaptchaState.input.set()
                return
    
            database.add_user(user_id, bot_token)
    
        cities = database.get_cities()
        random.shuffle(cities)
    
        city_list = "\n➖➖\n".join(
            [f"🏠 <b>{city[1]}</b>\n[ Для выбора нажмите 👉 /city{city[0]} ]" for city in cities]
        )
    
        await message.answer(
            f"Привет, <b>{user_username}</b>\n"
            "Ваш баланс: <b>💰0 руб.</b>\n"
            "Всего покупок: 0шт.\n"
            "➖➖➖\n"
            "Для просмотра полного сообщения (с контактами магазина и командами бота) отправьте 👉 <b>@@</b>\n"
            "➖➖➖\n"
            "Для управления персональными ботами нажмите 👉 /mybots\n"
            "Для добавления персонального бота нажмите 👉 /addbot\n"
            "Чтобы заработать денег нажмите 👉 /ref\n"
            "➖➖➖\n"
            "<b>Выберите город:</b>\n"
            "➖➖➖\n"
            f"{city_list}",
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    
    @dp.message_handler(lambda message: message.text.lower() in ["/start", "@@"], state="*")
    async def send_full_message(message: types.Message, state: FSMContext):
        await state.finish()
    
        user_id = message.from_user.id
        user_username = message.from_user.username if message.from_user.username else str(user_id)

        cities = database.get_cities()
        random.shuffle(cities)

        city_list = "\n➖➖\n".join(
            [f"🏠 <b>{city[1]}</b>\n[ Для выбора нажмите 👉 /city{city[0]} ]" for city in cities]
        )
    
        await message.answer(
            "<b>Вас приветствует магазин - kfp24.com \n\nНаши контакты: </b>\nСайт автопродаж - https://kfp24.com\n\nУдачных покупок!\n"
            "➖➖➖\n"
            f"Привет, <b>{user_username}</b>\n"
            "Ваш баланс: <b>💰0 руб.</b>\n"
            "Всего покупок: 0шт.\n"
            "➖➖➖\n"
            "Для пополнения баланса нажмите 👉/pay или !\n"
            "Для просмотра баланса нажмите 👉/balance или =\n"
            "Для просмотра истории операций по счету нажмите 👉 /history или *\n"
            "Для получения информации о тикетах, перезакладах и зависших платежах нажмите 👉 /connect\n"
            "➖➖➖\n"
            "Для того чтобы узнать как проверять заказы нажмите 👉/check или $\n"
            "➖➖➖\n"
            "Для того чтобы посмотреть 10 последних отзывов о нашем магазине нажмите 👉/reviews\n"
            "Для того чтобы добавить отзыв нажмите 👉/addreview или +\n"
            "➖➖➖\n"
            "Для управления персональными ботами нажмите 👉 /mybots\n"
            "Для добавления персонального бота нажмите 👉 /addbot\n"
            "Для получения информации о реферальной программе нажмите 👉 /ref\n"
            "➖➖➖\n"
            "Список подписок 👉 /sub\n"
            "Создать новую подписку 👉 /addsub\n"
            "Удалить подписку 👉 /remsub\n"
            "➖➖➖➖➖➖\n"
            "Чтобы посмотреть список заявок на покупки или пополнения через SIM или банковскую карту нажмите 👉/trans или /\n"
            "➖➖➖\n"
            "Для получения помощи нажмите 👉 /help или ?\n"
            "Для просмотра последнего заказа нажмите 👉 /lastorder или #\n"
            "➖➖➖\n"
            "<b>Выберите город:</b>\n"
            "➖➖➖\n"
            f"{city_list}",
            parse_mode='HTML',
            disable_web_page_preview=True
        )

    @dp.message_handler(state=CaptchaState.input)
    async def handle_captcha_input(message: types.Message, state: FSMContext):
        async with state.proxy() as data:
            correct_answer = data.get('captcha_answer')
    
        if message.text.lower() == correct_answer.lower():
            user_id = message.from_user.id
            database.add_user(user_id, bot_token)
            await state.finish()
    
            cities = database.get_cities()
            city_list = "\n".join(
                [f"🏠 <b>{city[1]}</b>\n[ Для выбора нажмите 👉 /city{city[0]} ]" for city in cities]
            )

            await message.answer(
                "Для просмотра полного сообщения (с контактами магазина и командами бота) отправьте 👉 <b>@@</b>\n"
                "➖➖➖\n"
                "Для управления персональными ботами нажмите 👉 /mybots\n"
                "Для добавления персонального бота нажмите 👉 /addbot\n"
                "Чтобы заработать денег нажмите 👉 /ref\n"
                "➖➖➖\n"
                "<b>Выберите город:</b>\n"
                "➖➖➖\n"
                f"{city_list}\n"
                "➖➖➖",
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        else:
            await message.answer(
                "Неправильный код проверки. Попробуйте еще раз!\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            await send_random_captcha(message, state)

    async def send_random_captcha(message: types.Message, state: FSMContext):
        captcha_dir = os.path.join(os.path.dirname(__file__), 'captcha')
        if not os.path.exists(captcha_dir):
            logging.warning(f"Captcha directory does not exist: {captcha_dir}")
            return False
    
        if not os.listdir(captcha_dir):
            logging.warning(f"Captcha directory is empty: {captcha_dir}")
            return False
    
        captcha_files = [f for f in os.listdir(captcha_dir) if f.endswith('.jpg')]
        if not captcha_files:
            logging.warning("No captcha files found in the directory.")
            return False
    
        captcha_file = random.choice(captcha_files)
        captcha_path = os.path.join(captcha_dir, captcha_file)
        logging.info(f"Selected captcha file: {captcha_file}")
    
        try:
            with open(captcha_path, 'rb') as photo:
                await message.answer_photo(photo=photo, caption="Введите код с картинки 👆")
                async with state.proxy() as data:
                    data['captcha_answer'] = captcha_file.rstrip('.jpg')
            logging.info(f"Captcha sent successfully. Answer: {captcha_file.rstrip('.jpg')}")
        except Exception as e:
            logging.error(f"Error sending captcha: {e}")
            return False
    
        return True

    @dp.message_handler(commands=['mybots'])
    async def handle_mybots(message: types.Message):
        await message.answer(
            "Приватные боты не найдены. Используйте команду /addbot чтобы добавить приватного бота.\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(commands=['addbot'])
    async def handle_addbot(message: types.Message):
        await message.answer(
            "✌ Отправьте API Token своего Telegram бота в ответном сообщении:\n"
            "➖➖➖➖\n"
            "Если у Вас нет своего API Token'а или Вы не знаете, что это такое, тогда прочитайте <b>подробную инструкцию</b> "
            '<a href="https://telegra.ph/Instrukciya-po-sozdaniyu-personalnogo-Telegram-bota-04-26-2">здесь</a>\n'
            "➖➖➖➖\n"
            "1. Воспользуйтесь официальным Telegram аккаунтом для создания ботов - @BotFather\n"
            "➖➖➖➖\n"
            "2. Отправьте ему команду /newbot.\n"
            "➖➖➖➖\n"
            "3. Далее он попросит Вас придумать имя для Вашего бота.\n"
            "➖➖➖➖\n"
            "4. Далее он попросит Вас придумать username для Вашего бота. Обратите внимание, username должен ОБЯЗАТЕЛЬНО заканчиваться словом bot\n"
            "➖➖➖➖\n"
            "5. Скопируйте свой API Token и отправьте его нашему боту в ответ на это сообщение.\n"
            "➖➖➖➖\n"
            "Вам необходимо получить свой API Token самостоятельно, только после этого, Вы сможете добавить своего персонального бота, выше описан процесс, что Вам необходимо сделать, чтобы получить API Token\n"
            "Если Вы все сделаете верно, то Вам пришлют API Token, выглядить он примерно так - 1542120167:SFQ8ELnPFEQSQChTFEQLGQSXlImiU1f3F2a (не используйте данный токен, это пример, он работать не будет - Вам необходимо получить свой)\n"
            "➖➖➖➖\n"
            "Внимание! Добавлять и управлять своими персональными ботами можно через команды /addbot, /mybots\n"
            "➖➖➖➖\n"
            "Для того, чтобы все уведомления приходили в Ваш персональный бот - ни в коем случае не меняйте ник или токен своего персонального бота, иначе сам бот и уведомления перестанут работать!\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML',
            disable_web_page_preview=False
        )
    
    @dp.message_handler(commands=['ref'])
    async def handle_ref(message: types.Message):
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
    
        await message.answer(
            "💰 Уважаемые клиенты! Делитесь своими ботами с друзьями и получайте <b>100 руб.</b> с каждого его оплаченного заказа на минимальную сумму от <b>1500 руб.</b>\n"
            "➖➖\n"
            "Для этого просто добавьте персонального бота, с помощью команды /addbot и переведите его в режим 'Отвечать всем', с помощью команды /editbot\n"
            "Либо если у Вас уже добавлен бот, то просто переведите его в режим 'Отвечать всем', но советуем лучше иметь 2 бота - один лично для Вас, который отвечает только Вам, а второй для друзей, который отвечает всем.\n"
            "➖➖\n"
            "Успехов!\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
    
        user_id_base64 = base64.b64encode(str(message.from_user.id).encode()).decode().rstrip("=").lower()
    
        await message.answer(
            "<b>Внимание!</b> Делитесь с друзьями Вашей персональной ссылкой на бота и получайте <b>100 руб.</b> с каждого его оплаченного заказа на минимальную сумму от <b>1500 руб.</b>\n"
            "➖\n"
            "<b>Ваша ссылка и код:</b>\n"
            "➖\n"
            f"<code>https://t.me/{bot_username}?start={user_id_base64}</code>\n"
            "➖\n"
            "Для ручной активации кода используйте команду /activate и код ниже:\n"
            "➖\n"
            f"<code>{user_id_base64}</code>\n"
            "➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
    
    @dp.message_handler(commands=['activate'])
    async def handle_activate(message: types.Message, state: FSMContext):
        await message.answer(
            "В ответном сообщении введите код Вашего рефовода, если кода нет, нажмите 👉/start или отправьте @ чтобы начать покупки."
        )
        await ActivateState.waiting_for_referral_code.set()
    
    @dp.message_handler(state=ActivateState.waiting_for_referral_code)
    async def handle_referral_code_input(message: types.Message, state: FSMContext):
        await message.answer(
            "Некорректный реферальный код\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )

    @dp.message_handler(commands=['mytickets', 'myissues', 'myextickets'])
    async def handle_not_found_commands(message: types.Message):
        if message.text == '/mytickets' or message.text == '/myissues':
            await message.answer("Диалоги не найдены")
        elif message.text == '/myextickets':
            await message.answer("Обращения не найдены")
    
    @dp.message_handler(commands=['ticket'])
    async def handle_ticket_command(message: types.Message, state: FSMContext):
        cities = database.get_cities()
        city_list = "\n".join(
            [f"🏠 <b>{city[1]}</b>\n[ Для выбора отправьте 👉 {city[0]} ]" for city in cities]
        )
    
        await message.answer(
            "Для создания тикета выберите нужный город:\n"
            "➖➖➖\n"
            f"{city_list}\n"
            "➖➖➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
    
        await TicketState.waiting_for_city.set()
    
    @dp.message_handler(state=TicketState.waiting_for_city)
    async def handle_city_selection(message: types.Message, state: FSMContext):
        cities = database.get_cities()
        city_ids = [str(city[0]) for city in cities]
    
        if message.text not in city_ids:
            await message.answer(
                "Выберите город строго из списка\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            return
    
        await state.update_data(selected_city=message.text)
        await message.answer(
            "Введите тему тикета\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
        await state.finish()
    
    @dp.message_handler(commands=['connect'])
    async def handle_connect(message: types.Message):
        await message.answer(
            "Чтобы посмотреть список тикетов нажмите 👉 /mytickets\n"
            "Чтобы создать тикет нажмите 👉 /ticket\n"
            "➖➖➖\n"
            "Чтобы посмотреть список заявок на перезаклад нажмите 👉 /myissues\n"
            "Чтобы создать заявку на перезаклад нажмите 👉 /issue\n"
            "➖➖➖\n"
            "Чтобы посмотреть список обращений по зависшим платежам нажмите 👉 /myextickets\n"
            "Чтобы создать обращение по зависшему платежу нажмите 👉 /exticket\n"
            "➖➖➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(commands=['issue'])
    async def handle_issue(message: types.Message):
        await message.answer(
            "Вы еще не делали заказов чтобы создавать заяки на перезаклад\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(commands=['exticket'])
    async def handle_exticket(message: types.Message):
        await message.answer(
            "Вы еще не делали пополнений чтобы создавать обращения\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(lambda message: message.text.lower() in ["/balance", "="], state="*")
    async def handle_balance(message: types.Message, state: FSMContext):
        await state.finish()
        await message.answer(
            "Ваш баланс:\n"
            "💰0 руб.\n"
            "➖\n"
            "Для пополнения баланса нажмите 👉/pay или !\n"
            "Для просмотра баланса нажмите 👉/balance или =\n"
            "Для просмотра истории операций по счету нажмите 👉/history или *\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(lambda message: message.text.lower() in ["/history", "*"], state="*")
    async def handle_history(message: types.Message, state: FSMContext):
        await state.finish()
        await message.answer(
            "История пополнений и расходов:\n"
            "➖➖➖➖\n"
            "Операции не найдены\n"
            "➖➖➖➖\n"
            "Для пополнения баланса нажмите 👉/pay или !\n"
            "Для просмотра баланса нажмите 👉/balance или =\n"
            "Для просмотра истории операций по счету нажмите 👉/history или *\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(lambda message: message.text.lower() in ["/check", "$"], state="*")
    async def handle_check(message: types.Message):
        await message.answer(
            "➖➖➖➖\n"
            "Если Вы произвели оплату и закрыли страницу:\n"
            "➖➖➖➖\n"
            "👉 Просто отправьте \n"
            "<b>/checkXXXX_XXXXXXXXX</b> (номер заказа_комментарий), например \n"
            "<b>/check1234_5678910</b>, чтобы проверить статус заказа и получить адрес. Номер заказа и комментарий Вы получаете на странице оплаты заказа, где выдаются реквизиты, обязательно сохраните эти данные перед оплатой.\n"
            "➖➖➖➖\n"
            "Список подписок 👉 /sub\n"
            "Создать новую подписку 👉 /addsub\n"
            "Удалить подписку 👉 /remsub\n"
            "➖➖➖➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
        await message.answer("Введите номер заказа который нужно проверить")
        await CheckOrderState.waiting_for_order_number.set()
    
    @dp.message_handler(lambda message: re.match(r'/check\d+_\d+', message.text), state='*')
    async def handle_check_order_with_comment(message: types.Message, state: FSMContext):
        await message.answer(
            "Платеж не найден в системе. Свяжитесь с технической поддержкой!\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
        await state.finish()
    
    @dp.message_handler(lambda message: message.text.lower().startswith('/check'), state='*')
    async def handle_check_command(message: types.Message, state: FSMContext):
        await state.finish()  # Завершение любого предыдущего состояния
        await message.answer("Введите комментарий к заказу который нужно проверить")
        await CheckOrderState.waiting_for_order_comment.set()
    
    @dp.message_handler(state=CheckOrderState.waiting_for_order_number)
    async def handle_order_number(message: types.Message, state: FSMContext):
        await state.update_data(order_number=message.text)
        await message.answer("Введите комментарий к заказу который нужно проверить")
        await CheckOrderState.waiting_for_order_comment.set()
    
    @dp.message_handler(state=CheckOrderState.waiting_for_order_comment)
    async def handle_order_comment(message: types.Message, state: FSMContext):
        await message.answer(
            "Платеж не найден в системе. Свяжитесь с технической поддержкой!\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
        await state.finish()
    
    @dp.message_handler(commands=['reviews'])
    async def handle_reviews(message: types.Message):
        review_text = (
            "🏃 Автор: <b>A*********1</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>🧊 MEPHEDRONE CRYSTAL ICE 2.01гр 🧊</b>\n"
            "📆 Дата: <b>30-08-2024 19:15:36</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Все чики пики\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>3*******9</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>Шишки \"White Widow\" 1гр</b>\n"
            "📆 Дата: <b>30-08-2024 19:51:21</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Бабка в кресле.\n"
            "Снова сыровата\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>v*****6</b>\n"
            "📆 Дата: <b>30-08-2024 22:27:48</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "131826 отлично в касание и качество огонь только далеко писец\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>a*********1</b>\n"
            "📆 Дата: <b>31-08-2024 05:08:19</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "10/10\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>5********4</b>\n"
            "🏢 Город: <b>Казань</b>\n"
            "🍕 Товар: <b>🗡 МЕФЕДРОН ХРУСТАЛЬНЫЕ ИГОЛКИ 3.01гр 🗡</b>\n"
            "📆 Дата: <b>31-08-2024 06:36:26</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "В касание 👌\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>g********6</b>\n"
            "🏢 Город: <b>Казань</b>\n"
            "🍕 Товар: <b>🗡 МЕФЕДРОН ХРУСТАЛЬНЫЕ ИГОЛКИ 3.01гр 🗡</b>\n"
            "📆 Дата: <b>31-08-2024 07:43:23</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Забрал все отлично\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>s*****8</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>🧊 MEPHEDRONE CRYSTAL ICE 2.01гр 🧊</b>\n"
            "📆 Дата: <b>31-08-2024 08:30:11</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Впервые у вас , пришел , поднял , пошли пробывать .\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>D*********a</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>🧊 MEPHEDRONE CRYSTAL ICE 2.01гр 🧊</b>\n"
            "📆 Дата: <b>31-08-2024 08:50:48</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Всё ровно!!!\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>s*****8</b>\n"
            "📆 Дата: <b>31-08-2024 11:41:25</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Впервые брал в данном шопе ,остался довольный , зайду еще 😎\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>Z***2</b>\n"
            "🏢 Город: <b>Казань</b>\n"
            "🍕 Товар: <b>🧊 MEPHEDRONE CRYSTAL ICE 3.01гр 🧊</b>\n"
            "📆 Дата: <b>31-08-2024 13:36:45</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "И здесь все мгновенно, быстро. Все отлично\n\n"
            "➖➖➖➖\n"
            "Чтобы добавить отзыв нажмите 👉 <b>/addreview</b>\n"
            "➖➖➖➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
        
        review_text_additional = (
            "🏃 Автор: <b>Z******g</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>🗡 МЕФЕДРОН ХРУСТАЛЬНЫЕ ИГОЛКИ 1.01гр 🗡</b>\n"
            "📆 Дата: <b>31-08-2024 14:22:42</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "В касание,стаф берет.\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>Z******g</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>🗡 МЕФЕДРОН ХРУСТАЛЬНЫЕ ИГОЛКИ 1.01гр 🗡</b>\n"
            "📆 Дата: <b>31-08-2024 14:25:37</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Сходу поднял,ст. Пушка\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>T**********8</b>\n"
            "📆 Дата: <b>31-08-2024 15:00:39</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Все отлично👍👏😆\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>6********9</b>\n"
            "🏢 Город: <b>Казань</b>\n"
            "🍕 Товар: <b>🗡 МЕФЕДРОН ХРУСТАЛЬНЫЕ ИГОЛКИ 2.01гр 🗡</b>\n"
            "📆 Дата: <b>31-08-2024 15:25:43</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Дома в касание\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>d******o</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>🗡 МЕФЕДРОН ХРУСТАЛЬНЫЕ ИГОЛКИ 1.01гр 🗡</b>\n"
            "📆 Дата: <b>31-08-2024 15:38:42</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "все нормально можно брать, качает\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>T******8</b>\n"
            "🏢 Город: <b>Казань</b>\n"
            "🍕 Товар: <b>🗡 МЕФЕДРОН ХРУСТАЛЬНЫЕ ИГОЛКИ 2.01гр 🗡</b>\n"
            "📆 Дата: <b>31-08-2024 18:22:40</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Вопрос решили все хорошо спасибо команде ☺️\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>d********1</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>Шишки \"White Widow\" 2гр</b>\n"
            "📆 Дата: <b>31-08-2024 18:30:41</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Пришлось попотеть чтобы поднять, корды на фото неверные, нашли место чудом в 20-30 метрах от кордов в подлеске кустистом спустя час, неплохо бы дать купон на шишки как ...\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>c*******r</b>\n"
            "🏢 Город: <b>Йошкар-Ола</b>\n"
            "🍕 Товар: <b>Шишки \"White Widow\" 2гр</b>\n"
            "📆 Дата: <b>31-08-2024 19:18:46</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Все отлично, качество пушка, сначала подумал про другой район, но не так уж и далеко оказался, ваши все 10ки. Подогреваете купонами?\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>M******7</b>\n"
            "📆 Дата: <b>31-08-2024 21:42:47</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Все дома душа)\n\n"
            "➖➖➖➖\n\n"
            "🏃 Автор: <b>a********2</b>\n"
            "🏢 Город: <b>Казань</b>\n"
            "🍕 Товар: <b>🗡 МЕФЕДРОН ХРУСТАЛЬНЫЕ ИГОЛКИ 3.01гр 🗡</b>\n"
            "📆 Дата: <b>31-08-2024 22:37:16</b>\n"
            "📊 Оценка: ⭐⭐⭐⭐⭐\n\n"
            "Магаз бомба стаф бомба все дома\n\n"
            "➖➖➖➖\n"
            "Чтобы добавить отзыв нажмите 👉 <b>/addreview</b>\n"
            "➖➖➖➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
        await message.answer(review_text, parse_mode='HTML')
        await message.answer(review_text_additional, parse_mode='HTML')
    
    @dp.message_handler(lambda message: message.text.lower() in ["/addreview", "+"], state="*")
    async def handle_addreview(message: types.Message):
        await message.answer(
            "📊 Отправьте текст Вашего отзыва\n"
            "➖➖\n"
            "❗️ минимальная длина отзыва - 5 букв\n"
            "❗️ максимальная длина отзыва - 255 букв\n"
            "➖➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
        await ReviewState.waiting_for_review_text.set()
    
    @dp.message_handler(state=ReviewState.waiting_for_review_text)
    async def handle_review_text(message: types.Message, state: FSMContext):
        review_text = message.text.strip()
    
        if len(review_text) < 5:
            await message.answer(
                "Минимальная длина отзыва 5 символов!\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
        elif len(review_text) > 255:
            await message.answer(
                "Максимальная длина отзыва 255 символов!\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
        else:
            await state.update_data(review_text=review_text)
            await message.answer(
                "Отправьте оценку Вашего отзыва от 1 до 5\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            await ReviewState.waiting_for_review_rating.set()
    
    @dp.message_handler(state=ReviewState.waiting_for_review_rating)
    async def handle_review_rating(message: types.Message, state: FSMContext):
        rating = message.text.strip()
    
        if rating.isdigit() and 1 <= int(rating) <= 5:
            await message.answer(
                "😍 Спасибо за отзыв!\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            await state.finish()
        else:
            await message.answer(
                "Не указана оценка отзыва!\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
    
    @dp.message_handler(commands=['sub'])
    async def handle_sub(message: types.Message):
        await message.answer(
            "Нет активных подписок. Чтобы добавить новую подписку используйте команду /addsub\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    
    @dp.message_handler(commands=['addsub'])
    async def handle_addsub(message: types.Message):
        await message.answer(
            "❗️ Выберите тип желаемой подписки:\n"
            "➖\n"
            "1. Подписка на город\n"
            "➖\n"
            "2. Подписка на район\n"
            "➖\n"
            "3. Подписка на товар\n"
            "➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    
    @dp.message_handler(commands=['remsub'])
    async def handle_remsub(message: types.Message):
        await message.answer(
            "Нет активных подписок. Чтобы добавить новую подписку используйте команду /addsub\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    
    @dp.message_handler(lambda message: message.text.lower() in ["/trans", "/"])
    async def handle_trans(message: types.Message):
        await message.answer(
            "Заявки не найдены\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    
    @dp.message_handler(lambda message: message.text.lower() in ["/help", "?"])
    async def handle_help(message: types.Message):
        await message.answer(
            "Добро пожаловать в наш магазин.\n"
            "Уважаемый клиент, будьте внимательны при оплате и выборе товара.\n"
            "Перед покупкой товара, бот предложит Вам город, товар и удобный для Вас район, после чего, выдаст реквизиты для оплаты.\n"
            "Внимательно перед покупкой проверяйте товар и выбранный район. Обязательно записывайте реквизиты для оплаты (номер кошелька и комментарий).\n\n"
            "При оплате, Вам необходимо обязательно указатькомментарий, который выдал Вам бот, иначе оплата не будет засчитана в автоматическом режиме и Вы не получите адрес.\n"
            "Всегда записывайте номер заказа и комментарий, с помощью них, вы сможете узнать статус заказа (получить адрес) в любой момент и с любого устройства. Сохраняйте чек до тех пор, пока не получили адрес. Присутствует возможность производить несколько платежей с одним комментарием. Платежи суммируются и в случае, если сумма полная - Вы получаете свой адрес.\n"
            "Будьте внимательны, кошелек, комментарий и сумма должны быть точными. Если возникли какие-либо проблемы - обращайтесь к оператору.\n\n"
            "После внесения оплаты, нажмите кнопку проверки платежа и если Ваша оплата будет найдена - Вы получите адрес в автоматическом режиме.\n"
            "Так же для Вашего удобства реализована возможность просмотра Вашего последнего заказа, для этого необходимо нажать /lastorder\n"
            "А для того, чтобы вернуться на стартовую страницу к выбору городов, просто нажмите /start или напишите любое сообщение.\n\n"
            "Нужные команды:\n"
            "/connect - выводит все доступные команды для связи с Администрацией\n"
            "/ticket - создать тикет с Администрацией\n"
            "/mytickets - последние 10 тикетов\n"
            "/myissues - последние 10 заявок по ненаходам\n"
            "/myextickets - последние 10 зависших платежей на обменник\n"
            "Приятных покупок!\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    
    @dp.message_handler(lambda message: message.text.lower() in ["/lastorder", "#"])
    async def handle_lastorder(message: types.Message):
        await message.answer(
            "Всего покупок: 0шт.\n"
            "➖➖➖➖\n"
            "У вас нет заказов.\n\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(commands=['poll'])
    async def handle_poll(message: types.Message):
        await message.answer(
            "Нет активных голосований.\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )

    async def handle_pay_command(message: types.Message, state: FSMContext):
        await PayState.choosing_method.set()
        await message.answer(
            "Выберите метод пополения баланса:\n"
            "➖➖➖➖\n"
            "<b>Bitcoin</b>\n"
            "[Для выбора нажмите 👉 /pay1]\n"
            "➖➖➖➖\n"
            "<b>Litecoin</b>\n"
            "[Для выбора нажмите 👉 /pay7]\n"
            "➖➖➖➖\n"
            "<b>Банковская карта</b>\n"
            "[Для выбора нажмите 👉 /pay11]\n"
            "➖➖➖➖\n"
            "<b>SIM</b>\n"
            "[Для выбора нажмите 👉 /pay10]\n"
            "➖➖➖➖\n"
            "<b>Оплата купоном</b>\n"
            "[Для выбора нажмите 👉 /pay12]\n"
            "➖➖➖➖\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
    
    @dp.message_handler(lambda message: message.text.lower() in ["/pay", "!"], state="*")
    async def handle_pay_start(message: types.Message, state: FSMContext):
        await handle_pay_command(message, state)
        await PaymentState.choosing_method.set()
    
    @dp.message_handler(lambda message: message.text.lower() in ["/pay11"], state=PaymentState.choosing_method)
    async def handle_pay_card(message: types.Message, state: FSMContext):
        await state.update_data(payment_method="card")
        await message.answer(
            "❗<b>Внимание! Перед пополнением, обязательно ознакомьтесь с правилами. Нажимая кнопку 'Пополнить' - Вы автоматически соглашаетесь с данными правилами.</b>\n\n"
            "Введите сумму в рублях, на которую Вы хотите пополнить баланс, ознакомьтесь с правилами и только после этого нажмите кнопку ❗<b>'Пополнить'. В следующем окне система выдаст точную сумму к оплате (с учетом комиссии) и реквизиты. Реквизиты актуальны 30 минут, после чего заявка на пополнение будет удалена и деньги не будут возвращены. Оплата должна быть одним переводом. Если будет несколько переводов - оплата не зачтется и деньги не вернутся.</b>\n\n"
            "Пополнение баланса происходит только после поступления ❗<b>ТОЧНОЙ СУММЫ</b> денег на баланс банковской карты! Обычно это занимает 2-3 минуты.\n\n"
            "❗<b>Нажимайте 'Я оплатил', только после реальной оплаты.</b> Если после нажатия 'Я оплатил' система не увидит Вашу оплату в течении 30 минут, ваш заказ будет отменен и Вы не получите деньги на баланс.\n\n"
            "Пополнить банковскую карту можно любым удобным способом, например: со своего QIWI-кошелька, терминала, банковской карты (card2card), Yandex.Деньги, Payeer, WebMoney и другие платежные системы.\n\n"
            "При пополнении - переводите обязательно ❗<b>ТОЧНУЮ сумму</b>, которую Вам выдал сайт вместе с реквизитами! Многие терминалы берут комиссию и с них сложно оплатить точную сумму, старайтесь этого избегать. Важно!\n\n"
            "❗<b>Кнопка 'Я оплатил' нажимается в самый последний момент, когда Вы произвели оплату и уверены в точной сумме.</b>\n\n"
            "При точном выполнении всех правил - Ваш баланс будет мгновенно пополнен! Вопросы по зависшим платежам принимаются в течении суток с момента оплаты. Если Ваш баланс не был пополнен и Вы реально перевели деньги на выданные Вам реквизиты - свяжитесь со службой поддержки обменника на вкладке 'Завис платеж?' или 'Заявки на покупки и пополнения', либо в боте команда /exticket и обязательно укажите номер заявки и детали вашего платежа вместе с точной суммой оплаты. Скриншоты чеков обязательны! По истечении суток запросы по зависшим платежам не принимаются! Заявки на пополнение баланса обрабатываются через сторонний обменник, если Вы создали обращение по зависшему платежу и Вашу проблему не решили - обратитесь к Администрации магазина во вкладке 'Тикеты', либо в боте команда /ticket\n\n"
            "По истечении суток запросы по зависшим платежам не принимаются!\n\n"
            "Заявки обрабатываются через сторонний обменник, если Вы создали обращение по зависшему платежу и Вашу проблему не решили - обратитесь к Администрации магазина\n\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
        await message.answer(
            "Минимальная сумма для пополнения:\n"
            "❗ <b>500 рублей.</b>\n"
            "Максимальная сумма для пополнения:\n"
            "❗ <b>150 000 рублей.</b>\n"
            "➖➖\n"
            "Введите сумму, на которую хотите пополнить баланс\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
        await CardPayState.entering_amount.set()
    
    @dp.message_handler(lambda message: message.text.lower() in ["/pay10"], state=PaymentState.choosing_method)
    async def handle_pay_sim(message: types.Message, state: FSMContext):
        await state.update_data(payment_method="sim")
        await message.answer(
            "❗<b>Внимание! Перед пополнением, обязательно ознакомьтесь с правилами. Нажимая кнопку 'Пополнить' - Вы автоматически соглашаетесь с данными правилами.</b>\n\n"
            "Введите сумму в рублях, на которую Вы хотите пополнить баланс, ознакомьтесь с правилами и только после этого нажмите кнопку ❗<b>'Пополнить'. В следующем окне система выдаст точную сумму к оплате (с учетом комиссии) и реквизиты. Реквизиты актуальны 30 минут, после чего заявка на пополнение будет удалена и деньги не будут возвращены. Оплата должна быть одним переводом. Если будет несколько переводов - оплата не зачтется и деньги не вернутся.</b>\n\n"
            "Пополнение баланса происходит только после поступления ❗<b>ТОЧНОЙ СУММЫ</b> денег на баланс мобильного телефона! Обычно это занимает 30-60 секунд.\n\n"
            "❗<b>Нажимайте 'Я оплатил', только после реальной оплаты.</b> Если после нажатия 'Я оплатил' система не увидит Вашу оплату в течении 3х минут, ваш заказ будет отменен и Вы не получите деньги на баланс.\n\n"
            "Оплата принимается только на ❗<b>НОМЕР МОБИЛЬНОГО ТЕЛЕФОНА</b>. Пополнять выданный номер можно любым способом, например через терминал, офис мобильного оператора, банковской картой, QIWI и так далее.\n\n"
            "❗<b>Не переводите деньги на QIWI или любую другую платежную систему вы их теряете БЕЗ ВОЗМОЖНОСТИ ВОЗВРАТА!</b>\n\n"
            "При пополнении - переводите обязательно ❗<b>ТОЧНУЮ сумму</b>, которую Вам выдал сайт вместе с реквизитами! Многие терминалы берут комиссию и с них сложно оплатить точную сумму, старайтесь этого избегать. ❗<b>Важно! Если по какой-либо причине Вы отправили не точную сумму - воспользуйтесь кнопкой 'Изменить сумму' и введите правильную сумму (которую Вы отправили или которую зачислил терминал). Только после того, как Вы уверены в сумме - нажмите кнопку 'Я оплатил'.</b>\n\n"
            "Внимание! Если Вы не можете получить реквизиты, то сделайте отмену и создайте заявку с другой уникальной суммой! Например если вы создали заявку на 1500 рублей и не можете получить реквизиты, то сделайте отмену и создайте заявку на 1531 или 1532 рубля.\n\n"
            "❗<b>Кнопка 'Я оплатил' нажимается в самый последний момент, когда Вы произвели оплату и уверены в точной сумме. При точном выполнении всех правил - Ваш баланс будет мгновенно пополнен!</b>\n\n"
            "Вопросы по зависшим платежам принимаются в течении суток с момента оплаты. Если Ваш баланс не был пополнен и Вы реально перевели деньги на выданные Вам реквизиты - свяжитесь со службой поддержки обменника на вкладке 'Завис платеж?' или 'Заявки на покупки и пополнения', либо в боте команда /exticket и обязательно укажите номер заявки и детали вашего платежа вместе с точной суммой оплаты. Скриншоты чеков обязательны! По истечении суток запросы по зависшим платежам не принимаются! Заявки на пополнение баланса обрабатываются через сторонний обменник, если Вы создали обращение по зависшему платежу и Вашу проблему не решили - обратитесь к Администрации магазина во вкладке 'Тикеты', либо в боте команда /ticket\n\n"
            "Заявки обрабатываются через сторонний обменник, если Вы создали обращение по зависшему платежу и Вашу проблему не решили - обратитесь к Администрации магазина\n\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
        await message.answer(
            "Минимальная сумма для пополнения:\n"
            "❗ <b>500 рублей.</b>\n"
            "Максимальная сумма для пополнения:\n"
            "❗ <b>100 000 рублей.</b>\n"
            "➖➖\n"
            "Введите сумму, на которую хотите пополнить баланс\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )
        await SimPayState.entering_amount.set()
    
    @dp.message_handler(lambda message: message.text.startswith("/pay"), state=PaymentState.choosing_method)
    async def handle_pay_method_choice(message: types.Message, state: FSMContext):
        method = message.text.strip().lower()
        
        if method == "/pay1":
            await state.update_data(payment_method="btc")
            price_btc = database.get_crypto_price("btc")
            formatted_price_btc = f"{int(price_btc):,}".replace(",", " ")
            await message.answer(
                f"Курс 1 BTC = {formatted_price_btc} рублей.\n"
                "➖➖\n"
                "На какую сумму в рублях Вы хотите пополнить баланс?\n"
                "➖➖\n"
                "В ответном сообщении, отправьте просто цифру, например 1000\n"
                "Напоминаем, что минимальная сумма пополнения через Bitcoin - 500 рублей.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            await PayState.entering_amount.set()
    
        elif method == "/pay7":
            await state.update_data(payment_method="ltc")
            price_ltc = database.get_crypto_price("ltc")
            formatted_price_ltc = f"{int(price_ltc):,}".replace(",", " ")
            await message.answer(
                f"Курс 1 LTC = {formatted_price_ltc} рублей.\n"
                "➖➖\n"
                "На какую сумму в рублях Вы хотите пополнить баланс?\n"
                "➖➖\n"
                "В ответном сообщении, отправьте просто цифру, например 1000\n"
                "Напоминаем, что минимальная сумма пополнения через Litecoin - 500 рублей.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            await PayState.entering_amount.set()
    
        elif method == "/pay12":
            await message.answer(
                "Для пополнения баланса с помощью купона, необходимо отправить код купона, после чего Ваш баланс моментально будет пополнен на сумму купона, который Вы активировали.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
                parse_mode='HTML'
            )
            await CouponPayState.entering_coupon.set()
    
        else:
            await message.answer(
                "Выберите метод пополнения строго из списка\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )

    @dp.message_handler(state=CouponPayState.entering_coupon)
    async def handle_coupon_input(message: types.Message, state: FSMContext):
        await message.answer(
            "Ошибка. Купон не найден\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
            parse_mode='HTML'
        )

    @dp.message_handler(lambda message: message.text.isdigit(), state=PayState.entering_amount)
    async def handle_pay_amount(message: types.Message, state: FSMContext):
        amount = int(message.text.strip())
        data = await state.get_data()
        payment_method = data.get("payment_method")
        
        if amount < 500:
            method_name = "Bitcoin" if payment_method == "btc" else "Litecoin"
            await message.answer(
                f"Ошибка. Укажите правильную сумму пополнения. Минимальная сумма пополнения через {method_name} - 500 рублей.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
        else:
            if payment_method == "btc":
                price_btc = database.get_crypto_price("btc")
                coefficient = database.get_payment_coefficient_biz("btc")
    
                if coefficient is None:
                    coefficient = 1
    
                adjusted_amount = amount * coefficient
                btc_address = database.get_payment_address("btc")
                btc_amount = adjusted_amount / price_btc
                btc_amount_formatted = f"{btc_amount:.8f}".rstrip("0")
    
                await message.answer(
                    f"Для пополнения баланса оплатите:\n"
                    "➖➖➖\n"
                    f"💰 <code>{btc_amount_formatted}</code> BTC\n"
                    "➖➖➖\n"
                    "На Bitcoin кошелёк:\n"
                    "➖➖➖\n"
                    f"👉 <code>{btc_address}</code>\n"
                    "➖➖➖\n"
                    "Переведите Bitcoin на указанный кошелек и просто ожидайте 1 подтверждения в сети Bitcoin - система автоматически зачислит Вам баланс и отправит сообщение об успешном пополнении баланса.\n"
                    "➖➖➖\n"
                    "Это Ваш постоянный Bitcoin кошелек для пополнения баланса Вашего личного кабинета. Чтобы пополнить баланс в магазине, просто отправьте на данный кошелек средства, после 1 подтверждения - система зачислит Вам баланс в автоматическом режиме. Вы можете отправлять любое количество Bitcoin на Ваш кошелек - система автоматически рассчитает Вам баланс в рублях, по курсу Bitcoin на момент Вашего перевода. Старайтесь пополнять всегда немного большую сумму (например на 20-30 рублей больше), так как курс Bitcoin может измениться в момент Вашего перевода и Вам может не хватить денег для покупки товара.\n"
                    "➖➖➖\n"
                    f'<a href="https://chart.googleapis.com/chart?chs=250x250&cht=qr&chl=bitcoin%{btc_address}%3Famount%3D{btc_amount_formatted}">QR код для более удобной оплаты (если нужен)</a>\n'
                    "➖➖➖\n"
                    "Для пополнения баланса нажмите 👉/pay\n"
                    "Для просмотра баланса нажмите 👉/balance\n"
                    "Для просмотра истории операций по счету 👉/history\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
                    parse_mode='HTML'
                )
                await state.finish()
    
            elif payment_method == "ltc":
                price_ltc = database.get_crypto_price("ltc")
                coefficient = database.get_payment_coefficient_biz("ltc")
    
                if coefficient is None:
                    coefficient = 1
    
                adjusted_amount = amount * coefficient
                ltc_address = database.get_payment_address("ltc")
                ltc_amount = adjusted_amount / price_ltc
                ltc_amount_formatted = f"{ltc_amount:.8f}".rstrip("0")
    
                await message.answer(
                    f"Для пополнения баланса оплатите:\n"
                    "➖➖➖\n"
                    f"💰 <code>{ltc_amount_formatted}</code> LTC\n"
                    "➖➖➖\n"
                    "На Litecoin кошелёк:\n"
                    "➖➖➖\n"
                    f"👉 <code>{ltc_address}</code>\n"
                    "➖➖➖\n"
                    "Переведите Litecoin на указанный кошелек и просто ожидайте 1 подтверждения в сети Litecoin - система автоматически зачислит Вам баланс и отправит сообщение об успешном пополнении баланса.\n"
                    "➖➖➖\n"
                    "Это Ваш постоянный Litecoin кошелек для пополнения баланса Вашего личного кабинета. Чтобы пополнить баланс в магазине, просто отправьте на данный кошелек средства, после 1 подтверждения - система зачислит Вам баланс в автоматическом режиме. Вы можете отправлять любое количество Litecoin на Ваш кошелек - система автоматически рассчитает Вам баланс в рублях, по курсу Litecoin на момент Вашего перевода. Старайтесь пополнять всегда немного большую сумму (например на 20-30 рублей больше), так как курс Litecoin может измениться в момент Вашего перевода и Вам может не хватить денег для покупки товара.\n"
                    "➖➖➖\n"
                    f'<a href="https://chart.googleapis.com/chart?chs=250x250&cht=qr&chl=litecoin%{ltc_address}%3Famount%3D{ltc_amount_formatted}">QR код для более удобной оплаты (если нужен)</a>\n'
                    "➖➖➖\n"
                    "Для пополнения баланса нажмите 👉/pay\n"
                    "Для просмотра баланса нажмите 👉/balance\n"
                    "Для просмотра истории операций по счету 👉/history\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
                    parse_mode='HTML'
                )
                await state.finish()
        
    @dp.message_handler(lambda message: not message.text.isdigit(), state=PayState.entering_amount)
    async def handle_invalid_pay_amount(message: types.Message):
        await message.answer(
            "Ошибка. Укажите правильную сумму пополнения. Минимальная сумма пополнения через Bitcoin - 500 рублей.\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(state=CardPayState.entering_amount)
    async def handle_card_payment_amount(message: types.Message, state: FSMContext):
        if not message.text.isdigit():
            await message.answer(
                "Ошибка. Минимальная сумма пополнения 500 руб.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            return
    
        amount = int(message.text.strip())
    
        if amount < 500:
            await message.answer(
                "Ошибка. Минимальная сумма пополнения 500 руб.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
        elif amount > 150000:
            await message.answer(
                "Максимальная сумма пополнения 150000 рублей.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
        else:
            coefficient = database.get_payment_coefficient_biz("card")
    
            adjusted_amount = int(amount * coefficient)
            card_details = database.get_payment_address("card")
            transaction_id = database.increment_and_get_order_value()
    
            await state.update_data(adjusted_amount=adjusted_amount, amount=amount)
    
            await message.answer(
                f"Заявка на пополнение через банковскую карту:\n"
                f"👉 # <b>{transaction_id}</b>\n"
                f"Статус заявки:\n"
                f"❗ <b>Ожидает оплаты</b>\n"
                f"Сумма для оплаты:\n"
                f"💰 <code>{adjusted_amount}</code> руб.\n"
                f"Номер банковской карты для оплаты:\n"
                f"👉 <code>{card_details}</code>\n"
                "➖➖\n"
                "❗ <b>Реквизиты действительны в течении 30 минут!</b>\n"
                "➖➖\n"
                f"👉 На Ваш баланс будет зачислено <code>{amount}</code> руб.\n"
                "➖➖\n"
                "❗ После оплаты отправьте любую цифру\n"
                "❗ Чтобы изменить сумму заявки, нажмите 👉 /amount\n\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
                parse_mode='HTML'
            )
            await CardPayState.waiting_for_payment_confirmation.set()
    
    @dp.message_handler(commands=['amount'], state=CardPayState.waiting_for_payment_confirmation)
    async def handle_amount_change_command(message: types.Message):
        await message.answer(
            "Введите новую сумму\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
        await CardPayState.entering_amount.set()
    
    @dp.message_handler(lambda message: message.text.isdigit(), state=CardPayState.waiting_for_payment_confirmation)
    async def handle_payment_confirmation(message: types.Message, state: FSMContext):
        data = await state.get_data()
        amount = data.get('amount')
        adjusted_amount = data.get('adjusted_amount')
    
        if message.text.isdigit():
            user_input_amount = int(message.text.strip())
            if user_input_amount < 500:
                await message.answer(
                    "Ошибка. Минимальная сумма пополнения 500 руб.\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
            elif user_input_amount > 150000:
                await message.answer(
                    "Максимальная сумма пополнения 150000 рублей.\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
            else:
                coefficient = database.get_payment_coefficient_biz("card")
                if coefficient is None:
                    coefficient = 1
    
                adjusted_amount = int(user_input_amount * coefficient)
                card_details = database.get_payment_address("card")
                transaction_id = database.increment_and_get_order_value()
    
                await state.update_data(adjusted_amount=adjusted_amount, amount=user_input_amount)
    
                await message.answer(
                    f"Заявка на пополнение через банковскую карту:\n"
                    f"👉 # <b>{transaction_id}</b>\n"
                    f"Статус заявки:\n"
                    f"❗ <b>Ожидает оплаты</b>\n"
                    f"Сумма для оплаты:\n"
                    f"💰 <code>{adjusted_amount}</code> руб.\n"
                    f"Номер банковской карты для оплаты:\n"
                    f"👉 <code>{card_details}</code>\n"
                    "➖➖\n"
                    "❗ <b>Реквизиты действительны в течении 30 минут!</b>\n"
                    "➖➖\n"
                    f"👉 На Ваш баланс будет зачислено <code>{user_input_amount}</code> руб.\n"
                    "➖➖\n"
                    "❗ После оплаты отправьте любую цифру\n"
                    "❗ Чтобы изменить сумму заявки, нажмите 👉 /amount\n\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
                    parse_mode='HTML'
                )
        else:
            await message.answer(
                "Ошибка. Минимальная сумма пополнения 500 руб.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
    
    @dp.message_handler(state=SimPayState.entering_amount)
    async def handle_sim_payment_amount(message: types.Message, state: FSMContext):
        if not message.text.isdigit():
            await message.answer(
                "Ошибка. Минимальная сумма пополнения 500 руб.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            return
    
        amount = int(message.text.strip())
    
        if amount < 500:
            await message.answer(
                "Ошибка. Минимальная сумма пополнения 500 руб.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
        elif amount > 100000:
            await message.answer(
                "Ошибка. Максимальная сумма пополнения 100 000 руб.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
        else:
            coefficient = database.get_payment_coefficient_biz("sim")
            if coefficient is None:
                coefficient = 1
    
            adjusted_amount = int(amount * coefficient)
            sim_details = database.get_payment_address("sim")
            
            if sim_details == "Реквизиты не найдены.":
                await message.answer(
                    "Что то пошло не так!\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
                return
    
            transaction_id = database.increment_and_get_order_value()
    
            await state.update_data(adjusted_amount=adjusted_amount, amount=amount)
    
            await message.answer(
                f"Заявка на пополнение через SIM:\n"
                f"👉 # <b>{transaction_id}</b>\n"
                f"Статус заявки:\n"
                f"❗ <b>Ожидает оплаты</b>\n"
                f"Сумма для оплаты:\n"
                f"💰 <code>{adjusted_amount}</code> руб.\n"
                f"Телефон для оплаты:\n"
                f"👉 <code>{sim_details}</code>\n"
                "➖➖\n"
                "❗ <b>Реквизиты действительны в течении 30 минут!</b>\n"
                "➖➖\n"
                f"👉 На Ваш баланс будет зачислено <code>{amount}</code> руб.\n"
                "➖➖\n"
                "❗ После оплаты отправьте любую цифру\n"
                "❗ Чтобы изменить сумму заявки, нажмите 👉 /amount\n\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
                parse_mode='HTML'
            )
            await SimPayState.waiting_for_payment_confirmation.set()

    @dp.message_handler(commands=['amount'], state=SimPayState.waiting_for_payment_confirmation)
    async def handle_sim_amount_change_command(message: types.Message):
        await message.answer(
            "Введите новую сумму\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
        await SimPayState.entering_amount.set()
    
    @dp.message_handler(lambda message: message.text.isdigit(), state=SimPayState.waiting_for_payment_confirmation)
    async def handle_sim_payment_confirmation(message: types.Message, state: FSMContext):
        data = await state.get_data()
        amount = data.get('amount')
        adjusted_amount = data.get('adjusted_amount')
    
        if message.text.isdigit():
            user_input_amount = int(message.text.strip())
            if user_input_amount < 500:
                await message.answer(
                    "Ошибка. Минимальная сумма пополнения 500 руб.\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
            elif user_input_amount > 100000:
                await message.answer(
                    "Ошибка. Максимальная сумма пополнения 100 000 руб.\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
            else:
                coefficient = database.get_payment_coefficient_biz("sim")
                if coefficient is None:
                    coefficient = 1
    
                adjusted_amount = int(user_input_amount * coefficient)
                sim_details = database.get_payment_address("sim")
                
                if sim_details == "Реквизиты не найдены.":
                    await message.answer(
                        "Что то пошло не так!\n"
                        "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                    )
                    return
    
                transaction_id = database.increment_and_get_order_value()
    
                await state.update_data(adjusted_amount=adjusted_amount, amount=user_input_amount)
    
                await message.answer(
                    f"Заявка на пополнение через SIM:\n"
                    f"👉 # <b>{transaction_id}</b>\n"
                    f"Статус заявки:\n"
                    f"❗ <b>Ожидает оплаты</b>\n"
                    f"Сумма для оплаты:\n"
                    f"💰 <code>{adjusted_amount}</code> руб.\n"
                    f"Телефон для оплаты:\n"
                    f"👉 <code>{sim_details}</code>\n"
                    "➖➖\n"
                    "❗ <b>Реквизиты действительны в течении 30 минут!</b>\n"
                    "➖➖\n"
                    f"👉 На Ваш баланс будет зачислено <code>{user_input_amount}</code> руб.\n"
                    "➖➖\n"
                    "❗ После оплаты отправьте любую цифру\n"
                    "❗ Чтобы изменить сумму заявки, нажмите 👉 /amount\n\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
                    parse_mode='HTML'
                )
        else:
            await message.answer(
                "Ошибка. Минимальная сумма пополнения 500 руб.\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
    
    @dp.message_handler(lambda message: True, state=None)
    async def handle_all_texts(message: types.Message, state: FSMContext):
        text = message.text.strip()
        
        if text.startswith("/city"):
            city_id_match = re.match(r"/city(\d+)", text)
            if city_id_match:
                city_id = int(city_id_match.group(1))
                if database.check_city_exists(city_id):
                    products = database.get_products_by_city_id(city_id)
                    if products:
                        city_name = database.get_city_name(city_id)[0]
                        response = f"🏠 Город: <b>{city_name}</b>\n➖➖\n<b>Выберите товар:</b>\n➖➖\n"
                        
                        for product_id, product_name, product_price in products:
                            response += (
                                f"🎁 <b>{product_name}</b>\n"
                                f"💰 Цена: <b>{int(product_price)} руб.</b>\n"
                                f"[ Для покупки нажмите 👉 /item{product_id} ]\n"
                                f"[ Посмотреть отзывы о данном товаре 👉 /reviews{product_id} ]\n"
                                "➖➖\n"
                            )
                        
                        response += (
                            "Список подписок 👉 /sub\n"
                            "Создать новую подписку 👉 /addsub\n"
                            "Удалить подписку 👉 /remsub\n"
                            "➖➖\n"
                            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                        )
    
                        await message.answer(response, parse_mode='HTML')
                        await state.update_data(selected_city=city_id)  # Сохранить выбранный город
                        await CitySelectionState.choosing_product.set()
                    else:
                        await message.answer(
                            "Товары для данного города не найдены!\n"
                            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                        )
                else:
                    await message.answer(
                        "Выберите город строго из списка!\n"
                        "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                    )
            else:
                await message.answer(
                    "Выберите город строго из списка!\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
        elif text.startswith("/reviews"):
            await message.answer(
                "🙅 Отзывы не найдены!\n"
                "Чтобы добавить отзыв нажмите 👉 /addreview\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
        else:
            await message.answer(
                "Выберите город строго из списка!\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
    
    @dp.message_handler(lambda message: message.text.startswith("/item"), state=CitySelectionState.choosing_product)
    async def handle_product_choice(message: types.Message, state: FSMContext):
        product_id_match = re.match(r"/item(\d+)", message.text)
        if product_id_match:
            product_id = int(product_id_match.group(1))
            product_info = database.get_product_name(product_id)
            if product_info:
                product_name = product_info[0]
                city_id = (await state.get_data()).get('selected_city')
                city_name = database.get_city_name(city_id)[0]
                product_details = database.get_product_details(product_id)
    
                if product_details:
                    price_full, districts = product_details[0]
                    price = int(price_full)
                    response = f"🏠 Город: <b>{city_name}</b>\n"
                    response += f"🎁 Товар: <b>{product_name}</b>\n"
                    response += f"💰 Цена: <b>{price} руб.</b>\n"
                    response += "➖➖\n<b>Выберите район:</b>\n➖➖\n"
    
                    for district in districts.split(","):
                        district_id = database.get_district_id_by_name(district.strip())
                        if district_id:
                            response += f"🏃 район <b>{district.strip()}</b>\n"
                            response += f"[Для выбора нажмите 👉 /district{district_id} ]\n"
                            response += "➖➖\n"
    
                    response += "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                    await message.answer(response, parse_mode='HTML')
                    await state.update_data(selected_product=product_id)
                    await CitySelectionState.choosing_district.set()
                else:
                    await message.answer(
                        "Районы для данного товара не найдены!\n"
                        "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                    )
            else:
                await message.answer(
                    "Выберите продукт строго из списка!\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
        else:
            await message.answer(
                "Выберите продукт строго из списка!\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
    
    @dp.message_handler(state=CitySelectionState.choosing_product)
    async def wrong_product_input(message: types.Message):
        await message.answer(
            "Выберите продукт строго из списка!\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(lambda message: True, state=CitySelectionState.choosing_district)
    async def handle_district_choice(message: types.Message, state: FSMContext):
        if not message.text.startswith("/district"):
            await message.answer(
                "Выберите район строго из списка\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            return
    
        district_id_match = re.match(r"/district(\d+)", message.text)
        if district_id_match:
            district_id = int(district_id_match.group(1))
            district_name = database.get_district_name_by_id(district_id)
            if district_name:
                data = await state.get_data()
                city_name = database.get_city_name(data.get('selected_city'))[0]
                product_name = database.get_product_name(data.get('selected_product'))[0]
                price_full = database.get_product_details(data.get('selected_product'))[0][0]
                price = int(price_full)
                response = (
                    f"🏠 Город: <b>{city_name}</b>\n"
                    f"🏃 Район: <b>{district_name}</b>\n"
                    f"🎁 Товар: <b>{product_name}</b>\n"
                    f"💰 Цена: <b>{price} руб.</b>\n"
                    "➖➖➖\nВыберите метод оплаты:\n➖➖➖\n"
                    "Bitcoin\n[Для выбора нажмите 👉 /buy1 ]\n"
                    "➖➖➖\nLitecoin\n[Для выбора нажмите 👉 /buy7 ]\n"
                    "➖➖➖\nБанковская карта\n[Для выбора нажмите 👉 /buy11 ]\n"
                    "➖➖➖\nSIM\n[Для выбора нажмите 👉 /buy10 ]\n"
                    "➖➖➖\nОплата купоном\n[Для выбора нажмите 👉 /buy12 ]\n"
                    "➖➖➖\nОплата с баланса\n[Для выбора нажмите 👉 /buy5 ]\n"
                    "➖➖➖\nЧтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
                await message.answer(response, parse_mode='HTML')
                await state.update_data(selected_district=district_id)
                await PaymentSelectionState.choosing_payment_method.set()
            else:
                await message.answer(
                    "Выберите район строго из списка\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
        else:
            await message.answer(
                "Выберите район строго из списка\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
    
    @dp.message_handler(lambda message: message.text.startswith("/buy"), state=PaymentSelectionState.choosing_payment_method)
    async def handle_payment_method_choice(message: types.Message, state: FSMContext):
        payment_method = message.text.strip().lower()
        data = await state.get_data()
        city_name = database.get_city_name(data.get('selected_city'))[0]
        district_name = database.get_district_name_by_id(data.get('selected_district'))
        product_name = database.get_product_name(data.get('selected_product'))[0]
        price_full = database.get_product_details(data.get('selected_product'))[0][0]
        price = int(price_full)
    
        method_map = {
            "/buy1": "Bitcoin",
            "/buy7": "Litecoin",
            "/buy11": "Банковская карта",
            "/buy10": "SIM",
            "/buy12": "Оплата купоном",
            "/buy5": "Оплата с баланса"
        }
    
        if payment_method in ["/buy1", "/buy7", "/buy11"]:
            method_name = method_map[payment_method]
            transaction_id = database.increment_and_get_order_value()
            comment_code = "".join(random.choices("0123456789", k=5))
    
            response = (
                f"🏠 Город: <b>{city_name}</b>\n"
                f"🏃 Район: <b>{district_name}</b>\n"
                f"🎁 Название: <b>{product_name}</b>\n"
                f"💰 Стоимость: <b>{price} руб.</b>\n"
                f"💱 Метод оплаты: <b>{method_name}</b>\n"
                "➖➖➖➖\n"
            )
    
            if payment_method == "/buy1":
                btc_coefficient = database.get_payment_coefficient_biz("btc") or 1
                adjusted_price = int(price * btc_coefficient)
                price_btc = database.get_crypto_price("btc")
                btc_address = database.get_payment_address("btc")
                btc_amount = adjusted_price / price_btc
                btc_amount_formatted = f"{btc_amount:.8f}".rstrip("0")
                response += (
                    f"Для приобретения выбранного товара, оплатите:\n"
                    "➖➖➖➖\n"
                    f"💸 <code>{btc_amount_formatted}</code> BTC\n"
                    "➖➖➖➖\n"
                    "на Bitcoin кошелек:\n"
                    f"<code>{btc_address}</code>\n"
                    "➖➖➖➖\n"
                    f'👉 <a href="https://chart.googleapis.com/chart?chs=250x250&cht=qr&chl=bitcoin%{btc_address}%3Famount%3D{btc_amount_formatted}">QR код для более удобной оплаты (если нужен)</a>\n'
                    "➖➖➖➖\n"
                    f"#⃣ <b>Заказ №</b><code>{transaction_id}</code>, запомните его.\n"
                    "➖➖➖➖\n"
                    f"Комментарий к платежу\n"
                    f"💬 <b>{comment_code}</b>\n"
                    "➖➖➖➖\n"
                    "По номеру заказа и комментарию вы сможете узнать статус заказа (получить адрес) в любой момент и с любого устройства на 👉 <a href='https://kazanmall.shop/check'>нашем сайте</a>.\n"
                    "➖➖➖➖\n"
                    "Комментарий служит исключительно для идентификации Вашего заказа. Отправлять BTC с комментарием не нужно, достаточно просто на указанный кошелек перевести точную сумму, дождаться 1 подтверждение в системе Bitcoin, после чего Вы получите свой адрес. Оплачивать необходимо одним переводом. Сумма перевода и кошелек должны быть точными, как указано в реквизитах выше, иначе Ваша оплата не засчитается. Будьте внимательны, так как при ошибочном платеже получить адрес или возврат средств будет невозможно!\n"
                    "➖➖➖➖\n"
                    "После оплаты отправьте любую цифру и если на Вашем платеже есть 1 подтверждение - Вы получите адрес. Так же, получить адрес можно и на нашем сайте, на странице 👉 <a href='https://kazanmall.shop/check'>проверка заказа</a>. Создать свой кошелек Bitcoin можно 👉 <a href='https://blockchain.info/ru/wallet/new'>здесь</a> или 👉 <a href='https://bitcoin.org/ru/choose-your-wallet'>здесь</a>.\n"
                    "➖➖➖➖\n"
                    "Купить Bitcoin можно через обменники, например 👉 <a href='http://www.bestchange.ru/qiwi-to-bitcoin.html'>здесь</a>.\n"
                    "➖➖➖➖\n"
                    "Для того, чтобы посмотреть последний Ваш заказ нажмите 👉 <b>/lastorder</b>\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
    
            elif payment_method == "/buy7":
                ltc_coefficient = database.get_payment_coefficient_biz("ltc") or 1
                adjusted_price = int(price * ltc_coefficient)
                price_ltc = database.get_crypto_price("ltc")
                ltc_address = database.get_payment_address("ltc")
                ltc_amount = adjusted_price / price_ltc
                ltc_amount_formatted = f"{ltc_amount:.8f}".rstrip("0")
                response += (
                    f"Для приобретения выбранного товара, оплатите:\n"
                    "➖➖\n"
                    f"💸 <code>{ltc_amount_formatted}</code> LTC\n"
                    "на Litecoin кошелек:\n"
                    "➖➖\n"
                    f"<code>{ltc_address}</code>\n"
                    "➖➖\n"
                    f'👉 <a href="https://chart.googleapis.com/chart?chs=250x250&cht=qr&chl=litecoin%{ltc_address}%3Famount%3D{ltc_amount_formatted}">QR код для более удобной оплаты (если нужен)</a>\n'                    "➖➖\n"
                    "➖➖\n"
                    f"#⃣ <b>Заказ №</b><code>{transaction_id}</code>, запомните его.\n"
                    "➖➖\n"
                    f"Комментарий к платежу\n"
                    f"💬 <b>{comment_code}</b>\n"
                    "➖➖\n"
                    "По номеру заказа и комментарию вы сможете узнать статус заказа (получить адрес) в любой момент и с любого устройства на 👉 <a href='https://kazanmall.shop/check'>нашем сайте</a>.\n"
                    "➖➖\n"
                    "Комментарий служит исключительно для идентификации Вашего заказа. Отправлять LTC с комментарием не нужно, достаточно просто на указанный кошелек перевести точную сумму, дождаться 1 подтверждение в системе Litecoin, после чего Вы получите свой адрес. Оплачивать необходимо одним переводом. Сумма перевода и кошелек должны быть точными, как указано в реквизитах выше, иначе Ваша оплата не засчитается. Будьте внимательны, так как при ошибочном платеже получить адрес или возврат средств будет невозможно!\n"
                    "➖➖\n"
                    "После оплаты отправьте любую цифру и если на Вашем платеже есть 1 подтверждение - Вы получите адрес. Так же, получить адрес можно и на нашем сайте, на странице 👉 <a href='https://kazanmall.shop/check'>проверка заказа</a>. Создать свой кошелек Litecoin можно 👉 <a href='https://litecoin.info/'>здесь</a>.\n"
                    "➖➖\n"
                    "Купить Litecoin можно через обменники, например 👉 <a href='http://www.bestchange.ru/qiwi-to-litecoin.html'>здесь</a>.\n"
                    "➖➖\n"
                    "Для того, чтобы посмотреть последний Ваш заказ нажмите 👉 <b>/lastorder</b>\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
    
            elif payment_method == "/buy11":
                
                card_coefficient = database.get_payment_coefficient_biz("card") or 1
                adjusted_price = int(price * card_coefficient)
                card_number = database.get_payment_address("card")
                response += (
                    f"Для приобретения выбранного товара, оплатите:\n"
                    "➖➖➖\n"
                    f"💰 <code>{adjusted_price}</code> руб.\n"
                    "Номер банковской карты для оплаты:\n"
                    f"👉 <code>{card_number}</code>\n"
                    "➖➖➖\n"
                    "❗ <b>Реквизиты действительны в течении 30 минут!</b>\n"
                    "➖➖➖\n"
                    "<b>Оплатите ТОЧНУЮ СУММУ на номер банковской карты! Обычно это занимает 30-60 секунд.</b>\n"
                    "➖➖➖\n"
                    "<b>Отправьте любую цифру, только после реальной оплаты.</b> Если после этого система не увидит Вашу оплату в течении 3х минут, ваш заказ будет отменен и Вы не получите ни товар, ни деньги на баланс.\n"
                    "➖➖➖\n"
                    "Оплата принимается только на <b>НОМЕР БАНКОВСКОЙ КАРТЫ</b>. Пополнить банковскую карту можно любым удобным способом, например: со своего QIWI-кошелька, терминала, банковской карты (card2card), Yandex.Деньги, Payeer, WebMoney и другие платежные системы.\n"
                    "➖➖➖\n"
                    "Переводите обязательно <b>ТОЧНУЮ</b> сумму, которую Вам выдал бот! Пожалуйста, учитывайте сумму комиссии к платежу!\n"
                    "➖➖➖\n"
                    "<b>Любая цифра отправляется в самый последний момент, когда Вы произвели оплату и уверены в точной сумме. При точном выполнении всех правил - Вы получите товар.</b>\n"
                    "➖➖➖\n"
                    "Вопросы по зависшим платежам принимаются в течении суток с момента оплаты. Если Вы не получили товар, но реально перевели деньги на выданные Вам реквизиты - свяжитесь со службой поддержки обменника отправив 👉 <b>/exticket</b>, обязательно укажите номер заявки и детали вашего платежа вместе с точной суммой оплаты. Скриншоты чеков обязательны! По истечении суток запросы по зависшим платежам не принимаются!\n"
                    "➖➖➖\n"
                    "Заявки обрабатываются через сторонний обменник, если Вы создали обращение по зависшему платежу и Вашу проблему не решили - обратитесь к Администрации магазина через команду 👉 <b>/ticket</b>\n"
                    "➖➖➖\n"
                    "❗ После оплаты отправьте любую цифру\n"
                    "➖➖➖\n"
                    f"#⃣ <b>Заказ №</b><code>{transaction_id}</code>, запомните его.\n"
                    "➖➖➖\n"
                    f"Комментарий для проверки\n"
                    f"💬 <b>{comment_code}</b>\n"
                    "➖➖➖\n"
                    "❗ Внимание! Оплачивать с комментарием не нужно. Номер заказа и комментарий служит исключительно для проверки платежа на странице проверки заказа.\n"
                    "По номеру заказа и комментарию вы сможете узнать статус заказа (получить адрес) в любой момент и с любого устройства на 👉 <a href='https://kfp24.com/check'>нашем сайте</a>.\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
    
            await message.answer(response, parse_mode='HTML')
    
        else:
            await message.answer(
                "Для оплаты данным методом Вам необходимо пополнить баланс купоном. Используйте команду /pay\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @",
                parse_mode='HTML'
            )
    
    @dp.message_handler(state=CitySelectionState.choosing_product)
    async def wrong_product_input(message: types.Message):
        await message.answer(
            "Выберите продукт строго из списка!\n"
            "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        )
    
    @dp.message_handler(lambda message: True, state=CitySelectionState.choosing_district)
    async def handle_district_choice(message: types.Message, state: FSMContext):
        if not message.text.startswith("/district"):
            await message.answer(
                "Выберите район строго из списка\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
            return
        
        district_id_match = re.match(r"/district(\d+)", message.text)
        if district_id_match:
            district_id = int(district_id_match.group(1))
            district_name = database.get_district_name_by_id(district_id)
            if district_name:
                # Логика для обработки выбранного района
                await message.answer(
                    f"Вы выбрали район: {district_name}\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
            else:
                await message.answer(
                    "Выберите район строго из списка\n"
                    "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                )
        else:
            await message.answer(
                "Выберите район строго из списка\n"
                "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            )
    