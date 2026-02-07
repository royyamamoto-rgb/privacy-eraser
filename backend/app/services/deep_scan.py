"""Deep scan using Bing Search API for comprehensive people search."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import re
import httpx

from app.config import settings


@dataclass
class SearchResult:
    """Result from search API."""
    query: str
    url: str
    title: str
    snippet: str
    source_domain: str = ""


def _normalize(s: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")
    except:
        return ""


# Known data broker domains for prioritization
DATA_BROKER_DOMAINS = [
    "spokeo.com", "whitepages.com", "beenverified.com", "intelius.com",
    "truepeoplesearch.com", "fastpeoplesearch.com", "radaris.com",
    "peoplefinder.com", "peekyou.com", "zabasearch.com", "nuwber.com",
    "instantcheckmate.com", "mylife.com", "truthfinder.com", "pipl.com",
    "familytreenow.com", "thatsthem.com", "usphonebook.com", "addresses.com",
    "anywho.com", "411.com", "peoplelooker.com", "peoplefinders.com",
    "publicrecordsnow.com", "cyberbackgroundchecks.com", "checkpeople.com",
    "infotracer.com", "ussearch.com", "peoplesmart.com", "voterrecords.com",
    "clustrmaps.com", "classmates.com", "reunion.com", "spytox.com",
    "searchpeoplefree.com", "privateeye.com", "publicrecords360.com",
    "socialcatfish.com", "idtrue.com", "peoplewhiz.com", "verifythem.com",
]


def generate_queries(profile: dict) -> list[str]:
    """
    Generate search queries from profile data.

    profile keys:
      full_name, first_name, last_name, city, state,
      emails(list), phones(list), addresses(list),
      employers(list), usernames(list), date_of_birth
    """
    full_name = profile.get("full_name", "").strip()
    first_name = profile.get("first_name", "").strip()
    last_name = profile.get("last_name", "").strip()

    if not full_name and first_name and last_name:
        full_name = f"{first_name} {last_name}"

    city = (profile.get("city") or "").strip()
    state = (profile.get("state") or "").strip()

    emails = profile.get("emails") or []
    if profile.get("email") and profile.get("email") not in emails:
        emails.append(profile.get("email"))

    phones = profile.get("phones") or []
    if profile.get("phone") and profile.get("phone") not in phones:
        phones.append(profile.get("phone"))

    employers = profile.get("employers") or []
    usernames = profile.get("usernames") or []
    addresses = profile.get("addresses") or []

    queries = set()

    # Base name searches
    if full_name:
        queries.add(f'"{full_name}"')
        queries.add(f'"{full_name}" address phone')
        queries.add(f'"{full_name}" personal information')

        if city:
            queries.add(f'"{full_name}" "{city}"')
        if city and state:
            queries.add(f'"{full_name}" "{city}" "{state}"')
        if state:
            queries.add(f'"{full_name}" "{state}"')

    # Email pivots
    for email in emails[:3]:
        if email:
            queries.add(f'"{email}"')
            if full_name:
                queries.add(f'"{full_name}" "{email}"')

    # Phone pivots
    for phone in phones[:3]:
        if phone:
            # Normalize phone for search
            phone_clean = re.sub(r'[^\d]', '', phone)
            if len(phone_clean) >= 10:
                queries.add(f'"{phone}"')
                queries.add(f'"{phone_clean[-10:]}"')
                if full_name:
                    queries.add(f'"{full_name}" "{phone}"')

    # Address pivots
    for addr in addresses[:3]:
        if addr:
            addr_str = addr if isinstance(addr, str) else addr.get("street", "")
            if addr_str and full_name:
                queries.add(f'"{full_name}" "{addr_str}"')

    # Employer pivots
    for emp in employers[:2]:
        if emp and full_name:
            queries.add(f'"{full_name}" "{emp}"')

    # Username pivots
    for username in usernames[:3]:
        if username:
            queries.add(f'"{username}"')
            if full_name:
                queries.add(f'"{full_name}" "{username}"')

    # Data broker site-specific searches
    if full_name:
        for domain in DATA_BROKER_DOMAINS[:20]:
            queries.add(f'site:{domain} "{full_name}"')

    # Social media site searches
    if full_name:
        queries.add(f'site:linkedin.com/in "{full_name}"')
        queries.add(f'site:facebook.com "{full_name}"')
        queries.add(f'site:twitter.com "{full_name}"')
        queries.add(f'site:instagram.com "{full_name}"')

    # Keep bounded
    return list(sorted(queries))[:250]


async def bing_search(query: str, count: int = 10) -> list[SearchResult]:
    """Execute Bing Search API query."""
    if not settings.bing_search_key:
        return []

    headers = {"Ocp-Apim-Subscription-Key": settings.bing_search_key}
    params = {
        "q": query,
        "count": count,
        "textDecorations": False,
        "textFormat": "Raw",
        "safeSearch": "Off",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                settings.bing_search_endpoint,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

        results: list[SearchResult] = []
        web_pages = (data.get("webPages") or {}).get("value") or []

        for item in web_pages:
            url = item.get("url", "")
            results.append(
                SearchResult(
                    query=query,
                    url=url,
                    title=item.get("name", ""),
                    snippet=item.get("snippet", ""),
                    source_domain=_extract_domain(url),
                )
            )
        return results

    except Exception as e:
        print(f"Bing search error for '{query}': {e}")
        return []


def score_match(profile: dict, result: SearchResult) -> tuple[float, list[str]]:
    """
    Score how well a search result matches the profile.
    Returns (score 0-1, list of matching reasons).
    """
    reasons = []
    score = 0.0

    text = _normalize(" ".join([result.title, result.snippet, result.url]))

    # Full name match
    full_name = profile.get("full_name", "")
    if not full_name:
        first = profile.get("first_name", "")
        last = profile.get("last_name", "")
        if first and last:
            full_name = f"{first} {last}"

    full_name_norm = _normalize(full_name)
    if full_name_norm and full_name_norm in text:
        score += 0.35
        reasons.append("name")

    # Email match (high confidence)
    emails = profile.get("emails") or []
    if profile.get("email"):
        emails = list(set(emails + [profile.get("email")]))

    for email in emails:
        if email and _normalize(email) in text:
            score += 0.55
            reasons.append("email")
            break

    # Phone match (high confidence)
    phones = profile.get("phones") or []
    if profile.get("phone"):
        phones = list(set(phones + [profile.get("phone")]))

    for phone in phones:
        if phone:
            phone_clean = re.sub(r'[^\d]', '', phone)
            if phone_clean and (phone_clean in text or _normalize(phone) in text):
                score += 0.55
                reasons.append("phone")
                break

    # City match
    city = _normalize(profile.get("city") or "")
    if city and len(city) > 2 and city in text:
        score += 0.10
        reasons.append("city")

    # State match
    state = _normalize(profile.get("state") or "")
    if state and len(state) >= 2 and state in text:
        score += 0.05
        reasons.append("state")

    # Address match
    addresses = profile.get("addresses") or []
    for addr in addresses:
        addr_str = addr if isinstance(addr, str) else addr.get("street", "")
        if addr_str and _normalize(addr_str) in text:
            score += 0.20
            reasons.append("address")
            break

    # Bonus for data broker domains
    if result.source_domain in DATA_BROKER_DOMAINS:
        score += 0.15
        reasons.append("data_broker_site")

    score = min(1.0, score)
    return score, reasons


def categorize_result(result: SearchResult) -> dict:
    """Categorize the result by type and risk level."""
    domain = result.source_domain

    # Data broker - high risk
    if domain in DATA_BROKER_DOMAINS:
        return {
            "category": "data_broker",
            "risk": "high",
            "can_remove": True,
        }

    # Social media - user controlled
    social_domains = ["facebook.com", "linkedin.com", "twitter.com", "instagram.com",
                     "tiktok.com", "snapchat.com", "pinterest.com", "youtube.com"]
    if any(s in domain for s in social_domains):
        return {
            "category": "social_media",
            "risk": "medium",
            "can_remove": True,
            "note": "You control this profile",
        }

    # News/media - cannot remove
    news_domains = ["nytimes.com", "washingtonpost.com", "cnn.com", "bbc.com",
                   "foxnews.com", "nbcnews.com", "abcnews.com"]
    if any(s in domain for s in news_domains):
        return {
            "category": "news",
            "risk": "low",
            "can_remove": False,
            "note": "News articles generally cannot be removed",
        }

    # Government/court - cannot remove
    gov_domains = [".gov", "courtlistener.com", "unicourt.com", "pacer.gov"]
    if any(s in domain for s in gov_domains):
        return {
            "category": "government",
            "risk": "medium",
            "can_remove": False,
            "note": "Public records cannot be removed",
        }

    # Default
    return {
        "category": "other",
        "risk": "medium",
        "can_remove": True,
    }


async def deep_scan_profile(profile: dict, max_queries: int = 80) -> list[dict]:
    """
    Run deep scan using Bing Search API.

    Returns list of high-confidence hits with scores.
    """
    queries = generate_queries(profile)

    all_hits = []
    seen_urls = set()

    for query in queries[:max_queries]:
        try:
            results = await bing_search(query, count=8)

            for result in results:
                # Skip duplicates
                if result.url in seen_urls:
                    continue
                seen_urls.add(result.url)

                score, reasons = score_match(profile, result)

                # Only include high-confidence matches
                if score >= 0.40:
                    category_info = categorize_result(result)

                    all_hits.append({
                        "score": score,
                        "reasons": reasons,
                        "url": result.url,
                        "title": result.title,
                        "snippet": result.snippet,
                        "domain": result.source_domain,
                        "query": result.query,
                        **category_info,
                    })

        except Exception as e:
            print(f"Error processing query '{query}': {e}")
            continue

    # Sort by score descending
    all_hits.sort(key=lambda x: x["score"], reverse=True)

    # Return top 200
    return all_hits[:200]
