import requests

url1 = "http://localhost:8000/api/v1/procurement/vendor-categories?include_inactive=true"
url2 = "http://localhost:8000/api/v1/procurement/vendor-types?include_inactive=true"

print("Direct request to running server on port 8000:")
try:
    r = requests.get(url1)
    print("vendor-categories STATUS:", r.status_code)
    print("vendor-categories RESPONSE:", r.text[:200])
except Exception as e:
    print("vendor-categories ERROR:", e)

try:
    r = requests.get(url2)
    print("vendor-types STATUS:", r.status_code)
    print("vendor-types RESPONSE:", r.text[:200])
except Exception as e:
    print("vendor-types ERROR:", e)
