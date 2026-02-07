"""Data broker scanner service."""

import asyncio
from dataclasses import dataclass
from typing import Optional
import httpx
from playwright.async_api import async_playwright

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
    """Service for scanning data broker sites."""

    def __init__(self):
        self.timeout = 30000  # 30 seconds
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
        search_url = broker.search_url_pattern.format(
            first_name=profile.first_name or "",
            last_name=profile.last_name or "",
            city=self._get_city(profile),
            state=self._get_state(profile),
        )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(search_url, timeout=self.timeout)
                await page.wait_for_load_state("networkidle", timeout=self.timeout)

                # Check if profile was found
                # This would need to be customized per broker
                content = await page.content()
                found = await self._check_if_found(page, broker, profile)

                profile_url = None
                data_found = None

                if found:
                    profile_url = page.url
                    data_found = await self._extract_found_data(page, broker)

                await browser.close()

                return ScanResult(
                    broker_id=str(broker.id),
                    found=found,
                    profile_url=profile_url,
                    data_found=data_found,
                )

        except Exception as e:
            return ScanResult(
                broker_id=str(broker.id),
                found=False,
                error=str(e),
            )

    async def _check_if_found(self, page, broker, profile) -> bool:
        """Check if user's profile was found on the page."""
        # Look for common indicators
        content = await page.content()
        content_lower = content.lower()

        # Check if name appears
        if profile.first_name and profile.last_name:
            full_name = f"{profile.first_name} {profile.last_name}".lower()
            if full_name in content_lower:
                return True

        # Check for "no results" indicators
        no_result_indicators = [
            "no results",
            "no records found",
            "we couldn't find",
            "no matches",
            "0 results",
        ]

        for indicator in no_result_indicators:
            if indicator in content_lower:
                return False

        return False

    async def _extract_found_data(self, page, broker) -> dict:
        """Extract what data was found about the user."""
        data = {
            "name": False,
            "address": False,
            "phone": False,
            "email": False,
            "relatives": False,
            "age": False,
        }

        content = await page.content()
        content_lower = content.lower()

        # Simple heuristics - would need refinement per broker
        if any(word in content_lower for word in ["address", "street", "city", "state"]):
            data["address"] = True

        if any(word in content_lower for word in ["phone", "mobile", "cell"]):
            data["phone"] = True

        if "@" in content and any(word in content_lower for word in ["email", "mail"]):
            data["email"] = True

        if any(word in content_lower for word in ["relatives", "family", "associates"]):
            data["relatives"] = True

        if any(word in content_lower for word in ["age", "born", "birth"]):
            data["age"] = True

        data["name"] = True  # If we found a profile, name is always there

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
        results = []
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def scan_with_limit(broker):
            async with semaphore:
                return await self.scan_broker(broker, profile)

        tasks = [scan_with_limit(broker) for broker in brokers]
        results = await asyncio.gather(*tasks)

        return results
