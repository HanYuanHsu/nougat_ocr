import requests

api_url = 'http://127.0.0.1:8503/predict-from-image'
headers = {
    'accept': 'application/json',
}
files = {
    'file': ('captured_screen.png', open('images/captured_screen.png', 'rb'), 'image/png'),
}

if __name__ == '__main__':
    response = requests.post(api_url, headers=headers, files=files) # pretty slow
    print('response text:')
    print(response.text)