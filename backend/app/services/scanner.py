"""Data broker scanner service."""

import asyncio
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


class BrokerScanner:
    """Service for scanning data broker sites using HTTP requests."""

    def __init__(self):
        self.timeout = 15  # 15 seconds
        self.concurrent_limit = 5  # Max concurrent scans

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

        # Build search URL
        first_name = (profile.first_name or "").lower().replace(" ", "-")
        last_name = (profile.last_name or "").lower().replace(" ", "-")

        search_url = broker.search_url_pattern.format(
            first_name=first_name,
            last_name=last_name,
            city=self._get_city(profile),
            state=self._get_state(profile),
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
            ) as client:
                response = await client.get(search_url)

                if response.status_code != 200:
                    return ScanResult(
                        broker_id=str(broker.id),
                        found=False,
                        error=f"HTTP {response.status_code}",
                    )

                content = response.text
                found = self._check_if_found(content, broker, profile)

                profile_url = None
                data_found = None

                if found:
                    profile_url = str(response.url)
                    data_found = self._extract_found_data(content, broker)

                return ScanResult(
                    broker_id=str(broker.id),
                    found=found,
                    profile_url=profile_url,
                    data_found=data_found,
                )

        except httpx.TimeoutException:
            return ScanResult(
                broker_id=str(broker.id),
                found=False,
                error="Request timeout",
            )
        except Exception as e:
            return ScanResult(
                broker_id=str(broker.id),
                found=False,
                error=str(e),
            )

    def _check_if_found(self, content: str, broker, profile) -> bool:
        """Check if user's profile was found on the page."""
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
        ]

        for indicator in no_result_indicators:
            if indicator in content_lower:
                return False

        # Check if name appears
        if profile.first_name and profile.last_name:
            full_name = f"{profile.first_name} {profile.last_name}".lower()
            if full_name in content_lower:
                return True

            # Also check if both names appear separately
            if profile.first_name.lower() in content_lower and profile.last_name.lower() in content_lower:
                # Verify it looks like a person profile, not just a form
                profile_indicators = ["age", "address", "phone", "lives in", "related to", "associated with"]
                if any(ind in content_lower for ind in profile_indicators):
                    return True

        return False

    def _extract_found_data(self, content: str, broker) -> dict:
        """Extract what data was found about the user."""
        data = {
            "name": True,  # If we found a profile, name is always there
            "address": False,
            "phone": False,
            "email": False,
            "relatives": False,
            "age": False,
        }

        content_lower = content.lower()

        # Simple heuristics
        if any(word in content_lower for word in ["address", "street", "lives in", "lived in"]):
            data["address"] = True

        if any(word in content_lower for word in ["phone", "mobile", "cell", "(xxx)"]):
            data["phone"] = True

        if "@" in content or any(word in content_lower for word in ["email"]):
            data["email"] = True

        if any(word in content_lower for word in ["relatives", "family", "associates", "related to"]):
            data["relatives"] = True

        if any(word in content_lower for word in ["age", "born", "birth", "years old"]):
            data["age"] = True

        return data

    def _get_city(self, profile: UserProfile) -> str:
        """Get city from profile addresses."""
        if profile.addresses and len(profile.addresses) > 0:
            return profile.addresses[0].get("city", "")
        return ""

    def _get_state(self, profile: UserProfile) -> str:
        """Get state from profile addresses."""
        if profile.addresses and len(profile.addresses) > 0:
            return profile.addresses[0].get("state", "")
        return ""

    async def scan_all_brokers(
        self,
        brokers: list,
        profile: UserProfile,
    ) -> list[ScanResult]:
        """Scan all brokers with rate limiting."""
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def scan_with_limit(broker):
            async with semaphore:
                return await self.scan_broker(broker, profile)

        tasks = [scan_with_limit(broker) for broker in brokers]
        results = await asyncio.gather(*tasks)

        return results
