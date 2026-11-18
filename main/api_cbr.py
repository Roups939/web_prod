#интеграция с API ЦБ РФ
import requests
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import timedelta

def fetch_cbr_ids():#bдет на сайт ЦБ, скачивает XML-справочник всех валют и составляет словарь вида {'USD': 'R01235', 'EUR': 'R01239', ...}
    url = "https://www.cbr.ru/scripts/XML_valFull.asp"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content = response.content.decode('windows-1251')#старый стандарт, 100% рабочий
        root = ET.fromstring(content)
        
        ids = {}
        for item in root.findall('Item'):
            code = item.find('ISO_Char_Code').text
            cbr_id = item.get('ID')
            if code and cbr_id:
                ids[code] = cbr_id
        return ids
    except Exception as e:
        return {}

def get_rate_on_date(cbr_id, target_date):#зная ID валюты и дату, запрашивает историю курсов за 7 дней до нужной даты. 
    date_to = target_date.strftime('%d/%m/%Y')
    date_from = (target_date - timedelta(days=7)).strftime('%d/%m/%Y')
    
    url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date_from}&date_req2={date_to}&VAL_NM_RQ={cbr_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        last_rate = None
        for record in root.findall('Record'):
            value = Decimal(record.find('Value').text.replace(',', '.'))
            nominal = Decimal(record.find('Nominal').text)
            last_rate = value / nominal
            
        return round(last_rate, 4) if last_rate else None #округление до 4 знаков после запятой 
    except Exception as e:
        return None