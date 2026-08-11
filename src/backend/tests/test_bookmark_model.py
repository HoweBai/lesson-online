import pytest
from datetime import datetime
from src.models.bookmark import Bookmark


def test_create_bookmark(db_session, test_user, sample_tutorial):
    bookmark = Bookmark.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id)
    )
    assert bookmark.user_id == str(test_user.id)
    assert bookmark.tutorial_id == str(sample_tutorial.id)
    assert bookmark.id is not None


def test_bookmark_to_dict(db_session, test_user, sample_tutorial):
    bookmark = Bookmark.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id)
    )
    d = bookmark.to_dict()
    assert d["user_id"] == str(test_user.id)
    assert d["tutorial_id"] == str(sample_tutorial.id)
    assert "id" in d
    assert "created_at" in d
