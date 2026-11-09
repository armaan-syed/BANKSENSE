"""Rule-assisted priority suggestion.

This is a triage hint, not fraud or risk scoring. Rules are evaluated strictly
from most to least severe; the first match wins. Every result carries the
matched rule id and a plain-language reason.
"""

from __future__ import annotations

import re

from backend.nlp.config import PRIORITIES

CRITICAL_INTENTS = {
    "compromised_card",
    "lost_or_stolen_card",
    "lost_or_stolen_phone",
    "card_payment_not_recognised",
    "cash_withdrawal_not_recognised",
    "direct_debit_payment_not_recognised",
}

HIGH_INTENTS = {
    "transaction_charged_twice",
}

CASH_ACCESS_INTENTS = {
    "balance_not_updated_after_bank_transfer",
    "balance_not_updated_after_cheque_or_cash_deposit",
    "card_not_working",
    "card_payment_fee_charged",
    "card_payment_wrong_exchange_rate",
    "card_swallowed",
    "cash_withdrawal_charge",
    "contactless_not_working",
    "declined_card_payment",
    "declined_cash_withdrawal",
    "declined_transfer",
    "extra_charge_on_statement",
    "failed_transfer",
    "pending_card_payment",
    "pending_cash_withdrawal",
    "pending_top_up",
    "pending_transfer",
    "pin_blocked",
    "top_up_by_bank_transfer_charge",
    "top_up_by_card_charge",
    "top_up_failed",
    "top_up_reverted",
    "transfer_fee_charged",
    "transfer_not_received_by_recipient",
    "virtual_card_not_working",
    "wrong_amount_of_cash_received",
    "wrong_exchange_rate_for_cash_withdrawal",
}

REFUND_INTENTS = {
    "request_refund",
    "refund_not_showing_up",
    "reverted_card_payment",
}

INFORMATIONAL_INTENTS = {
    "activate_my_card",
    "age_limit",
    "apple_pay_or_google_pay",
    "atm_support",
    "automatic_top_up",
    "beneficiary_not_allowed",
    "cancel_transfer",
    "card_about_to_expire",
    "card_acceptance",
    "card_arrival",
    "card_delivery_estimate",
    "card_linking",
    "change_pin",
    "country_support",
    "disposable_card_limits",
    "edit_personal_details",
    "exchange_charge",
    "exchange_rate",
    "exchange_via_app",
    "fiat_currency_support",
    "get_disposable_virtual_card",
    "get_physical_card",
    "getting_spare_card",
    "getting_virtual_card",
    "order_physical_card",
    "passcode_forgotten",
    "receiving_money",
    "supported_cards_and_currencies",
    "terminate_account",
    "top_up_by_cash_or_cheque",
    "top_up_limits",
    "topping_up_by_card",
    "transfer_into_account",
    "transfer_timing",
    "unable_to_verify_identity",
    "verify_my_identity",
    "verify_source_of_funds",
    "verify_top_up",
    "visa_or_mastercard",
    "why_do_i_need_to_do_this",
    "why_verify_identity",
}

KNOWN_INTENTS = (
    CRITICAL_INTENTS
    | HIGH_INTENTS
    | CASH_ACCESS_INTENTS
    | REFUND_INTENTS
    | INFORMATIONAL_INTENTS
)

_CRITICAL_TEXT = re.compile(
    r"\b(unauthori[sz]ed|fraud|stolen|scam|"
    r"someone (else )?used|did(?:n't| not) (?:make|authori[sz]e)|"
    r"not me|wasn't me|never made)\b",
    re.IGNORECASE,
)
_HIGH_TEXT = re.compile(
    r"(\b(charged|billed|debited)\b.{0,30}\b(twice|two times|double)\b|"
    r"\b(double|duplicate|repeated)\b.{0,20}\b(charge|payment|transaction)\b|"
    r"\bcharged me again\b)",
    re.IGNORECASE,
)
_REFUND_TEXT = re.compile(r"\brefund|reimburse|money back\b", re.IGNORECASE)
_CASH_TEXT = re.compile(
    r"\b(declined|failed|blocked|not working|can't|cannot|unable|"
    r"not received|not showing|pending)\b.{0,35}"
    r"\b(payment|transfer|withdrawal|top.?up|atm|card|cash)\b",
    re.IGNORECASE,
)
_INFO_TEXT = re.compile(
    r"^\s*(how|what|when|where|why|can i|could i|is it|do i)\b",
    re.IGNORECASE,
)


def _normalize_intent(intent: str) -> str:
    return str(intent).strip().lower().rstrip("?")


def suggest_priority(text: str, intent: str) -> dict:
    """Return a triage priority for a classified complaint.

    The output always contains a value from `PRIORITIES` plus `rule_id` and
    `priority_reason`. No fraud/risk conclusion is asserted.
    """

    cleaned = " ".join(str(text or "").split())
    key = _normalize_intent(intent)

    if key in CRITICAL_INTENTS or _CRITICAL_TEXT.search(cleaned):
        return {
            "priority": "critical",
            "priority_reason": (
                "Rule matched: possible unauthorised card activity; "
                "route to the card-security queue."
            ),
            "rule_id": "unauthorised_card",
        }

    if key in HIGH_INTENTS or _HIGH_TEXT.search(cleaned):
        return {
            "priority": "high",
            "priority_reason": "Rule matched: duplicate or repeated charge reported.",
            "rule_id": "duplicate_charge",
        }

    if key in CASH_ACCESS_INTENTS:
        return {
            "priority": "medium",
            "priority_reason": (
                "Rule matched: payment, card, or cash-access issue reported."
            ),
            "rule_id": "cash_access",
        }

    if key in REFUND_INTENTS or _REFUND_TEXT.search(cleaned):
        return {
            "priority": "medium",
            "priority_reason": "Rule matched: refund or reversal request reported.",
            "rule_id": "refund",
        }

    if _CASH_TEXT.search(cleaned):
        return {
            "priority": "medium",
            "priority_reason": (
                "Rule matched: payment, card, or cash-access issue reported."
            ),
            "rule_id": "cash_access",
        }

    if key in INFORMATIONAL_INTENTS or _INFO_TEXT.search(cleaned):
        return {
            "priority": "low",
            "priority_reason": (
                "Rule matched: informational or routine request; "
                "no urgent access issue detected."
            ),
            "rule_id": "informational",
        }

    if key not in KNOWN_INTENTS:
        return {
            "priority": "low",
            "priority_reason": (
                "Rule matched: fallback; intent is not in the priority rule table."
            ),
            "rule_id": "fallback",
        }

    return {
        "priority": "low",
        "priority_reason": (
            "Rule matched: fallback; no higher-severity rule applied."
        ),
        "rule_id": "fallback",
    }


__all__ = [
    "PRIORITIES",
    "suggest_priority",
    "CRITICAL_INTENTS",
    "HIGH_INTENTS",
    "CASH_ACCESS_INTENTS",
    "REFUND_INTENTS",
    "INFORMATIONAL_INTENTS",
]
