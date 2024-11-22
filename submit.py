import json
import requests
from config import Config


def submit():
    data = {
        'user': '111111',
        'products': [
            {
                'id': {Config.SUBMIT_API_URL},
                'qty': '3',
                'total': '600'
            }
        ]
    }

    url = Config.SUBMIT_API_URL

    headers = {
        'Content-type': 'application/json',
        'Accept': 'text/plain'
    }

    requests.post("http://httpbin.org/post", json=data)