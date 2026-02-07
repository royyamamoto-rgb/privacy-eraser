"""TruePeopleSearch data broker implementation."""

from typing import Optional
from playwright.async_api import async_playwright

from brokers.base import BaseBroker, BrokerInfo


class TruePeopleSearchBroker(BaseBroker):
    """TruePeopleSearch opt-out implementation - can be automated."""

    @property
    def info(self) -> BrokerInfo:
        return BrokerInfo(
            name="TruePeopleSearch",
            domain="truepeoplesearch.com",
            category="people_search",
            search_url_pattern="https://www.truepeoplesearch.com/results?name={first_name}%20{last_name}&citystatezip={city}%20{state}",
            opt_out_url="https://www.truepeoplesearch.com/removal",
            opt_out_method="form",
            opt_out_email=None,
            opt_out_instructions="""
1. Find your profile on TruePeopleSearch
2. Copy the profile URL
3. Go to https://www.truepeoplesearch.com/removal
4. Paste your profile URL
5. Click "Remove This Record"
6. Your listing will be removed within 72 hours
""",
            requires_verification=False,
            requires_id=False,
            processing_days=3,
            can_automate=True,  # No CAPTCHA, no verification
            difficulty=1,
            captcha_type="none",
        )

    async def search(self, first_name: str, last_name: str, city: str, state: str) -> dict:
        """Search for a person on TruePeopleSearch."""

        search_url = f"https://www.truepeoplesearch.com/results?name={first_name}%20{last_name}"
        if city:
            search_url += f"&citystatezip={city}"
        if state:
            search_url += f"%20{state}"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.goto(search_url, timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                content = await page.content()

                # Check for results
                full_name = f"{first_name} {last_name}".lower()
                found = full_name in content.lower() and "no results found" not in content.lower()

                # Get first profile link
                profile_url = None
                if found:
                    profile_link = await page.query_selector('a[href*="/find/person/"]')
                    if profile_link:
                        profile_url = await profile_link.get_attribute("href")
                        if profile_url and not profile_url.startswith("http"):
                            profile_url = f"https://www.truepeoplesearch.com{profile_url}"

                await browser.close()

                return {
                    "found": found,
                    "profile_url": profile_url or search_url if found else None,
                    "data_found": {
                        "name": True,
                        "address": "address" in content.lower() or "lives in" in content.lower(),
                        "phone": "phone" in content.lower(),
                        "email": "email" in content.lower(),
                        "relatives": "relatives" in content.lower() or "associated" in content.lower(),
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
        """Auto-submit opt-out request."""

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                page = await context.new_page()

                # Go to removal page
                await page.goto("https://www.truepeoplesearch.com/removal", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Enter profile URL
                url_input = await page.query_selector('input[name="RecordUrl"], input[placeholder*="URL"]')
                if url_input:
                    await url_input.fill(profile_url)

                # Click remove button
                remove_button = await page.query_selector('button[type="submit"], input[value*="Remove"]')
                if remove_button:
                    await remove_button.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)

                # Check for success
                content = await page.content()
                success = any(phrase in content.lower() for phrase in [
                    "has been removed",
                    "successfully removed",
                    "removal request",
                    "will be removed",
                ])

                await browser.close()

                return {
                    "success": success,
                    "confirmation": "SUBMITTED" if success else None,
                    "error": None if success else "Could not confirm submission",
                }

        except Exception as e:
            return {
                "success": False,
                "confirmation": None,
                "error": str(e),
            }

    def get_form_selectors(self) -> dict:
        return {
            "profile_url": 'input[name="RecordUrl"], input[placeholder*="URL"]',
            "submit": 'button[type="submit"], input[value*="Remove"]',
        }
