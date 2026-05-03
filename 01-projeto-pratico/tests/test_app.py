from password_generator import create_app


def test_index_page_loads():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Gerador de Senhas" in response.data


def test_api_generates_password():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/passwords",
        json={
            "length": 18,
            "use_uppercase": True,
            "use_lowercase": True,
            "use_digits": True,
            "use_symbols": False,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["password"]) == 18
    assert payload["strength"]["score"] >= 1


def test_api_rejects_invalid_request():
    app = create_app()
    client = app.test_client()

    response = client.post(
        "/api/passwords",
        json={
            "length": 12,
            "use_uppercase": False,
            "use_lowercase": False,
            "use_digits": False,
            "use_symbols": False,
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()
