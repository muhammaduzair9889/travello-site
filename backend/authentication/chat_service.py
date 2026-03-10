"""
Travello AI Chat Service — Enhanced with travel knowledge, scraper integration,
conversation memory, and booking flow.
"""
import json
import logging
import os
import re
from datetime import datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons ──────────────────────────────────────────────────
_emotion_service = None
_EMOTION_SERVICE_AVAILABLE = True
_travel_knowledge = None


def _get_emotion_service():
    global _emotion_service, _EMOTION_SERVICE_AVAILABLE
    if _emotion_service is not None:
        return _emotion_service
    try:
        from .emotion_service import emotion_service
        _emotion_service = emotion_service
        _EMOTION_SERVICE_AVAILABLE = True
        return _emotion_service
    except Exception as e:
        logger.warning(f"Could not import emotion service: {e}")
        _EMOTION_SERVICE_AVAILABLE = False
        return None


def _get_travel_knowledge() -> dict:
    """Load the structured travel dataset once."""
    global _travel_knowledge
    if _travel_knowledge is not None:
        return _travel_knowledge
    try:
        data_path = os.path.join(
            str(settings.BASE_DIR.parent), 'data', 'datasets',
            'pakistan_travel_knowledge.json',
        )
        with open(data_path, 'r', encoding='utf-8') as f:
            _travel_knowledge = json.load(f)
        logger.info("Travel knowledge dataset loaded")
    except Exception as e:
        logger.warning(f"Could not load travel knowledge: {e}")
        _travel_knowledge = {}
    return _travel_knowledge


# ── In-memory conversation store (keyed by session_id) ──────────────────────
_conversations: dict = {}
_MAX_HISTORY = 20
_SESSION_TTL_MINS = 60


def _get_conversation(session_id: str) -> dict:
    now = datetime.utcnow()
    stale = [k for k, v in _conversations.items()
             if (now - v['last_active']).total_seconds() > _SESSION_TTL_MINS * 60]
    for k in stale:
        del _conversations[k]

    if session_id not in _conversations:
        _conversations[session_id] = {
            'messages': [],
            'context': {},
            'last_active': now,
        }
    conv = _conversations[session_id]
    conv['last_active'] = now
    return conv


def _add_to_history(conv: dict, role: str, text: str):
    conv['messages'].append({'role': role, 'text': text})
    if len(conv['messages']) > _MAX_HISTORY:
        conv['messages'] = conv['messages'][-_MAX_HISTORY:]


# ── Request classification ──────────────────────────────────────────────────

TEXT_PROCESSING_TYPES = {
    'grammar': [
        'correct the grammar', 'fix grammar', 'fix spelling', 'fix punctuation',
        'grammar and spelling', 'spelling and punctuation', 'correct spelling',
        'proofread', 'correct the text', 'fix the text', 'grammar check',
    ],
    'enhance': [
        'enhance', 'improve', 'make it better', 'rewrite', 'polish',
        'make it more descriptive', 'make it more engaging', 'improve writing',
        'enhance writing', 'better wording',
    ],
    'summarize': [
        'summarize', 'summary', 'shorten', 'make it shorter', 'brief version',
        'tldr', 'condense', 'key points',
    ],
    'expand': [
        'expand', 'add details', 'elaborate', 'make it longer',
        'more detail', 'more descriptive', 'add more', 'flesh out',
        'vivid descriptions', 'sensory details',
    ],
}

_HOTEL_SEARCH_KEYWORDS = [
    'find hotel', 'search hotel', 'show hotel', 'hotel in', 'hotels in',
    'book a hotel', 'book hotel', 'need a hotel', 'looking for hotel',
    'recommend hotel', 'best hotel', 'cheap hotel', 'budget hotel',
    'luxury hotel', 'stay in', 'accommodation', 'where to stay',
    'hotel recommendation', 'suggest hotel', 'hotel near',
]

_BOOKING_KEYWORDS = [
    'book option', 'book this', 'i want to book', 'confirm booking',
    'reserve', 'book number', 'book #', 'select option', 'select hotel',
    'book it', "i'll take", "let's book",
]

_DESTINATION_KEYWORDS = [
    'visit', 'travel to', 'trip to', 'going to', 'plan a trip',
    'things to do in', 'what to see in', 'places in', 'explore',
    'sightseeing in', 'tourist spots', 'attractions in',
    'tell me about', 'info about', 'information about', 'guide to',
]

_AI_RECOMMENDATION_KEYWORDS = [
    'personalized recommendation', 'ai recommend', 'recommend based on my preferences',
    'recommend based on preference', 'personalized hotel', 'ai hotel recommendation',
    'find me the perfect hotel', 'hotel based on my taste',
    'recommendation based on my', 'suggest based on',
]


