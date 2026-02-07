"""Data broker scanner service - Deep Web Search."""

import asyncio
import re
import urllib.parse
from dataclasses import dataclass
from typing import Optional
import httpx

from app.models.user import UserProfile


@dataclass
class ScanResult:
    """Result of scanning a single broker."""
    broker_id: str
    found: bool
    profile_url: Optional[str] = None
    data_found: Optional[dict] = None
    error: Optional[str] = None
    source: Optional[str] = None  # broker, google, social


# Additional people search sites to scan (beyond database)
ADDITIONAL_SEARCH_SITES = [
    {"name": "PeekYou", "url": "https://www.peekyou.com/{first_name}_{last_name}"},
    {"name": "ZabaSearch", "url": "https://www.zabasearch.com/people/{first_name}+{last_name}/"},
    {"name": "That's Them", "url": "https://thatsthem.com/name/{first_name}-{last_name}"},
    {"name": "Addresses.com", "url": "https://www.addresses.com/people/{first_name}+{last_name}"},
    {"name": "Nuwber", "url": "https://nuwber.com/search?name={first_name}%20{last_name}"},
    {"name": "ClustrMaps", "url": "https://clustrmaps.com/persons/{first_name}-{last_name}"},
    {"name": "Cyberbackgroundchecks", "url": "https://www.cyberbackgroundchecks.com/people/{first_name}-{last_name}"},
    {"name": "PublicRecords360", "url": "https://publicrecords360.com/records/{first_name}-{last_name}"},
    {"name": "PrivateEye", "url": "https://www.privateeye.com/people/{first_name}-{last_name}"},
    {"name": "Spokeo Alt", "url": "https://www.spokeo.com/search?q={first_name}+{last_name}"},
    {"name": "411.com", "url": "https://www.411.com/name/{first_name}-{last_name}/"},
    {"name": "AnyWho", "url": "https://www.anywho.com/people/{first_name}+{last_name}"},
    {"name": "FamilyTreeNow", "url": "https://www.familytreenow.com/search/genealogy/results?first={first_name}&last={last_name}"},
    {"name": "Instant Checkmate", "url": "https://www.instantcheckmate.com/people/{first_name}-{last_name}"},
    {"name": "SearchPeopleFree", "url": "https://www.searchpeoplefree.com/find/{first_name}-{last_name}"},
]

# Social media platforms to check
SOCIAL_PLATFORMS = [
    {"name": "LinkedIn", "url": "https://www.linkedin.com/pub/dir?firstName={first_name}&lastName={last_name}"},
    {"name": "Facebook", "url": "https://www.facebook.com/public/{first_name}-{last_name}"},
    {"name": "Twitter/X", "url": "https://twitter.com/search?q={first_name}%20{last_name}&f=user"},
    {"name": "Instagram", "url": "https://www.instagram.com/{first_name}{last_name}/"},
]


