import requests
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from main.models import Currency

class Command(BaseCommand):
    help = 'Fetches actual currency rates from CBR API and updates the database'

    def handle(self, *args, **options):
        url = 'https://www.cbr.ru/scripts/XML_daily.asp'
        self.stdout.write('Fetching data from CBR...')
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status() # Проверка на HTTP-ошибки (4xx, 5xx)
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f'Network error: {e}'))
            return

        try:
            # Парсинг XML. encoding='windows-1251' нужен, так как ЦБ отдает данные в этой кодировке
            root = ET.fromstring(response.content.decode('windows-1251'))
        except ET.ParseError as e:
            self.stderr.write(self.style.ERROR(f'XML parsing error: {e}'))
            return

        updated_count = 0
        created_count = 0

        for valute in root.findall('Valute'):
            code = valute.find('CharCode').text.strip()
            name = valute.find('Name').text.strip()
            nominal_str = valute.find('Nominal').text.strip()
            value_str = valute.find('Value').text.strip().replace(',', '.')

            try:
                nominal = Decimal(nominal_str)
                value = Decimal(value_str)
                # ЦБ указывает курс за номинал (например, за 10 единиц). Приводим к курсу за 1 единицу.
                rate_per_unit = value / nominal
            except (InvalidOperation, AttributeError, TypeError) as e:
                self.stderr.write(self.style.WARNING(f'Skipping {code}: data format error ({e})'))
                continue

            # Обновляем или создаем валюту
            currency, created = Currency.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'current_rate': rate_per_unit,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done. Created: {created_count}, Updated: {updated_count}'
        ))