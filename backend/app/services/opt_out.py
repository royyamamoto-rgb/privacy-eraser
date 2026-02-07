"""Automated opt-out service - submits removal requests automatically."""

import asyncio
import httpx
from datetime import datetime
from typing import Optional
import re


# Broker opt-out configurations
BROKER_OPT_OUT_CONFIG = {
    "spokeo": {
        "method": "form",
        "url": "https://www.spokeo.com/optout",
        "api_url": "https://www.spokeo.com/optout/submit",
        "fields": {
            "url": "{profile_url}",
            "email": "{user_email}",
        },
        "can_automate": True,
    },
    "truepeoplesearch": {
        "method": "form",
        "url": "https://www.truepeoplesearch.com/removal",
        "api_url": "https://www.truepeoplesearch.com/api/removal",
        "fields": {
            "recordUrl": "{profile_url}",
        },
        "can_automate": True,
    },
    "fastpeoplesearch": {
        "method": "form",
        "url": "https://www.fastpeoplesearch.com/removal",
        "api_url": "https://www.fastpeoplesearch.com/removal/submit",
        "can_automate": True,
    },
    "beenverified": {
        "method": "email",
        "email": "privacy@beenverified.com",
        "subject": "Opt-Out Request - Data Removal",
        "can_automate": True,
    },
    "intelius": {
        "method": "email",
        "email": "privacy@intelius.com",
        "subject": "Opt-Out Request - Personal Data Removal",
        "can_automate": True,
    },
    "whitepages": {
        "method": "email",
        "email": "privacy@whitepages.com",
        "subject": "Data Removal Request",
        "can_automate": True,
    },
    "radaris": {
        "method": "email",
        "email": "privacy@radaris.com",
        "subject": "CCPA/GDPR Data Deletion Request",
        "can_automate": True,
    },
    "peoplefinder": {
        "method": "email",
        "email": "privacy@peoplefinder.com",
        "subject": "Opt-Out Request",
        "can_automate": True,
    },
    "peekyou": {
        "method": "email",
        "email": "privacy@peekyou.com",
        "subject": "Data Removal Request",
        "can_automate": True,
    },
    "instantcheckmate": {
        "method": "email",
        "email": "privacy@instantcheckmate.com",
        "subject": "Opt-Out / Data Removal Request",
        "can_automate": True,
    },
    "mylife": {
        "method": "email",
        "email": "privacy@mylife.com",
        "subject": "Data Deletion Request - CCPA",
        "can_automate": True,
    },
    "truthfinder": {
        "method": "email",
        "email": "privacy@truthfinder.com",
        "subject": "Opt-Out Request",
        "can_automate": True,
    },
    "nuwber": {
        "method": "email",
        "email": "privacy@nuwber.com",
        "subject": "Data Removal Request",
        "can_automate": True,
    },
    "zabasearch": {
        "method": "email",
        "email": "privacy@zabasearch.com",
        "subject": "Opt-Out Request - Remove My Information",
        "can_automate": True,
    },
    "thatsthem": {
        "method": "form",
        "url": "https://thatsthem.com/optout",
        "can_automate": True,
    },
    "familytreenow": {
        "method": "email",
        "email": "privacy@familytreenow.com",
        "subject": "Data Removal Request",
        "can_automate": True,
    },
}


