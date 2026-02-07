"""Spokeo data broker implementation."""

from typing import Optional
from playwright.async_api import async_playwright

from brokers.base import BaseBroker, BrokerInfo


class SpokeoBroker(BaseBroker):
    """Spokeo opt-out implementation."""

    @property
    def info(self) -> BrokerInfo:
        return BrokerInfo(
            name="Spokeo",
            domain="spokeo.com",
            category="people_search",
            search_url_pattern="https://www.spokeo.com/{first_name}-{last_name}/{state}/{city}",
            opt_out_url="https://www.spokeo.com/optout",
            opt_out_method="form",
            opt_out_email=None,
            opt_out_instructions="""
1. Go to https://www.spokeo.com/optout
2. Enter the URL of your profile
3. Enter your email address
4. Complete the CAPTCHA
5. Click "Remove this listing"
6. Check your email for verification link
7. Click the verification link to confirm removal
""",
            requires_verification=True,
            requires_id=False,
            processing_days=3,
            can_automate=False,  # Requires CAPTCHA
            difficulty=2,
            captcha_type="recaptcha",
        )

    async def search(self, first_name: str, last_name: str, city: str, state: str) -> dict:
        """Search for a person on Spokeo."""

        search_url = f"https://www.spokeo.com/{first_name}-{last_name}"
        if state:
            search_url += f"/{state}"
        if city:
            search_url += f"/{city}"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(search_url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                content = await page.content()
                current_url = page.url

                # Check for results
                full_name = f"{first_name} {last_name}".lower()
                found = full_name in content.lower() and "no results" not in content.lower()

                # Look for profile cards
                profile_cards = await page.query_selector_all('[data-testid="person-card"]')
                if not profile_cards:
                    profile_cards = await page.query_selector_all('.person-card, .search-result')

                await browser.close()

                return {
                    "found": found or len(profile_cards) > 0,
                    "profile_url": current_url if found else None,
                    "data_found": {
                        "name": True,
                        "address": "address" in content.lower(),
                        "phone": "phone" in content.lower(),
                        "email": "@" in content,
                        "relatives": "relatives" in content.lower(),
                        "age": "age" in content.lower() or "born" in content.lower(),
                    } if found else None,
                }

        except Exception as e:
            return {
                "found": False,
                "profile_url": None,
                "data_found": None,
                "error": str(e),
            }

    async def submit_opt_out(self, profile_url: str, user_info: dict) -> dict:
        """Submit opt-out - requires manual CAPTCHA."""
        return {
            "success": False,
            "confirmation": None,
            "error": "Spokeo requires CAPTCHA - manual submission needed",
            "instructions": self.info.opt_out_instructions,
        }

    def get_form_selectors(self) -> dict:
        return {
            "profile_url": 'input[name="url"], input[id="url"]',
            "email": 'input[name="email"], input[type="email"]',
            "submit": 'button[type="submit"], input[type="submit"]',
        }
