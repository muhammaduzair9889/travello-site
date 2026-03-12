"""Quick test: Tavily API + classification + destination query"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from authentication.chat_service import (
    tool_internet_search, _should_use_internet_search, get_ai_response
)

print("=== Test 1: Tavily API direct ===")
r = tool_internet_search("travel tips Pakistan", max_results=3)
if r and r.get('results'):
    answer = (r.get('answer') or 'N/A')[:120]
    print(f"  Answer: {answer}")
    print(f"  Results: {len(r['results'])}")
    for x in r['results']:
        print(f"    - {x['title'][:60]}")
    print("  PASSED")
else:
    print(f"  No results: {r}")

print("\n=== Test 2: _should_use_internet_search ===")
tests = [
    ("tourist attractions in Islamabad", True),
    ("travel tips for Pakistan", True),
    ("best time to visit Hunza", True),
    ("Hello", False),
    ("Thanks", False),
]
for msg, exp in tests:
    got = _should_use_internet_search(msg)
    s = "OK" if got == exp else "FAIL"
    print(f"  [{s}] '{msg[:40]}' => {got}")

print("\n=== Test 3: Destination query via get_ai_response ===")
resp = get_ai_response("What are the best places to visit in Lahore?", "test_tavily_1")
print(f"  Reply: {resp.get('reply', '')[:200]}...")
print(f"  web_search_used: {resp.get('web_search_used')}")
print(f"  sources: {resp.get('sources')}")
print(f"  {'PASSED' if resp.get('web_search_used') else 'web search not triggered (Gemini may be rate limited or Tavily failed)'}")

print("\n=== Test 4: Hotel search with tools_used ===")
resp2 = get_ai_response("Find hotels in Lahore under 8000", "test_tavily_2")
print(f"  has_hotels: {resp2.get('has_hotels')}")
print(f"  tools_used: {resp2.get('tools_used')}")
print(f"  Hotels: {len(resp2.get('hotels', []))}")
if resp2.get('hotels'):
    h = resp2['hotels'][0]
    print(f"  First: {h['name']} — PKR {h.get('price_per_night', 'N/A')}")

print("\nDone!")
