from unittest.mock import MagicMock, patch


def test_is_authenticated_false_when_no_credentials(db):
    from reddit.auth import is_authenticated
    assert is_authenticated(db) is False


def test_is_authenticated_false_when_partial_credentials(db):
    from reddit.auth import is_authenticated
    db.execute("INSERT INTO user_settings (key, value) VALUES ('reddit_client_id', 'abc')")
    db.execute("INSERT INTO user_settings (key, value) VALUES ('reddit_client_secret', 'xyz')")
    db.commit()
    assert is_authenticated(db) is False


def test_is_authenticated_true_when_all_credentials_present(db):
    from reddit.auth import is_authenticated
    for key, val in [
        ("reddit_client_id", "abc"),
        ("reddit_client_secret", "xyz"),
        ("reddit_username", "testuser"),
        ("reddit_password", "testpass"),
    ]:
        db.execute("INSERT INTO user_settings (key, value) VALUES (?, ?)", (key, val))
    db.commit()
    assert is_authenticated(db) is True


def test_get_reddit_instance_returns_none_when_missing_credentials(db):
    from reddit.auth import get_reddit_instance
    assert get_reddit_instance(db) is None


def test_get_reddit_instance_returns_reddit_when_credentials_present(db):
    from reddit.auth import get_reddit_instance
    for key, val in [
        ("reddit_client_id", "abc"),
        ("reddit_client_secret", "xyz"),
        ("reddit_username", "testuser"),
        ("reddit_password", "testpass"),
    ]:
        db.execute("INSERT INTO user_settings (key, value) VALUES (?, ?)", (key, val))
    db.commit()
    with patch("reddit.auth.praw.Reddit") as MockReddit:
        mock_reddit = MagicMock()
        MockReddit.return_value = mock_reddit
        result = get_reddit_instance(db)
    assert result is mock_reddit
    MockReddit.assert_called_once_with(
        client_id="abc",
        client_secret="xyz",
        username="testuser",
        password="testpass",
        user_agent="redditsave/1.0",
    )
