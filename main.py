from scraping_model import GeoModel

# Инициация модели
avoska = GeoModel()
magnit = GeoModel()
beeline = GeoModel()
# Скрейпинг сайтов
avoska.scrap_avoska()
magnit.scrap_magnit()
beeline.scrap_beeline()
# Экспорт данных в CSV
avoska.export_csv('avoska.csv')
magnit.export_csv('magnit.csv')
beeline.export_csv('beeline.csv')
# Экспорт данных в GeoJSON
avoska.export_geojson('avoska.json')
magnit.export_geojson('magnit.json')
beeline.export_geojson('beeline.json')
