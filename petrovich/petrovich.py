import codecs
import json
import requests


def get_data(codes):
    """
    Возвращает список магазинов по заданным параметрам
    :param list codes: коды регионов
    Доступные значения кодов (выборки не пересекаются):
    r_spb - Санкт-Петербург
    r_rf - Вся Россия
    r_szfo - Северо-Западный ФО
    r_cfo - Москва и Тверь
    :return: list, список магазинов
    """

    response = requests.get('https://api.petrovich.ru/api/pet/v002/base/getSubdivisionsForMap')
    data = json.loads(response.content)
    result = []
    for region in codes:
        for city in data['data']['regions'][region]['cities']:
            for point in city['subdivisions']:
                result.append({
                    'address': f"{city['title']}, {point['address']}",
                    'phone': point['phone'] if point['phone'] != '' else city['phone'],
                    'geo': point['geo'],
                    'work_time': ', '.join(point['workTime']).replace('&ndash;', '—')
                })
    return result


def to_geojson(points, filename):
    """
    Сохраняет список магазинов в формате GeoJSON
    :param list points: список магазинов
    :param str filename: имя файла
    """
    output = {
        'type': 'FeatureCollection',
        'features': []
    }
    for point in points:
        output['features'].append({
            'geometry': {
                'type': 'Point',
                'coordinates': [point['geo']['longitude'], point['geo']['latitude']]
            },
            'properties': {
                'address': point['address'],
                'opening_hours': point['work_time'],
                'phone': point['phone']
            }
        })
    with codecs.open(filename, 'w', 'utf-8') as f:
        f.write(json.dumps(output, indent=4, ensure_ascii=False))


if __name__ == '__main__':
    data = get_data(['r_spb', 'r_rf', 'r_szfo', 'r_cfo'])
    to_geojson(data, 'petrovich/points.geojson')
