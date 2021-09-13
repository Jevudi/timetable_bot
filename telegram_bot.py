from pdf2image import convert_from_path, convert_from_bytes
from telebot import types
import requests
from lxml import html
import urllib.request
import cv2
import numpy as np
import datetime
import telebot

e_counter = 0  # счётчик ошибок


# обновление расписания
def update_timetable(chat_id):
    page = requests.get('https://phtt.ru/raspisanie_zanyatiy/')
    webpage = html.fromstring(page.content)
    link = webpage.xpath('//*[@id="content_contaner"]/div/div/table[1]/tbody/tr[1]/td[4]/a/@href')
    link = link[0]
    
    # сравнение даты расписания с завтрашней
    current_datetime = datetime.datetime.now() + datetime.timedelta(days = 1)
    date = str(current_datetime.date()).split('-')[2] + '_' + str(current_datetime.date()).split('-')[1]
   
    print(link.find(date))  # проверка правого расписания

    # сравнение двух расписаний и выбор нужного
    if link.find(date) != -1:  # если подходит, то берёт его
        link = 'https://phtt.ru/' + link
        pdf = urllib.request.urlretrieve(link, "timetable.pdf")
        png = convert_from_path(r'timetable.pdf', 500, poppler_path=r'')  # в '' путь до poopler'a
        png[0].save('out.png', 'PNG')
        png = cv2.imread('out.png')
                                
        # вырезает расписание нужной группы
        crop = png[416:4037, 48:570]
        cv2.imwrite('timetable.png', crop)
        bot.send_message(chat_id, 'Расписание обновлено')
                                
    link = webpage.xpath('//*[@id="content_contaner"]/div/div/table[1]/tbody/tr[1]/td[1]/a/@href')
    link = link[0]
    link = 'https://phtt.ru/' + link
                                
    # проверка левого расписания
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


# читает базу пользователей, и создаёт словарь (user_id:group)
dictionary = {}

a = open(r'user_data.txt', 'r')
for line in a:
    key, value = line.split(':')
    dictionary[key] = value[:-1]


# подсчёт времени до звонка
def calling():
    # переводит настоящее время в секунды
    current_datetime = datetime.datetime.now()
    current_time = (current_datetime.hour * 60 * 60 + current_datetime.minute * 60 + current_datetime.second)
    
    # массив со всеми возможными звонками, выраженных в секундах
    schedule = [31500, 34200, 34500, 37200, 38400, 41100, 41400, 44100, 45900, 48600, 48900, 51600, 52200, 54900, 55200, 57900, 58500, 61200, 61500, 64200, 64800, 67200, 67500, 69900, 70500, 72900, 73200, 75600]
    schedule = np.array(schedule)
            
    schedule = np.where(schedule > current_time, schedule, schedule*0)  # заменяет все прошедшие звонки на 0
    lost_ring = [i for i in schedule if i != 0 ]  # отбрасывает нули
                                
    # переводит время в минуты
    minutes = str((lost_ring[0] - current_time) // 60)
    secundes = str((lost_ring[0] - current_time) % 60)
                                
    # добавляет нолик перед однозначной секундой чтобы было красиво
    if len(secundes) == 1:
        secundes = ('0'+ secundes)
                                
    # возвращает время оставшееся до звонка
    lost_time = minutes + ':' + secundes
    return lost_time
                                

# добавление новых пользователей в базу
# TODO: переписать под sql
def add_to_base(chat_id, group):
    global dictionary
    joinedUsers = set()
                                
    joinedFile = open(r'user_data.txt', 'r')  # открывает файл для чтения 
    for line in joinedFile:
        joinedUsers.add(line.strip())
    joinedFile.close()
                            
    joinedFile = open(r'user_data.txt', 'a')  # открывает файл для изменения и делит строки
    joinedFile.write((str(chat_id) + ':' + group) + '\n')
    joinedUsers.add((str(chat_id) + ':' + group))
                                
    # добавление строк в словарь
    dictionary = {}
    a = open(r'user_data.txt', 'r')
    for line in a:
        key, value = line.split(':')
        dictionary[key] = value[:-1]
    dictionary[str(chat_id)] = group
                                
    print('[{}]   Database update'.format(datetime.datetime.now()))  # логи
                                
    return(dictionary)

                                
# начинается сам бот
bot = telebot.TeleBot('')  # в '' должен быть токен бота (взять у @BotFather)

                                
# ответ на запуск бота
@bot.message_handler(commands=['start'])
def welcome(message):
    # созание кнопок для выбора группы
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton("ИБ-21", callback_data='ИБ-21')
    item2 = types.InlineKeyboardButton("other", callback_data='other')

    markup.add(item1, item2)

    bot.send_message(message.chat.id, 'Выбери группу', reply_markup=markup)
                                
                                
# обработка выбора группы
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
                                
            print('[{}]   New user!'.format(datetime.datetime.now()))  # логи
    except Exception as e:
        print(e)  # вывод количества ошибок
                                
                                
# обработка основных кнопок
@bot.message_handler(content_types=['text'])
def calculator(message):
    if message.chat.type == 'private':
        # реакция на кнопку звонка
        if message.text == 'Когда звонок?':
            bot.send_message(message.chat.id, ('Звонок через: '+ str(calling())) )
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
                                
        else:  # реакция на непредвиденные сообщения
            bot.send_message(message.chat.id, 'Ну тут же есть кнопки, зачем ты что-то сюда пишешь?')
            print('[{}]   Somebody idiot'.format(datetime.datetime.now()))  # ахахахахахахахахахахаха :)
                                
                                
while True:
    try:  # запуск бота
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)
        e_counter += 1
        print('Бот упал {} раз.'.format(e_counter))
