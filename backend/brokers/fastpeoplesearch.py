"""FastPeopleSearch data broker implementation."""

from typing import Optional
from playwright.async_api import async_playwright

from brokers.base import BaseBroker, BrokerInfo


class FastPeopleSearchBroker(BaseBroker):
    """FastPeopleSearch opt-out implementation - can be automated."""

    @property
    def info(self) -> BrokerInfo:
        return BrokerInfo(
            name="FastPeopleSearch",
            domain="fastpeoplesearch.com",
            category="people_search",
            search_url_pattern="https://www.fastpeoplesearch.com/name/{first_name}-{last_name}_{city}-{state}",
            opt_out_url="https://www.fastpeoplesearch.com/removal",
            opt_out_method="form",
            opt_out_email=None,
            opt_out_instructions="""
1. Find your profile on FastPeopleSearch
2. Click "View Free Details" to get the full profile URL
3. Go to https://www.fastpeoplesearch.com/removal
4. Enter your profile URL
5. Check "I'm not a robot"
6. Click "Begin Removal Process"
""",
            requires_verification=False,
            requires_id=False,
            processing_days=1,
            can_automate=True,  # Simple form, no verification
            difficulty=1,
            captcha_type="recaptcha",
        )

    async def search(self, first_name: str, last_name: str, city: str, state: str) -> dict:
        """Search for a person on FastPeopleSearch."""

        search_url = f"https://www.fastpeoplesearch.com/name/{first_name}-{last_name}"
        if city and state:
            search_url += f"_{city}-{state}"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(search_url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                content = await page.content()
                full_name = f"{first_name} {last_name}".lower()
                found = full_name in content.lower() and "no results" not in content.lower()

                # Try to get profile URL
                profile_url = None
                if found:
                    link = await page.query_selector('a[href*="/address/"]')
                    if link:
                        href = await link.get_attribute("href")
                        if href:
                            profile_url = f"https://www.fastpeoplesearch.com{href}" if href.startswith("/") else href

                await browser.close()

                return {
                    "found": found,
                    "profile_url": profile_url or search_url if found else None,
                    "data_found": {
                        "name": True,
                        "address": "address" in content.lower(),
                        "phone": "phone" in content.lower(),
                        "email": "email" in content.lower(),
                        "relatives": "relative" in content.lower(),
                        "age": "age" in content.lower(),
                    } if found else None,
                }

        except Exception as e:
            return {"found": False, "profile_url": None, "error": str(e)}

    async def submit_opt_out(self, profile_url: str, user_info: dict) -> dict:
        """Auto-submit opt-out request."""

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto("https://www.fastpeoplesearch.com/removal", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Fill URL
                url_input = await page.query_selector('input[name="url"], input[placeholder*="url"]')
                if url_input:
                    await url_input.fill(profile_url)

                # Would need CAPTCHA solving here
                await browser.close()

                return {
                    "success": False,
                    "confirmation": None,
                    "error": "CAPTCHA required for FastPeopleSearch",
                    "instructions": self.info.opt_out_instructions,
                }

        except Exception as e:
            return {"success": False, "confirmation": None, "error": str(e)}

    def get_form_selectors(self) -> dict:
        return {
            "profile_url": 'input[name="url"]',
            "submit": 'button[type="submit"]',
        }
