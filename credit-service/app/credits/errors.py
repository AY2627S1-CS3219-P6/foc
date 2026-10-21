"""Safe API errors and definitive credit rejections. Messages never echo inputs."""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message


def unavailable(code: str = "DEPENDENCY_UNAVAILABLE") -> ApiError:
    return ApiError(503, code, "A required service is unavailable. Retry safely.")


class CreditError(Exception):
    """A definitive business rejection. The transaction rolled back; nothing was written."""

    code = "CREDIT_REJECTED"
    # Consumer only: True means a later attempt may succeed (e.g. a wallet still being created).
    retryable = False

    def __init__(self):
        super().__init__(self.code)


class InsufficientCredit(CreditError):
    code = "INSUFFICIENT_CREDIT"


class WalletNotReady(CreditError):
    code = "WALLET_NOT_READY"
    retryable = True


class IdentityConflict(CreditError):
    code = "IDENTITY_CONFLICT"


class SettlementConflict(CreditError):
    code = "SETTLEMENT_CONFLICT"


class UnknownReservation(CreditError):
    code = "UNKNOWN_RESERVATION"