def _classify_request(message: str, conv_context: dict | None = None):
    """Return request type and optional sub-type."""
    msg_lower = message.lower().strip()
    conv_context = conv_context or {}

    # Active booking flow takes priority
    if conv_context.get('booking_flow'):
        return 'booking_flow', None

    # "book option 1" / "book #2"
    for kw in _BOOKING_KEYWORDS:
        if kw in msg_lower:
            return 'booking_request', None

    # AI recommendation — guide to widget
    for kw in _AI_RECOMMENDATION_KEYWORDS:
        if kw in msg_lower:
            return 'ai_recommendation', None

    # Text processing
    for kind, keywords in TEXT_PROCESSING_TYPES.items():
        if any(kw in msg_lower for kw in keywords):
            return 'text_processing', kind

    # Hotel search
    for kw in _HOTEL_SEARCH_KEYWORDS:
        if kw in msg_lower:
            return 'hotel_search', None

    # Destination / sightseeing query
    for kw in _DESTINATION_KEYWORDS:
        if kw in msg_lower:
            return 'destination_query', None

    return 'chat', None


# ── Travel knowledge helpers ────────────────────────────────────────────────

def _extract_city_from_message(message: str):
    """Detect a known destination from the message text."""
    knowledge = _get_travel_knowledge()
    msg_lower = message.lower()
    for city_name in knowledge.get('destinations', {}):
        if city_name.lower() in msg_lower:
            return city_name
    aliases = {
        'isb': 'Islamabad', 'isl': 'Islamabad', 'rwp': 'Rawalpindi',
        'khi': 'Karachi', 'lhr': 'Lahore', 'hunza': 'Hunza Valley',
        'swat': 'Swat Valley', 'naran': 'Naran Kaghan',
    }
    for alias, city in aliases.items():
        if alias in msg_lower and city in knowledge.get('destinations', {}):
            return city
    return None


def _build_city_knowledge_snippet(city_name: str) -> str:
    knowledge = _get_travel_knowledge()
    city = knowledge.get('destinations', {}).get(city_name)
    if not city:
        return ""
    lines = [f"\n--- {city_name} Travel Data ---"]
    lines.append(f"Description: {city.get('description', '')}")
    lines.append(f"Best season: {city.get('best_season', 'year-round')}")
    prices = city.get('avg_hotel_price_pkr', {})
    lines.append(
        f"Avg prices (PKR/night): Budget={prices.get('budget', 'N/A')}, "
        f"Mid={prices.get('mid_range', 'N/A')}, Luxury={prices.get('luxury', 'N/A')}"
    )
    if city.get('top_attractions'):
        lines.append("Top attractions: " + ", ".join(
            f"{a['name']} ({a.get('type', '')}, ★{a.get('rating', '')})"
            for a in city['top_attractions'][:6]
        ))
    if city.get('popular_hotels'):
        lines.append("Popular hotels:")
        for h in city['popular_hotels'][:5]:
            amen = ", ".join(h.get('amenities', [])[:4])
            lines.append(
                f"  - {h['name']} ({h.get('stars', '')}★, "
                f"PKR {h.get('price_range', 'N/A')}/night, "
                f"★{h.get('rating', '')}, {amen})"
            )
    if city.get('local_cuisine'):
        lines.append("Must-try food: " + ", ".join(city['local_cuisine']))
    if city.get('tips'):
        lines.append("Tips: " + " | ".join(city['tips'][:3]))
    return "\n".join(lines)


def _build_hotels_db_context() -> str:
    """Fetch hotels from the database for extra context."""
    try:
        from hotels.models import Hotel
        hotels = (
            Hotel.objects.select_related()
            .prefetch_related('room_types')
            .order_by('-rating')[:20]
        )
        if not hotels:
            return ""
        lines = ["\n--- Hotels in Travello Database ---"]
        for h in hotels:
            room_info = []
            for rt in h.room_types.all()[:3]:
                room_info.append(f"{rt.get_type_display()}: PKR {rt.price_per_night}/night")
            rooms_str = " | ".join(room_info) if room_info else "Contact for rates"
            lines.append(f"  - {h.name} ({h.city}, ★{h.rating}) — {rooms_str}")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Could not fetch DB hotels: {e}")
        return ""


# ── Scraper integration ─────────────────────────────────────────────────────

def _extract_dates_from_message(message: str):
    """Extract check-in / check-out dates from user message."""
    dates = re.findall(r'(\d{4}-\d{2}-\d{2})', message)
    checkin = dates[0] if len(dates) >= 1 else None
    checkout = dates[1] if len(dates) >= 2 else None
    return checkin, checkout


def _extract_adults_from_message(message: str) -> int:
    """Extract guest/adult count from user message."""
    m = re.search(r'(\d+)\s*(?:guest|adult|person|people)', message.lower())
    return int(m.group(1)) if m else 2


