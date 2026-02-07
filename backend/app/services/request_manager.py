"""Request manager service for handling opt-out submissions."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from playwright.async_api import async_playwright, Page
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request import RemovalRequest
from app.models.broker import DataBroker
from app.models.exposure import BrokerExposure
from app.models.user import User, UserProfile


@dataclass
class SubmissionResult:
    """Result of an opt-out submission."""
    success: bool
    method: str  # auto_form, email, manual
    confirmation_number: Optional[str] = None
    error: Optional[str] = None
    requires_followup: bool = False
    followup_instructions: Optional[str] = None


class RequestManager:
    """Manages opt-out request submissions."""

    def __init__(self):
        self.timeout = 60000  # 60 seconds for form submissions

    async def submit_request(
        self,
        request: RemovalRequest,
        broker: DataBroker,
        profile: UserProfile,
        exposure: Optional[BrokerExposure] = None,
    ) -> SubmissionResult:
        """Submit an opt-out request based on broker method."""

        method = broker.opt_out_method

        if method == "form" and broker.can_automate:
            return await self._submit_form(broker, profile, exposure)
        elif method == "email":
            return await self._submit_email(broker, profile, exposure)
        elif method == "api":
            return await self._submit_api(broker, profile, exposure)
        else:
            return self._get_manual_instructions(broker)

    async def _submit_form(
        self,
        broker: DataBroker,
        profile: UserProfile,
        exposure: Optional[BrokerExposure],
    ) -> SubmissionResult:
        """Auto-submit opt-out form using Playwright."""

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                page = await context.new_page()

                # Navigate to opt-out page
                await page.goto(broker.opt_out_url, timeout=self.timeout)
                await page.wait_for_load_state("networkidle", timeout=30000)

                # Get form selectors from broker config
                selectors = broker.form_selectors or {}

                # Fill out form fields
                if profile.first_name and selectors.get("first_name"):
                    await self._safe_fill(page, selectors["first_name"], profile.first_name)

                if profile.last_name and selectors.get("last_name"):
                    await self._safe_fill(page, selectors["last_name"], profile.last_name)

                if profile.emails and selectors.get("email"):
                    await self._safe_fill(page, selectors["email"], profile.emails[0])

                # Handle profile URL if needed
                if exposure and exposure.profile_url and selectors.get("profile_url"):
                    await self._safe_fill(page, selectors["profile_url"], exposure.profile_url)

                # Handle address fields
                if profile.addresses and len(profile.addresses) > 0:
                    addr = profile.addresses[0]
                    if selectors.get("street"):
                        await self._safe_fill(page, selectors["street"], addr.get("street", ""))
                    if selectors.get("city"):
                        await self._safe_fill(page, selectors["city"], addr.get("city", ""))
                    if selectors.get("state"):
                        await self._safe_fill(page, selectors["state"], addr.get("state", ""))
                    if selectors.get("zip"):
                        await self._safe_fill(page, selectors["zip"], addr.get("zip", ""))

                # Check for CAPTCHA
                if broker.captcha_type and broker.captcha_type != "none":
                    await browser.close()
                    return SubmissionResult(
                        success=False,
                        method="auto_form",
                        error="CAPTCHA required",
                        requires_followup=True,
                        followup_instructions=f"Please visit {broker.opt_out_url} and complete the form manually."
                    )

                # Submit form
                if selectors.get("submit"):
                    await page.click(selectors["submit"])
                    await page.wait_for_load_state("networkidle", timeout=30000)

                # Check for confirmation
                confirmation = await self._extract_confirmation(page)

                await browser.close()

                return SubmissionResult(
                    success=True,
                    method="auto_form",
                    confirmation_number=confirmation,
                )

        except Exception as e:
            return SubmissionResult(
                success=False,
                method="auto_form",
                error=str(e),
                requires_followup=True,
                followup_instructions=f"Auto-submission failed. Please visit {broker.opt_out_url} manually."
            )

    async def _safe_fill(self, page: Page, selector: str, value: str) -> bool:
        """Safely fill a form field if it exists."""
        try:
            element = await page.query_selector(selector)
            if element:
                await element.fill(value)
                return True
        except Exception:
            pass
        return False

    async def _extract_confirmation(self, page: Page) -> Optional[str]:
        """Try to extract a confirmation number from the page."""
        content = await page.content()
        content_lower = content.lower()

        # Common confirmation patterns
        if "confirmation" in content_lower or "reference" in content_lower:
            # Try to find a number pattern
            import re
            patterns = [
                r'confirmation[:\s#]*([A-Z0-9-]+)',
                r'reference[:\s#]*([A-Z0-9-]+)',
                r'request[:\s#]*([A-Z0-9-]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)

        # If no confirmation number, check for success message
        success_indicators = [
            "successfully submitted",
            "request received",
            "we've received your request",
            "your request has been submitted",
            "thank you for your submission",
        ]
        for indicator in success_indicators:
            if indicator in content_lower:
                return "SUBMITTED"

        return None

    async def _submit_email(
        self,
        broker: DataBroker,
        profile: UserProfile,
        exposure: Optional[BrokerExposure],
    ) -> SubmissionResult:
        """Submit opt-out via email."""

        if not broker.opt_out_email:
            return SubmissionResult(
                success=False,
                method="email",
                error="No opt-out email configured",
            )

        # Generate email content
        email_content = self._generate_opt_out_email(broker, profile, exposure)

        # TODO: Actually send email via configured email service
        # For now, return instructions
        return SubmissionResult(
            success=True,
            method="email",
            requires_followup=True,
            followup_instructions=f"Please send an email to {broker.opt_out_email} with the following content:\n\n{email_content}"
        )

    def _generate_opt_out_email(
        self,
        broker: DataBroker,
        profile: UserProfile,
        exposure: Optional[BrokerExposure],
    ) -> str:
        """Generate opt-out email content."""

        full_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()

        email_body = f"""Subject: Data Removal Request - {full_name}

