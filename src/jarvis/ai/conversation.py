"""Short-term conversation context.

The history is APPEND-ONLY: earlier turns are never edited, reordered or removed, because
the model's reasoning blocks are bound to the exact conversation prefix that produced them
(editing it makes the API reject or drop them) and because a stable prefix keeps the prompt
cache warm. When the conversation gets too long it is summarized and restarted from scratch.
"""

from __future__ import annotations

from collections.abc import Sequence

from anthropic.types.beta import BetaContentBlock, BetaMessageParam


def history_content(blocks: Sequence[BetaContentBlock]) -> list[BetaContentBlock]:
    """Blocks of an assistant response that are safe to send back in later requests.

    After a server-side fallback (another model continued after a decline), only text blocks
    from before the last `fallback` marker may be echoed; everything after it is echoed as is.
    """
    last_fallback = max((i for i, b in enumerate(blocks) if b.type == "fallback"), default=-1)
    if last_fallback < 0:
        return list(blocks)
    before = [b for b in blocks[:last_fallback] if b.type == "text"]
    return before + list(blocks[last_fallback + 1 :])


class Conversation:
    def __init__(self, max_turns: int) -> None:
        self._max_turns = max_turns
        self._messages: list[BetaMessageParam] = []
        self._turns = 0
        self._pending_summary: str | None = None

    @property
    def turns(self) -> int:
        return self._turns

    @property
    def is_full(self) -> bool:
        return self._turns >= self._max_turns

    @property
    def pending_summary(self) -> str | None:
        """Summary of the previous conversation; goes into the next user turn until committed."""
        return self._pending_summary

    def with_user_turn(self, user_text: str) -> list[BetaMessageParam]:
        """History plus a new user turn. Does NOT modify the history."""
        return [*self._messages, {"role": "user", "content": user_text}]

    def commit(self, user_text: str, assistant_blocks: Sequence[BetaContentBlock]) -> None:
        """Append a completed exchange. Call only after a successful response."""
        content = history_content(assistant_blocks)
        if not content:
            raise ValueError("assistant turn has no content to store")
        self._messages.append({"role": "user", "content": user_text})
        self._messages.append({"role": "assistant", "content": content})
        self._turns += 1
        self._pending_summary = None

    def restart(self, summary: str | None = None) -> None:
        """Start a fresh conversation, optionally carrying a summary of the old one."""
        self._messages = []
        self._turns = 0
        self._pending_summary = summary or None
