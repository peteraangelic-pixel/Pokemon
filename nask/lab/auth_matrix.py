"""Offline triage of hypothetical authorization observations.

Input must use synthetic resources and numeric status codes only. Differences
never establish a vulnerability. This module performs no network operations.
"""

def classify(owner_status: int, other_status: int, relationship: str) -> str:
    if type(owner_status) is not int or type(other_status) is not int or not (100 <= owner_status <= 599 and 100 <= other_status <= 599):
        raise ValueError('statuses must be integers between 100 and 599')
    if relationship not in {'private', 'shared', 'unknown'}:
        raise ValueError('unknown expected relationship')
    if relationship == 'unknown' or owner_status < 200 or owner_status >= 300:
        return 'inconclusive'
    if other_status in (401, 403, 404):
        return 'access_denied_or_hidden' if relationship == 'private' else 'unexpected_denial_check_setup'
    if 200 <= other_status < 300:
        return 'review_required_not_a_finding' if relationship == 'private' else 'consistent_with_shared_access'
    return 'inconclusive'
