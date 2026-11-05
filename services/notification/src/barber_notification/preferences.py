"""Notification preferences: one switch per kind and channel, on by default.

Stored as a JSON matrix in ``recipients.preferences``. Only an explicit ``false`` disables a
channel. The confirmation email ignores preferences.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from barber_notification.providers.base import Channel

__all__ = ["NotificationKind", "PreferenceChanges", "Preferences"]


class NotificationKind(StrEnum):
    """What a notification is about, as the user switches it."""

    # A booking was made, moved or cancelled.
    BOOKINGS = "bookings"
    # A visit is coming up.
    REMINDERS = "reminders"


# Switches to flip: the kinds and channels named, and nothing else.
PreferenceChanges = Mapping[NotificationKind, Mapping[Channel, bool]]


@dataclass(frozen=True, slots=True)
class Preferences:
    """The switches of one user. Kept as the ones turned off: the rest are on."""

    switched_off: frozenset[tuple[NotificationKind, Channel]] = frozenset()

    @classmethod
    def from_stored(cls, stored: Mapping[str, object]) -> Preferences:
        """Read what ``recipients.preferences`` holds."""
        switched_off = set()
        for kind in NotificationKind:
            channels = stored.get(kind.value)
            if not isinstance(channels, Mapping):
                continue
            for channel in Channel:
                if channels.get(channel.value) is False:
                    switched_off.add((kind, channel))
        return cls(frozenset(switched_off))

    def allows(self, kind: NotificationKind, channel: Channel) -> bool:
        return (kind, channel) not in self.switched_off

    def with_changes(self, changes: PreferenceChanges) -> Preferences:
        """These switches flipped as asked, every other one as it was."""
        switched_off = set(self.switched_off)
        for kind, channels in changes.items():
            for channel, enabled in channels.items():
                if enabled:
                    switched_off.discard((kind, channel))
                else:
                    switched_off.add((kind, channel))
        return Preferences(frozenset(switched_off))

    def to_stored(self) -> dict[str, object]:
        """The whole matrix, as ``recipients.preferences`` keeps it."""
        return {
            kind.value: {channel.value: self.allows(kind, channel) for channel in Channel}
            for kind in NotificationKind
        }
