"""Intelius data broker implementation."""

from typing import Optional
from playwright.async_api import async_playwright

from brokers.base import BaseBroker, BrokerInfo


class InteliusBroker(BaseBroker):
    """Intelius opt-out implementation."""

    @property
    def info(self) -> BrokerInfo:
        return BrokerInfo(
            name="Intelius",
            domain="intelius.com",
            category="background_check",
            search_url_pattern="https://www.intelius.com/people/{first_name}-{last_name}/{state}/{city}",
            opt_out_url="https://www.intelius.com/opt-out/submit/",
            opt_out_method="form",
            opt_out_email="privacy@intelius.com",
            opt_out_instructions="""
1. Go to https://www.intelius.com/opt-out/submit/
2. Enter your name, city, state
3. Enter your email for confirmation
4. Complete the form and submit
5. Check your email for verification
6. Click verification link
7. Processing takes up to 72 hours
""",
            requires_verification=True,
            requires_id=False,
            processing_days=3,
            can_automate=False,  # Requires email verification
            difficulty=2,
            captcha_type="recaptcha",
        )

    async def search(self, first_name: str, last_name: str, city: str, state: str) -> dict:
        """Search for a person on Intelius."""

        search_url = f"https://www.intelius.com/people/{first_name}-{last_name}"
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
                full_name = f"{first_name} {last_name}".lower()
                found = full_name in content.lower() and "no results" not in content.lower()

                await browser.close()

                return {
                    "found": found,
                    "profile_url": search_url if found else None,
                    "data_found": {
                        "name": True,
                        "address": "address" in content.lower() or "location" in content.lower(),
                        "phone": "phone" in content.lower(),
                        "email": "email" in content.lower(),
                        "relatives": "relatives" in content.lower() or "family" in content.lower(),
                        "age": "age" in content.lower() or "birth" in content.lower(),
                    } if found else None,
                }

        except Exception as e:
            return {"found": False, "profile_url": None, "error": str(e)}

    async def submit_opt_out(self, profile_url: str, user_info: dict) -> dict:
        """Submit opt-out - requires email verification."""
        return {
            "success": False,
            "confirmation": None,
            "error": "Intelius requires email verification - manual submission needed",
            "instructions": self.info.opt_out_instructions,
        }

    def get_form_selectors(self) -> dict:
        return {
            "first_name": 'input[name="firstName"]',
            "last_name": 'input[name="lastName"]',
            "city": 'input[name="city"]',
            "state": 'select[name="state"]',
            "email": 'input[type="email"]',
            "submit": 'button[type="submit"]',
        }
