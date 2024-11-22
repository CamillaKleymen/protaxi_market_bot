import requests

url = 'https://protaxi-market.uz/module/shop/api/submit'
data = {
    'test': '2'
}

response = requests.post(url, json=data)

print (response.text)