import requests
import json
import re
from bs4 import BeautifulSoup


class GeoObject:
    """Объект данных в модели"""

    def __init__(self, address, coord, contacts=None, opening_hours=None, extra=None):
        self.address = address
        self.coord = coord
        self.contacts = contacts
        self.opening_hours = opening_hours
        self.extra = extra

    def export_csv(self):
        return f'"{self.address if self.address else ""}","{self.coord[0] if self.coord else ""}","{self.coord[1] if self.coord else ""}","{self.contacts if self.contacts else ""}","{self.opening_hours if self.opening_hours else ""}","{self.extra if self.extra else ""}"'

    def export_geojson(self):
        return {
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': self.coord},
            'properties': {
                'address': self.address,
                'contacts': self.contacts,
                'openingHours': self.opening_hours,
                'extra': self.extra
            }
        }


class GeoModel:
    """Модель для скрейпинга сайтов Авоська и Магнит Косметик"""

    def __init__(self):
        self.geo_objects = []  # Список магазинов

    def __str__(self):
        return '\n\n'.join(
            f'{obj.address}; {obj.coord}; {obj.contacts}; {obj.opening_hours}; {obj.extra}' for obj in self.geo_objects)

    def export_csv(self, file):
        """Экспорт в CSV"""
        text = '"address","longitude","latitude","contacts","opening_hours","extra"\r\n' + \
               '\r\n'.join(_.export_csv() for _ in self.geo_objects)
        with open(file, 'w') as f:
            f.write(text)

    def export_geojson(self, file):
        """Экспорт в GeoJSON"""
        text = {
            'type': 'FeatureCollection',
            'features': [_.export_geojson() for _ in self.geo_objects]
        }
        with open(file, 'w') as f:
            json.dump(text, f, indent=4)

    def scrap_avoska(self):
        """Скрейпинг Авоськи"""
        # Получение адресов
        response = requests.get('https://avoska.ru/api/get_shops.php', params={'map': '1'})
        # Получение контактов
        data = json.loads(response.content)
        response = requests.get('https://avoska.ru/contacts/')
        # Парсинг контактов
        soup = BeautifulSoup(response.content, 'html.parser')
        phone_email = soup.find_all(lambda tag: tag.name == 'p' and ('Тел' in tag.text or 'Email' in tag.text))
        contacts = ', '.join(_.text for _ in phone_email) + \
                   ', Почтовый адрес: ' + \
                   soup.find(lambda tag: tag.name == 'p' and 'Почтовый адрес' in tag.text).find_next_sibling('p').text
        extra = 'Юридический адрес: ' + \
                soup.find(lambda tag: tag.name == 'p' and 'Главный офис' in tag.text).find_next_sibling('p').text
        # Заполнение списка магазинов
        for feature in data['features']:
            self.geo_objects.append(GeoObject(
                feature['properties']['hintContent'],
                [float(feature['geometry']['coordinates'][1]), float(feature['geometry']['coordinates'][0])],
                contacts=contacts,
                extra=extra
            ))

    def scrap_magnit(self):
        """Скрейпинг Магнита"""
        # Получение адресов
        response = requests.get('https://magnitcosmetic.ru/shops/map/')
        text = str(response.content)
        # Вытаскивание JSON из скрипта
        result = re.search(r'(?<=var shopDataList = ).*?(?=</script>)', text)
        data = json.loads(result.group(0).replace('\\\\', '\\'))
        # Получение контактов
        response = requests.get('https://magnitcosmetic.ru/contacts/')
        soup = BeautifulSoup(response.content, 'html.parser')
        contacts = 'Тел:' + soup.find('a', {'class': 'office-detail__phone'}).text + \
                   ', Email: ' + soup.find('a', href=re.compile(r'mailto')).text.strip() + \
                   ', Почтовый адрес: ' + soup.find('div', {'class': 'office-detail__address'}).text
        # Заполнение списка магазинов
        for obj in data['shops']:
            self.geo_objects.append(GeoObject(
                obj['name'],
                [obj['coords']['lng'], obj['coords']['lat']],
                contacts=contacts,
                opening_hours=obj['time']
            ))

    def scrap_beeline(self):
        """Скрейпинг Билайна"""
        # Получение списка магазинов
        response = requests.get('https://beeline-tochki.ru/store')
        soup = BeautifulSoup(response.content, 'html.parser')
        columns = soup.find_all('div', {'class': 'col-sm-4 col-xs-6'})
        cities = []  # Ссылки на города
        for col in columns:
            cities += col.find_all('a', href=re.compile(r'/store/'))
        shops = []  # Ссылки на магазины
        count = 0   # Счётчик макс. кол-ва магазинов, чтобы долго не ждать
        max_count = 100
        for city in cities:
            response = requests.get('https://beeline-tochki.ru' + city['href'])
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find('div', {'class': 'wrapper'}).find_all('a', href=re.compile(r'/store/'))
            shops += links[:max_count - count]
            count += len(links)
            if count >= max_count:
                break
        # Получение информации о магазинах
        for shop in shops:
            response = requests.get('https://beeline-tochki.ru' + shop['href'])
            soup = BeautifulSoup(response.content, 'html.parser')
            address = soup.find('span', {'itemprop': 'streetAddress'}).text
            text_coord = re.search(r'(?<=DG.marker\(\[).*?(?=\]\))', str(response.content)).group(0)
            split_coord = text_coord.split(', ')
            coord = [float(split_coord[1]), float(split_coord[0])]
            # Не у всех точек есть телефон, почта и комментарий
            phone = soup.find('span', {'itemprop': 'telephone'})
            if phone:
                phone = phone.text.strip()
            else:
                phone = None
            email = soup.find('span', {'itemprop': 'email'})
            if email:
                email = email.text.strip()
            else:
                email = None
            contacts = f'Тел: {phone}' if phone else '' + \
                       ', ' if email and phone else '' + \
                       f'Email: {email}' if email else ''
            if contacts == '':
                contacts = None
            timetable = soup.find('table', {'class': 'gray_table'})
            opening_hours = ' '.join([_.text for _ in timetable.find_all(['th', 'td'])])
            comment = soup.find('div', {'class': 'title'}, text='Комментарий: ')
            if comment:
                extra = 'Комментарий: ' + comment.find_next_sibling('div').text
            else:
                extra = None
            self.geo_objects.append(GeoObject(
                address,
                coord,
                contacts,
                opening_hours,
                extra
            ))
