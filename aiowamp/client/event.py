from __future__ import annotations

from typing import Generic, Tuple, TypeVar

import aiowamp
from .abstract import ClientABC, SubscriptionEventABC

__all__ = ["SubscriptionEvent"]

ClientT = TypeVar("ClientT", bound=ClientABC)


class SubscriptionEvent(SubscriptionEventABC[ClientT], Generic[ClientT]):
    __slots__ = ("__client",
                 "__topic", "__publication_id",
                 "__args", "__kwargs", "__details")

    __client: ClientT

    __topic: aiowamp.URI
    __publication_id: int

    __args: Tuple[aiowamp.WAMPType, ...]
    __kwargs: aiowamp.WAMPDict
    __details: aiowamp.WAMPDict

    def __init__(self, client: ClientT, msg: aiowamp.msg.Event, *,
                 topic: aiowamp.URI) -> None:
        """Create a new SubscriptionEven instance.

        There shouldn't be a need to create these yourself, unless you're
        creating your own `aiowamp.ClientABC`.
        Unlike `aiowamp.Invocation` it doesn't require to be managed though.

        Args:
            client: Client used to unsubscribe.
            msg: Event message.
            topic: Registered topic URI.
        """
        self.__client = client

        self.__topic = topic
        self.__publication_id = msg.publication_id

        self.__args = tuple(msg.args) if msg.args else ()
        self.__kwargs = msg.kwargs or {}
        self.__details = msg.details

    @property
    def client(self) -> ClientT:
        return self.__client

    @property
    def publication_id(self) -> int:
        return self.__publication_id

    @property
    def subscribed_topic(self) -> aiowamp.URI:
        return self.__topic

    @property
    def args(self) -> Tuple[aiowamp.WAMPType, ...]:
        return self.__args

    @property
    def kwargs(self) -> aiowamp.WAMPDict:
        return self.__kwargs

    @property
    def details(self) -> aiowamp.WAMPDict:
        return self.__details

    async def unsubscribe(self) -> None:
        await self.__client.unsubscribe(self.__topic)
