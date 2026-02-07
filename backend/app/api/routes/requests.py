"""Removal request routes with actual opt-out processing."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models.request import RemovalRequest
from app.models.broker import DataBroker
from app.models.exposure import BrokerExposure

router = APIRouter()


# Opt-out instructions for common sites
OPT_OUT_INSTRUCTIONS = {
    "spokeo": {
        "url": "https://www.spokeo.com/optout",
        "steps": [
            "1. Go to the opt-out page: https://www.spokeo.com/optout",
            "2. Enter the URL of your profile (found during scan)",
            "3. Enter your email address",
            "4. Click 'Remove This Listing'",
            "5. Check your email for confirmation link",
            "6. Click the confirmation link to complete removal",
        ],
        "time": "24-48 hours",
    },
    "whitepages": {
        "url": "https://www.whitepages.com/suppression-requests",
        "steps": [
            "1. Go to: https://www.whitepages.com/suppression-requests",
            "2. Search for your listing",
            "3. Click 'Remove Me'",
            "4. Verify with phone number",
            "5. Confirm removal",
        ],
        "time": "24 hours",
    },
    "beenverified": {
        "url": "https://www.beenverified.com/app/optout/search",
        "steps": [
            "1. Go to: https://www.beenverified.com/app/optout/search",
            "2. Search for your name",
            "3. Find your listing and click it",
            "4. Click 'Proceed to opt out'",
            "5. Enter email and complete verification",
        ],
        "time": "24 hours",
    },
    "truepeoplesearch": {
        "url": "https://www.truepeoplesearch.com/removal",
        "steps": [
            "1. Go to: https://www.truepeoplesearch.com/removal",
            "2. Find your listing on their site",
            "3. Copy the URL of your profile",
            "4. Paste it in the removal form",
            "5. Complete the CAPTCHA and submit",
        ],
        "time": "24-72 hours",
    },
    "fastpeoplesearch": {
        "url": "https://www.fastpeoplesearch.com/removal",
        "steps": [
            "1. Find your listing on FastPeopleSearch",
            "2. Scroll to bottom and click 'Privacy' link",
            "3. Or go directly to: https://www.fastpeoplesearch.com/removal",
            "4. Enter the URL of your profile",
            "5. Complete the removal form",
        ],
        "time": "24-48 hours",
    },
    "intelius": {
        "url": "https://www.intelius.com/opt-out/submit/",
        "steps": [
            "1. Go to: https://www.intelius.com/opt-out/submit/",
            "2. Fill in your information",
            "3. Upload a photo ID (redact sensitive info)",
            "4. Submit the request",
            "5. Wait for email confirmation",
        ],
        "time": "7-14 days",
    },
    "radaris": {
        "url": "https://radaris.com/control/privacy",
        "steps": [
            "1. Go to: https://radaris.com/control/privacy",
            "2. Search for your name",
            "3. Find your profile",
            "4. Click 'Control Information'",
            "5. Select 'Remove information'",
            "6. Verify your identity",
        ],
        "time": "3-7 days",
    },
    "peoplefinder": {
        "url": "https://www.peoplefinder.com/optout.php",
        "steps": [
            "1. Go to: https://www.peoplefinder.com/optout.php",
            "2. Search for your listing",
            "3. Select your profile",
            "4. Click 'Opt Out'",
            "5. Complete the form",
        ],
        "time": "24-48 hours",
    },
    "default": {
        "url": None,
        "steps": [
            "1. Visit the website where your data was found",
            "2. Look for 'Privacy Policy' or 'Opt Out' links (usually in footer)",
            "3. Follow their removal process",
            "4. You may need to email privacy@[sitename].com",
            "5. Reference CCPA/GDPR rights if in CA or EU",
        ],
        "time": "7-30 days",
    },
}


# Schemas
class RequestCreate(BaseModel):
    exposure_id: str
    request_type: str = "opt_out"


class RequestResponse(BaseModel):
    id: str
    broker_id: str | None
    broker_name: str
    exposure_id: str | None
    request_type: str
    status: str
    submitted_at: datetime | None
    expected_completion: datetime | None
    completed_at: datetime | None
    requires_user_action: bool
    instructions: str | None
    opt_out_url: str | None
    profile_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RequestStats(BaseModel):
    total: int
    pending: int
    submitted: int
    completed: int
    failed: int
    requires_action: int


def get_opt_out_info(broker_name: str, profile_url: str = None) -> dict:
    """Get opt-out instructions for a broker."""
    broker_key = broker_name.lower().replace(" ", "").replace("'", "")

    # Check for known brokers
    for key in OPT_OUT_INSTRUCTIONS:
        if key in broker_key:
            info = OPT_OUT_INSTRUCTIONS[key].copy()
            if profile_url:
                info["steps"] = [s.replace("(found during scan)", profile_url) for s in info["steps"]]
            return info

    return OPT_OUT_INSTRUCTIONS["default"]


@router.get("/", response_model=list[RequestResponse])
async def list_requests(current_user: CurrentUser, db: DbSession):
    """List all removal requests for current user."""
    result = await db.execute(
        select(RemovalRequest)
        .options(
            selectinload(RemovalRequest.broker),
            selectinload(RemovalRequest.exposure)
        )
        .where(RemovalRequest.user_id == current_user.id)
        .order_by(RemovalRequest.created_at.desc())
    )
    requests = result.scalars().all()

    response_list = []
    for req in requests:
        # Determine broker name and URLs
        if req.broker:
            broker_name = req.broker.name
            opt_out_url = req.broker.opt_out_url
        elif req.exposure and req.exposure.source_name:
            broker_name = req.exposure.source_name
            opt_out_url = req.exposure.profile_url
        else:
            broker_name = "Unknown Source"
            opt_out_url = None

        profile_url = req.exposure.profile_url if req.exposure else None

        response_list.append(RequestResponse(
            id=str(req.id),
            broker_id=str(req.broker_id) if req.broker_id else None,
            broker_name=broker_name,
            exposure_id=str(req.exposure_id) if req.exposure_id else None,
            request_type=req.request_type,
            status=req.status,
            submitted_at=req.submitted_at,
            expected_completion=req.expected_completion,
            completed_at=req.completed_at,
            requires_user_action=req.requires_user_action,
            instructions=req.instructions,
            opt_out_url=opt_out_url,
            profile_url=profile_url,
            created_at=req.created_at,
        ))

    return response_list


@router.get("/stats", response_model=RequestStats)
async def get_request_stats(current_user: CurrentUser, db: DbSession):
    """Get request statistics."""
    result = await db.execute(
        select(RemovalRequest).where(RemovalRequest.user_id == current_user.id)
    )
    requests = result.scalars().all()

    return RequestStats(
        total=len(requests),
        pending=sum(1 for r in requests if r.status == "pending"),
        submitted=sum(1 for r in requests if r.status == "submitted"),
        completed=sum(1 for r in requests if r.status == "completed"),
        failed=sum(1 for r in requests if r.status == "failed"),
        requires_action=sum(1 for r in requests if r.requires_user_action),
    )


@router.post("/", response_model=RequestResponse)
async def create_request(
    request_data: RequestCreate,
    current_user: CurrentUser,
    db: DbSession,
    background_tasks: BackgroundTasks,
):
    """Create a removal request and automatically submit opt-out."""
    from app.services.opt_out import OptOutService
    from app.models.user import UserProfile

    # Get exposure
    exposure_result = await db.execute(
        select(BrokerExposure)
        .where(BrokerExposure.id == request_data.exposure_id)
        .where(BrokerExposure.user_id == current_user.id)
    )
    exposure = exposure_result.scalar_one_or_none()

    if not exposure:
        raise HTTPException(status_code=404, detail="Exposure not found")

    # Check for existing active request
    existing_result = await db.execute(
        select(RemovalRequest)
        .where(RemovalRequest.exposure_id == exposure.id)
        .where(RemovalRequest.status.not_in(["completed", "failed"]))
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A removal request is already in progress for this exposure")

    # Get user profile for opt-out submission - need all identifying info
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile or not profile.first_name or not profile.last_name:
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile with name before requesting removal"
        )

    first_name = profile.first_name or ""
    last_name = profile.last_name or ""
    addresses = profile.addresses if profile else None
    phone_numbers = profile.phone_numbers if profile else None
    date_of_birth = str(profile.date_of_birth) if profile and profile.date_of_birth else None

    # Get broker if exists
    broker = None
    broker_name = "Unknown Source"
    opt_out_url = None

    if exposure.broker_id:
        broker_result = await db.execute(
            select(DataBroker).where(DataBroker.id == exposure.broker_id)
        )
        broker = broker_result.scalar_one_or_none()
        if broker:
            broker_name = broker.name
            opt_out_url = broker.opt_out_url
    else:
        broker_name = exposure.source_name or "Unknown Source"
        opt_out_url = exposure.profile_url

    # Try automated opt-out first with full profile info for matching
    opt_out_service = OptOutService()
    auto_result = await opt_out_service.submit_opt_out(
        broker_name=broker_name,
        first_name=first_name,
        last_name=last_name,
        user_email=current_user.email,
        date_of_birth=date_of_birth,
        phone_numbers=phone_numbers,
        addresses=addresses,
        profile_url=exposure.profile_url,
    )

    # Build instructions based on automation result
    if auto_result["success"]:
        if auto_result["method"] == "email":
            instructions = f"✅ AUTOMATED OPT-OUT SENT!\n\n"
            instructions += f"We automatically sent an opt-out request email to {broker_name}.\n"
            instructions += f"Email sent to: {auto_result.get('sent_to', 'their privacy team')}\n\n"
            instructions += "What happens next:\n"
            instructions += "1. The broker will process your request (usually 24-72 hours)\n"
            instructions += "2. They may send a confirmation email to verify your identity\n"
            instructions += "3. Check your email for any confirmation requests\n"
            instructions += "4. Your data should be removed within 7-14 days\n\n"
            instructions += "No further action needed unless they request verification!"
            method_used = "auto_email"
            requires_action = False
        else:
            instructions = f"✅ AUTOMATED OPT-OUT SUBMITTED!\n\n"
            instructions += f"We automatically submitted an opt-out request to {broker_name}.\n\n"
            instructions += "What happens next:\n"
            instructions += "1. The broker will process your request\n"
            instructions += "2. Your data should be removed within 24-72 hours\n\n"
            instructions += "No further action needed!"
            method_used = "auto_form"
            requires_action = False
    else:
        # Fallback to manual instructions
        opt_out_info = get_opt_out_info(broker_name, exposure.profile_url)
        instructions = f"Manual removal required for {broker_name}:\n\n"
        instructions += "\n".join(opt_out_info["steps"])
        instructions += f"\n\nExpected removal time: {opt_out_info['time']}"
        if exposure.profile_url:
            instructions += f"\n\nYour profile URL: {exposure.profile_url}"
        if opt_out_info.get("url"):
            instructions += f"\n\nDirect opt-out link: {opt_out_info['url']}"
            opt_out_url = opt_out_info["url"]
        method_used = "manual"
        requires_action = True

    # Determine processing time
    if broker and broker.processing_days:
        processing_days = broker.processing_days
    else:
        processing_days = 14 if requires_action else 7  # Faster for automated

    # Create request
    request = RemovalRequest(
        user_id=current_user.id,
        broker_id=exposure.broker_id,
        exposure_id=exposure.id,
        request_type=request_data.request_type,
        status="submitted",
        submitted_at=datetime.utcnow(),
        expected_completion=(datetime.utcnow() + timedelta(days=processing_days)).date(),
        requires_user_action=requires_action,
        instructions=instructions,
        method_used=method_used,
        notes=f"Auto result: {auto_result.get('message', '')}",
    )
    db.add(request)

    # Update exposure status
    exposure.status = "pending_removal"

    await db.commit()
    await db.refresh(request)

    return RequestResponse(
        id=str(request.id),
        broker_id=str(request.broker_id) if request.broker_id else None,
        broker_name=broker_name,
        exposure_id=str(request.exposure_id),
        request_type=request.request_type,
        status=request.status,
        submitted_at=request.submitted_at,
        expected_completion=request.expected_completion,
        completed_at=request.completed_at,
        requires_user_action=request.requires_user_action,
        instructions=request.instructions,
        opt_out_url=opt_out_url,
        profile_url=exposure.profile_url,
        created_at=request.created_at,
    )


@router.post("/{request_id}/submit")
async def submit_request(
    request_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Mark a request as submitted (user has followed instructions)."""
    result = await db.execute(
        select(RemovalRequest)
        .options(selectinload(RemovalRequest.broker))
        .where(RemovalRequest.id == request_id)
        .where(RemovalRequest.user_id == current_user.id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    if request.status not in ["pending", "submitted"]:
        raise HTTPException(status_code=400, detail="Request cannot be submitted in current state")

    request.status = "submitted"
    request.submitted_at = datetime.utcnow()

    # Calculate expected completion
    processing_days = request.broker.processing_days if request.broker else 14
    request.expected_completion = (datetime.utcnow() + timedelta(days=processing_days)).date()

    await db.commit()

    return {
        "status": "submitted",
        "expected_completion": request.expected_completion,
        "message": "Request submitted. Follow the instructions to complete the opt-out process."
    }


@router.post("/{request_id}/complete")
async def mark_request_complete(
    request_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Mark a request as completed (user confirms removal)."""
    result = await db.execute(
        select(RemovalRequest)
        .where(RemovalRequest.id == request_id)
        .where(RemovalRequest.user_id == current_user.id)
    )
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    request.status = "completed"
    request.completed_at = datetime.utcnow()
    request.requires_user_action = False

    # Update exposure status
    if request.exposure_id:
        exposure_result = await db.execute(
            select(BrokerExposure).where(BrokerExposure.id == request.exposure_id)
        )
        exposure = exposure_result.scalar_one_or_none()
        if exposure:
            exposure.status = "removed"
            exposure.removed_at = datetime.utcnow()

    await db.commit()

    return {"status": "completed", "message": "Your data has been marked as removed!"}
