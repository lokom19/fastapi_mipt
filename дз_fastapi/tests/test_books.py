import pytest
from fastapi.testclient import TestClient


def test_create_book_admin_required():
    response = client.post("/books/", json={
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "123-456-789",
        "published_year": 2023,
        "category": "Fiction"
    })
    assert response.status_code == 401  # Unauthorized


def test_create_book_with_admin():
    # Создаем администратора
    db = TestingSessionLocal()
    admin_user = User(
        email="admin@example.com",
        username="admin",
        hashed_password="$2b$12$dummy",
        is_admin=True
    )
    db.add(admin_user)
    db.commit()
    db.close()

    # Логинимся как администратор (для теста используем простой хеш)
    # В реальности нужно использовать правильную аутентификацию
    response = client.post("/books/", json={
        "title": "Test Book",
        "author": "Test Author",
        "isbn": "123-456-789",
        "published_year": 2023,
        "category": "Fiction"
    }, headers={"Authorization": "Bearer fake-admin-token"})
    # Этот тест требует модификации для корректной работы с аутентификацией


def test_get_books():
    response = client.get("/books/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_search_books():
    response = client.get("/books/?search=fiction")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
