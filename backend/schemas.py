from pydantic import BaseModel
from typing import Optional, List

# Category Schemas
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    
    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    contact_number: Optional[str] = None
    address_line_1: str
    address_line_2: str
    address_line_3: str

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    
    class Config:
        from_attributes = True

# Seller Schemas
class SellerBase(BaseModel):
    category_id: int
    first_name: str
    last_name: str
    email: str
    password: str
    contact_number: Optional[str] = None
    address_line_1: str
    address_line_2: str
    address_line_3: str

class SellerCreate(SellerBase):
    pass

class SellerResponse(SellerBase):
    id: int
    
    class Config:
        from_attributes = True

# Company Schemas
class CompanyBase(BaseModel):
    name: str
    email: str
    password: str
    contact_number: Optional[str] = None
    address_line_1: str
    address_line_2: str
    address_line_3: str

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: int
    
    class Config:
        from_attributes = True

# Product Schemas
class ProductBase(BaseModel):
    category_id: int
    seller_id: int
    company_id: int
    name: str
    price: int
    description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    
    class Config:
        from_attributes = True
