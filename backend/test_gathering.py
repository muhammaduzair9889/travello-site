"""Test the hotel search gathering flow."""
import os, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
import django; django.setup()
from authentication.chat_service import get_ai_response

session = f'gather_{int(time.time())}'

# Test 1: No city -> should ask
print('--- Test 1: No city (should ask for destination) ---')
r = get_ai_response('I want to find a hotel', session_id=session)
print('has_hotels:', r.get('has_hotels'))
print('Hotels:', len(r.get('hotels', [])))
print('Reply:', r.get('reply', '')[:400])
print()

# Test 2: Follow up with city (same session) -> should scrape
print('--- Test 2: Follow up with "Lahore" (same session) ---')
r2 = get_ai_response('Lahore', session_id=session)
print('has_hotels:', r2.get('has_hotels'))
print('Hotels:', len(r2.get('hotels', [])))
print('search_params:', r2.get('search_params'))
for h in r2.get('hotels', [])[:3]:
    name = h.get('name', '?')
    price = h.get('price_per_night', '?')
    scraped = h.get('is_scraped', False)
    print(f'  - {name}: PKR {price} (scraped={scraped})')
print()

# Test 3: Direct search with filters
print('--- Test 3: Direct with city + price filter ---')
r3 = get_ai_response('Hotels in Islamabad under 10000', session_id=f'{session}_3')
print('has_hotels:', r3.get('has_hotels'))
print('Hotels:', len(r3.get('hotels', [])))
for h in r3.get('hotels', [])[:3]:
    name = h.get('name', '?')
    price = h.get('price_per_night', '?')
    print(f'  - {name}: PKR {price}')

print('\nDone!')
