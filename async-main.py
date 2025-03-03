import asyncio
import concurrent.futures

from aiogram import Bot,Dispatcher,types,Router

from aiogram.filters import Command
from aiogram.filters import Command, StateFilter

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import CallbackQuery
from aiogram.types import FSInputFile

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup

from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode

from instagrapi import Client

import csv

from random import choice

class FSMForm(StatesGroup):
    process_info = State() # Log in process
    parse_by_user = State() # Target username process
    parsing = State() # Parsing process
    second_parsing = State() # Second parsing process

class UserData:
    def __init__(self, user_id, username=None, password=None):
        self.user_id = user_id
        self.username = username
        self.password = password
        self.cl = None
        self.parsing = False
        self.count = 0
        self.captcha = False
        self.mode = "following"
        self.has_logged = False

user_data_list = {}

TOKEN = "7004836648:AAHMF-3fhThZFGN0drrTkrIGM7imfxJBiig"
PROXIES = [
    "http://185.33.85.84:50100"
]

dp = Dispatcher()
router = Router()

dp.include_router(router)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

start_button_text = "Начать парсинг ✅"
settings_button_text = "Настройки аккаунта ⚙️"

@router.message(Command(commands=['start']), StateFilter(default_state))
async def start_message(msg: types.Message):
    user_id = msg.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)
    
    item = KeyboardButton(text=start_button_text)
    item1 = KeyboardButton(text=settings_button_text)

    greet_kb = ReplyKeyboardMarkup(keyboard=[[item,item1]], resize_keyboard=True)

    bot_info = await bot.get_me()

    await bot.send_message(msg.chat.id, 
                           f"Привет, <b>{msg.from_user.full_name}</b>!👋\nМеня зовут <b>{bot_info.full_name}</b>. Я помогаю в парсинге данных из инстаграма 🔍 \nВыбери нужную опцую ниже, чтобы начать 👀\n\nДля дополнительной информации используй /help",
                           reply_markup=greet_kb)

@router.message(Command(commands=['change_account']), StateFilter(default_state))
async def change_account(msg: types.Message, state: FSMContext):
    sent_msg = await msg.reply("Хорошо! Предоставь мне никнейм и пароль через кому для входа в таком формате: никнейм,пароль")
    await state.set_state(FSMForm.process_info)

@router.message(Command(commands=['stop']))
async def stop_parsing(msg: types.Message):
    user_data = user_data_list[msg.chat.id]

    if user_data.parsing:
        await msg.reply(f"⚡Процесс парсинга был остановлен! Данные вот-вот придут 🏃‍♂️")
        user_data.parsing = False
    else:
        await msg.reply(f"👀Процесс парсинга не был запущен!")

@router.message(Command(commands=['stats']))  
async def get_stat(msg: types.Message):
    user_data = user_data_list[msg.chat.id]

    await msg.reply(f'<b>Статус парсинга: {user_data.parsing}</b>\n<b>Капча: {user_data.captcha}</b>\n<b>Получено данных: {user_data.count}</b>\n<b>Текущий режим: {user_data.mode}</b>\nИспользуй /stop, чтобы <b>принудительно прервать процесс</b> парсинга данных.') 

@router.message(Command(commands=['help']))
async def help_docs(msg: types.Message):
    bot_info = await bot.get_me()
    await msg.reply(f"<b>{bot_info.full_name}</b> - это бот, который помогает парсить данные с инстаграма. В его задачу входит сбор данных подписчиков конкретного аккаунта.\n\nДанный бот собирает такую информацию в CSV файл:\n- <code>Username</code>: юзернейм аккаунта\n- <code>Bio</code>: биография аккаунта\n- <code>Followers count</code>: количество подписчиков у аккаунта\n- <code>Following count</code>: количество подписок у аккаунта\n- <code>Full name</code>: полное имя аккаунта\n\nВсе возможные команды, которые принимает бот:\n/change_account - смена аккаунта\n/stop - принудительная остановка процесса парсинга\n/stats - отображение статистики парсинга\n/help - вся информация о боте и не только\n\n")

