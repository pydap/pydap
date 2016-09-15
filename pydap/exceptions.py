"""
DAP exceptions.

These exceptions are mostly used by the server. When an exception is
captured, a proper error message is displayed (according to the DAP
2.0 spec), with information about the exception and the error code 
associated with it.

The error codes are attributed using the "first come, first serve"
algorithm.

"""


class DapError(Exception):
    """
    Base DAP exception.

    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ClientError(DapError):
    """
    Generic error with the client.

    """
    code = 100


class ServerError(DapError):
    """
    Generic error with the server.

    """
    code = 200


class ConstraintExpressionError(ServerError):
    """
    Exception raised when an invalid constraint expression is given.

    """
    code = 201


class HandlerError(DapError):
    """
    Generic error with a handler.

    """
    code = 300


class ExtensionNotSupportedError(HandlerError):
    """
    Exception raised when trying to open a file not supported by any
    handlers.

    """
    code = 301


class OpenFileError(HandlerError):
    """
    Exception raised when unable to open a file.

    """
    code = 302
