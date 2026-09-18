from typing import Annotated
from pydantic import ConfigDict, BaseModel, EmailStr, Field

class Supplier(BaseModel):
    sid: int = Field(strict=True, gt=0)
    sname: str = Field(..., min_length=5, max_length=35)
    email: EmailStr | None = None


class Product(BaseModel):
    pid: int = Field(..., strict=True, gt=0)
    name: str = Field(..., min_length=3, max_length=25)
    description: str | None = None
    price: float = Field(..., gt=0.00)
    supplier: Supplier 


class UpdateSupplier(BaseModel):
    sname: str | None = None
    slocation: str | None = None
    email: EmailStr | None = None


class UpdateProduct(BaseModel):
    name: Annotated[str | None, Field(..., min_length=3, max_length=25)] = None
    description: str | None = None
    price: Annotated[float | None,  Field(gt=0)] = None
    supplier: Supplier | None = None

class ResponseBody(Product):
    model_config = ConfigDict(from_attributes=True)

