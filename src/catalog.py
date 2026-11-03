"""Compatibility shim: logic now lives in badminton.domain and badminton.data."""
from badminton.container import get_usecases
from badminton.domain.contracts import RACKET_SORTS as SORTS, SHOE_SORTS

_uc = get_usecases()
list_rackets = _uc.list_rackets
list_shoes = _uc.list_shoes