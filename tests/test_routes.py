def test_index(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"message": "App!"}
