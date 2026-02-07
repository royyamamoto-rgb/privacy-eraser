"""Data broker definitions."""

from brokers.base import BaseBroker, BrokerInfo
from brokers.spokeo import SpokeoBroker
from brokers.whitepages import WhitePagesBroker
from brokers.truepeoplesearch import TruePeopleSearchBroker
from brokers.beenverified import BeenVerifiedBroker
from brokers.fastpeoplesearch import FastPeopleSearchBroker
from brokers.intelius import InteliusBroker

# Registry of all broker implementations
BROKER_REGISTRY = {
    "spokeo.com": SpokeoBroker,
    "whitepages.com": WhitePagesBroker,
    "truepeoplesearch.com": TruePeopleSearchBroker,
    "beenverified.com": BeenVerifiedBroker,
    "fastpeoplesearch.com": FastPeopleSearchBroker,
    "intelius.com": InteliusBroker,
}


def get_broker(domain: str) -> BaseBroker | None:
    """Get broker implementation by domain."""
    broker_class = BROKER_REGISTRY.get(domain)
    if broker_class:
        return broker_class()
    return None


def list_brokers() -> list[BaseBroker]:
    """Get all registered broker implementations."""
    return [cls() for cls in BROKER_REGISTRY.values()]


__all__ = [
    "BaseBroker",
    "BrokerInfo",
    "SpokeoBroker",
    "WhitePagesBroker",
    "TruePeopleSearchBroker",
    "BeenVerifiedBroker",
    "FastPeopleSearchBroker",
    "InteliusBroker",
    "BROKER_REGISTRY",
    "get_broker",
    "list_brokers",
]
