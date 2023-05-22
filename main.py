import requests
import telebot
import random
from telebot import types

bot = telebot.TeleBot('ключ бота')  # Объект телеграм бота
URl_P2P = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
URl_filt = 'https://p2p.binance.com/bapi/c2c/v2/public/c2c/adv/filter-conditions'

'''Параметры для POST запросов'''
PAYLOAD = {
    "asset": "USDT",
    "fiat": "",
    "merchantCheck": False,
    "page": 1,
    "payTypes": [],
    "publisherType": None,
    "rows": 10,
    "tradeType": "",
    "transAmount": ""
}

'''Хедеры для запросов'''
HEADERS_P2P = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "cache-control": "no-cache",
    "connection": "keep-alive",
    "content-length": "139",
    "content-type": "application/json",
    "host": "p2p.binance.com",
    "origin": "https://p2p.binance.com",
    "pragma": "no-cache",
    "te": "Trailers",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.114 YaBrowser/22.9.1.1095 Yowser/2.5 Safari/537.36"
}


class OFFER(object):  # Класс предложения с Binance
    '''Класс предложения покупки/продажи на Binance P2P'''

    def __init__(self, price, monthOrderCount, monthFinishRate, nickName, limitMin, limitMax):
        self.price = float(price)  # Цена за один токен
        self.monthOrderCount = monthOrderCount  # Количество сделок у создателя оффера за месяц
        self.monthFinishRate = monthFinishRate  # Процент успешных сделок за месяц
        self.nickName = nickName  # Ник создателя оффера
        self.limitMin = limitMin  # Минимальный предел в токенах
        self.limitMax = limitMax  # Максимальный предел в токенах

    ''' Функция, выводящая основные параметры сделки'''

    def get_params(self):
        return 'Price:' + str(self.price) + '\nNick:' + self.nickName + '\nAmount of orders:' + str(
            self.monthOrderCount) + '\nRate: ' + str(
            round(self.monthFinishRate * 100, 2)) + '%'


def get_offers(url, headers, payload):
    '''Функция получения данных о предложениях. Возвращает список объектов класса OFFER'''

    offers = []
    response = requests.post(url, headers=headers, json=payload).json()
    for i in range(3):
        offers.append(OFFER(response['data'][i]['adv']['price'], response['data'][i]['advertiser']['monthOrderCount'],
                            response['data'][i]['advertiser']['monthFinishRate'],
                            response['data'][i]['advertiser']['nickName'],
                            response['data'][i]['adv']['minSingleTransAmount'],
                            response['data'][i]['adv']['dynamicMaxSingleTransAmount']))
    return offers


def get_unistream_price(amount):
    '''Функция получения стоимости перевода определенного количества UZS в рублях. В качестве параметра принимает
    количество UZS. Возвращает стоимость в рублях.'''

    payload = {
        'senderBankId': 361934,
        'acceptedCurrency': 'RUB',
        'withdrawCurrency': 'UZS',
        'amount': amount,
        'countryCode': 'UZB'
    }
    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "ru",
        "connection": "keep-alive",
        "content-length": "92",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "origin": "https://unistream.ru",
        "user-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.114 YaBrowser/22.9.1.1095 Yowser/2.5 Safari/537.36"
    }
    url = 'https://api6.unistream.com/api/v1/transfer/calculate'  # Ссылка на расчет стоимости перевода UZS в рублях
    price = float(requests.post(url, headers=headers, data=payload).json()['fees'][0]['acceptedAmount'])
    return price


def change_payload(payload, fiat, tradeType, transAmount, payTypes):  # Функция для подстановки значений в пэйлоад
    payload["fiat"], payload["tradeType"], payload["transAmount"], payload[
        "payTypes"] = fiat, tradeType, transAmount, payTypes


def create_keyboard(buttons, data=None, width=1):
    ''' Функция создания кнопок под сообщениями '''
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keys = []
    for i in range(len(buttons)):
        if data is None:
            callback_data = buttons[i].lower()
        else:
            callback_data = data[i]
        key = types.InlineKeyboardButton(text=buttons[i].upper(), callback_data=callback_data)
        keys.append(key)
        if len(keys) == width:
            keyboard.row(*keys)
            keys = []
    return keyboard


