"""Live view of a Lexman video doorbell: WebRTC signaling over REST (#259).

The doorbell has no signaling socket. Two routes carry the whole negotiation, as
one mailbox per node::

    POST videophone/{nodeId}/change-sdp-candidates-info   our offer + candidates
    GET  videophone/{nodeId}/check-sdp-candidates-info     the doorbell's answer

The app is always the offering side (APK ``yde``/``ude``): it waits for its own
ICE gathering to finish, posts the offer with the entire candidate list in one
body, then polls for the answer under a ten second budget. Home Assistant's
frontend takes the app's part here, so the sequence is the same, except that it
trickles its candidates after sending the offer, which is why the offer is held
back for a moment to let them in.

No route starts or ends a session: depositing the offer is what wakes the
doorbell, and hanging up is local (APK ``yde.a`` cancels its jobs and closes its
peer, it calls nothing). ``change-videophone-call`` is for answering a ring, not
for this: its ``ringingMediaId`` is required and only a real call has one.
"""

from __future__ import annotations

import asyncio
from time import monotonic
from typing import TYPE_CHECKING, Any

from ..const import LOGGER
from ..domain.videophone import offer_candidates, parse_sdp_answer
from ..exceptions import EnkiConnectionError
from .meari_signaling import reject_unanswered

if TYPE_CHECKING:
    from .transport import EnkiHttpClient

# How long the offer waits for the browser's candidates. They go in a single
# body, so one that arrives after the post is lost, hence the wait.
_GATHER_SECONDS = 2.5
# The app's own budget for the doorbell to answer, and how often it looks.
_ANSWER_SECONDS = 10.0
_POLL_SECONDS = 0.5


class VideophoneLiveSession:
    """One live view: the browser's offer, posted once, then its answer."""

    def __init__(self, offer_sdp: str) -> None:
        self._offer_sdp = offer_sdp
        # The frontend appends what it has gathered to the offer it sends.
        self._candidates = offer_candidates(offer_sdp)
        self._closed = False

    def add_candidate(self, candidate: dict[str, Any]) -> None:
        """Keep a candidate the browser trickled, as long as the offer is held."""
        if candidate not in self._candidates:
            self._candidates.append(candidate)

    def close(self) -> None:
        """Give up: the viewer closed the stream before it was negotiated."""
        self._closed = True

    async def negotiate(
        self, transport: EnkiHttpClient, home_id: str, node_id: str
    ) -> tuple[str, list[dict[str, Any]]]:
        """Post the offer once the candidates are in, and wait for the answer."""
        await asyncio.sleep(_GATHER_SECONDS)
        if self._closed:
            raise EnkiConnectionError("the live view was closed before it started")
        LOGGER.debug(
            "Videophone live offer for %s: %s candidate(s)", node_id, len(self._candidates)
        )
        await transport.change_videophone_sdp_info(
            home_id,
            node_id,
            {"sdp": self._offer_sdp, "candidates": self._candidates},
        )
        return await self._await_answer(transport, home_id, node_id)

    async def _await_answer(
        self, transport: EnkiHttpClient, home_id: str, node_id: str
    ) -> tuple[str, list[dict[str, Any]]]:
        deadline = monotonic() + _ANSWER_SECONDS
        while not self._closed and monotonic() < deadline:
            await asyncio.sleep(_POLL_SECONDS)
            answer = parse_sdp_answer(
                await transport.get_videophone_sdp_info(home_id, node_id),
                offered=self._offer_sdp,
            )
            if answer is not None:
                sdp, candidates = answer
                # The app opens no data channel, so the doorbell drops the one the
                # browser offers, and a browser refuses a shorter answer.
                return reject_unanswered(self._offer_sdp, sdp), candidates
        raise EnkiConnectionError("the doorbell did not answer the live view offer")
