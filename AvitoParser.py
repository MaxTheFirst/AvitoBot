from bs4 import BeautifulSoup  # для парсинга старниц
import requests                # для запросов к сайту, получения содержимого веб-страницы
import random
import time
import vk_api
import lxml
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from vk_api import VkUpload
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import os

url_proxies = "https://hidemy.name/ru/proxy-list/?maxtime=500&type=h&anon=4#list"
VERSION = '2.1'

InnerBlock = namedtuple('Block', 'title,price,url_comp,address,description')

class Block(InnerBlock):

    def __str__(self):
        return f'{self.title}\nЦена: {self.price}\nСсылка: {self.url_comp}\nАдрес: {self.address}\nОписание: {self.description}'

class Parser_Avito:
    
    def __init__(self):
        mytoken = os.environ.get('BOT_TOKEN') #Этот токен при загрузке на хостинг лучше убрать
        self.vk_session = vk_api.VkApi(token=mytoken)
        self.session_api = self.vk_session.get_api()
        self.upload = VkUpload(self.vk_session)
        self.longpoll =  VkLongPoll(self.vk_session)
        self.keyboard = VkKeyboard()
        self.keyboard.add_button('Добавить ссылку', color=VkKeyboardColor.PRIMARY)
        self.keyboard.add_line()
        self.keyboard.add_button('Удалить', color=VkKeyboardColor.NEGATIVE)
        self.list_of_users = {}
        self.url_list = []
        self.proxies = ['178.128.143.54:8080']
        with open('uas.txt') as file_uas:
            self.useragents = file_uas.read().split('\n')
        self.count = 0
    
    def parse_proxies(self):
        try:
            html_text = self.download(full_url=url_proxies)
            html = BeautifulSoup(html_text, 'lxml')
            blocks = html.select('div.table_block tr')[:-1]
            self.proxies.clear()
            for block in blocks[1:]:
                texts = block.next_sibling('td')
                self.proxies.append(texts[0].text + ':' + texts[1].text)
            if blocks == [] or self.proxies == []:
                self.proxies = ['178.128.143.54:8080', '46.4.96.137:8080', '5.189.133.231:80']
        except:
            self.proxies = ['178.128.143.54:8080', '46.4.96.137:8080', '5.189.133.231:80']
        print(self.proxies)

    def download(self, full_url):
        useragent = {'User-Agent': random.choice(self.useragents)}
        proxy = {'http': 'http://' + random.choice(self.proxies)}
        print(useragent, proxy)
        r = requests.get(full_url, headers=useragent, proxies=proxy)
        return r.text

    def get_block(self, url_, name):
        text = self.download(full_url=url_)
        soup = BeautifulSoup(text, 'lxml')
        container = soup.select_one(name) 
        if container == None:
            print(text) 
        return container
    
    def parse_block(self, avito_url):
        try:
            self.url_comp = 'https://www.avito.ru/' + self.get_block(url_=avito_url, name='a.iva-item-sliderLink-2hFV_').get('href')
            full_block = self.get_block(url_=self.url_comp, name='div.item-view-content')        
            self.title = full_block.select_one('h1.title-info-title').text.strip()
            self.price = full_block.select_one('div.price-value.price-value_side-card').text.strip()
            self.url_img = full_block.select_one('div.gallery-img-frame.js-gallery-img-frame').get('data-url')        
            self.address = full_block.select_one('span.item-address__string').text.strip()
            self.description = full_block.select_one('div.item-description-text p').text.strip()
        except:
            return '0'
        return Block(title=self.title, price=self.price, url_comp=self.url_comp, address=self.address, description=self.description)

    def send_photo(self, peer_id, url):
        img = requests.get(url).content
        f = BytesIO(img)
        response = self.upload.photo_messages(f)[0]
        owner_id = response['owner_id']
        photo_id = response['id']
        access_key = response['access_key']
        attachment = f'photo{owner_id}_{photo_id}_{access_key}'
        self.session_api.messages.send(
            random_id=get_random_id(),
            peer_id=peer_id,
            attachment=attachment
        )
    
    def sender(self, id, text):
        self.vk_session.method('messages.send', {'user_id' : id, 'message' : text, 'random_id' : get_random_id(), 'keyboard' : self.keyboard.get_keyboard()})

    def send_mess(self):
        for user in self.list_of_users:
            for url_ in self.list_of_users[user]['urls']:
                time.sleep(random.uniform(5, 20))
                self.check()
                mess = self.parse_block(avito_url=url_)
                if mess == '0':
                    self.sender(user, 'Ошибочная ссылка: ' + url_)
                    self.list_of_users[user]['urls'].remove(url_)
                    break
                new_comp = True
                if self.url_comp in self.list_of_users[user]['last_url']:
                    new_comp = False
                if new_comp:
                    print('New!')
                    self.list_of_users[user]['last_url'].append(self.url_comp)
                    self.sender(user, str(mess))
                    self.send_photo(user, self.url_img)
                    if len(self.list_of_users[user]['last_url']) > len(self.list_of_users[user]['urls']) * 3:
                        self.list_of_users[user]['last_url'].pop(0)
                print(str(mess) + '\n')
        
    def check(self):
        print('count', self.count)
        self.count += 1
        if self.count == 100:
            self.count = 0
            self.parse_proxies()

    def vk_mess(self):
        messages = self.vk_session.method("messages.getConversations", {"offset": 0, "count": 20, "filter": "unanswered"})
        if messages["count"] >= 1:
            for i in range(messages["count"]):
                id = messages["items"][i]["last_message"]["from_id"]
                msg = messages["items"][i]["last_message"]["text"]
                if msg.lower() == 'старт':
                    self.sender(id, 'Привет! Если хотите получать рассылку с сайта Avito.ru, то напишите мне "добавить ссылку".')
                elif msg.lower() == 'добавить ссылку':
                    if id not in self.list_of_users:
                        self.list_of_users[id] = { 
                            'urls': [],
                            'last_url': [],
                            'flags': False  
                        }
                    self.list_of_users[id]['flags'] = True
                    self.sender(id, 'Вставте ссылку на интересующие Вас предложения. (Пример: "Ссылка:https://www.avito.ru/")')
                elif msg.lower() == 'удалить':
                    if id in self.list_of_users:
                        del self.list_of_users[id]
                        self.sender(id, 'Теперь вам не будет приходит рассылка с сайта Avito.ru!')
                    else:
                        self.sender(id, 'Вас нет в списке! Если хотите получать рассылку с сайта Avito.ru, то напишите мне "добавить ссылку".')
                elif msg.lower() == 'версия':
                    self.sender(id, VERSION)
                elif id in self.list_of_users:
                    if self.list_of_users[id]['flags'] == True:
                        self.list_of_users[id]['flags'] = False
                        if msg[7:] not in self.list_of_users[id]['urls']:
                            self.list_of_users[id]['urls'].append(msg[7:])
                            mess_string = 'Ваш список ссылок:\n'
                            for i in range(len(self.list_of_users[id]['urls'])):
                                mess_string += str(i+1) + '. ' + self.list_of_users[id]['urls'][i] + '\n'
                            self.sender(id, mess_string + '\nЕсли не хотите получать рассылку, то напишите "удалить".')

    def run(self):
        self.send_mess()
        self.vk_mess()
        self.run()


def main():
    Avito = Parser_Avito()
    Avito.parse_proxies()
    Avito.run()

if __name__ == "__main__":
    main()