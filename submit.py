import json
import requests
from config import Config


def submit():
    data = {
        'user': '111111',
        'products': [
            {
                'id': {Config.SUBMIT_API_URL},
                'qty': '3',  # количество
                'total': '600'  # цена на момент добавления в корзину
            }
        ]
    }

    url = Config.SUBMIT_API_URL

    headers = {
        'Content-type': 'application/json',
        'Accept': 'text/plain'
    }

    return requests.post(url, data=json.dumps(data), headers=headers)
