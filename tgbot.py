#импорт библиотек (предварительно установить их через pip (читай readme.txt)
import requests
from lxml import html
import urllib.request
from pdf2image import convert_from_path, convert_from_bytes
import cv2
import numpy as np
import datetime

#счётчик ошибок
e_counter = 0


#Функция обновления расписания
def update(chat_id):
    page = requests.get('https://phtt.ru/raspisanie_zanyatiy/')
    webpage = html.fromstring(page.content)
    link = webpage.xpath('//*[@id="content_contaner"]/div/div/table[1]/tbody/tr[1]/td[4]/a/@href')
    link = link[0]
    #Сравниваем дату расписнание с завтрашней
    current_datetime = datetime.datetime.now() + datetime.timedelta(days = 1)
    date = str(current_datetime.date()).split('-')[2] + '_' + str(current_datetime.date()).split('-')[1]
    #проверяет подходит ли правое расписание,
    print(link.find(date))

    #сравнивает два расписания и выбирает
    if link.find(date) != -1:
        #если подходит то берёт его
        link = 'https://phtt.ru/' + link
        pdf = urllib.request.urlretrieve(link, "timetable.pdf")
        png = convert_from_path(r'timetable.pdf', 500)
        png[0].save('out.png', 'PNG')
        png = cv2.imread('out.png')
        #вырезает расписание нужной группы
        crop = png[416:4037, 48:570]
        cv2.imwrite('timetable.png', crop)
        bot.send_message(chat_id, 'Расписание обновлено')
    link = webpage.xpath('//*[@id="content_contaner"]/div/div/table[1]/tbody/tr[1]/td[1]/a/@href')
    link = link[0]
    link = 'https://phtt.ru/' + link
    #Проверяет левое
    if link.find(date) != -1:
        pdf = urllib.request.urlretrieve(link, "timetable.pdf")
        png = convert_from_path(r'timetable.pdf', 500)
        png[0].save('out.png', 'PNG')
        png = cv2.imread('out.png')
        # вырезает расписание нужной группы
        crop = png[416:4037, 48:570]
        cv2.imwrite('timetable.png', crop)
        bot.send_message(chat_id, 'Расписание обновлено')
    else:
        bot.send_message(chat_id, 'Расписания на завтра на сайте пока что нету')


#читает базу пользователей, и создаёт словарь (user_id:group)
dictionary = {}
a = open(r'user_data.txt', 'r')
for line in a:
    key, value = line.split(':')
    dictionary[key] = value[:-1]


