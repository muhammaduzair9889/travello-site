"""Test chatbot with price filter."""
import os, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
import django
django.setup()

from authentication.chat_service import get_ai_response

sid = f'filter_test_{int(time.time())}'
print(f'Testing: "Show hotels in Lahore under 10000 per night" session={sid}')
r = get_ai_response('Show hotels in Lahore under 10000 per night', session_id=sid)
print('has_hotels:', r.get('has_hotels'))
h = r.get('hotels', [])
print('Hotel count:', len(h))
for x in h[:5]:
    print(f'  {x.get("name")}: PKR {x.get("price_per_night")}')
print('search_params:', r.get('search_params'))
