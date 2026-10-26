from dataclasses import dataclass


@dataclass
class Customer:
    customer_id: str
    name: str


@dataclass
class KycInput:
    customer: Customer
    product: str  # the product the customer accepted


@dataclass
class KycResult:
    approved: bool
    steps: list[str]


@dataclass
class ComplianceDecision:
    approved: bool
    reviewer: str


@dataclass
class Message:
    sender: str  # "Agent", "KYC" or "Timer"
    text: str


@dataclass
class Turn:
    """What the customer sees after each input, and what to send next."""

    messages: list[Message]
    expecting: str  # "message", "choice", "kyc" or "done"