@bot.message_handler(commands=['p2p'])
def p2p(message):
    keyboard = create_keyboard(['buy', 'sell'], width=2)
    bot.send_message(message.chat.id, text='Choose offer type', reply_markup=keyboard)  # Вызывается ф-я callback_worker


payTypes = []
payTypeNames = []


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    '''Функция обработки нажатий на кнопки для получения определенного предложения на P2P Binance'''

    global payTypes, payTypeNames
    trade_types = ['buy', 'sell']
    cryptocurrencies = ['usdt', 'btc', 'busd', 'bnb', 'eth']
    fiats = ['rub', 'uzs', 'usd', 'eur']
    p2p_payload = PAYLOAD

    def get_amount(message):
        ''' Функция обработки последнего этапа, при котором должна вводиться сумма покупки/продажи и выводиться сами сделки'''

        if message.text.isdigit():
            p2p_payload['transAmount'] = message.text
            offers = get_offers(URl_P2P, HEADERS_P2P, p2p_payload)
            for offer in offers:
                bot.send_message(message.chat.id, offer.get_params())
            payTypes, payTypeNames = [], []
        else:
            keyboard = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, text='Invalid amount\nPlease, enter the amount in ' + p2p_payload[
                'fiat'].lower() + ' again',
                             reply_markup=keyboard)
            bot.register_next_step_handler(message, get_amount)

    '''В зависимости от содержания ответа данные записываются в период по нужному ключу, формируется новая клавиатура 
    с кнопками и отправляется сообщение с этими кнопками '''
    if call.data in trade_types:
        p2p_payload['tradeType'] = call.data.upper()
        payTypes, payTypeNames = [], []
        keyboard = create_keyboard(cryptocurrencies, width=2)
        bot.send_message(call.message.chat.id, text='Choose cryptocurrency', reply_markup=keyboard)
    if call.data in cryptocurrencies:
        p2p_payload['asset'] = call.data.upper()
        payTypes, payTypeNames = [], []
        keyboard = create_keyboard(fiats, width=2)
        bot.send_message(call.message.chat.id, text='Choose fiat', reply_markup=keyboard)
    if call.data in fiats:
        p2p_payload['fiat'] = call.data.upper()
        payTypes, payTypeNames = [], []
        resp_payload = {'fiat': p2p_payload['fiat']}
        response = requests.post(URl_filt, headers=HEADERS_P2P, json=resp_payload).json()
        for i in range(4):
            payTypes.append(response['data']['tradeMethods'][i]['identifier'])
            payTypeNames.append(response['data']['tradeMethods'][i]['tradeMethodName'])
        keyboard = create_keyboard(payTypeNames, data=payTypes, width=2)
        bot.send_message(call.message.chat.id, text='Choose pay type', reply_markup=keyboard)
    if call.data in payTypes:
        p2p_payload['payTypes'] = [call.data]
        keyboard = types.ReplyKeyboardRemove()
        bot.send_message(call.message.chat.id, text='Enter the amount in ' + p2p_payload['fiat'],
                         reply_markup=keyboard)
        bot.register_next_step_handler(call.message, get_amount)


