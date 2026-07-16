def test_analytics_should_302(guest):
    assert guest.get('/analytics').status_code == 302


def test_analytics_logged_in_should_200(logged_in_user):
    resp = logged_in_user.get('/analytics')
    assert resp.status_code == 200