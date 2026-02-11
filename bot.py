import telebot
import requests
from bs4 import BeautifulSoup
import openai
import re
import time
from telebot import types


TELEGRAM_TOKEN = ''
OPENAI_API_KEY = ''
UNIVERSITY_URL = 'https://alt.edu.kz'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY


user_language = {}
user_awaiting_ai = {}


LANG = {
    'ru': {
        'welcome': "🎓 Добро пожаловать в ИИ-гид по ALT UNIVERSITY!\n\nВыберите язык:",
        'lang_selected': "✅ Язык установлен: Русский",
        'menu': [["Об университете", "Институты", "Поступление"], ["Контакты", "Новости", "Спросить ИИ"]],
        'about': "🏛️ *Об университете*\nALT UNIVERSITY — главный транспортно-коммуникационный вуз Казахстана и стран Центральной Азии. [[1]]\n\nСпециализируется на подготовке кадров в сферах:\n• IT и телекоммуникации\n• Логистика и управление\n• Транспортная инженерия\n• Энергетика и строительство",
        'institutes': "📚 *Институты университета:*\n",
        'admission': "📝 *Поступление*\nБакалавриат, магистратура, докторантура.\n42 образовательные программы.\nПрезидентско-ректорские гранты доступны.\n\nПодробнее: https://alt.edu.kz/ru/postupayushhim/",
        'contacts': "📞 *Контакты*\n📍 г. Алматы, ул. Шевченко, 97\n📱 +7 (727) 292-43-60\n📧 info@alt.edu.kz\n🌐 https://alt.edu.kz",
        'news': "📰 *Последние новости*\nСледите за актуальными новостями на сайте:\nhttps://alt.edu.kz/ru/",
        'ask_ai': "🤖 Напишите ваш вопрос об университете:",
        'no_info': "Информация временно недоступна.",
        'processing': "⏳ Ищу информацию на сайте университета...",
        'back': "🔙 Назад"
    },
    'kk': {
        'welcome': "🎓 ALT UNIVERSITY ИИ-гидіне қош келдіңіз!\n\nТілді таңдаңыз:",
        'lang_selected': "✅ Тіл орнатылды: Қазақша",
        'menu': [["Университет туралы", "Институттар", "Түсу"], ["Байланыс", "Жаңалықтар", "ИИ-дан сұрау"]],
        'about': "🏛️ *Университет туралы*\nALT UNIVERSITY — Қазақстанның және Орталық Азия елдерінің басты көлік-коммуникациялық жоғары оқу орны. [[1]]\n\nМамандандыру салалары:\n• IT және телекоммуникациялар\n• Логистика және басқару\n• Көлік инженериясы\n• Энергетика және құрылыс",
        'institutes': "📚 *Университет институттары:*\n",
        'admission': "📝 *Түсу*\nБакалавриат, магистратура, докторантура.\n42 білім беру бағдарламасы.\nПрезидент–Ректор гранттары бар.\n\nТолығырақ: https://alt.edu.kz/kk/postupayushhim/",
        'contacts': "📞 *Байланыс*\n📍 Алматы қаласы, Шевченко көшесі, 97\n📱 +7 (727) 292-43-60\n📧 info@alt.edu.kz\n🌐 https://alt.edu.kz",
        'news': "📰 *Соңғы жаңалықтар*\nЖаңалықтарды сайтта көріңіз:\nhttps://alt.edu.kz/kk/",
        'ask_ai': "🤖 Университет туралы сұрағыңызды жазыңыз:",
        'no_info': "Ақпарат уақытша қолжетімсіз.",
        'processing': "⏳ Университет сайтынан ақпарат іздеймін...",
        'back': "🔙 Артқа"
    }
}


