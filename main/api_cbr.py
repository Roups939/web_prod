import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from decimal import Decimal

def fetch_cbr_ids():
    url = "https://www.cbr.ru/scripts/XML_valFull.asp"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content = response.content.decode('windows-1251')
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

def get_rate_on_date(cbr_id, target_date):
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
            
        return last_rate
    except Exception as e:
        return None