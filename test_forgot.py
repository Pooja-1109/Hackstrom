import urllib.request, json

url = 'http://localhost:5000/forgot'
body = {'email': 'john@example.com', 'new_password': 'password'}
req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers={'Content-Type':'application/json'}, method='POST')
with urllib.request.urlopen(req) as resp:
    print(resp.status)
    print(resp.read().decode('utf-8'))
