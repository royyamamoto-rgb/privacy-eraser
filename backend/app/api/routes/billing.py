"""Billing and subscription routes."""

import stripe
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from sqlalchemy import select

from app.config import settings
from app.api.deps import CurrentUser, DbSession
from app.models.user import User

router = APIRouter()

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key

# Price IDs - set these in your Stripe dashboard
PRICE_IDS = {
    "basic_monthly": settings.stripe_price_basic_monthly,
    "basic_yearly": settings.stripe_price_basic_yearly,
    "premium_monthly": settings.stripe_price_premium_monthly,
    "premium_yearly": settings.stripe_price_premium_yearly,
}


class CheckoutRequest(BaseModel):
    price_id: str  # basic_monthly, basic_yearly, premium_monthly, premium_yearly


class CheckoutResponse(BaseModel):
    checkout_url: str


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool


class BillingPortalResponse(BaseModel):
    portal_url: str


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(current_user: CurrentUser, db: DbSession):
    """Get current user's subscription status."""

    status = "inactive"
    cancel_at_period_end = False

    if current_user.stripe_subscription_id:
        try:
            subscription = stripe.Subscription.retrieve(current_user.stripe_subscription_id)
            status = subscription.status
            cancel_at_period_end = subscription.cancel_at_period_end
        except stripe.error.StripeError:
            pass

    return SubscriptionResponse(
        plan=current_user.plan,
        status=status if current_user.stripe_subscription_id else ("active" if current_user.plan == "free" else "inactive"),
        current_period_end=current_user.subscription_ends_at,
        cancel_at_period_end=cancel_at_period_end,
    )


@router.post("/sync")
async def sync_subscription(current_user: CurrentUser, db: DbSession):
    """Sync subscription status from Stripe (fallback if webhook fails)."""

    if not current_user.stripe_customer_id:
        return {"status": "no_customer", "plan": "free"}

    try:
        # List all subscriptions for this customer
        subscriptions = stripe.Subscription.list(
            customer=current_user.stripe_customer_id,
            status="active",
            limit=1
        )

        if subscriptions.data:
            subscription = subscriptions.data[0]

            # Determine plan from price
            price_id = subscription.items.data[0].price.id
            plan = "basic"
            if price_id in [settings.stripe_price_premium_monthly, settings.stripe_price_premium_yearly]:
                plan = "premium"

            # Update user
            current_user.plan = plan
            current_user.stripe_subscription_id = subscription.id
            current_user.subscription_ends_at = datetime.fromtimestamp(subscription.current_period_end)

            await db.commit()

            return {
                "status": "synced",
                "plan": plan,
                "subscription_id": subscription.id,
                "ends_at": current_user.subscription_ends_at.isoformat()
            }
        else:
            # No active subscription found
            return {"status": "no_subscription", "plan": current_user.plan}

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    checkout_data: CheckoutRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Create a Stripe checkout session for subscription."""

    if checkout_data.price_id not in PRICE_IDS:
        raise HTTPException(status_code=400, detail="Invalid price ID")

    stripe_price_id = PRICE_IDS[checkout_data.price_id]

    if not stripe_price_id:
        raise HTTPException(status_code=400, detail="Price not configured")

    # Get or create Stripe customer
    if not current_user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            metadata={"user_id": str(current_user.id)},
        )
        current_user.stripe_customer_id = customer.id
        await db.commit()

    # Create checkout session
    try:
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": stripe_price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{settings.frontend_url}/dashboard/billing?success=true",
            cancel_url=f"{settings.frontend_url}/dashboard/billing?canceled=true",
            metadata={
                "user_id": str(current_user.id),
            },
        )

        return CheckoutResponse(checkout_url=session.url)

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portal", response_model=BillingPortalResponse)
async def create_billing_portal(current_user: CurrentUser, db: DbSession):
    """Create a Stripe billing portal session for managing subscription."""

    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{settings.frontend_url}/dashboard/billing",
        )

        return BillingPortalResponse(portal_url=session.url)

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """Handle Stripe webhook events."""

    payload = await request.body()

    # If no webhook secret configured, skip signature verification (dev mode)
    if not settings.stripe_webhook_secret:
        try:
            event = stripe.Event.construct_from(
                stripe.util.json.loads(payload),
                stripe.api_key
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload,
                stripe_signature,
                settings.stripe_webhook_secret,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event.type == "checkout.session.completed":
        session = event.data.object
        await handle_checkout_completed(session, db)

    elif event.type == "customer.subscription.updated":
        subscription = event.data.object
        await handle_subscription_updated(subscription, db)

    elif event.type == "customer.subscription.deleted":
        subscription = event.data.object
        await handle_subscription_deleted(subscription, db)

    elif event.type == "invoice.payment_failed":
        invoice = event.data.object
        await handle_payment_failed(invoice, db)

    return {"status": "success"}


async def handle_checkout_completed(session, db: DbSession):
    """Handle successful checkout."""

    user_id = session.metadata.get("user_id")
    if not user_id:
        return

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return

    # Get subscription details
    subscription = stripe.Subscription.retrieve(session.subscription)

    # Determine plan from price
    price_id = subscription.items.data[0].price.id
    plan = "basic"
    if price_id in [settings.stripe_price_premium_monthly, settings.stripe_price_premium_yearly]:
        plan = "premium"

    # Update user
    user.plan = plan
    user.stripe_subscription_id = subscription.id
    user.subscription_ends_at = datetime.fromtimestamp(subscription.current_period_end)

    await db.commit()


async def handle_subscription_updated(subscription, db: DbSession):
    """Handle subscription update."""

    customer_id = subscription.customer

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return

    # Update subscription end date
    user.subscription_ends_at = datetime.fromtimestamp(subscription.current_period_end)

    # Update plan if changed
    if subscription.items.data:
        price_id = subscription.items.data[0].price.id
        if price_id in [settings.stripe_price_premium_monthly, settings.stripe_price_premium_yearly]:
            user.plan = "premium"
        else:
            user.plan = "basic"

    # Handle cancellation
    if subscription.status == "canceled":
        user.plan = "free"
        user.stripe_subscription_id = None

    await db.commit()


async def handle_subscription_deleted(subscription, db: DbSession):
    """Handle subscription cancellation."""

    customer_id = subscription.customer

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return

    user.plan = "free"
    user.stripe_subscription_id = None
    user.subscription_ends_at = None

    await db.commit()


async def handle_payment_failed(invoice, db: DbSession):
    """Handle failed payment."""
    # Could send email notification here
    pass
