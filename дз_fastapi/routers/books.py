from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Book as BookModel, User as UserModel
from schemas import Book, BookCreate, BookUpdate
from auth import get_current_user, get_admin_user

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/", response_model=Book)
def create_book(book: BookCreate, db: Session = Depends(get_db),
                current_user: UserModel = Depends(get_admin_user)):
    db_book = db.query(BookModel).filter(BookModel.isbn == book.isbn).first()
    if db_book:
        raise HTTPException(status_code=400, detail="ISBN already registered")

    db_book = BookModel(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book


@router.get("/", response_model=List[Book])
def read_books(skip: int = 0, limit: int = 100, category: Optional[str] = None,
               search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(BookModel)

    if category:
        query = query.filter(BookModel.category == category)

    if search:
        query = query.filter(
            (BookModel.title.contains(search)) |
            (BookModel.author.contains(search))
        )

    books = query.offset(skip).limit(limit).all()
    return books


@router.get("/{book_id}", response_model=Book)
def read_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=Book)
def update_book(book_id: int, book: BookUpdate, db: Session = Depends(get_db),
                current_user: UserModel = Depends(get_admin_user)):
    db_book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    update_data = book.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_book, field, value)

    db.commit()
    db.refresh(db_book)
    return db_book


@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db),
                current_user: UserModel = Depends(get_admin_user)):
    db_book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(db_book)
    db.commit()
    return {"detail": "Book deleted successfully"}