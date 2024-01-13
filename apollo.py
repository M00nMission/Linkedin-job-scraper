import requests
import os

url = "https://api.apollo.io/api/v1/organizations/bulk_enrich"
API_KEY = os.getenv("APOLLO_IO_API_KEY")

data = {
    "api_key": f"API_KEY",
    "domains": [
        "datadoghq.com",
        "snowflake.com"
    ]
}

headers = {
    'Cache-Control': 'no-cache',
    'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, json=data)

print(response.text)
