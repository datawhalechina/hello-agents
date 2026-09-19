from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar('T')

class Response(BaseModel, Generic[T]):
    code: int = 200
    message: str = "Success"
    data: Optional[T] = None

def success(data: T = None, message: str = "Success") -> Response[T]:
    return Response(code=200, message=message, data=data)

def error(code: int = 500, message: str = "Error", data: Any = None) -> Response:
    return Response(code=code, message=message, data=data)
