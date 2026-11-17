import requests
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from main.models import Currency
from main.api_cbr import fetch_cbr_ids

class Command(BaseCommand):
    help = 'Fetches actual rates and CBR IDs'

    def handle(self, *args, **options):
        cbr_ids = fetch_cbr_ids()

        url = 'https://www.cbr.ru/scripts/XML_daily.asp'
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.content.decode('windows-1251'))
        except Exception as e:
            return

        updated_count = 0
        created_count = 0

        for valute in root.findall('Valute'):
            code = valute.find('CharCode').text.strip()
            name = valute.find('Name').text.strip()
            nominal_str = valute.find('Nominal').text.strip()
            value_str = valute.find('Value').text.strip().replace(',', '.')
            cbr_id = cbr_ids.get(code)

            try:
                nominal = Decimal(nominal_str)
                value = Decimal(value_str)
                rate_per_unit = value / nominal
            except (InvalidOperation, AttributeError, TypeError):
                continue

            currency, created = Currency.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'current_rate': rate_per_unit,
                    'cbr_id': cbr_id,
                }
            )
            if created: created_count += 1
            else: updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Done. Created: {created_count}, Updated: {updated_count}'))