from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True


# Book schemas
class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    published_year: int
    category: str
    copies_available: int = 1
    total_copies: int = 1


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    published_year: Optional[int] = None
    category: Optional[str] = None
    copies_available: Optional[int] = None
    total_copies: Optional[int] = None


class Book(BookBase):
    id: int

    class Config:
        from_attributes = True


# Loan schemas
class LoanBase(BaseModel):
    user_id: int
    book_id: int
    due_date: datetime


class LoanCreate(LoanBase):
    pass


class Loan(LoanBase):
    id: int
    loan_date: datetime
    return_date: Optional[datetime]
    status: str

    class Config:
        from_attributes = True


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Recommendation schema
class RecommendationRequest(BaseModel):
    user_id: int
    limit: int = 5


class RecommendationResponse(BaseModel):
    books: List[Book]
    reason: str