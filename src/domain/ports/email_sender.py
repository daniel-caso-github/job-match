from __future__ import annotations

from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    def send_password_reset(self, to_email: str, reset_token: str) -> None: ...
