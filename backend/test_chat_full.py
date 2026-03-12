"""Full chatbot test: gathering flow, scraper, filters, hotel cards."""
import os, sys, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')

import django
django.setup()

from authentication.chat_service import get_ai_response

session = f'test_{int(time.time())}'

# ── Test 1: Direct city search ──────────────────────────────────────────
print('='*60)
print('TEST 1: Direct hotel search with city')
print('='*60)
result = get_ai_response('Show hotels in Lahore', session_id=f'{session}_1')
print('Status:', result.get('status'))
print('has_hotels:', result.get('has_hotels'))
hotels = result.get('hotels', [])
print('Hotel count:', len(hotels))
for h in hotels[:3]:
    print(f"  - {h.get('name')}: PKR {h.get('price_per_night')} | is_scraped={h.get('is_scraped')} | rooms={len(h.get('rooms', []))}")
print('search_params:', result.get('search_params'))
print('Reply (first 200):', result.get('reply', '')[:200])
print()

# ── Test 2: No city → should ask follow-up ──────────────────────────────
print('='*60)
print('TEST 2: No city - should ask for destination')
print('='*60)
result2 = get_ai_response('I want to find a hotel', session_id=f'{session}_2')
print('Status:', result2.get('status'))
print('has_hotels:', result2.get('has_hotels'))
print('Hotel count:', len(result2.get('hotels', [])))
print('Reply (first 300):', result2.get('reply', '')[:300])
print()

# ── Test 3: Follow-up with city → should scrape ────────────────────────
print('='*60)
print('TEST 3: Follow-up with city (same session)')
print('='*60)
result3 = get_ai_response('Islamabad', session_id=f'{session}_2')
print('Status:', result3.get('status'))
print('has_hotels:', result3.get('has_hotels'))
hotels3 = result3.get('hotels', [])
print('Hotel count:', len(hotels3))
for h in hotels3[:3]:
    print(f"  - {h.get('name')}: PKR {h.get('price_per_night')}")
print('search_params:', result3.get('search_params'))
print('Reply (first 200):', result3.get('reply', '')[:200])
print()

# ── Test 4: Price filter ────────────────────────────────────────────────
print('='*60)
print('TEST 4: Hotels with price filter')
print('='*60)
result4 = get_ai_response('Hotels in Karachi under 8000 per night', session_id=f'{session}_4')
print('Status:', result4.get('status'))
print('has_hotels:', result4.get('has_hotels'))
hotels4 = result4.get('hotels', [])
print('Hotel count:', len(hotels4))
for h in hotels4[:5]:
    print(f"  - {h.get('name')}: PKR {h.get('price_per_night')}")
print()

print('='*60)
print('ALL TESTS COMPLETE')
print('='*60)