@bot.message_handler(commands=['unistream'])
def unistream(message):  # Вывод спреда и данных о нужных офферах
    ''' Функция обработки команды /unistream. Получает стоимость в рублях перевода узбекских сум в количестве amount_uzs,
    получает выручку с продажи USDT и рассчитывает прибыль'''

    bot.send_message(message.from_user.id, 'Wait a second...')
    amount_uzs = 7000000
    change_payload(PAYLOAD, 'UZS', 'BUY', str(amount_uzs), ['Humo'])
    offers_uzs = get_offers(URl_P2P, HEADERS_P2P, PAYLOAD)  # Получение предложений купить USDT за UZS
    change_payload(PAYLOAD, 'RUB', 'SELL', '50000', ['RosBankNew'])
    offers_rub = get_offers(URl_P2P, HEADERS_P2P, PAYLOAD)  # Получение предложений продать USDT за RUB
    price_uni = get_unistream_price(amount_uzs)  # Получение стоимости перевода через Unistream
    sell_price = round((amount_uzs / offers_uzs[0].price) * offers_rub[0].price, 2)  # Расчет выручки
    spread = round(sell_price - price_uni, 2)  # Расчет спреда (чистой прибыли/убытка)
    if spread <= 150:
        sticker = ' ⛔️'
    elif 150 < spread <= 400:
        sticker = ' ✅'
    elif 400 < spread <= 650:
        sticker = ' ✅✅'
    else:
        sticker = ' ✅✅✅'
    bot.send_message(message.from_user.id,
                     'Purchase price usdt: ' + str(price_uni) + '\nAmount from sale usdt: ' + str(
                         sell_price) + '\nSpread: ' + str(spread) + sticker)
    bot.send_message(message.from_user.id, 'BUY\n' + offers_uzs[0].get_params())
    bot.send_message(message.from_user.id, 'SALE\n' + offers_rub[0].get_params())


@bot.message_handler(commands=['aboutme'])  # Функция обработки команды /aboutme (Вывод информации о функционале бота)
def aboutme(message):
    bot.send_message(message.from_user.id,
                     "I can calculate the cryptocurrency arbitrage spread or show you the p2p offer you are "
                     "interested in\n\nThe /unistream command calculates the cryptocurrency arbitrage spread "
                     "through the Unistream payment system for 9000000uzs(≈50000rub)\n\nThe /p2p command finds an "
                     "offer according to the given parameters: deal type, cryptocurrency, payment currency, "
                     "quantity\n\nThe /help command tells you where to go for help")


@bot.message_handler(commands=['help'])  # Функция обработки команды /help
def aboutme(message):
    bot.send_message(message.from_user.id,
                     "Use /aboutme to get general information\nIf you have a question or found any error, please, write me down\n@berezhok02")


@bot.message_handler(content_types=['sticker'])  # Функция обработки стикеров
def get_sticker_messages(message):
    stickers = ['CAACAgIAAxkBAAIP_GNBdSeQoUINwJzmsiuwo9ucR9vjAAKbFQACJ6BRSrfN9j1Fhf5GKgQ',
                'CAACAgIAAxkBAAIP_mNBdZ1YKxXbdLxYEQ2WkeWINyyjAAJXEwACsdrYSxCdi3yCDx7WKgQ',
                'CAACAgIAAxkBAAIQAAFjQXWg0waxP18X899VK2uo6fCddwACPAIAAlwohgi44TcbWzCeGSoE',
                'CAACAgIAAxkBAAIQAmNBdovopS-RCWxmLQZSva7F525ZAAKCFAACQE_ZS5SP1IxG2z-OKgQ',
                'CAACAgIAAxkBAAIQBGNBdpaBzWzou2zLRd7wn5zo-8wlAAIJFQACKC_ZS7d5clm5aoKgKgQ',
                'CAACAgIAAxkBAAIQL2NDIrveFN45dFTKAAGNK6XFHE-G3AACXQAD98zUGAfjoR2AuAw-KgQ',
                'CAACAgIAAxkBAAIQM2NDIs2bha4QbCLlcAnFbf12NSa0AAKnAAP3zNQYZ_LXKaDC-3wqBA']
    bot.send_sticker(message.from_user.id, random.choice(stickers))


@bot.message_handler(content_types=['text'])  # Функция обработки остальных сообщений
def get_text_messages(message):
    greetings = ['ПРИВЕТ', 'ХАЙ', 'HELLO', 'HI', 'ЗДАРОВА', 'START', 'GO', 'BEGIN']
    if message.text.upper() in greetings or message.text == '/start':
        bot.send_message(message.from_user.id,
                         f"Hello, {message.from_user.first_name}! 👋\nWrite /aboutme to find out what I can")
    else:
        bot.send_message(message.from_user.id,
                         "Sorry, I don't understand you\nPlease, use commands:\n/aboutme\n/unistream\n/p2p\n/help")


bot.polling(none_stop=True, interval=0)
