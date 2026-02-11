class AIMBlockedException(Exception):
    def __init__(self, reason: str, details: dict = None):
        self.reason = reason
        self.details = details or {}
        super().__init__(f"AIM blocked: {reason}")
