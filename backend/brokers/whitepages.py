"""WhitePages data broker implementation."""

from typing import Optional
from playwright.async_api import async_playwright

from brokers.base import BaseBroker, BrokerInfo


class WhitePagesBroker(BaseBroker):
    """WhitePages opt-out implementation."""

    @property
    def info(self) -> BrokerInfo:
        return BrokerInfo(
            name="WhitePages",
            domain="whitepages.com",
            category="people_search",
            search_url_pattern="https://www.whitepages.com/name/{first_name}-{last_name}/{city}-{state}",
            opt_out_url="https://www.whitepages.com/suppression-requests",
            opt_out_method="form",
            opt_out_email=None,
            opt_out_instructions="""
1. Go to https://www.whitepages.com/suppression-requests
2. Search for your listing
3. Click on your name in the results
4. Scroll down and click "Control your info"
5. Enter your phone number for verification
6. Complete the verification process
7. Wait for confirmation email
""",
            requires_verification=True,
            requires_id=False,
            processing_days=3,
            can_automate=False,  # Requires phone verification
            difficulty=3,
            captcha_type="none",
        )

    async def search(self, first_name: str, last_name: str, city: str, state: str) -> dict:
        """Search for a person on WhitePages."""

        search_url = f"https://www.whitepages.com/name/{first_name}-{last_name}"
        if city and state:
            search_url += f"/{city}-{state}"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(search_url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                content = await page.content()

                # Check for search results
                full_name = f"{first_name} {last_name}".lower()
                found = full_name in content.lower()

                # Look for person cards
                person_elements = await page.query_selector_all('[data-testid="person-name"], .person-primary-info')

                await browser.close()

                return {
                    "found": found and len(person_elements) > 0,
                    "profile_url": search_url if found else None,
                    "data_found": {
                        "name": True,
                        "address": "address" in content.lower() or "lives in" in content.lower(),
                        "phone": "phone" in content.lower(),
                        "email": False,  # WhitePages typically doesn't show emails
                        "relatives": "relatives" in content.lower() or "related to" in content.lower(),
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
        """Submit opt-out - requires phone verification."""
        return {
            "success": False,
            "confirmation": None,
            "error": "WhitePages requires phone verification - manual submission needed",
            "instructions": self.info.opt_out_instructions,
        }

    def get_form_selectors(self) -> dict:
        return {
            "phone": 'input[name="phone"], input[type="tel"]',
            "submit": 'button[type="submit"]',
        }