def _fetch_live_hotels(city: str, checkin: str = None, checkout: str = None,
                       adults: int = 2) -> tuple:
    """Always fetch live hotel data via scraper.  Returns (hotels, resolved_params)."""
    from datetime import date, timedelta as td
    today = date.today()
    resolved_checkin = checkin or (today + td(days=1)).isoformat()
    resolved_checkout = checkout or (today + td(days=2)).isoformat()
    resolved_adults = int(adults or 2)

    try:
        # Check short-term cache (≤15 min) using resolved dates
        from django.core.cache import cache
        cache_key = f"realtime_v7_{city}_{resolved_checkin}_{resolved_checkout}_{resolved_adults}"
        cached = cache.get(cache_key)
        if cached:
            hotels = cached.get('hotels', []) if isinstance(cached, dict) else cached
            if hotels:
                logger.info(f"Chat: {len(hotels)} fresh cached hotels for {city}")
                return hotels[:10], (resolved_checkin, resolved_checkout, resolved_adults)

        # ── Run a real-time scrape ──────────────────────────────────────
        hotels = _run_realtime_scrape(city, resolved_checkin, resolved_checkout, resolved_adults)
        if hotels:
            return hotels[:10], (resolved_checkin, resolved_checkout, resolved_adults)

        # Last resort: recent completed scrape job (< 30 min old)
        from scraper.models import ScrapeJob
        from django.utils import timezone as tz
        cutoff = tz.now() - td(minutes=30)
        recent = ScrapeJob.objects.filter(
            city__iexact=city,
            status=ScrapeJob.Status.COMPLETED,
            hotel_count__gt=0,
            updated_at__gte=cutoff,
        ).order_by('-updated_at').first()

        if recent and recent.results:
            hotels = recent.results.get('hotels', [])
            if hotels:
                logger.info(f"Chat: using recent ScrapeJob ({recent.pk}) for {city}")
                return hotels[:10], (resolved_checkin, resolved_checkout, resolved_adults)
    except Exception as e:
        logger.warning(f"Could not fetch live hotels: {e}")
    return [], (resolved_checkin, resolved_checkout, resolved_adults)


def _run_realtime_scrape(city, checkin, checkout, adults):
    """Execute the Puppeteer scraper synchronously for the chatbot.
    Expects already-resolved dates (non-None)."""
    try:
        from scraper.views import _run_puppeteer, _normalize_hotels, _cache_key
        from scraper.booking_scraper import PAKISTAN_DESTINATIONS

        search_params = {
            'city': city,
            'checkin': checkin,
            'checkout': checkout,
            'adults': int(adults or 2),
            'rooms': 1,
            'children': 0,
            'order': 'popularity',
            'max_seconds': 50,
            'max_results': 30,
        }
        city_lower = city.lower()
        if city_lower in PAKISTAN_DESTINATIONS:
            search_params['dest_id'] = PAKISTAN_DESTINATIONS[city_lower]['dest_id']

        logger.info(f"Chat: running real-time scrape for {city}")
        hotels, meta = _run_puppeteer(search_params)
        if hotels:
            _normalize_hotels(hotels, search_params)
            from django.core.cache import cache as django_cache
            ck = _cache_key(search_params)
            django_cache.set(ck, {'hotels': hotels, 'meta': meta}, 15 * 60)
            logger.info(f"Chat: scraped {len(hotels)} hotels for {city}")
            return hotels
    except Exception as e:
        logger.warning(f"Chat real-time scrape failed: {e}")
    return []


def _format_scraped_hotels_for_context(hotels: list, city: str) -> str:
    if not hotels:
        return ""
    lines = [f"\n--- Live Hotel Prices (scraped for {city}) ---"]
    for i, h in enumerate(hotels[:8], 1):
        name = h.get('hotel_name') or h.get('name', 'Hotel')
        price = h.get('price_per_night') or h.get('total_stay_price', 'N/A')
        rating = h.get('review_score') or h.get('rating', 'N/A')
        room = h.get('room_type', 'Standard Room')
        stars = h.get('stars', '')
        avail = h.get('availability_status', '')
        rooms_left = h.get('rooms_left')
        avail_note = f" — {avail}" if avail else ""
        if rooms_left:
            avail_note += f" (only {rooms_left} left)"
        lines.append(
            f"{i}. **{name}** {'★' * int(stars) if stars else ''}"
            f" — Room: {room}, PKR {price}/night, Rating: {rating}/10{avail_note}"
        )
    return "\n".join(lines)


def _build_hotels_for_response(hotels: list, city: str) -> list:
    """Build a structured list of hotel dicts for the frontend to render cards
    and navigate to the in-app hotel details page."""
    result = []
    for i, h in enumerate(hotels[:8]):
        name = h.get('hotel_name') or h.get('name', 'Hotel')
        ppn = h.get('price_per_night') or h.get('double_bed_price_per_day')
        result.append({
            'id': h.get('id') or f'chat_{i}',
            'name': name,
            'city': city or '',
            'url': h.get('url') or h.get('booking_url') or '',
            'image_url': h.get('image_url') or h.get('image') or '',
            'rating': h.get('review_score') or h.get('review_rating') or h.get('rating'),
            'review_count': h.get('review_count') or h.get('review_count_num'),
            'rating_label': h.get('rating_label'),
            'stars': h.get('stars'),
            'price_per_night': ppn,
            'double_bed_price_per_day': ppn,
            'total_stay_price': h.get('total_stay_price'),
            'currency': h.get('currency', 'PKR'),
            'nights': h.get('nights', 1),
            'room_type': h.get('room_type', 'Standard Room'),
            'rooms': h.get('rooms') or [],
            'is_scraped': True,
            'is_real_time': True,
            'source': 'booking.com',
            'availability_status': h.get('availability_status', ''),
            'rooms_left': h.get('rooms_left'),
            'is_sold_out': h.get('is_sold_out', False),
            'is_limited': h.get('is_limited', False),
            'distance_from_center': h.get('distance_from_center') or h.get('distance', ''),
            'location': h.get('location') or h.get('location_area') or '',
            'address': h.get('address') or h.get('location') or '',
            'amenities': h.get('amenities') or [],
            'meal_plan': h.get('meal_plan'),
            'cancellation_policy': h.get('cancellation_policy'),
            'has_deal': h.get('has_deal', False),
            'deal_label': h.get('deal_label'),
        })
    return result