@dp.message(StateFilter(FSMForm.process_info))
async def process_info(msg: types.Message, state: FSMContext):
    user_data = user_data_list[msg.chat.id]
    info = msg.text

    if info == settings_button_text:
        await msg.reply(f"Ты вошёл в аккаунт под именем: <b>{user_data.username}</b>\n\n<b>Информация об аккаунте</b>\n\nНикнейм: <code>{user_data.username}</code>\nПароль: <code>{user_data.password}</code>\n\nТекущий режим: <b>{user_data.mode}</b>\n\n/change_account - чтобы сменить аккаунт\n")
        await state.set_state(default_state)

    else:
        try:
            username,password = info.split(',')
            username = username.strip()
            password = password.strip()

            await msg.reply('Загружаем... Перейди в инстаграм, чтобы пройти капчу и разрешить вход в аккаунт (запрос появится сразу при входе в приложение или в уведомлениях)')

            process_user_data(msg.chat.id, username, password)

            if login_user(msg.chat.id):
                user_data.has_logged = True
                
                await msg.reply(f"Ты успешно вошёл в аккаунт!✅\nНикнейм: <code>{user_data.username}</code>\nПароль: <code>{user_data.password}</code>\n\nТы также можешь сменить аккаунт в настройках ⚙️")
                await state.set_state(default_state)

                btn = InlineKeyboardButton(text='Парсинг подписок', callback_data='following')
                btn1 = InlineKeyboardButton(text='Парсинг подписчиков', callback_data='followers')
                
                kb = InlineKeyboardMarkup(inline_keyboard=[[btn, btn1]])
                await msg.reply('Выбери режим, чтобы начать ⬇️', reply_markup=kb)
            else:
                await msg.reply(f"❌Я не смог найти аккаунт с таким именем <b>{username}</b>. Проверь имя с паролем и попробуй ещё раз 🔄️\n\n🎯Возможные проблемы и их решения:\n - Скорее всего Инстаграм запрашивает капчу для подтверждения, что ты не робот (проверь instagram.com и нажми на галочку, если появилась капча)\n - Проблемы с серверами Instagram \n - Подожди несколько минут и попробуй ещё раз. \n - Такого никнейма действительно не существует. Попробуй другой")
                user_data.username = None
                user_data.password = None
                user_data.has_logged = False
        except ValueError as e:
            await msg.reply(f"Неправильные данные! Пожалуйста, введи без пробелов данные в таком формате: никнейм,пароль (кома разделитель)")
            await state.set_state(FSMForm.process_info)


@dp.message(StateFilter(FSMForm.parse_by_user))
async def parse_by_user(msg: types.Message, state: FSMContext):
    user_data = user_data_list[msg.chat.id]
    info = msg.text

    if info == settings_button_text:
        await msg.reply(f"Ты вошёл в аккаунт под именем: <b>{user_data.username}</b>\n\n<b>Информация об аккаунте</b>\n\nНикнейм: <code>{user_data.username}</code>\nПароль: <code>{user_data.password}</code>\n\nТекущий режим: <b>{user_data.mode}</b>\n\n/change_account - чтобы сменить аккаунт\n")
    elif info == start_button_text or '/' in info:
        await msg.reply(f"<b>❌Укажи корректные данные для парсинга</b>")
        await state.set_state(FSMForm.parse_by_user)
    else:
        await msg.reply(f"Хорошо! Парсинг начинается..\n\n<b>Это может занять время в зависимости от количества необходимых данных..</b>\n\n<b>В случае, если ты захочешь остановить процесс используй: /stop</b>\nИспользуй /stats для отслеживания процесса")
        await state.set_state(default_state)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            try:
                user_data.parsing=True
                user_data.count = 0

                result = asyncio.get_event_loop().run_in_executor(executor, get_all_info, info, msg.chat.id, msg)
                await result

                if result:
                    file = FSInputFile('data.csv')
                    await bot.send_document(msg.chat.id, file, caption='Данные получены! ✅')
                user_data.parsing = False

            except KeyboardInterrupt:
                executor.shutdown(wait=False)
                print("Stopped by user..")

# When start button clicked
@dp.message(lambda msg: msg.text == start_button_text, StateFilter(default_state))
async def start_button_clicked(msg: types.Message, state: FSMContext):
    user_id = msg.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)
    
    user_data = user_data_list[user_id]
    
    if not user_data.has_logged and not user_data.parsing:
        await msg.reply("Хорошо! Предоставь мне никнейм и пароль для входа в таком формате: никнейм,пароль (без пробелов) Это поможет мне при парсинге данных <b>(внимание, аккаунт может быть заблокирован из-за большого количества запросов, не предоставляй данные своего основного аккаунта)</b>❗")
        await state.set_state(FSMForm.process_info)
    elif user_data.has_logged and not user_data.parsing:
        btn = InlineKeyboardButton(text='Парсинг подписок', callback_data='following')
        btn1 = InlineKeyboardButton(text='Парсинг подписчиков', callback_data='followers')
        
        kb = InlineKeyboardMarkup(inline_keyboard=[[btn, btn1]])
        await msg.reply('Выбери режим, чтобы начать ⬇️', reply_markup=kb)

    else:
        await msg.reply(f"Подожди пока закончиться предыдущий парсинг данных! \n\n<b>Используй /stop, если хочешь остановить процесс</b>")

