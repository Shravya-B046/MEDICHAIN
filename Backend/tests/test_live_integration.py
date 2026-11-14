import urllib.request
import json

origin = 'http://127.0.0.1:8081'

def check_cors(req_obj):
    req_obj.add_header('Origin', origin)
    res = urllib.request.urlopen(req_obj)
    cors_hdr = res.headers.get('Access-Control-Allow-Origin')
    assert cors_hdr == origin or cors_hdr == '*', f'Invalid CORS: {cors_hdr}'
    return res

print('Testing Module 1: AI Health Assistant...')
req1 = urllib.request.Request(
    'http://127.0.0.1:8000/api/assistant/chat',
    data=json.dumps({'message': 'What are symptoms of dehydration?'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
res1 = check_cors(req1)
data1 = json.loads(res1.read().decode('utf-8'))
print(f' [PASS] AI Assistant: HTTP {res1.status} | Source: {data1.get("source")} | Reply length: {len(data1.get("reply", ""))}')

print('Testing Module 2: Hospital Resources...')
req2_sum = urllib.request.Request('http://127.0.0.1:8000/api/resources/summary')
res2_sum = check_cors(req2_sum)
data2_sum = json.loads(res2_sum.read().decode('utf-8'))
print(f' [PASS] Resource Summary: HTTP {res2_sum.status} | Beds: {data2_sum.get("available_beds")} | ICU: {data2_sum.get("icu_beds")}')

req2_list = urllib.request.Request('http://127.0.0.1:8000/api/resources')
res2_list = check_cors(req2_list)
data2_list = json.loads(res2_list.read().decode('utf-8'))
print(f' [PASS] Resource List: HTTP {res2_list.status} | Total resource categories: {len(data2_list)}')

print('Testing Module 3: Emergency Coordination...')
req3_sum = urllib.request.Request('http://127.0.0.1:8000/api/emergency/summary')
res3_sum = check_cors(req3_sum)
data3_sum = json.loads(res3_sum.read().decode('utf-8'))
print(f' [PASS] Emergency Summary: HTTP {res3_sum.status} | Active: {data3_sum.get("active_emergencies")} | Total: {data3_sum.get("total_emergencies")}')

req3_list = urllib.request.Request('http://127.0.0.1:8000/api/emergency')
res3_list = check_cors(req3_list)
data3_list = json.loads(res3_list.read().decode('utf-8'))
print(f' [PASS] Emergency List: HTTP {res3_list.status} | Cases in system: {len(data3_list)}')

print('Testing Module 4: Report Upload & Temporary Memory Pipeline...')
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    f'--{boundary}\r\n'
    'Content-Disposition: form-data; name="file"; filename="test_blood_panel.pdf"\r\n'
    'Content-Type: application/pdf\r\n\r\n'
    '%PDF-1.4 Mock Lab Complete Blood Count Report\r\n'
    f'--{boundary}--\r\n'
).encode('utf-8')

req4 = urllib.request.Request(
    'http://127.0.0.1:8000/api/reports/upload',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)
res4 = check_cors(req4)
data4 = json.loads(res4.read().decode('utf-8'))
print(f' [PASS] Report Upload: HTTP {res4.status} | Cleaned: {data4.get("temporary_file_cleaned")} | Title: {data4.get("summary_title")}')

print('Testing Hospital Administration Directory...')
req5 = urllib.request.Request('http://127.0.0.1:8000/api/hospitals')
res5 = check_cors(req5)
data5 = json.loads(res5.read().decode('utf-8'))
print(f' [PASS] Hospital Directory: HTTP {res5.status} | Hospitals in registry: {len(data5)}')
print('\n*** ALL MODULES PASSED LIVE INTEGRATION TEST ***')