# ── Prompt builders ─────────────────────────────────────────────────────────

def _build_text_processing_prompt(message: str, kind: str) -> tuple:
    system_instructions = {
        'grammar': (
            "You are a precise proofreader. "
            "Correct all grammar, spelling, and punctuation errors in the user's text. "
            "Return ONLY the corrected text — no explanations, no commentary, no quotes around it. "
            "Preserve the original tone, meaning, and paragraph structure."
        ),
        'enhance': (
            "You are a skilled writing editor. "
            "Enhance the user's text to be more vivid, engaging, and well-written. "
            "Keep the original meaning and facts intact. "
            "Return ONLY the enhanced text — no explanations, no commentary, no quotes around it."
        ),
        'summarize': (
            "You are a concise summarizer. "
            "Provide a clear, brief summary of the user's text. "
            "Capture the key points in 2-4 sentences. "
            "Return ONLY the summary — no labels, no prefixes, no extra commentary."
        ),
        'expand': (
            "You are a creative travel writer. "
            "Expand the user's text with richer descriptions, sensory details, and vivid imagery. "
            "Stay faithful to the original content and facts. "
            "Return ONLY the expanded text — no explanations, no commentary, no quotes around it."
        ),
    }
    system_text = system_instructions.get(kind, system_instructions['grammar'])
    contents = [{"parts": [{"text": message}]}]
    return system_text, contents