class BrokerScanner:
    """Deep web scanner for personal information exposure."""

    def __init__(self):
        self.timeout = 20  # 20 seconds for thorough scanning
        self.concurrent_limit = 10  # More concurrent scans for speed
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def scan_broker(
        self,
        broker,
        profile: UserProfile,
    ) -> ScanResult:
        """Scan a single broker for user's information."""

        if not broker.search_url_pattern:
            return ScanResult(
                broker_id=str(broker.id),
                found=False,
                error="No search URL pattern defined",
            )

        # Build search URL with multiple name formats
        first_name = (profile.first_name or "").strip()
        last_name = (profile.last_name or "").strip()

        search_url = broker.search_url_pattern.format(
            first_name=first_name.lower().replace(" ", "-"),
            last_name=last_name.lower().replace(" ", "-"),
            city=self._get_city(profile),
            state=self._get_state(profile),
        )

        return await self._scan_url(
            url=search_url,
            broker_id=str(broker.id),
            profile=profile,
            source="broker"
        )

    async def _scan_url(
        self,
        url: str,
        broker_id: str,
        profile: UserProfile,
        source: str = "broker"
    ) -> ScanResult:
        """Scan a URL for personal information."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.headers
            ) as client:
                response = await client.get(url)

                if response.status_code != 200:
                    return ScanResult(
                        broker_id=broker_id,
                        found=False,
                        error=f"HTTP {response.status_code}",
                        source=source,
                    )

                content = response.text
                found = self._check_if_found(content, profile)

                profile_url = None
                data_found = None

                if found:
                    profile_url = str(response.url)
                    data_found = self._extract_found_data(content, profile)

                return ScanResult(
                    broker_id=broker_id,
                    found=found,
                    profile_url=profile_url,
                    data_found=data_found,
                    source=source,
                )

        except httpx.TimeoutException:
            return ScanResult(
                broker_id=broker_id,
                found=False,
                error="Request timeout",
                source=source,
            )
        except Exception as e:
            return ScanResult(
                broker_id=broker_id,
                found=False,
                error=str(e)[:100],
                source=source,
            )

    def _check_if_found(self, content: str, profile) -> bool:
        """Deep check if user's profile was found on the page."""
        content_lower = content.lower()

        # Check for "no results" indicators first
        no_result_indicators = [
            "no results",
            "no records found",
            "we couldn't find",
            "no matches",
            "0 results",
            "no people found",
            "we found 0",
            "couldn't find anyone",
            "did not find",
            "no listings",
            "not found",
            "try again",
            "no data available",
            "person not found",
        ]

        for indicator in no_result_indicators:
            if indicator in content_lower:
                return False

        first_name = (profile.first_name or "").lower()
        last_name = (profile.last_name or "").lower()

        if not first_name or not last_name:
            return False

        # Check for full name
        full_name = f"{first_name} {last_name}"
        if full_name in content_lower:
            return True

        # Check name with middle initial if available
        if profile.middle_name:
            middle_init = profile.middle_name[0].lower()
            name_with_middle = f"{first_name} {middle_init} {last_name}"
            if name_with_middle in content_lower:
                return True

        # Check if both names appear with profile indicators
        if first_name in content_lower and last_name in content_lower:
            profile_indicators = [
                "age", "address", "phone", "lives in", "related to",
                "associated with", "current address", "previous address",
                "relatives", "email", "born", "years old", "resident",
                "property", "court records", "criminal", "marriage",
                "divorce", "bankruptcy", "liens", "judgments"
            ]
            if any(ind in content_lower for ind in profile_indicators):
                return True

        return False

    def _extract_found_data(self, content: str, profile) -> dict:
        """Extract detailed data found about the user."""
        data = {
            "name": True,
            "address": False,
            "phone": False,
            "email": False,
            "relatives": False,
            "age": False,
            "social_media": False,
            "property_records": False,
            "court_records": False,
            "education": False,
            "employment": False,
        }

        content_lower = content.lower()

        # Address detection
        if any(word in content_lower for word in [
            "address", "street", "lives in", "lived in", "current address",
            "previous address", "residence", "ave", "blvd", "rd", "drive"
        ]):
            data["address"] = True

        # Phone detection
        phone_patterns = [
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',
            r'\d{3}[-.]?\d{3}[-.]?\d{4}',
        ]
        if any(word in content_lower for word in ["phone", "mobile", "cell", "telephone"]):
            data["phone"] = True
        for pattern in phone_patterns:
            if re.search(pattern, content):
                data["phone"] = True
                break

        # Email detection
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        if re.search(email_pattern, content) or "email" in content_lower:
            data["email"] = True

        # Relatives detection
        if any(word in content_lower for word in [
            "relatives", "family", "associates", "related to", "mother",
            "father", "sister", "brother", "spouse", "wife", "husband"
        ]):
            data["relatives"] = True

        # Age detection
        if any(word in content_lower for word in ["age", "born", "birth", "years old", "dob"]):
            data["age"] = True

        # Social media detection
        if any(word in content_lower for word in [
            "facebook", "twitter", "linkedin", "instagram", "tiktok", "social"
        ]):
            data["social_media"] = True

        # Property records
        if any(word in content_lower for word in [
            "property", "real estate", "home value", "ownership", "deed"
        ]):
            data["property_records"] = True

        # Court records
        if any(word in content_lower for word in [
            "court", "criminal", "arrest", "judgment", "lawsuit", "bankruptcy"
        ]):
            data["court_records"] = True

        # Education
        if any(word in content_lower for word in [
            "education", "school", "university", "college", "degree"
        ]):
            data["education"] = True

        # Employment
        if any(word in content_lower for word in [
            "employment", "employer", "work", "job", "occupation", "company"
        ]):
            data["employment"] = True

        return data

    def _get_city(self, profile: UserProfile) -> str:
        """Get city from profile addresses."""
        if profile.addresses and len(profile.addresses) > 0:
            return profile.addresses[0].get("city", "") or ""
        return ""

    def _get_state(self, profile: UserProfile) -> str:
        """Get state from profile addresses."""
        if profile.addresses and len(profile.addresses) > 0:
            return profile.addresses[0].get("state", "") or ""
        return ""

    async def deep_scan_additional_sites(self, profile: UserProfile) -> list[ScanResult]:
        """Scan additional people search sites not in database."""
        first_name = (profile.first_name or "").strip().lower()
        last_name = (profile.last_name or "").strip().lower()

        if not first_name or not last_name:
            return []

        results = []
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def scan_site(site):
            async with semaphore:
                url = site["url"].format(
                    first_name=first_name.replace(" ", "-"),
                    last_name=last_name.replace(" ", "-"),
                )
                result = await self._scan_url(
                    url=url,
                    broker_id=f"additional_{site['name'].lower().replace(' ', '_')}",
                    profile=profile,
                    source="additional_site"
                )
                if result.found:
                    result.data_found = result.data_found or {}
                    result.data_found["site_name"] = site["name"]
                return result

        tasks = [scan_site(site) for site in ADDITIONAL_SEARCH_SITES]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r.found]

    async def scan_social_media(self, profile: UserProfile) -> list[ScanResult]:
        """Scan social media platforms for user profiles."""
        first_name = (profile.first_name or "").strip().lower()
        last_name = (profile.last_name or "").strip().lower()

        if not first_name or not last_name:
            return []

        results = []
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def scan_platform(platform):
            async with semaphore:
                url = platform["url"].format(
                    first_name=first_name.replace(" ", ""),
                    last_name=last_name.replace(" ", ""),
                )
                result = await self._scan_url(
                    url=url,
                    broker_id=f"social_{platform['name'].lower().replace('/', '_')}",
                    profile=profile,
                    source="social_media"
                )
                if result.found:
                    result.data_found = result.data_found or {}
                    result.data_found["platform"] = platform["name"]
                return result

        tasks = [scan_platform(p) for p in SOCIAL_PLATFORMS]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r.found]

    async def google_search_scan(self, profile: UserProfile) -> list[ScanResult]:
        """Search Google for name mentions and exposed information."""
        first_name = (profile.first_name or "").strip()
        last_name = (profile.last_name or "").strip()

        if not first_name or not last_name:
            return []

        results = []
        full_name = f"{first_name} {last_name}"
        city = self._get_city(profile)
        state = self._get_state(profile)

        # Different search queries
        search_queries = [
            f'"{full_name}"',
            f'"{full_name}" address',
            f'"{full_name}" phone',
            f'"{full_name}" email',
        ]

        if city and state:
            search_queries.append(f'"{full_name}" {city} {state}')

        # Use DuckDuckGo HTML search (more permissive than Google)
        for query in search_queries[:2]:  # Limit to avoid rate limiting
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    headers=self.headers
                ) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        content = response.text

                        # Check if name appears in search results with concerning context
                        if self._check_search_results(content, profile):
                            results.append(ScanResult(
                                broker_id="google_search",
                                found=True,
                                profile_url=url,
                                data_found={
                                    "query": query,
                                    "name": True,
                                    "search_exposure": True
                                },
                                source="search_engine"
                            ))
                            break  # One result is enough
            except Exception:
                continue

            await asyncio.sleep(1)  # Rate limiting

        return results

    def _check_search_results(self, content: str, profile) -> bool:
        """Check if search results contain concerning personal info."""
        content_lower = content.lower()
        first_name = (profile.first_name or "").lower()
        last_name = (profile.last_name or "").lower()

        if first_name not in content_lower or last_name not in content_lower:
            return False

        # Look for people search sites in results
        data_broker_domains = [
            "spokeo", "whitepages", "beenverified", "truepeoplesearch",
            "fastpeoplesearch", "intelius", "radaris", "peoplefinder",
            "peekyou", "zabasearch", "nuwber", "instantcheckmate"
        ]

        for domain in data_broker_domains:
            if domain in content_lower:
                return True

        return False

    async def scan_all_brokers(
        self,
        brokers: list,
        profile: UserProfile,
    ) -> list[ScanResult]:
        """Comprehensive deep scan across all sources."""
        all_results = []
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        # 1. Scan database brokers
        async def scan_with_limit(broker):
            async with semaphore:
                return await self.scan_broker(broker, profile)

        broker_tasks = [scan_with_limit(broker) for broker in brokers]
        broker_results = await asyncio.gather(*broker_tasks)
        all_results.extend(broker_results)

        # 2. Scan additional people search sites
        additional_results = await self.deep_scan_additional_sites(profile)
        all_results.extend(additional_results)

        # 3. Scan social media
        social_results = await self.scan_social_media(profile)
        all_results.extend(social_results)

        # 4. Google/DuckDuckGo search scan
        search_results = await self.google_search_scan(profile)
        all_results.extend(search_results)

        return all_results
