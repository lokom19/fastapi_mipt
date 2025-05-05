from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from database import get_db
from models import Loan as LoanModel, Book as BookModel, User as UserModel
from schemas import Loan, LoanCreate
from auth import get_current_user, get_admin_user

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("/", response_model=Loan)
def create_loan(loan: LoanCreate, db: Session = Depends(get_db),
                current_user: UserModel = Depends(get_admin_user)):
    # Проверяем существование книги и пользователя
    book = db.query(BookModel).filter(BookModel.id == loan.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    user = db.query(UserModel).filter(UserModel.id == loan.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверяем доступность книги
    if book.copies_available <= 0:
        raise HTTPException(status_code=400, detail="Book not available")

    # Создаем займ
    db_loan = LoanModel(**loan.dict())
    book.copies_available -= 1

    db.add(db_loan)
    db.commit()
    db.refresh(db_loan)
    return db_loan


@router.get("/", response_model=List[Loan])
def read_loans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
               current_user: UserModel = Depends(get_admin_user)):
    loans = db.query(LoanModel).offset(skip).limit(limit).all()
    return loans


@router.get("/my", response_model=List[Loan])
def read_user_loans(current_user: UserModel = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    loans = db.query(LoanModel).filter(LoanModel.user_id == current_user.id).all()
    return loans


@router.put("/{loan_id}/return", response_model=Loan)
def return_book(loan_id: int, db: Session = Depends(get_db),
                current_user: UserModel = Depends(get_admin_user)):
    loan = db.query(LoanModel).filter(LoanModel.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status != "active":
        raise HTTPException(status_code=400, detail="Book already returned")

    # Возвращаем книгу
    loan.return_date = datetime.utcnow()
    loan.status = "returned"

    # Увеличиваем количество доступных экземпляров
    book = db.query(BookModel).filter(BookModel.id == loan.book_id).first()
    book.copies_available += 1

    db.commit()
    db.refresh(loan)
    return loan


@router.get("/overdue", response_model=List[Loan])
def get_overdue_loans(db: Session = Depends(get_db),
                      current_user: UserModel = Depends(get_admin_user)):
    current_time = datetime.utcnow()
    overdue_loans = db.query(LoanModel).filter(
        LoanModel.status == "active",
        LoanModel.due_date < current_time
    ).all()

    # Обновляем статус просроченных займов
    for loan in overdue_loans:
        loan.status = "overdue"

    db.commit()
    return overdue_loans