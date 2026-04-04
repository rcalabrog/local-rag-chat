import requests

url = "http://localhost:11434/api/generate"

payload = {
    "model": "llama3.1:8b",
    "prompt": "Say hello in one short sentence",
    "stream": False
}

response = requests.post(url, json=payload)

print(response.status_code)
print(response.json())