# === ПАРСЕР САЙТА ALT UNIVERSITY (ИСПРАВЛЕННЫЙ) ===
def fetch_university_data():
    """Собирает данные с сайта ALT University"""
    data = {'ru': {}, 'kk': {}}

    # Структура институтов (из официального сайта)
    institutes = [
        {
            'name_ru': 'Институт «Энергетика и цифровые технологии»',
            'name_kk': '«Энергетика және цифровық технологиялар» институты',
            'url': '/ru/instituty/energetika-i-cifrovye-tehnologii/'
        },
        {
            'name_ru': 'Институт «Логистика и бизнес»',
            'name_kk': '«Логистика және бизнес» институты',
            'url': '/ru/instituty/logistika-i-upravlenie/'
        },
        {
            'name_ru': 'Институт «Транспорт и строительство»',
            'name_kk': '«Көлік және құрылыс» институты',
            'url': '/ru/instituty/transport-i-stroitelstvo/'
        },
        {
            'name_ru': 'Институт «Базовое и дистанционное образование»',
            'name_kk': '«Негізгі және қашықтан білім беру» институты',
            'url': '/ru/instituty/bazovoe-i-distantsionnoe-obrazovanie/'
        }
    ]

    data['ru']['institutes'] = institutes
    data['kk']['institutes'] = institutes

    # Контакты (фиксированные — с сайта)
    contacts = {
        'phone': '+7 (727) 292-43-60',
        'email': 'info@alt.edu.kz',
        'address_ru': 'г. Алматы, ул. Шевченко, 97',
        'address_kk': 'Алматы қаласы, Шевченко көшесі, 97'
    }

    data['ru']['contacts'] = contacts
    data['kk']['contacts'] = contacts

    return data


# Кэш данных
_cache = {'data': None, 'time': 0}


def get_university_data():
    now = time.time()
    if _cache['data'] is None or now - _cache['time'] > 3600:  # обновлять раз в час
        _cache['data'] = fetch_university_data()
        _cache['time'] = now
    return _cache['data']


# === СИСТЕМНЫЕ ПРОМПТЫ ДЛЯ OPENAI ===
SYSTEM_PROMPT_RU = """Ты — официальный ИИ-гид ALT UNIVERSITY (Алматы, Казахстан). Отвечай ТОЛЬКО на русском языке.

Контекст университета:
- Полное название: Мухамеджан Тынышпаев атындағы ALT университеті / ALT University named after Mukhametzhan Tynyshbayev
- Специализация: транспорт, логистика, телекоммуникации, IT, энергетика, строительство
- Институты: Энергетика и цифровые технологии, Логистика и бизнес, Транспорт и строительство, Базовое и дистанционное образование
- Адрес: г. Алматы, ул. Шевченко, 97
- Телефон: +7 (727) 292-43-60
- Сайт: https://alt.edu.kz

Правила:
1. Отвечай ТОЛЬКО на вопросы об университете
2. Если информации нет — скажи: "Эта информация не указана на официальном сайте. Рекомендую уточнить по телефону +7 (727) 292-43-60"
3. Всегда упоминай официальный сайт для проверки: https://alt.edu.kz
4. Будь вежливым, кратким и точным
5. НЕ выдумывай информацию"""

SYSTEM_PROMPT_KK = """Сен — ALT UNIVERSITY (Алматы, Қазақстан) ресми ИИ-гиді. ТЕК қазақ тілінде жауап бер.

Университет контексті:
- Толық атауы: Мұхамеджан Тынышбаев атындағы ALT университеті
- Мамандандыру: көлік, логистика, телекоммуникациялар, IT, энергетика, құрылыс
- Институттар: Энергетика және цифровық технологиялар, Логистика және бизнес, Көлік және құрылыс, Негізгі және қашықтан білім беру
- Мекенжай: Алматы қаласы, Шевченко көшесі, 97
- Телефон: +7 (727) 292-43-60
- Сайт: https://alt.edu.kz

Ережелер:
1. Университет туралы СҰРАҚТАРҒА ғана жауап бер
2. Ақпарат жоқ болса: "Бұл ақпарат ресми сайтта көрсетілмеген. +7 (727) 292-43-60 нөміріне хабарласып сұраңыз"
3. Әрқашан ресми сайтқа сілтеме бер: https://alt.edu.kz
4. Әдепті, қысқа және дәл бол
5. Ақпаратты өзіңнен шығарма"""


# === МЕНЮ ===
def create_lang_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        types.InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kk")
    )
    return markup


def create_main_menu(lang):
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    for row in LANG[lang]['menu']:
        markup.add(*[types.KeyboardButton(text) for text in row])
    return markup


