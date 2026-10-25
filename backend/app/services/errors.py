"""Base class for business-rule violations raised by services."""


class ServiceError(Exception):
    """`code` is a stable machine-readable id; `message` (also `str(error)`) is shown to people.

    Services don't know about HTTP; `app.errors` maps each subclass to a status code.
    """

    code = "service_error"
    message = "Service error"

    def __init__(self) -> None:
        super().__init__(self.message)
