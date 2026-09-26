"""Errors services raise. fixa/api/main.py turns each into an HTTP status code."""


class NotFoundError(Exception):
    """The job, quote or user doesn't exist. -> 404"""


class PermissionDeniedError(Exception):
    """This user may not do this, e.g. a provider accepting their own quote. -> 403"""


class ContactDetailsLockedError(PermissionDeniedError):
    """Someone asked for contact details before both sides approved. -> 403"""
