from unittest.mock import MagicMock, patch


def test_is_authenticated_false_when_no_token(db):
    from reddit.auth import is_authenticated
    with patch("reddit.auth.settings") as mock_settings:
        mock_settings.database_path = ":memory:"
        # Using db fixture directly
        assert is_authenticated(db) is False


def test_is_authenticated_true_when_token_present(db):
    from reddit.auth import is_authenticated
    db.execute("INSERT INTO user_settings (key, value) VALUES ('reddit_refresh_token', 'tok123')")
    db.commit()
    assert is_authenticated(db) is True


def test_handle_callback_rejects_wrong_state(db):
    from reddit.auth import handle_callback
    db.execute("INSERT INTO user_settings (key, value) VALUES ('oauth_state', 'correct_state')")
    db.commit()
    result = handle_callback(db, code="somecode", state="wrong_state")
    assert result is False


def test_handle_callback_stores_token(db):
    from reddit.auth import handle_callback
    db.execute("INSERT INTO user_settings (key, value) VALUES ('oauth_state', 'mystate')")
    db.commit()
    with patch("reddit.auth.praw.Reddit") as MockReddit:
        mock_reddit = MagicMock()
        mock_reddit.auth.authorize.return_value = "refresh_token_abc"
        MockReddit.return_value = mock_reddit
        result = handle_callback(db, code="authcode", state="mystate")
    assert result is True
    row = db.execute("SELECT value FROM user_settings WHERE key = 'reddit_refresh_token'").fetchone()
    assert row["value"] == "refresh_token_abc"
