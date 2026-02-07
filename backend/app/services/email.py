"""Email service using Resend."""

import resend
from app.config import settings

# Initialize Resend
resend.api_key = settings.resend_api_key


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send an email using Resend."""
    if not settings.resend_api_key:
        print(f"[Email] Would send to {to}: {subject}")
        return True

    try:
        resend.Emails.send({
            "from": settings.from_email,
            "to": to,
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


async def send_verification_email(email: str, token: str) -> bool:
    """Send email verification link."""
    verify_url = f"{settings.frontend_url}/auth/verify?token={token}"

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #0f172a;">Verify your email</h1>
        <p>Thanks for signing up for Privacy Eraser! Please verify your email address by clicking the button below.</p>
        <a href="{verify_url}"
           style="display: inline-block; background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; margin: 16px 0;">
            Verify Email
        </a>
        <p style="color: #64748b; font-size: 14px;">
            If you didn't create an account, you can safely ignore this email.
        </p>
        <p style="color: #64748b; font-size: 14px;">
            Or copy this link: {verify_url}
        </p>
    </div>
    """

    return await send_email(email, "Verify your email - Privacy Eraser", html)


async def send_password_reset_email(email: str, token: str) -> bool:
    """Send password reset link."""
    reset_url = f"{settings.frontend_url}/auth/reset-password?token={token}"

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #0f172a;">Reset your password</h1>
        <p>We received a request to reset your password. Click the button below to choose a new password.</p>
        <a href="{reset_url}"
           style="display: inline-block; background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; margin: 16px 0;">
            Reset Password
        </a>
        <p style="color: #64748b; font-size: 14px;">
            This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.
        </p>
        <p style="color: #64748b; font-size: 14px;">
            Or copy this link: {reset_url}
        </p>
    </div>
    """

    return await send_email(email, "Reset your password - Privacy Eraser", html)


async def send_removal_complete_email(email: str, broker_name: str) -> bool:
    """Send notification when removal is complete."""
    dashboard_url = f"{settings.frontend_url}/dashboard"

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #0f172a;">Removal Complete!</h1>
        <p>Great news! Your personal information has been successfully removed from <strong>{broker_name}</strong>.</p>
        <a href="{dashboard_url}"
           style="display: inline-block; background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; margin: 16px 0;">
            View Dashboard
        </a>
        <p style="color: #64748b; font-size: 14px;">
            We'll continue monitoring this site to make sure your data doesn't reappear.
        </p>
    </div>
    """

    return await send_email(email, f"Removal Complete: {broker_name} - Privacy Eraser", html)


async def send_new_exposure_alert(email: str, broker_name: str, profile_url: str) -> bool:
    """Send alert when new exposure is found."""
    dashboard_url = f"{settings.frontend_url}/dashboard"

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #ef4444;">⚠️ New Exposure Found</h1>
        <p>We found your personal information on <strong>{broker_name}</strong>.</p>
        <p style="background-color: #fef2f2; padding: 12px; border-radius: 8px; color: #991b1b;">
            Your data is exposed at: {profile_url}
        </p>
        <a href="{dashboard_url}"
           style="display: inline-block; background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; margin: 16px 0;">
            Remove My Data
        </a>
        <p style="color: #64748b; font-size: 14px;">
            Click above to start a removal request and protect your privacy.
        </p>
    </div>
    """

    return await send_email(email, f"New Exposure Found: {broker_name} - Privacy Eraser", html)


async def send_subscription_confirmation(email: str, plan: str) -> bool:
    """Send subscription confirmation email."""
    dashboard_url = f"{settings.frontend_url}/dashboard"

    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #0f172a;">Welcome to Privacy Eraser {plan.title()}!</h1>
        <p>Thank you for subscribing! Your {plan} plan is now active.</p>
        <h2 style="color: #0f172a; font-size: 18px;">What's included:</h2>
        <ul>
            <li>Unlimited privacy scans</li>
            <li>Automatic removal requests</li>
            <li>Continuous monitoring</li>
            <li>Priority support</li>
        </ul>
        <a href="{dashboard_url}"
           style="display: inline-block; background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; margin: 16px 0;">
            Go to Dashboard
        </a>
        <p style="color: #64748b; font-size: 14px;">
            Questions? Reply to this email and we'll help you out.
        </p>
    </div>
    """

    return await send_email(email, f"Welcome to Privacy Eraser {plan.title()}!", html)
