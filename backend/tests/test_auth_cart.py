from app.models.product import Product
from app.models.user import User
from app.core.security import hash_password


def test_register_login_refresh_and_me(client):
    register_payload = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "password": "StrongPass1",
        "phone": "0712345678",
        "address": "Nairobi",
    }
    register_response = client.post("/auth/register", json=register_payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": "jane@example.com", "password": "StrongPass1"},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data

    me_response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "jane@example.com"

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": token_data["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()


def test_cart_persists_and_returns_product_details(client, db_session):
    db_session.add(
        User(
            full_name="Cart User",
            email="cart@example.com",
            password_hash=hash_password("StrongPass1"),
            phone=None,
            address=None,
        )
    )
    db_session.add(
        Product(
            name="Sample Product",
            description="Used for tests",
            price=999.99,
            image_url="/uploads/products/sample.png",
        )
    )
    db_session.commit()

    login_response = client.post(
        "/auth/login",
        json={"email": "cart@example.com", "password": "StrongPass1"},
    )
    token = login_response.json()["access_token"]

    add_response = client.post(
        "/cart/items",
        json={"product_id": 1, "quantity": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert add_response.status_code == 201
    data = add_response.json()
    assert data["product"]["name"] == "Sample Product"
    assert data["quantity"] == 2

    list_response = client.get("/cart/items", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["product"]["id"] == 1
