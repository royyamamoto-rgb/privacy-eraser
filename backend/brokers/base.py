"""Base class for data broker implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class BrokerInfo:
    """Data broker information."""
    name: str
    domain: str
    category: str
    search_url_pattern: Optional[str]
    opt_out_url: str
    opt_out_method: str  # form, email, mail, api
    opt_out_email: Optional[str]
    opt_out_instructions: str
    requires_verification: bool
    requires_id: bool
    processing_days: int
    can_automate: bool
    difficulty: int  # 1-5
    captcha_type: Optional[str]  # none, recaptcha, hcaptcha


class BaseBroker(ABC):
    """Base class for data broker implementations."""

    @property
    @abstractmethod
    def info(self) -> BrokerInfo:
        """Return broker information."""
        pass

    @abstractmethod
    async def search(self, first_name: str, last_name: str, city: str, state: str) -> dict:
        """
        Search for a person on this broker.

        Returns:
            dict with keys: found (bool), profile_url (str), data_found (dict)
        """
        pass

    @abstractmethod
    async def submit_opt_out(self, profile_url: str, user_info: dict) -> dict:
        """
        Submit an opt-out request.

        Returns:
            dict with keys: success (bool), confirmation (str), error (str)
        """
        pass

    def get_form_selectors(self) -> Optional[dict]:
        """Return CSS selectors for opt-out form fields."""
        return None
