from sqlalchemy.exc import OperationalError

from app.db.session import _is_auth_failure


class FakeDriverError(Exception):
    def __init__(self, message, sqlstate=None):
        super().__init__(message)
        self.sqlstate = sqlstate


def operational(message, sqlstate=None):
    return OperationalError("SELECT 1", {}, FakeDriverError(message, sqlstate))


def test_login_refusals_are_recognised_with_or_without_a_sqlstate():
    assert _is_auth_failure(operational("anything", sqlstate="28P01"))
    assert _is_auth_failure(operational('connection failed: FATAL:  password authentication failed for user "u"'))
    assert _is_auth_failure(operational('FATAL:  no pg_hba.conf entry for host "1.2.3.4", user "u"'))


def test_other_connection_problems_are_not_mistaken_for_a_login_refusal():
    assert not _is_auth_failure(operational("connection failed: Connection refused"))
    assert not _is_auth_failure(operational("timeout expired"))
    assert not _is_auth_failure(operational("could not translate host name to address"))
