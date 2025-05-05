from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from main import app
from database import Base, get_db
from models import User, Book, Loan

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Очищаем БД перед каждым тестом
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Очищаем после теста
    Base.metadata.drop_all(bind=engine)


def test_register_user():
    response = client.post("/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "hashed_password" not in data


def test_login():
    # Сначала регистрируем пользователя
    client.post("/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })

    # Проверяем вход
    response = client.post("/token", data={
        "username": "testuser",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_protected_route():
    # Тест без токена
    response = client.get("/users/me")
    assert response.status_code == 401

    # Регистрация и вход
    client.post("/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })

    login_response = client.post("/token", data={
        "username": "testuser",
        "password": "password123"
    })
    token = login_response.json()["access_token"]

    # Тест с токеном
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
