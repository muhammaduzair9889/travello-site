"""Quick debug script to test the chatbot end-to-end."""
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')

import django
django.setup()

from authentication.chat_service import get_ai_response

# Use a fresh session to avoid cached state
import time
session_id = f'test_debug_{int(time.time())}'

print(f'Calling get_ai_response("Show hotels in Lahore") session={session_id}...')
try:
    result = get_ai_response('Show hotels in Lahore', session_id=session_id)
    print('Status:', result.get('status'))
    print('has_hotels:', result.get('has_hotels'))
    hotels = result.get('hotels', [])
    print('Hotel count:', len(hotels))
    if hotels:
        for h in hotels[:3]:
            name = h.get('name', 'Unknown')
            price = h.get('price_per_night', 'N/A')
            print(f'  - {name}: PKR {price}')
    else:
        print('  (no structured hotels in response)')
    print('search_params:', result.get('search_params'))
    reply = result.get('reply', '')
    print('Reply (first 500):', reply[:500])
    if result.get('error'):
        print('Error:', result.get('error'))
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {type(e).__name__}: {e}')

# Test 2: With price filter
print('\n\n=== Test 2: Hotels under 10000 ===')
try:
    result2 = get_ai_response('Hotels in Lahore under 10000 per night', session_id=f'{session_id}_filter')
    print('Status:', result2.get('status'))
    print('has_hotels:', result2.get('has_hotels'))
    hotels2 = result2.get('hotels', [])
    print('Hotel count:', len(hotels2))
    for h in hotels2[:5]:
        name = h.get('name', 'Unknown')
        price = h.get('price_per_night', 'N/A')
        print(f'  - {name}: PKR {price}')
except Exception as e:
    import traceback
    traceback.print_exc()
