"""Email provider abstraction for password reset and notifications."""
from abc import ABC, abstractmethod
import logging
from config import settings

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract email delivery interface."""

    @abstractmethod
    async def send(self, recipient: str, subject: str, body: str) -> None:
        """Send an email message."""


class ConsoleEmailProvider(EmailProvider):
    """Development provider that logs email content."""

    async def send(self, recipient: str, subject: str, body: str) -> None:
        """Log an email instead of sending it."""
        logger.info("Email to %s: %s\n%s", recipient, subject, body)


def get_email_provider() -> EmailProvider:
    """Return the configured email provider."""
    return ConsoleEmailProvider()