# === ОБРАБОТЧИКИ ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🎓 ALT UNIVERSITY ИИ-гидіне қош келдіңіз!\n\nВыберите язык / Тілді таңдаңыз:",
        reply_markup=create_lang_menu()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    user_id = call.from_user.id
    lang = call.data.split('_')[1]  # lang_ru → ru
    user_language[user_id] = lang

    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=LANG[lang]['lang_selected']
    )

    bot.send_message(
        call.message.chat.id,
        "✅ Меню готово!" if lang == 'ru' else "✅ Мәзір дайын!",
        reply_markup=create_main_menu(lang)
    )


@bot.message_handler(func=lambda msg: msg.text in ["Об университете", "Университет туралы"])
def about(msg):
    lang = user_language.get(msg.from_user.id, 'ru')
    bot.send_message(msg.chat.id, LANG[lang]['about'], parse_mode='Markdown')


@bot.message_handler(func=lambda msg: msg.text in ["Институты", "Институттар"])
def institutes(msg):
    lang = user_language.get(msg.from_user.id, 'ru')
    data = get_university_data()
    institutes_list = data.get(lang, {}).get('institutes', [])

    if institutes_list:
        text = LANG[lang]['institutes']
        for i, inst in enumerate(institutes_list, 1):
            name = inst[f'name_{lang}'] if lang == 'kk' else inst['name_ru']
            text += f"\n{i}. {name}"
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, LANG[lang]['no_info'])


@bot.message_handler(func=lambda msg: msg.text in ["Поступление", "Түсу"])
def admission(msg):
    lang = user_language.get(msg.from_user.id, 'ru')
    bot.send_message(msg.chat.id, LANG[lang]['admission'], parse_mode='Markdown', disable_web_page_preview=False)


@bot.message_handler(func=lambda msg: msg.text in ["Контакты", "Байланыс"])
def contacts(msg):
    lang = user_language.get(msg.from_user.id, 'ru')
    data = get_university_data()
    cont = data.get(lang, {}).get('contacts', {})

    if cont:
        text = LANG[lang]['contacts']
        bot.send_message(msg.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(msg.chat.id, LANG[lang]['no_info'])


@bot.message_handler(func=lambda msg: msg.text in ["Новости", "Жаңалықтар"])
def news(msg):
    lang = user_language.get(msg.from_user.id, 'ru')
    bot.send_message(msg.chat.id, LANG[lang]['news'], parse_mode='Markdown', disable_web_page_preview=False)


@bot.message_handler(func=lambda msg: msg.text in ["Спросить ИИ", "ИИ-дан сұрау"])
def ask_ai(msg):
    user_id = msg.from_user.id
    lang = user_language.get(user_id, 'ru')
    user_awaiting_ai[user_id] = True

    bot.send_message(msg.chat.id, LANG[lang]['ask_ai'])


@bot.message_handler(func=lambda msg: user_awaiting_ai.get(msg.from_user.id, False))
def process_ai(msg):
    user_id = msg.from_user.id
    lang = user_language.get(user_id, 'ru')
    del user_awaiting_ai[user_id]  # Выходим из режима ожидания

    bot.send_chat_action(msg.chat.id, 'typing')
    bot.send_message(msg.chat.id, LANG[lang]['processing'])

    # Получаем ответ от OpenAI
    try:
        system_prompt = SYSTEM_PROMPT_RU if lang == 'ru' else SYSTEM_PROMPT_KK

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": msg.text}
            ],
            temperature=0.3,
            max_tokens=400
        )

        answer = response.choices[0].message['content']
        bot.send_message(msg.chat.id, answer)
    except Exception as e:
        error_msg = f"❌ Ошибка OpenAI: {str(e)}\n\nПопробуйте позже или свяжитесь с поддержкой."
        bot.send_message(msg.chat.id, error_msg)

    # Возвращаем меню
    bot.send_message(msg.chat.id, "✅ Вернулись в меню", reply_markup=create_main_menu(lang))


# === ЗАПУСК ===
if __name__ == '__main__':
    print("🚀 ALT UNIVERSITY ИИ-гид (руский + қазақша) ЗАПУЩЕН!")

    bot.polling(none_stop=True)