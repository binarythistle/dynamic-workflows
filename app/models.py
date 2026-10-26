from dataclasses import dataclass


@dataclass
class Customer:
    customer_id: str
    name: str


@dataclass
class KycInput:
    customer: Customer
    product: str  # the product the customer accepted
