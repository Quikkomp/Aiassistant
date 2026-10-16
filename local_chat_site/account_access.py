"""Roles are set from the account DB by the auth request guard, never by UI flags."""
from flask import session
from exam_store import ExamError


def is_teacher():
    return session.get('auth_role') == 'teacher'


def require_teacher():
    if not is_teacher():
        raise ExamError('此操作仅限老师账号使用。学生可以参加考试并查看自己的作答。', 403)
