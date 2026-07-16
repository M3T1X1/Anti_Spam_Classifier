def test_favicon_should_200(guest):
    assert guest.get('/favicon.png').status_code == 200