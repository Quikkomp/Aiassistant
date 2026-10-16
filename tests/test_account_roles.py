"""Real auth plus role-protected exam/group APIs, with disposable DBs and mock AI."""
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'local_chat_site'))
import test_auth_recovery as recovery_fixture
from auth_store import AuthStore
from werkzeug.security import generate_password_hash
from question_bank import BankStore
from exam_store import ExamStore
from exam_routes import make_exam_blueprint
from group_store import GroupStore
from group_routes import make_group_blueprint
from test_exams import FakeAI


class AccountRoleTests(unittest.TestCase):
    call = recovery_fixture.AuthRecoveryTests.call
    tearDown = recovery_fixture.AuthRecoveryTests.tearDown

    def setUp(self):
        recovery_fixture.AuthRecoveryTests.setUp(self)
        self.banks = BankStore(str(Path(self.temp.name)/'banks.sqlite3'))
        self.exams = ExamStore(str(Path(self.temp.name)/'exams.sqlite3'))
        self.app.register_blueprint(make_exam_blueprint(self.exams, self.banks, lambda:None, FakeAI()))
        self.app.register_blueprint(make_group_blueprint(GroupStore(self.exams)))

    def register(self, role='student', name='learner'):
        client = self.app.test_client()
        data = dict(username=name, email=name+'@qq.com', password='password-123', confirm_password='password-123', role=role)
        result = self.call('/api/auth/register', data, client=client)
        uid = self.call('/api/private', method='GET', client=client)['user_id']
        return client, uid, result

    def exam(self, teacher, uid):
        bank = self.banks.reserve(uid, '物理测试', {})
        self.banks.finish(bank, uid, 'Q1 [fill_blank]\n水的冰点是 ____ 摄氏度。')
        exam = self.call('/api/exams', dict(bank_id=bank), client=teacher)['exam']
        exam = self.call(f"/api/exams/{exam['id']}/prepare", dict(index=0,version=exam['version']), client=teacher)['exam']
        return self.call(f"/api/exams/{exam['id']}/publish", dict(version=exam['version'],reviewed=True), client=teacher)['exam']

    def test_both_roles_register_without_invitation_and_persist(self):
        for role in ('teacher', 'student'):
            client, uid, result = self.register(role, role)
            self.assertEqual(result['role'], role)
            self.assertEqual(AuthStore(self.connector, self.store.secret).role(uid), role)
            self.call('/api/auth/logout', {}, client=client)
            result = self.call('/api/auth/login', dict(account=role+'@qq.com', password='password-123', role=role), client=client)
            self.assertEqual(result['role'], role)
            self.assertEqual(self.call('/api/auth/status', method='GET', client=client)['role'], role)

    def test_wrong_entrance_or_session_role_cannot_promote_account(self):
        client, uid, _ = self.register()
        with client.session_transaction() as cookie:
            cookie['auth_role'] = 'teacher'
        self.assertEqual(self.call('/api/auth/status', method='GET', client=client)['role'], 'student')
        self.call('/api/groups', dict(name='forbidden', role='teacher'), client=client, status=403)
        self.call('/api/auth/logout', {}, client=client)
        result = self.call('/api/auth/login', dict(account='learner', password='password-123',role='teacher'), client=client, status=403)
        self.assertEqual(result['code'], 'role_mismatch')
        self.assertFalse(self.call('/api/auth/status', method='GET', client=client)['authenticated'])
        self.assertEqual(self.store.role(uid), 'student')
        result = self.call('/api/auth/register', dict(username='other', email='other@qq.com',password='password-123',confirm_password='password-123',role='admin'), status=400)
        self.assertEqual(result['code'], 'role_invalid')

    def test_legacy_accounts_keep_existing_teacher_capabilities(self):
        hashed = generate_password_hash('old-password')
        with self.store.db(write=True) as (cur, kind):
            cur.execute('INSERT INTO app_users(username,email,password_hash,public_user_id) VALUES(?,?,?,?)', ('legacy', 'legacy@qq.com', hashed, 'old-stable-id'))
        self.assertEqual(self.store.role('old-stable-id'), 'teacher')
        AuthStore(self.connector, 'isolated-tests-long-secret-only')
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT role FROM account_roles WHERE public_user_id=?', ('old-stable-id',)).fetchone()[0], 'teacher')
            self.assertEqual(db.execute('SELECT password_hash FROM app_users WHERE public_user_id=?', ('old-stable-id',)).fetchone()[0], hashed)
        self.assertEqual(self.call('/api/auth/login', dict(account='legacy',password='old-password',role='teacher'))['role'], 'teacher')

    def test_student_cannot_access_teacher_routes(self):
        teacher, uid, _ = self.register('teacher', 'teacher')
        student, _, _ = self.register()
        exam = self.exam(teacher, uid)
        group = self.call('/api/groups', dict(name='课堂'), client=teacher)['group']
        cases = [('POST','/api/exams'),('GET',f"/api/exams/{exam['id']}"),('PUT',f"/api/exams/{exam['id']}"),
                 *[('POST',f"/api/exams/{exam['id']}/{part}") for part in ('prepare','publish','close')],
                 *[('GET',f"/api/exams/{exam['id']}/{part}") for part in ('analytics','submissions','qr','submissions/unknown')],
                 ('POST','/api/groups'),('PUT',f"/api/groups/{group['id']}"),('POST',f"/api/groups/{group['id']}/invite"),
                 ('PUT',f"/api/groups/{group['id']}/members/{uid}"),('POST',f"/api/groups/{group['id']}/exams"),
                 ('GET',f"/api/groups/{group['id']}/exams/{exam['id']}/results")]
        for method, path in cases:
            with self.subTest(path=path, method=method):
                self.call(path, {}, method=method, client=student, status=403)
        self.assertEqual(self.call('/api/exams', method='GET', client=student)['owned'], [])
        self.assertEqual(self.call('/api/exams', method='GET', client=teacher)['owned'][0]['id'], exam['id'])

    def test_owner_can_review_only_own_exam_students_without_mutating(self):
        teacher, uid, _ = self.register('teacher', 'teacher')
        other, other_uid, _ = self.register('teacher', 'other')
        student, _, _ = self.register()
        exam = self.exam(teacher, uid)
        token = exam['share_url'].rsplit('/',1)[1]
        attempt = self.call(f'/api/exams/shared/{token}/start', {}, client=student)['attempt']
        self.assertNotIn('answer', attempt['questions'][0])
        review_path = f"/api/exams/{exam['id']}/submissions/{attempt['id']}"
        review = self.call(review_path, method='GET', client=teacher)['review']
        self.assertTrue(review['questions'][0]['answer'])
        self.call(review_path, method='GET', client=other, status=404)
        self.call(review_path, method='GET', client=student, status=403)
        other_exam = self.exam(other, other_uid)
        self.call(f"/api/exams/{other_exam['id']}/submissions/{attempt['id']}", method='GET', client=other, status=404)
        result = self.call(f"/api/exam_attempts/{attempt['id']}/answer", dict(index=0,answer='0°C'), client=student)['attempt']
        before = result['questions'][0]['submission']
        review = self.call(review_path, method='GET', client=teacher)['review']
        self.assertEqual(review['questions'][0]['submission'], before)
        self.assertEqual(self.call(f"/api/exam_attempts/{attempt['id']}", method='GET', client=student)['attempt']['questions'][0]['submission'], before)


if __name__ == '__main__':
    unittest.main()