To Whom It May Concern,

I am writing to request the immediate removal of my personal information from your database and website ({broker.domain}).

Personal Information to Remove:
- Name: {full_name}
"""

        if profile.addresses and len(profile.addresses) > 0:
            addr = profile.addresses[0]
            email_body += f"- Address: {addr.get('street', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('zip', '')}\n"

        if profile.emails:
            email_body += f"- Email: {', '.join(profile.emails)}\n"

        if profile.phone_numbers:
            email_body += f"- Phone: {', '.join(profile.phone_numbers)}\n"

        if exposure and exposure.profile_url:
            email_body += f"\nProfile URL: {exposure.profile_url}\n"

        email_body += """
Under the California Consumer Privacy Act (CCPA), General Data Protection Regulation (GDPR), and other applicable privacy laws, I have the right to request deletion of my personal information.

Please confirm receipt of this request and notify me once my data has been removed.

Thank you for your prompt attention to this matter.

Sincerely,
""" + full_name

        return email_body

    async def _submit_api(
        self,
        broker: DataBroker,
        profile: UserProfile,
        exposure: Optional[BrokerExposure],
    ) -> SubmissionResult:
        """Submit opt-out via API (for brokers that support it)."""
        # Most brokers don't have public APIs, so this is future-proofing
        return SubmissionResult(
            success=False,
            method="api",
            error="API submission not implemented for this broker",
        )

    def _get_manual_instructions(self, broker: DataBroker) -> SubmissionResult:
        """Return manual instructions for non-automatable brokers."""

        instructions = broker.opt_out_instructions or f"""
To remove your data from {broker.name}:

1. Visit: {broker.opt_out_url}
2. Locate your profile using the search function
3. Follow the opt-out process on the site
4. Keep a record of any confirmation number

Estimated processing time: {broker.processing_days} days
"""
        if broker.requires_verification:
            instructions += "\n⚠️ This broker requires email/phone verification."

        if broker.requires_id:
            instructions += "\n⚠️ This broker may require ID verification."

        return SubmissionResult(
            success=True,
            method="manual",
            requires_followup=True,
            followup_instructions=instructions,
        )

    async def process_pending_requests(self, db: AsyncSession) -> dict:
        """Process all pending requests (called by Celery worker)."""

        result = await db.execute(
            select(RemovalRequest)
            .where(RemovalRequest.status == "pending")
            .limit(50)  # Process in batches
        )
        requests = result.scalars().all()

        processed = 0
        success = 0
        failed = 0

        for request in requests:
            # Get broker and profile
            broker_result = await db.execute(
                select(DataBroker).where(DataBroker.id == request.broker_id)
            )
            broker = broker_result.scalar_one_or_none()

            user_result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == request.user_id)
            )
            profile = user_result.scalar_one_or_none()

            if not broker or not profile:
                continue

            exposure = None
            if request.exposure_id:
                exp_result = await db.execute(
                    select(BrokerExposure).where(BrokerExposure.id == request.exposure_id)
                )
                exposure = exp_result.scalar_one_or_none()

            # Submit request
            submission = await self.submit_request(request, broker, profile, exposure)

            # Update request status
            request.method_used = submission.method
            request.submitted_at = datetime.utcnow()

            if submission.success:
                request.status = "submitted"
                request.confirmation_number = submission.confirmation_number
                request.expected_completion = (
                    datetime.utcnow() + timedelta(days=broker.processing_days)
                ).date()
                success += 1
            else:
                request.status = "failed" if not submission.requires_followup else "pending"
                request.notes = submission.error
                failed += 1

            request.requires_user_action = submission.requires_followup
            if submission.followup_instructions:
                request.instructions = submission.followup_instructions

            processed += 1

        await db.commit()

        return {
            "processed": processed,
            "success": success,
            "failed": failed,
        }
