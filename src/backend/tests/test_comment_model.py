"""Tests for Comment model."""
import pytest
from datetime import datetime
from src.models.comment import Comment


def test_create_comment(db_session, test_user, sample_tutorial):
    comment = Comment.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id),
        content="Great tutorial!"
    )
    assert comment.user_id == str(test_user.id)
    assert comment.tutorial_id == str(sample_tutorial.id)
    assert comment.content == "Great tutorial!"
    assert comment.like_count == 0


def test_create_reply(db_session, test_user, sample_tutorial):
    """Test creating a reply to a comment."""
    parent = Comment.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id),
        content="Parent comment"
    )
    reply = Comment.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id),
        content="Reply",
        parent_id=parent.id
    )
    assert reply.parent_id == parent.id
    assert reply.is_reply is True


def test_comment_to_dict(db_session, test_user, sample_tutorial):
    comment = Comment.create(
        db=db_session,
        user_id=str(test_user.id),
        tutorial_id=str(sample_tutorial.id),
        content="Test comment"
    )
    d = comment.to_dict()
    assert d["content"] == "Test comment"
    assert d["like_count"] == 0
    assert "id" in d
    assert "created_at" in d


def test_get_by_tutorial(db_session, test_user, sample_tutorial):
    """Test getting comments for a tutorial."""
    Comment.create(db=db_session, user_id=str(test_user.id), tutorial_id=str(sample_tutorial.id), content="Comment 1")
    Comment.create(db=db_session, user_id=str(test_user.id), tutorial_id=str(sample_tutorial.id), content="Comment 2")

    comments = Comment.get_by_tutorial(db=db_session, tutorial_id=str(sample_tutorial.id))
    assert len(comments) == 2