def generate_opt_out_email(
    broker_name: str,
    first_name: str,
    last_name: str,
    user_email: str,
    date_of_birth: str = None,
    phone_numbers: list = None,
    addresses: list = None,
    profile_url: str = None,
) -> str:
    """Generate a professional opt-out request email with full identifying info."""

    full_name = f"{first_name} {last_name}".strip()

    # Format date of birth
    dob_text = ""
    if date_of_birth:
        dob_text = f"\n- Date of Birth: {date_of_birth}"

    # Format phone numbers
    phone_text = ""
    if phone_numbers and len(phone_numbers) > 0:
        phone_text = "\n- Phone Number(s): " + ", ".join(phone_numbers[:3])

    # Format addresses with full details including zip codes
    address_text = ""
    if addresses and len(addresses) > 0:
        address_text = "\n\nAddresses associated with my records:"
        for addr in addresses[:3]:  # Include up to 3 addresses
            street = addr.get('street', '')
            city = addr.get('city', '')
            state = addr.get('state', '')
            zip_code = addr.get('zip', '') or addr.get('zip_code', '')

            addr_line = "\n- "
            if street:
                addr_line += f"{street}, "
            if city:
                addr_line += f"{city}, "
            if state:
                addr_line += f"{state} "
            if zip_code:
                addr_line += f"{zip_code}"

            if addr_line.strip() != "-":
                address_text += addr_line.rstrip(", ")

    # Profile URL if found
    profile_text = ""
    if profile_url:
        profile_text = f"\n\nProfile URL found on your site: {profile_url}"

    email_body = f"""To Whom It May Concern,

I am writing to request the immediate removal of my personal information from your database and website, pursuant to my rights under the California Consumer Privacy Act (CCPA), General Data Protection Regulation (GDPR), and other applicable privacy laws.

PERSONAL INFORMATION TO REMOVE:

- First Name: {first_name}
- Last Name: {last_name}
- Email: {user_email}{dob_text}{phone_text}{address_text}{profile_text}

Please search for and remove ALL records matching any combination of the above information.

I REQUEST THAT YOU:
1. Delete all personal information you have collected about me
2. Remove any public-facing profile or listing containing my information
3. Remove my information from any people-search results
4. Refrain from selling or sharing my personal information with third parties
5. Confirm completion of this request via email within 45 days

This request is made pursuant to:
- California Consumer Privacy Act (CCPA) - Cal. Civ. Code § 1798.100
- California "Shine the Light" Law - Cal. Civ. Code § 1798.83
- GDPR Article 17 - Right to Erasure (if applicable)

Failure to comply may result in a complaint filed with the California Attorney General's Office or relevant data protection authority.

Please confirm receipt of this request and provide a timeline for completion.

Thank you for your prompt attention to this matter.

Sincerely,
{full_name}
{user_email}

---
This opt-out request was sent via Privacy Eraser
Reference ID: {broker_name.upper()}-{hash(user_email) % 100000:05d}
"""
    return email_body


