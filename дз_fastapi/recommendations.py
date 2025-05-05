from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from collections import Counter

from database import get_db
from models import Loan as LoanModel, Book as BookModel, User as UserModel
from schemas import RecommendationRequest, RecommendationResponse, Book
from auth import get_current_user

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def collaborative_filtering(db: Session, user_id: int, limit: int = 5) -> List[BookModel]:
    """
    Коллаборативная фильтрация основанная на займах книг
    Находит пользователей с похожими предпочтениями и рекомендует их любимые книги
    """
    # Получаем историю займов пользователя
    user_loans = db.query(LoanModel).filter(LoanModel.user_id == user_id).all()
    user_books = {loan.book_id for loan in user_loans}

    if not user_books:
        # Если у пользователя нет истории, возвращаем популярные книги
        return get_popular_books(db, limit)

    # Находим похожих пользователей по займам
    similar_users = []
    all_users = db.query(UserModel).filter(UserModel.id != user_id).all()

    for other_user in all_users:
        other_loans = db.query(LoanModel).filter(LoanModel.user_id == other_user.id).all()
        other_books = {loan.book_id for loan in other_loans}

        # Вычисляем схожесть (Jaccard similarity)
        intersection = user_books.intersection(other_books)
        union = user_books.union(other_books)
        similarity = len(intersection) / len(union) if union else 0

        if similarity > 0:
            similar_users.append((other_user.id, similarity))

    # Сортируем по схожести
    similar_users.sort(key=lambda x: x[1], reverse=True)

    # Собираем рекомендации от похожих пользователей
    recommendations = Counter()
    for similar_user_id, similarity in similar_users[:10]:  # Берем топ 10 похожих
        similar_loans = db.query(LoanModel).filter(LoanModel.user_id == similar_user_id).all()
        for loan in similar_loans:
            if loan.book_id not in user_books:  # Пропускаем уже прочитанные
                recommendations[loan.book_id] += similarity

    # Сортируем по скору и возвращаем топ N
    top_book_ids = [book_id for book_id, _ in recommendations.most_common(limit)]
    return db.query(BookModel).filter(BookModel.id.in_(top_book_ids)).all()


def content_based_filtering(db: Session, user_id: int, limit: int = 5) -> List[BookModel]:
    """
    Контентная фильтрация на основе категорий и авторов
    """
    # Анализируем предпочтения пользователя
    user_loans = db.query(LoanModel).join(BookModel).filter(LoanModel.user_id == user_id).all()

    if not user_loans:
        return get_popular_books(db, limit)

    # Собираем статистику по категориям и авторам
    categories = Counter()
    authors = Counter()

    for loan in user_loans:
        book = loan.book
        categories[book.category] += 1
        authors[book.author] += 1

    # Находим любимые категории и авторов
    favorite_category = categories.most_common(1)[0][0] if categories else None
    favorite_author = authors.most_common(1)[0][0] if authors else None

    # Формируем рекомендации
    query = db.query(BookModel)

    # Исключаем уже прочитанные книги
    read_book_ids = [loan.book_id for loan in user_loans]
    query = query.filter(~BookModel.id.in_(read_book_ids))

    # Приоритезируем любимые категории и авторов
    if favorite_category and favorite_author:
        # Сначала книги того же автора и категории
        same_author_category = query.filter(
            BookModel.author == favorite_author,
            BookModel.category == favorite_category
        ).limit(limit).all()

        if len(same_author_category) < limit:
            # Затем книги той же категории
            same_category = query.filter(
                BookModel.category == favorite_category
            ).limit(limit - len(same_author_category)).all()

            if len(same_author_category) + len(same_category) < limit:
                # Затем книги того же автора
                same_author = query.filter(
                    BookModel.author == favorite_author
                ).limit(limit - len(same_author_category) - len(same_category)).all()

                return same_author_category + same_category + same_author
            else:
                return same_author_category + same_category
        else:
            return same_author_category

    return get_popular_books(db, limit)


def get_popular_books(db: Session, limit: int = 5) -> List[BookModel]:
    """
    Возвращает популярные книги на основе количества займов
    """
    popular = db.query(BookModel, func.count(LoanModel.id).label('loan_count')) \
        .outerjoin(LoanModel) \
        .group_by(BookModel.id) \
        .order_by(func.count(LoanModel.id).desc()) \
        .limit(limit) \
        .all()

    return [book for book, _ in popular]


@router.post("/", response_model=RecommendationResponse)
def get_recommendations(request: RecommendationRequest, db: Session = Depends(get_db)):
    """
    Гибридная система рекомендаций, сочетающая коллаборативную и контентную фильтрацию
    """
    user = db.query(UserModel).filter(UserModel.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем рекомендации обоими методами
    collab_books = collaborative_filtering(db, request.user_id, request.limit // 2)
    content_books = content_based_filtering(db, request.user_id, request.limit - len(collab_books))

    # Объединяем результаты, избегая дубликатов
    all_books = collab_books + content_books
    unique_books = []
    seen_ids = set()

    for book in all_books:
        if book.id not in seen_ids:
            unique_books.append(book)
            seen_ids.add(book.id)

    # Обрезаем до нужного лимита
    final_books = unique_books[:request.limit]

    # Определяем причину рекомендации
    reason = "Based on your reading history and similar users' preferences"

    return RecommendationResponse(books=final_books, reason=reason)
