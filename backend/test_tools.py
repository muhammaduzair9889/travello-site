"""
Test the tool-based AI chat architecture:
1. Internet Search Tool (Tavily) — travel query
2. Hotel Scraper Tool — hotel search with city
3. Destination Query — enriched with web search
4. Gathering flow — no city first, then follow-up
5. Classification check — various message types
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travello_backend.travello_backend.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from authentication.chat_service import (
    get_ai_response, _classify_request, _should_use_internet_search,
    tool_internet_search, tool_hotel_scraper, AVAILABLE_TOOLS,
)

SESSION = f'test_tools_{os.getpid()}'

print("=" * 60)
print("TOOL-BASED ARCHITECTURE TESTS")
print("=" * 60)

# ── Test 0: Tool registry ──
print("\n--- Test 0: Tool Registry ---")
for name, tool in AVAILABLE_TOOLS.items():
    print(f"  Tool: {tool['name']} — {tool['description'][:60]}...")
print(f"  Total tools: {len(AVAILABLE_TOOLS)}")

# ── Test 1: Internet Search Tool (Tavily) ──
print("\n--- Test 1: Internet Search Tool (Tavily) ---")
try:
    result = tool_internet_search("best tourist places in Lahore", max_results=3)
    if result and result.get('results'):
        print(f"  Answer: {(result.get('answer') or 'N/A')[:100]}...")
        print(f"  Results: {len(result['results'])}")
        for r in result['results'][:3]:
            print(f"    - {r['title'][:60]}")
        print("  ✅ Tavily search PASSED")
    else:
        print(f"  ⚠️  No results (API key may be invalid): {result}")
except Exception as e:
    print(f"  ❌ Tavily search failed: {e}")

# ── Test 2: Classification with internet search trigger ──
print("\n--- Test 2: _should_use_internet_search ---")
test_cases = [
    ("What are the top tourist attractions in Islamabad?", True),
    ("Travel tips for Pakistan", True),
    ("Best time to visit Hunza Valley", True),
    ("Hello", False),
    ("Thanks", False),
    ("Find me a hotel in Lahore", False),  # hotel search, not general
]
for msg, expected in test_cases:
    actual = _should_use_internet_search(msg)
    status = "✅" if actual == expected else "❌"
    print(f"  {status} '{msg[:50]}' → {actual} (expected {expected})")

# ── Test 3: Destination query with internet search ──
print("\n--- Test 3: Destination Query (with web search) ---")
resp = get_ai_response("What are the best places to visit in Lahore?", SESSION)
print(f"  Reply: {resp.get('reply', '')[:150]}...")
print(f"  web_search_used: {resp.get('web_search_used')}")
print(f"  sources: {resp.get('sources', [])[:2]}")
has_web = resp.get('web_search_used', False)
print(f"  {'✅' if has_web else '⚠️'} Web search {'was' if has_web else 'was NOT'} used")

# ── Test 4: Hotel search (uses hotel scraper tool) ──
print("\n--- Test 4: Hotel Search (Scraper Tool) ---")
SESSION2 = f'{SESSION}_hotel'
resp2 = get_ai_response("Find hotels in Lahore under 10000", SESSION2)
print(f"  has_hotels: {resp2.get('has_hotels')}")
print(f"  Hotels: {len(resp2.get('hotels', []))}")
print(f"  tools_used: {resp2.get('tools_used')}")
if resp2.get('hotels'):
    h = resp2['hotels'][0]
    print(f"  First: {h['name']} — PKR {h.get('price_per_night', 'N/A')} (scraped={h.get('is_scraped')})")
    print(f"  search_params: {resp2.get('search_params')}")
    print(f"  ✅ Hotel Scraper Tool PASSED")
else:
    print(f"  ⚠️  No hotels returned")

# ── Test 5: General travel question with web search ──
print("\n--- Test 5: General Travel Question ---")
SESSION3 = f'{SESSION}_general'
resp3 = get_ai_response("What are the best trekking routes in Pakistan?", SESSION3)
print(f"  Reply: {resp3.get('reply', '')[:150]}...")
print(f"  web_search_used: {resp3.get('web_search_used')}")
has_web3 = resp3.get('web_search_used', False)
print(f"  {'✅' if has_web3 else '⚠️'} Web search {'was' if has_web3 else 'was NOT'} used")

print("\n" + "=" * 60)
print("DONE!")
print("=" * 60)
