def test_index(client):
    """Test the home page returns HTML."""
    response = client.get("/")

    assert response.status_code == 200
    assert b"Cloned-It" in response.data
    assert b"Welcome" in response.data
