"""Read-only fake business contract, derived from the pinned Java seed/profile policy.

Never imports dataset specifications, labels, test cases or a Java database client.
"""

from typing import Literal
from uuid import UUID

from vmarket_ai.mapping.spec import TARGETS, Candidate, Target
from vmarket_ai.qa.backend import DEMO_COLLECTIONS

JAVA_COMMIT = "32d82862526754b46efb774327ccc4774a4decf7"
PROFILES = (
    Candidate(
        profile_id="supplier-a",
        version=1,
        vendor_code="NAMI",
        encoding="CP932",
        active=True,
        mapping={"sku": "商品コード", "name": "商品名", "on_hand": "在庫数"},
    ),
    Candidate(
        profile_id="supplier-b",
        version=1,
        vendor_code="RIVERBYTE",
        encoding="UTF-8",
        active=True,
        mapping={"sku": "SKU", "name": "ProductName", "on_hand": "AvailableQuantity"},
    ),
)
SCOPES = {"NAMI": DEMO_COLLECTIONS[0], "RIVERBYTE": DEMO_COLLECTIONS[1]}
# Fixed before evaluation: Java seed names + P04 TRAIN aliases only. Exact matching;
# no normalization of authoritative source names and no dev/test alias expansion.
ALIASES: dict[Target, frozenset[str]] = {
    "sku": frozenset(("商品コード", "品番", "SKU", "ItemCode", "sku")),
    "name": frozenset(("商品名", "品名", "ProductName", "ItemName", "name")),
    "on_hand": frozenset(("在庫数", "実在庫", "AvailableQuantity", "UnitsOnHand", "on_hand")),
}


class StandalonePolicy:
    verification: Literal["standalone_fixture", "bff_profile_snapshot"] = "standalone_fixture"

    def scope(self, vendor: str) -> UUID | None:
        return SCOPES.get(vendor)

    def profiles(self, vendor: str, ids: tuple[str, ...]) -> tuple[Candidate, ...]:
        selected = tuple(p for p in PROFILES if p.vendor_code == vendor)
        if ids:
            selected = tuple(p for p in selected if p.profile_id in ids)
            if {p.profile_id for p in selected} != set(ids):
                from vmarket_ai.mapping.spec import MappingError

                raise MappingError("PROFILE_NOT_AVAILABLE", 409)
        return selected


def rule_choices(headers: tuple[str, ...]) -> tuple[dict[Target, str], bool]:
    mapping: dict[Target, str] = {}
    ambiguous = False
    for target in TARGETS:
        matches = [h for h in headers if h in ALIASES[target]]
        if len(matches) == 1:
            mapping[target] = matches[0]
        elif len(matches) > 1:
            ambiguous = True
    return mapping, ambiguous