class OptOutService:
    """Service for automated opt-out submissions."""

    def __init__(self):
        self.timeout = 30
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def get_broker_config(self, broker_name: str) -> Optional[dict]:
        """Get opt-out configuration for a broker."""
        broker_key = broker_name.lower().replace(" ", "").replace("'", "").replace(".", "")

        for key, config in BROKER_OPT_OUT_CONFIG.items():
            if key in broker_key or broker_key in key:
                return config

        return None

    async def submit_opt_out(
        self,
        broker_name: str,
        first_name: str,
        last_name: str,
        user_email: str,
        date_of_birth: str = None,
        phone_numbers: list = None,
        addresses: list = None,
        profile_url: str = None,
    ) -> dict:
        """Submit an automated opt-out request with full profile matching info."""

        config = self.get_broker_config(broker_name)

        if not config:
            return {
                "success": False,
                "method": "manual",
                "message": f"No automated opt-out available for {broker_name}. Manual removal required.",
            }

        if config["method"] == "email":
            return await self._submit_email_opt_out(
                broker_name=broker_name,
                email_to=config["email"],
                subject=config.get("subject", "Opt-Out Request"),
                first_name=first_name,
                last_name=last_name,
                user_email=user_email,
                date_of_birth=date_of_birth,
                phone_numbers=phone_numbers,
                addresses=addresses,
                profile_url=profile_url,
            )
        elif config["method"] == "form":
            return await self._submit_form_opt_out(
                broker_name=broker_name,
                config=config,
                first_name=first_name,
                last_name=last_name,
                user_email=user_email,
                profile_url=profile_url,
            )

        return {
            "success": False,
            "method": "unknown",
            "message": "Unknown opt-out method",
        }

    async def _submit_email_opt_out(
        self,
        broker_name: str,
        email_to: str,
        subject: str,
        first_name: str,
        last_name: str,
        user_email: str,
        date_of_birth: str = None,
        phone_numbers: list = None,
        addresses: list = None,
        profile_url: str = None,
    ) -> dict:
        """Send opt-out request via email using Resend with full profile info."""
        try:
            from app.config import settings
            import resend

            if not settings.resend_api_key:
                return {
                    "success": False,
                    "method": "email",
                    "message": "Email service not configured. Manual removal required.",
                }

            resend.api_key = settings.resend_api_key

            # Generate email with all identifying information
            email_body = generate_opt_out_email(
                broker_name=broker_name,
                first_name=first_name,
                last_name=last_name,
                user_email=user_email,
                date_of_birth=date_of_birth,
                phone_numbers=phone_numbers,
                addresses=addresses,
                profile_url=profile_url,
            )

            # Enhance subject with user name for better matching
            full_subject = f"{subject} - {first_name} {last_name}"

            # Send the opt-out email
            result = resend.Emails.send({
                "from": f"Privacy Eraser <{settings.from_email}>",
                "to": [email_to],
                "reply_to": user_email,
                "subject": full_subject,
                "text": email_body,
            })

            return {
                "success": True,
                "method": "email",
                "message": f"Opt-out email sent to {broker_name} ({email_to})",
                "email_id": result.get("id"),
                "sent_to": email_to,
                "includes": {
                    "name": f"{first_name} {last_name}",
                    "dob": bool(date_of_birth),
                    "phones": len(phone_numbers) if phone_numbers else 0,
                    "addresses": len(addresses) if addresses else 0,
                }
            }

        except Exception as e:
            return {
                "success": False,
                "method": "email",
                "message": f"Failed to send opt-out email: {str(e)[:100]}",
                "error": str(e),
            }

    async def _submit_form_opt_out(
        self,
        broker_name: str,
        config: dict,
        first_name: str,
        last_name: str,
        user_email: str,
        profile_url: str = None,
    ) -> dict:
        """Attempt to submit opt-out via form/API."""
        try:
            api_url = config.get("api_url")
            if not api_url:
                return {
                    "success": False,
                    "method": "form",
                    "message": f"Form submission not fully configured for {broker_name}. Visit {config.get('url', 'their website')} to complete manually.",
                    "opt_out_url": config.get("url"),
                }

            full_name = f"{first_name} {last_name}".strip()

            # Prepare form data with all available fields
            fields = config.get("fields", {})
            form_data = {}
            for key, value in fields.items():
                form_data[key] = value.format(
                    profile_url=profile_url or "",
                    user_email=user_email,
                    user_name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                )

            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.post(api_url, data=form_data)

                if response.status_code in [200, 201, 202, 204]:
                    return {
                        "success": True,
                        "method": "form",
                        "message": f"Opt-out request submitted to {broker_name}",
                    }
                else:
                    return {
                        "success": False,
                        "method": "form",
                        "message": f"Form submission failed. Please complete manually at {config.get('url')}",
                        "opt_out_url": config.get("url"),
                    }

        except Exception as e:
            return {
                "success": False,
                "method": "form",
                "message": f"Automated submission failed. Please complete manually at {config.get('url', 'their website')}",
                "opt_out_url": config.get("url"),
                "error": str(e)[:100],
            }

    async def submit_all_opt_outs(
        self,
        exposures: list,
        first_name: str,
        last_name: str,
        user_email: str,
        date_of_birth: str = None,
        phone_numbers: list = None,
        addresses: list = None,
    ) -> list:
        """Submit opt-out requests for multiple exposures with full profile info."""
        results = []

        for exposure in exposures:
            broker_name = exposure.get("broker_name", "Unknown")
            profile_url = exposure.get("profile_url")

            result = await self.submit_opt_out(
                broker_name=broker_name,
                first_name=first_name,
                last_name=last_name,
                user_email=user_email,
                date_of_birth=date_of_birth,
                phone_numbers=phone_numbers,
                addresses=addresses,
                profile_url=profile_url,
            )
            result["broker_name"] = broker_name
            result["exposure_id"] = exposure.get("id")
            results.append(result)

            # Small delay between requests
            await asyncio.sleep(0.5)

        return results