# When settings button clicked
@dp.message(lambda msg: msg.text == settings_button_text)
async def settings_button_clicked(msg: types.Message):
    user_id = msg.chat.id
    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(user_id)
    
    user_data = user_data_list[msg.chat.id]

    await msg.reply(f"Ты вошёл в аккаунт под именем: <b>{user_data.username}</b>\n\n<b>Информация об аккаунте</b>\n\nНикнейм: <code>{user_data.username}</code>\nПароль: <code>{user_data.password}</code>\n\nТекущий режим: <b>{user_data.mode}</b>\n\n/change_account - чтобы сменить аккаунт\n")


@dp.callback_query(lambda d: d.data, StateFilter(default_state))
async def parsing_following(callback: CallbackQuery, state: FSMContext):
    user_data = user_data_list[callback.message.chat.id]

    if callback.data == "following":
        user_data.mode = "following"
    else:
        user_data.mode = "followers"

    await callback.message.reply(f"Теперь мне нужен никнейм пользователя, которого ты хочешь спарсить 👁️")
    await state.set_state(FSMForm.parse_by_user)
# Function for processing user data
def process_user_data(user_id, username, password):
    global user_data_list

    if user_id not in user_data_list:
        user_data_list[user_id] = UserData(username, password)
    else:
        user_data = user_data_list[user_id]
        user_data.username = username
        user_data.password = password

# Instagrapi login function
def login_user(user_id):
    user_data = user_data_list[user_id]
    user_data.cl = Client(delay_range=[9,10])
    
    before_ip = user_data.cl._send_public_request("https://api.ipify.org/")
    with open('proxies.txt', 'r') as file:
        print("opening txt file")
        lines = file.readlines()
        user_data.cl.set_proxy(choice(lines).strip())

    after_ip = user_data.cl._send_public_request("https://api.ipify.org/")

    print(f'Before: {before_ip}')
    print(f'After: {after_ip}')

    try:
        user_data.cl.login(user_data.username, user_data.password)
        return True
    except Exception as e:
        print(e)
        user_data.cl = Client(delay_range=[9,10])
        return False
    
# Parsing process
def get_all_info(username, id, msg):

    print("Parsing has been started!")
    user_data = user_data_list[id]

    # Get ID from specified user
    try:

        target_id = user_data.cl.user_info_by_username_v1(username).model_dump()
    except Exception as e:
        print(f"Issue when trying to get target user information: {e}")
        msg.reply('❗Бот был остановлен из-за капчи. Пожалуйста, попробуйте ещё раз и пройдите капчу на instagram.com')
        user_data.parsing = False
        
        return False
    
    # Get followers ID's and append into the usernames export_data
    if user_data.mode == "followers":
        followers_id = user_data.cl.user_followers_v1(target_id['pk'])
    else:
        followers_id = user_data.cl.user_following_v1(target_id['pk'])

    with open('data.csv', 'w', encoding='utf-8', newline='') as file:
        data = csv.writer(file, delimiter=',', lineterminator='\n')
        data.writerow(['username', 'bio', 'followers_count', 'following_count', 'full_name'])

        try:
            for follower in followers_id:
                if user_data.parsing:
                    try:
                        full_info = user_data.cl.user_info_by_username_v1(follower.username)
                    except Exception as e:
                        print(f"Captcha: {e}")
                        msg.reply("❗<b>Неизвестная ошибка при попытке получить данные с пользователя\n\nВозможные проблемы:\n- Слишком много запросов. Попробуй позже\n- Капча. Проверь instagram.com</b>\n\nПосле прохождения не забудьте проверить /stats")
                        user_data.captcha = True
                        pass

                    user_data.captcha = False

                    info_username = full_info.username.strip()
                    bio = full_info.biography.strip()
                    follower_count = full_info.follower_count
                    following_count = full_info.following_count
                    full_name = full_info.full_name.strip()

                    data.writerow(['https://instagram.com/' + info_username, bio.replace('\n', ''), follower_count, following_count, full_name])

                    user_data.count += 1
                    print(f'\rScraped: {user_data.count}', end='', flush=True)
                else:
                    return True

        except Exception as e:
            print(f"Probably Captcha: {e}")
            user_data.captcha = True
            msg.reply("❗<b>Неизвестная ошибка при попытке получить данные с пользователя\n\nВозможные проблемы:\n- Слишком много запросов. Попробуй позже\n- Капча. Проверь instagram.com</b>\n\nПосле прохождения не забудьте проверить /stats")
            pass
    print("Parser has stop his work!")
    return True


async def main():
    print("Bot started")
    await dp.start_polling(bot)
    print("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
