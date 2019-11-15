from __future__ import annotations

import dataclasses
import logging
from typing import Callable, Dict, Optional, Type

import aiowamp
from .uri_map import URIMap

__all__ = ["Error",
           "TransportError",
           "AbortError", "AuthError",
           "InvalidMessage", "UnexpectedMessageError",
           "ErrorResponse",
           "ClientClosed",
           "Interrupt",
           "register_error_response", "error_to_exception",
           "InvocationError", "exception_to_invocation_error",
           "set_invocation_error"]

log = logging.getLogger(__name__)


class Error(Exception):
    """Base exception for all WAMP related errors.

    You will most likely never encounter this error directly, but its
    subclasses.
    """
    __slots__ = ()


class TransportError(Error):
    """Transport level error."""
    __slots__ = ()


class AbortError(Error):
    """Join abort error."""
    __slots__ = ("reason", "details")

    reason: str
    details: aiowamp.WAMPDict

    def __init__(self, msg: aiowamp.msg.Abort) -> None:
        self.reason = msg.reason
        self.details = msg.details

    def __str__(self) -> str:
        return f"{self.reason} (details = {self.details})"


class AuthError(Error):
    __slots__ = ()


class InvalidMessage(Error):
    """Exception for invalid messages."""
    __slots__ = ()


@dataclasses.dataclass()
class UnexpectedMessageError(InvalidMessage):
    """Exception raised when an unexpected message type is received."""
    __slots__ = ("received", "expected")

    received: aiowamp.MessageABC
    """Message that was received."""

    expected: Type[aiowamp.MessageABC]
    """Message type that was expected."""

    def __str__(self) -> str:
        return f"received message {self.received!r} but expected message of type {self.expected.__qualname__}"


class ErrorResponse(Error):
    __slots__ = ("message",)

    message: aiowamp.msg.Error
    """Error message."""

    def __init__(self, message: aiowamp.msg.Error):
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self.message!r})"

    def __str__(self) -> str:
        s = f"{self.message.error}"

        args_str = ", ".join(map(repr, self.message.args))
        if args_str:
            s += f" {args_str}"

        kwargs_str = ", ".join(f"{k}={v!r}" for k, v in self.message.kwargs.items())
        if kwargs_str:
            s += f" ({kwargs_str})"

        return s

    @property
    def uri(self) -> aiowamp.URI:
        return self.message.error


ErrorFactory = Callable[["aiowamp.msg.Error"], Exception]
"""Callable creating an exception from a WAMP error message."""

ERR_RESP_MAP: URIMap[ErrorFactory] = URIMap()
EXC_URI_MAP: Dict[Type[Exception], aiowamp.URI] = {}


def register_error_response(uri: str):
    uri = aiowamp.URI.as_uri(uri)

    def decorator(cls: ErrorFactory):
        if not callable(cls):
            raise TypeError("error factory must be callable")

        ERR_RESP_MAP[uri] = cls

        return cls

    return decorator


def get_exception_factory(uri: str) -> ErrorFactory:
    return ERR_RESP_MAP[uri]


def error_to_exception(message: aiowamp.msg.Error) -> Exception:
    try:
        return get_exception_factory(message.error)(message)
    except LookupError:
        return ErrorResponse(message)


def get_exception_uri(exc: Type[Exception]) -> aiowamp.URI:
    return EXC_URI_MAP[exc]


class InvocationError(Error):
    __slots__ = ("uri",
                 "args", "kwargs",
                 "details")

    uri: aiowamp.URI
    args: Optional[aiowamp.WAMPList]
    kwargs: Optional[aiowamp.WAMPDict]
    details: Optional[aiowamp.WAMPDict]

    def __init__(self, uri: str, *args: aiowamp.WAMPType,
                 kwargs: aiowamp.WAMPDict = None,
                 details: aiowamp.WAMPDict = None) -> None:
        self.uri = aiowamp.URI.as_uri(uri)
        self.args = list(args) or None
        self.kwargs = kwargs or None
        self.details = details or None

    def _init(self, other: InvocationError) -> None:
        self.uri = other.uri
        self.args = other.args
        self.kwargs = other.kwargs
        self.details = other.details

    def __repr__(self) -> str:
        if self.args:
            args_str = ", " + ", ".join(map(repr, self.args))
        else:
            args_str = ""

        if self.kwargs:
            kwargs_str = f", kwargs={self.kwargs!r}"
        else:
            kwargs_str = ""

        if self.details:
            details_str = f", details={self.details!r}"
        else:
            details_str = ""

        return f"{type(self).__qualname__}({self.uri!r}{args_str}{kwargs_str}{details_str})"

    def __str__(self) -> str:
        if self.args:
            args_str = ", ".join(map(str, self.args))
            return f"{self.uri} {args_str}"

        return self.uri


ATTACHED_ERR_KEY = "__invocation_error__"


def set_invocation_error(exc: Exception, err: InvocationError) -> None:
    if isinstance(exc, InvocationError):
        log.info("overwriting %s with %s", exc, err)
        exc._init(err)
        return

    setattr(exc, ATTACHED_ERR_KEY, err)


def exception_to_invocation_error(exc: Exception) -> InvocationError:
    if isinstance(exc, InvocationError):
        return exc

    try:
        return getattr(exc, ATTACHED_ERR_KEY)
    except AttributeError:
        pass

    try:
        uri = get_exception_uri(type(exc))
    except LookupError:
        log.info(f"no uri registered for exception {type(exc).__qualname__}. "
                 f"Using {aiowamp.uri.RUNTIME_ERROR!r}")
        uri = aiowamp.uri.RUNTIME_ERROR

    return InvocationError(uri, *exc.args)


class ClientClosed(Error):
    __slots__ = ()


class Interrupt(Error):
    __slots__ = ("options",)

    options: aiowamp.WAMPDict
    """Options sent with the interrupt."""

    def __init__(self, options: aiowamp.WAMPDict) -> None:
        self.options = options

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(options={self.options!r})"

    @property
    def cancel_mode(self) -> aiowamp.CancelMode:
        """Cancel mode sent with the interrupt."""
        return self.options["mode"]