#функция подсчёта времени до звонка
def zvonok():
    # переводит настоящее время в секунды
    current_datetime = datetime.datetime.now()
    current_time = (current_datetime.hour * 60 * 60 + current_datetime.minute * 60 + current_datetime.second)
    # в массиве все звонки (кол-во секунд прошедших с 00:00 (Например если звонок в 8:00, то в массиве будет 28800))
    schedule = [31500, 34200, 34500, 37200, 38400, 41100, 41400, 44100, 45900, 48600, 48900, 51600, 52200, 54900, 55200, 57900, 58500, 61200, 61500, 64200, 64800, 67200, 67500, 69900, 70500, 72900, 73200, 75600]
    schedule = np.array(schedule)
    # заменяет все прошедшие звонки на 0
    schedule = np.where(schedule > current_time, schedule, schedule*0)
    # отбрасывает нули
    lost_ring = [i for i in schedule if i != 0 ]
    # приводит время  нормальному виду
    minutes = str((lost_ring[0] - current_time) // 60)
    secundes = str((lost_ring[0] - current_time) % 60)
    # добавляет нолик перед однозначной секундой что бы красиво
    if len(secundes) == 1:
        secundes = ('0'+ secundes)
    # возвращает время оставшееся до звонка
    lost_time = minutes + ':' + secundes
    return lost_time
# функция добавления новых пользователей в базу (TODO: переписать под sql)
def add_to_base(chat_id, group):
    global dictionary
    # открывает файл который хочет изменить
    joinedFile = open(r'user_data.txt', 'r')
    joinedUsers = set()
    for line in joinedFile:
        joinedUsers.add(line.strip())
    joinedFile.close()
    joinedFile = open(r'user_data.txt', 'a')
    # делит строки
    joinedFile.write((str(chat_id) + ':' + group) + '\n')
    joinedUsers.add((str(chat_id) + ':' + group))
    # закидывает в словарь
    dictionary = {}
    a = open(r'user_data.txt', 'r')
    for line in a:
        key, value = line.split(':')
        dictionary[key] = value[:-1]
    dictionary[str(chat_id)] = group
    # логи
    print('[{}]   Database update'.format(datetime.datetime.now()))
    return(dictionary)

# начинается сам бот
import telebot
from telebot import types


bot = telebot.TeleBot('токен должен быть тут') # в '' должен быть токен бота, взять у @BotFather
# ответ на запуск бота
@bot.message_handler(commands=['start'])
def welcome(message):
    # создаёт кнопки выбора группы
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("ИБ-21", callback_data='ИБ-21')
    item2 = types.InlineKeyboardButton("other", callback_data='other')

    markup.add(item1, item2)

    bot.send_message(message.chat.id, 'Выбери группу', reply_markup=markup)
# обрабатывает выбор группы
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.message:
            # добавляет в базу uid и группу
            if call.data == 'ИБ-21':
                add_to_base(call.message.chat.id, 'ИБ-21')
            elif call.data == 'other':
                add_to_base(call.message.chat.id, 'other')
            # заменяет сообщение с кнопками
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Группа выбрана",
                                  reply_markup=None)

            # показывает алёрт
            bot.answer_callback_query(callback_query_id=call.id, show_alert=False,
                                      text="Что бы изменить выбор перезапусти бота.")
            # добавляет основные кнопки
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton('Когда звонок?')
            item2 = types.KeyboardButton('Расписание на завтра')
            item3 = types.KeyboardButton('Обновить расписание')
            markup.add(item3, item2, item1,)
            bot.send_message(call.message.chat.id, 'Теперь можешь использовать кнопки', reply_markup=markup)
            print('[{}]   New user!'.format(datetime.datetime.now()))
    except Exception as e:
        # принтит ошибки если они есть
        print(e)
# обрабатывает основные кнопки
@bot.message_handler(content_types=['text'])
def calculator(message):
    if message.chat.type == 'private':
        # реакция на кнопку звонка
        if message.text == 'Когда звонок?':
            bot.send_message(message.chat.id, ('Звонок через: '+ str(zvonok())) )
            print('[{}]   Somebody check bell'.format(datetime.datetime.now()))
        # реакция на кнопку расписания
        elif message.text == 'Расписание на завтра':
            # ответ зависит от выбранной группы
            if dictionary[str(message.chat.id)] == 'ИБ-21':
                bot.send_photo(message.chat.id, photo=open(r'timetable.png', 'rb'))
                print('[{}]   Somebody check timetable ИБ-21'.format(datetime.datetime.now()))
            if dictionary[str(message.chat.id)] == 'other':
                bot.send_photo(message.chat.id, photo=open(r'out.png', 'rb'))
                print('[{}]   Somebody check timetable other'.format(datetime.datetime.now()))
        # реакция на обновление расписания
        elif message.text == 'Обновить расписание':
            update(message.chat.id)
            print('[{}]   Somebody update timetable'.format(datetime.datetime.now()))
        # реакция на непредвиденные сообщения
        else:
            bot.send_message(message.chat.id, 'Ну тут же есть кнопки, зачем ты что-то сюда пишешь?')
            print('[{}]   Somebody idiot'.format(datetime.datetime.now()))
while True:
    try:
        #запусает бота
        bot.polling(none_stop=True)
    except  Exception as e:
        print(e)
        e_counter += 1
        print('Бот упал {} раз.'.format(e_counter))
