from typing import Any


def send_email_alert(subject: str, to_email: str, **kwargs: Any) -> None:
	# Lightweight default implementation for development.
	# Real implementation can live in a separate module and be imported here.
	print(f"[ALERT] To: {to_email} | Subject: {subject}")


__all__ = ["send_email_alert"]