def _build_chat_prompt(message: str, conversation: dict,
                       detected_emotion=None, emotion_confidence=0.0) -> tuple:
    """Build Gemini system instruction + multi-turn contents."""
    emotion_hint = ""
    if detected_emotion and emotion_confidence > 0.4:
        emotion_map = {
            'stress': "The user seems stressed — be calming and suggest relaxing destinations.",
            'anxiety': "The user seems anxious — be reassuring, suggest peaceful places.",
            'joy': "The user is in a great mood — match their energy, suggest exciting experiences.",
            'sadness': "The user seems down — be warm and empathetic, suggest uplifting experiences.",
            'disappointment': "The user seems disappointed — be understanding, offer alternatives.",
            'anger': "The user seems frustrated — be patient, suggest calming getaways.",
            'fear': "The user seems nervous — be reassuring, provide safety tips.",
            'surprise': "The user is surprised — engage their curiosity with interesting facts.",
            'neutral': "",
        }
        emotion_hint = emotion_map.get(detected_emotion, "")

    city = _extract_city_from_message(message)
    city_context = _build_city_knowledge_snippet(city) if city else ""
    db_context = _build_hotels_db_context()

    # If hotels were offered previously, remind Gemini
    offered_ctx = ""
    offered = conversation.get('context', {}).get('offered_hotels')
    if offered:
        offered_ctx = "\n--- Hotels Previously Offered to User ---\n"
        for i, h in enumerate(offered, 1):
            offered_ctx += (
                f"{i}. {h.get('name', 'Hotel')} — {h.get('city', '')}, "
                f"PKR {h.get('price_per_night', 'N/A')}/night, "
                f"★{h.get('rating', 'N/A')}\n"
            )

    system_text = f"""You are the Travello AI travel assistant — friendly, knowledgeable, and professional.

ABOUT TRAVELLO:
- Full-service travel booking platform for Pakistan and beyond.
- Features: Hotel Search & Booking, Real-time Price Comparison, Reviews, AI Itineraries, Sightseeing Guides.
- Users can search hotels by destination, dates, guests, and room type. Prices in PKR.
- Supported cities: Lahore, Karachi, Islamabad, Peshawar, Hunza Valley, Swat Valley, Murree, and more.

YOUR CAPABILITIES:
1. **Travel Recommendations**: Suggest destinations, hotels, attractions based on preferences.
2. **Hotel Information**: Provide real hotel details (name, room types, prices, ratings, amenities).
3. **Booking Assistance**: Guide users through booking — collect check-in, check-out, room type, guests, city.
4. **Price Guidance**: Quote actual hotel prices in PKR from the knowledge base.
5. **Destination Expertise**: Share info about Pakistani tourist destinations, cuisine, best seasons, tips.

RESPONSE GUIDELINES:
- Be natural, conversational, and concise — like a knowledgeable travel expert friend.
- When recommending hotels, use a numbered list: Hotel Name, Room Type, Price/night (PKR), Rating, Amenities.
- Use markdown: **bold** for names, bullet points for 3+ items, numbered lists for hotel recs.
- Do NOT overuse emojis — at most one per response.
- If no data available, say so honestly and suggest searching on the platform.
- Always quote prices in PKR.
{f"EMOTIONAL CONTEXT: {emotion_hint}" if emotion_hint else ""}
{city_context}
{db_context}
{offered_ctx}"""

    # Multi-turn contents from conversation history
    contents = []
    for msg in conversation.get('messages', [])[-10:]:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append({"role": role, "parts": [{"text": msg['text']}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    return system_text, contents


def _build_hotel_search_prompt(message: str, conversation: dict) -> tuple:
    city = _extract_city_from_message(message)
    city_context = _build_city_knowledge_snippet(city) if city else ""
    db_context = _build_hotels_db_context()

    system_text = f"""You are the Travello hotel search assistant.

YOUR TASK:
1. If the user specified a destination, present a brief summary of the real-time hotel options found.
2. IMPORTANT: The user will see detailed hotel cards with images, prices, ratings, and booking buttons displayed separately below your message. Do NOT repeat every detail — just give a friendly overview like "I found X great options in [city]" and highlight 2-3 standout picks.
3. If no city mentioned, ask which destination they want.
4. If details are missing (dates, guests), ask conversationally.
5. After your overview, say: "You can tap **Book** on any hotel card, or say **Book option 1** to start booking."
6. Consider budget if mentioned.
7. Keep your response concise — the hotel cards do the heavy lifting.
{city_context}
{db_context}"""

    contents = []
    for msg in conversation.get('messages', [])[-8:]:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append({"role": role, "parts": [{"text": msg['text']}]})
    contents.append({"role": "user", "parts": [{"text": message}]})
    return system_text, contents


def _build_booking_flow_prompt(message: str, conversation: dict) -> tuple:
    flow = conversation.get('context', {}).get('booking_flow', {})

    system_text = f"""You are the Travello booking assistant helping complete a hotel reservation.

BOOKING DETAILS COLLECTED SO FAR:
{json.dumps(flow, indent=2)}

REQUIRED FIELDS — ask for any missing, ONE at a time:
- hotel_name: Which hotel
- check_in: Check-in date (YYYY-MM-DD)
- check_out: Check-out date (YYYY-MM-DD)
- room_type: Room type (single, double, suite, deluxe, family, etc.)
- guests: Number of guests

INSTRUCTIONS:
1. Review collected info above. Ask for the NEXT missing field naturally.
2. If the user gives a date like "next Friday" or "July 10", convert it and confirm.
3. If ALL fields are collected, summarize and ask the user to confirm with "Yes" or "Confirm".
4. When confirmed, respond with EXACTLY: BOOKING_CONFIRMED: {{"hotel_name": "...", "check_in": "YYYY-MM-DD", "check_out": "YYYY-MM-DD", "room_type": "...", "guests": N}}
5. Keep responses short and helpful.
6. If user says "cancel" or "never mind", respond with: BOOKING_CANCELLED"""

    contents = []
    for msg in conversation.get('messages', [])[-10:]:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append({"role": role, "parts": [{"text": msg['text']}]})
    contents.append({"role": "user", "parts": [{"text": message}]})
    return system_text, contents


# ── Gemini API call ─────────────────────────────────────────────────────────

def _call_gemini(system_instruction: str, contents: list,
                 temperature: float = 0.7, max_tokens: int = 1024) -> str:
    from travello_backend.utils import call_gemini
    return call_gemini(system_instruction, contents, temperature, max_tokens)


# ── Booking processing ──────────────────────────────────────────────────────

def _process_booking_confirmation(booking_data: dict, user=None) -> dict:
    """Attempt to create a Booking record."""
    try:
        from hotels.models import Hotel, Booking
        from django.utils.dateparse import parse_date

        hotel_name = booking_data.get('hotel_name', '')
        hotel = Hotel.objects.filter(name__icontains=hotel_name).first()

        if not hotel:
            return {
                'success': False,
                'message': (
                    f"I couldn't find **{hotel_name}** in our system. "
                    "You can search and book it directly in the Hotels section."
                ),
            }

        if not user or not user.is_authenticated:
            return {
                'success': False,
                'message': (
                    f"Great choice! **{hotel.name}** is available. "
                    "To complete the booking please **log in** first and then "
                    "search for this hotel on the platform. Here are your details:\n\n"
                    f"- **Hotel**: {hotel.name}\n"
                    f"- **Check-in**: {booking_data.get('check_in')}\n"
                    f"- **Check-out**: {booking_data.get('check_out')}\n"
                    f"- **Room**: {booking_data.get('room_type', 'Standard')}\n"
                    f"- **Guests**: {booking_data.get('guests', 2)}"
                ),
            }

        check_in = parse_date(booking_data.get('check_in', ''))
        check_out = parse_date(booking_data.get('check_out', ''))
        if not check_in or not check_out:
            return {'success': False, 'message': "I need valid check-in and check-out dates."}
        if check_out <= check_in:
            return {'success': False, 'message': "Check-out must be after check-in."}

        room_type_str = (booking_data.get('room_type') or 'double').lower().strip()
        room_type = hotel.room_types.filter(type__iexact=room_type_str).first()
        if not room_type:
            room_type = hotel.room_types.first()
        if not room_type:
            return {
                'success': False,
                'message': f"**{hotel.name}** doesn't have room types in our system yet. Please book via the Hotels section.",
            }

        nights = (check_out - check_in).days
        guests = int(booking_data.get('guests', 2))

        booking = Booking(
            user=user,
            hotel=hotel,
            room_type=room_type,
            check_in=check_in,
            check_out=check_out,
            adults=guests,
            rooms_booked=1,
            status='CONFIRMED',
        )
        booking.save()

        return {
            'success': True,
            'booking_id': booking.id,
            'message': (
                f"Your booking is confirmed!\n\n"
                f"- **Hotel**: {hotel.name} ({hotel.city})\n"
                f"- **Room**: {room_type.get_type_display()}\n"
                f"- **Check-in**: {check_in.strftime('%B %d, %Y')}\n"
                f"- **Check-out**: {check_out.strftime('%B %d, %Y')}\n"
                f"- **Guests**: {guests}\n"
                f"- **{nights} night(s)**: PKR {booking.total_price:,.0f}\n"
                f"- **Reference**: {booking.booking_reference}\n\n"
                f"View your booking in **My Bookings**."
            ),
        }
    except Exception as e:
        logger.error(f"Booking creation error: {e}")
        return {
            'success': False,
            'message': "Something went wrong creating the booking. Please try via the Hotels section.",
        }


# ── Main entry point ────────────────────────────────────────────────────────

def get_ai_response(message: str, session_id: str = 'default', user=None) -> dict:
    """Main entry point — detect emotion, classify, call Gemini with context."""
    conv = _get_conversation(session_id)

    # 1. Detect emotion
    detected_emotion = None
    emotion_confidence = 0.0
    svc = _get_emotion_service()
    if svc and _EMOTION_SERVICE_AVAILABLE:
        try:
            detected_emotion, emotion_confidence = svc.detect_emotion(message)
        except Exception as e:
            logger.warning(f"Emotion detection failed: {e}")

    # 2. Classify request
    request_type, processing_kind = _classify_request(message, conv.get('context', {}))
    logger.info(f"Chat: type={request_type}, kind={processing_kind}")

    try:
        # ── Text processing (stateless) ──
        if request_type == 'text_processing':
            system_instruction, contents = _build_text_processing_prompt(message, processing_kind)
            temp = 0.3 if processing_kind in ('grammar', 'summarize') else 0.8
            max_tok = 512 if processing_kind == 'summarize' else 2048
            reply = _call_gemini(system_instruction, contents, temperature=temp, max_tokens=max_tok)
            return _success(reply, detected_emotion, emotion_confidence)

        # ── Booking request ("book option 1") ──
        if request_type == 'booking_request':
            offered = conv.get('context', {}).get('offered_hotels', [])
            match = re.search(r'(?:option|#|number)\s*(\d+)', message.lower())
            if not match:
                match = re.search(r'book\s+(\d+)', message.lower())
            if match and offered:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(offered):
                    hotel = offered[idx]
                    conv['context']['booking_flow'] = {
                        'hotel_name': hotel.get('name', ''),
                        'city': hotel.get('city', ''),
                        'room_type': hotel.get('room_type', ''),
                        'price_per_night': hotel.get('price_per_night', ''),
                    }
                    _add_to_history(conv, 'user', message)
                    reply = (
                        f"Great choice! Let me book **{hotel.get('name', 'the hotel')}** for you.\n\n"
                        f"When would you like to **check in**? (e.g. 2026-07-10)"
                    )
                    _add_to_history(conv, 'bot', reply)
                    return _success(reply, detected_emotion, emotion_confidence, booking_flow='active')

            # Couldn't parse — let Gemini handle naturally
            _add_to_history(conv, 'user', message)
            system_instruction, contents = _build_chat_prompt(
                message, conv, detected_emotion, emotion_confidence)
            reply = _call_gemini(system_instruction, contents)
            _add_to_history(conv, 'bot', reply)
            return _success(reply, detected_emotion, emotion_confidence)

        # ── AI Recommendation (guide to widget) ──
        if request_type == 'ai_recommendation':
            _add_to_history(conv, 'user', message)
            reply = (
                "Great idea! For **personalized AI hotel recommendations**, head to the "
                "**AI Recommendations** section on your dashboard.\n\n"
                "Here's how it works:\n"
                "1. Answer a few quick preference questions (destination, interests, travel style, budget, etc.)\n"
                "2. Our AI searches **real-time hotel data** and finds options near your areas of interest\n"
                "3. Hotels are **AI-ranked** based on your specific preferences and shown on our search results page\n\n"
                "You'll get personalized ratings and recommendations — all within our platform!\n\n"
                "Alternatively, I can help you **search hotels** right here — just tell me a city and I'll show you options."
            )
            _add_to_history(conv, 'bot', reply)
            return _success(reply, detected_emotion, emotion_confidence)

        # ── Active booking flow ──
        if request_type == 'booking_flow':
            _add_to_history(conv, 'user', message)
            _update_booking_flow(conv, message)
            system_instruction, contents = _build_booking_flow_prompt(message, conv)
            reply = _call_gemini(system_instruction, contents, temperature=0.4)

            if 'BOOKING_CONFIRMED:' in reply:
                try:
                    json_str = reply.split('BOOKING_CONFIRMED:')[1].strip()
                    json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                    if json_match:
                        booking_data = json.loads(json_match.group())
                        result = _process_booking_confirmation(booking_data, user)
                        reply = result['message']
                        conv['context'].pop('booking_flow', None)
                        conv['context'].pop('offered_hotels', None)
                except (json.JSONDecodeError, IndexError) as e:
                    logger.error(f"Failed to parse booking confirmation: {e}")
                    reply = reply.replace('BOOKING_CONFIRMED:', '').strip()
            elif 'BOOKING_CANCELLED' in reply:
                conv['context'].pop('booking_flow', None)
                reply = "No problem! Booking cancelled. Is there anything else I can help with?"

            _add_to_history(conv, 'bot', reply)
            flow_active = 'active' if conv.get('context', {}).get('booking_flow') else None
            return _success(reply, detected_emotion, emotion_confidence, booking_flow=flow_active)

        # ── Hotel search ──
        if request_type == 'hotel_search':
            _add_to_history(conv, 'user', message)
            city = _extract_city_from_message(message)

            # Extract dates & guests from user message for the scraper
            msg_checkin, msg_checkout = _extract_dates_from_message(message)
            msg_adults = _extract_adults_from_message(message)

            if city:
                live_hotels, (r_checkin, r_checkout, r_adults) = _fetch_live_hotels(
                    city, checkin=msg_checkin, checkout=msg_checkout, adults=msg_adults,
                )
            else:
                live_hotels, r_checkin, r_checkout, r_adults = [], msg_checkin, msg_checkout, msg_adults

            live_context = _format_scraped_hotels_for_context(live_hotels, city or 'Pakistan')
            system_instruction, contents = _build_hotel_search_prompt(message, conv)
            if live_context:
                system_instruction += live_context

            reply = _call_gemini(system_instruction, contents, temperature=0.5, max_tokens=1500)
            _store_offered_hotels(conv, city, live_hotels)
            _add_to_history(conv, 'bot', reply)

            # Build structured hotel data for frontend cards
            structured_hotels = _build_hotels_for_response(live_hotels, city) if live_hotels else []

            # Include search params (with resolved dates) so frontend can navigate to search page
            search_params = {
                'destination': city or '',
                'checkIn': r_checkin or '',
                'checkOut': r_checkout or '',
                'adults': r_adults,
            }

            return _success(
                reply, detected_emotion, emotion_confidence,
                has_hotels=True,
                hotels=structured_hotels,
                search_params=search_params,
            )

        # ── Destination query ──
        if request_type == 'destination_query':
            _add_to_history(conv, 'user', message)
            system_instruction, contents = _build_chat_prompt(
                message, conv, detected_emotion, emotion_confidence)
            reply = _call_gemini(system_instruction, contents, max_tokens=1500)
            _add_to_history(conv, 'bot', reply)
            return _success(reply, detected_emotion, emotion_confidence)

        # ── General chat ──
        _add_to_history(conv, 'user', message)
        system_instruction, contents = _build_chat_prompt(
            message, conv, detected_emotion, emotion_confidence)
        reply = _call_gemini(system_instruction, contents)
        _add_to_history(conv, 'bot', reply)
        return _success(reply, detected_emotion, emotion_confidence)

    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Gemini API failed: {e}")

        # Try to give a helpful local fallback instead of a generic error
        fallback = _get_fallback_response(message, request_type)
        if fallback:
            _add_to_history(conv, 'user', message)
            _add_to_history(conv, 'bot', fallback)
            return _success(fallback, detected_emotion, emotion_confidence)

        if 'rate limit' in error_msg or 'exhausted' in error_msg or '429' in error_msg:
            reply = (
                "I'm currently experiencing high demand. "
                "Please wait a moment and try again — I'll be right back! 😊"
            )
        elif 'not configured' in error_msg or 'api_key' in error_msg:
            reply = "The AI service is not properly configured. Please contact support."
        else:
            reply = "I'm having trouble connecting right now. Please try again in a moment."

        return {
            'status': 'success',
            'reply': reply,
            'emotion_detected': detected_emotion if emotion_confidence > 0.4 else None,
            'confidence': round(emotion_confidence, 2) if emotion_confidence > 0.4 else None,
        }


# ── Fallback responses (when Gemini API is unavailable) ─────────────────────

_GREETING_PATTERNS = re.compile(
    r'^(h(ello|i|ey|ola)|good\s*(morning|afternoon|evening)|'
    r'assalam|salam|aoa|hey there|what\'?s up|yo|sup|howdy)\b',
    re.IGNORECASE,
)

_THANKS_PATTERNS = re.compile(
    r'\b(thank|thanks|thx|shukriya|appreciated)\b', re.IGNORECASE
)


def _get_fallback_response(message: str, request_type: str):
    """Return a helpful canned response when the AI backend is unavailable."""
    msg_lower = message.lower().strip()

    # Greetings
    if _GREETING_PATTERNS.search(msg_lower):
        return (
            "Hello! 👋 Welcome to **Travello** — your smart travel companion for Pakistan!\n\n"
            "Here's what I can help you with:\n"
            "- 🏨 **Find hotels** — just tell me a city (e.g. \"hotels in Lahore\")\n"
            "- 🤖 **AI Recommendations** — try the AI Recommendations widget on your dashboard\n"
            "- 🗺️ **Destinations** — ask about any Pakistani city\n"
            "- ✍️ **Text help** — I can check grammar or translate text\n\n"
            "What would you like to explore?"
        )

    # Thanks
    if _THANKS_PATTERNS.search(msg_lower):
        return (
            "You're welcome! 😊 Happy to help. "
            "Let me know if there's anything else you'd like to explore on Travello!"
        )

    # Hotel/destination queries — try live scrape even in fallback
    if request_type in ('hotel_search', 'destination_query'):
        city = _extract_city_from_message(message)
        if city:
            live_hotels, _ = _fetch_live_hotels(city)
            if live_hotels:
                lines = [f"Here are real-time hotel options in **{city}**:\n"]
                for i, h in enumerate(live_hotels[:5], 1):
                    name = h.get('hotel_name') or h.get('name', 'Hotel')
                    price = h.get('price_per_night') or h.get('total_stay_price', 'N/A')
                    rating = h.get('review_score') or h.get('rating', 'N/A')
                    lines.append(f"{i}. **{name}** — PKR {price}/night, Rating: {rating}")
                lines.append("\nSay **Book option 1** (or any number) to start booking!")
                return "\n".join(lines)
            snippet = _build_city_knowledge_snippet(city)
            if snippet:
                return (
                    f"Here's what I know about **{city}**:\n{snippet}\n\n"
                    f"For real-time hotel prices, search **{city}** in the Hotels section "
                    f"or try the **AI Recommendations** widget!"
                )

    # AI recommendation request
    if request_type == 'ai_recommendation':
        return (
            "Great idea! For **personalized AI hotel recommendations**, head to the "
            "**AI Recommendations** section on your dashboard.\n\n"
            "Our AI will ask you a few quick questions about your travel preferences "
            "and find the best hotels matched to your interests! 🎯"
        )

    return None


# ── Helpers ─────────────────────────────────────────────────────────────────

def _success(reply, emotion=None, confidence=0.0, **extra):
    result = {'status': 'success', 'reply': reply, 'model': 'gemini-2.5-flash'}
    if emotion and confidence > 0.4:
        result['emotion_detected'] = emotion
        result['confidence'] = round(confidence, 2)
    result.update(extra)
    return result


def _update_booking_flow(conv, message):
    """Extract booking params from user message and update the flow context."""
    flow = conv.get('context', {}).get('booking_flow', {})
    if not flow:
        return
    msg_lower = message.lower()

    # Date patterns (YYYY-MM-DD)
    dates = re.findall(r'(\d{4}-\d{2}-\d{2})', message)
    if dates:
        if not flow.get('check_in'):
            flow['check_in'] = dates[0]
        elif not flow.get('check_out'):
            flow['check_out'] = dates[-1]

    # Guest count
    guest_match = re.search(r'(\d+)\s*(?:guest|person|people|adult)', msg_lower)
    if guest_match:
        flow['guests'] = int(guest_match.group(1))

    # Room type
    for rt in ['single', 'double', 'triple', 'family', 'suite', 'deluxe', 'dormitory']:
        if rt in msg_lower:
            flow['room_type'] = rt
            break


def _store_offered_hotels(conv, city, live_hotels):
    """Store hotel options for later "book option X" references."""
    offered = []
    if live_hotels:
        for h in live_hotels[:5]:
            offered.append({
                'name': h.get('hotel_name') or h.get('name', 'Hotel'),
                'city': city or '',
                'price_per_night': h.get('price_per_night') or h.get('total_stay_price', ''),
                'rating': h.get('review_score') or h.get('rating', ''),
                'room_type': h.get('room_type', 'Standard Room'),
            })
    else:
        knowledge = _get_travel_knowledge()
        if city and city in knowledge.get('destinations', {}):
            for h in knowledge['destinations'][city].get('popular_hotels', [])[:5]:
                offered.append({
                    'name': h['name'],
                    'city': city,
                    'price_per_night': str(h.get('price_range', '')).split('-')[0] if h.get('price_range') else '',
                    'rating': h.get('rating', ''),
                    'room_type': 'Deluxe' if h.get('stars', 0) >= 4 else 'Standard',
                })
    if offered:
        conv['context']['offered_hotels'] = offered