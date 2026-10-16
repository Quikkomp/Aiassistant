"""Isolated groups + actual examination routes; no production accounts or live AI."""
import sys
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tmp/exam-test-deps'))
sys.path.insert(0, str(ROOT / 'local_chat_site'))
from flask import Flask
from question_bank import BankStore
from exam_store import ExamStore, ExamError
from exam_routes import make_exam_blueprint
from group_store import GroupStore
from group_routes import make_group_blueprint
from test_exams import FakeAI


class GroupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bank = BankStore(str(Path(self.temp.name) / 'banks.sqlite3'))
        self.exams = ExamStore(str(Path(self.temp.name) / 'exams.sqlite3'))
        self.groups = GroupStore(self.exams)
        self.app = Flask(__name__, template_folder=str(ROOT / 'local_chat_site/templates'))
        self.app.secret_key = 'isolated-groups-tests'
        self.app.testing = True
        self.app.register_blueprint(make_exam_blueprint(self.exams, self.bank, lambda: None, FakeAI()))
        self.app.register_blueprint(make_group_blueprint(self.groups))
        self.teacher = self.client('teacher')
        self.student = self.client('student')
        self.other = self.client('other')
        self.guest = self.app.test_client()
        ident = self.bank.reserve('teacher', '冰点训练', {})
        self.bank.finish(ident, 'teacher', 'Q1 [fill_blank]\n冰点是 ____。\n\nQ2 [short_answer]\n请解释冰点。')
        self.bank_id = ident

    def tearDown(self):
        self.temp.cleanup()

    def client(self, user):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session.update(auth_user_id=user, username=user.title(), auth_role='student' if user=='student' else 'teacher')
        return client

    def call(self, client, method, path, data=None, status=200, headers=None):
        response = client.open(path, method=method, json=data, headers=headers)
        self.assertEqual(response.status_code, status, response.get_data(as_text=True))
        return response.get_json()

    def group(self, name='物理学习小组'):
        return self.call(self.teacher, 'POST', '/api/groups', {'name': name, 'description': '一起学习'})['group']

    def join(self, group, client=None, status=200):
        token = group['invite_url'].rsplit('/', 1)[1]
        return self.call(client or self.student, 'POST', f'/api/groups/shared/{token}/join', {}, status=status)

    def draft(self, ready=True):
        exam = self.call(self.teacher, 'POST', '/api/exams', {'bank_id': self.bank_id})['exam']
        if ready:
            for idx in range(len(exam['questions'])):
                exam = self.call(self.teacher, 'POST', f"/api/exams/{exam['id']}/prepare", {'index': idx, 'version': exam['version']})['exam']
        return exam

    def deliver(self, group, exam, status=200, **extra):
        return self.call(self.teacher, 'POST', f"/api/groups/{group['id']}/exams",
                         {'exam_id': exam['id'], 'version': exam['version'], 'reviewed': True, **extra}, status=status)

    def complete(self, exam, user='student', ratios=(1, 0)):
        token = self.exams.owned(exam['id'], 'teacher')['token']
        packet = self.exams.start(token, user, user.title())
        for idx, ratio in enumerate(ratios):
            claim, _ = self.exams.claim_answer(packet['id'], user, idx, 'answer')
            self.exams.finish_grade(packet['id'], idx, claim, ratio, 'Feedback')
        self.exams.complete(packet['id'], user)
        return packet

    def test_create_invite_privacy_and_idempotent_join(self):
        group = self.group()
        self.assertEqual(group['role'], 'owner')
        self.assertEqual(group['member_count'], 0)
        self.assertRegex(group['invite_url'], r'/group/[a-f0-9]{48}$')
        token = group['invite_url'].rsplit('/', 1)[1]
        preview = self.call(self.student, 'GET', '/api/groups/shared/'+token)['group']
        self.assertNotIn('members', preview)
        self.assertNotIn('invite_url', preview)
        for _ in range(2):
            joined = self.join(group)['group']
            self.assertEqual(joined['role'], 'member')
            self.assertNotIn('invite_url', joined)
            self.assertEqual([m['user_id'] for m in joined['members']], ['student'])
        detail = self.call(self.teacher, 'GET', '/api/groups/'+group['id'])['group']
        self.assertEqual(detail['member_count'], 1)

    def test_auth_ownership_and_origin_checks(self):
        group = self.group()
        self.call(self.guest, 'GET', '/api/groups', status=401)
        self.call(self.other, 'GET', '/api/groups/'+group['id'], status=404)
        self.join(group)
        for method, suffix, data in [('PUT', '', {'name': 'stolen'}), ('POST', '/invite', {}), ('PUT', '/members/teacher', {'status': 'removed'}), ('POST', '/exams', {})]:
            self.call(self.student, method, '/api/groups/'+group['id']+suffix, data, status=403)
        self.call(self.teacher, 'POST', '/api/groups', {'name': 'bad origin'}, status=403, headers={'Origin': 'https://evil.example'})

    def test_invitation_rotation_and_removed_member_restore(self):
        group = self.group()
        self.join(group)
        rotated = self.call(self.teacher, 'POST', f"/api/groups/{group['id']}/invite", {})['group']
        self.join(group, self.other, status=404)
        self.call(self.teacher, 'PUT', f"/api/groups/{group['id']}/members/student", {'status': 'removed'})
        self.join(rotated, status=403)
        self.assertEqual(self.call(self.student, 'GET', '/api/groups')['groups'], [])
        self.call(self.teacher, 'PUT', f"/api/groups/{group['id']}/members/student", {'status': 'active'})
        self.join(rotated)
        self.call(self.teacher, 'PUT', f"/api/groups/{group['id']}/members/teacher", {'status': 'removed'}, status=400)

    def test_delivery_does_not_start_attempt_or_expose_answers(self):
        group = self.group()
        self.join(group)
        exam = self.draft()
        result = self.deliver(group, exam)
        self.assertEqual(result['delivered_count'], 1)
        self.deliver(group, exam)
        joined = self.call(self.student, 'GET', '/api/exams')['joined']
        self.assertEqual(len(joined), 1)
        self.assertEqual(joined[0]['status'], 'assigned')
        self.assertNotIn('questions', joined[0])
        with self.exams.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM exam_attempts').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM exam_assignments').fetchone()[0], 1)
        packet = self.complete(exam)
        token = self.exams.owned(exam['id'], 'teacher')['token']
        self.assertEqual(self.exams.start(token, 'student', 'Student')['id'], packet['id'])
        self.assertEqual(len(self.call(self.student, 'GET', '/api/exams')['joined']), 1)

    def test_atomic_publication_requires_review_and_current_version(self):
        group = self.group()
        self.join(group)
        exam = self.draft(False)
        self.deliver(group, exam, status=400)
        self.assertEqual(self.exams.owned(exam['id'], 'teacher')['status'], 'draft')
        exam = self.draft()
        self.deliver(group, exam, status=400, reviewed=False)
        self.deliver(group, exam, status=409, version=exam['version']-1)
        with self.exams.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM group_exams').fetchone()[0], 0)
        other_group = self.call(self.other, 'POST', '/api/groups', {'name': '另一个小组'})['group']
        self.deliver(other_group, exam, status=404)
        self.deliver(group, exam)
        self.call(self.teacher, 'POST', f"/api/exams/{exam['id']}/close", {})
        self.deliver(group, exam, status=409)

    def test_late_join_gets_open_exams_only_and_removal_stops_delivery(self):
        group = self.group()
        old = self.draft()
        self.deliver(group, old)
        self.call(self.teacher, 'POST', f"/api/exams/{old['id']}/close", {})
        current = self.draft()
        self.deliver(group, current)
        self.join(group)
        self.assertEqual([e['id'] for e in self.call(self.student, 'GET', '/api/exams')['joined']], [current['id']])
        self.call(self.teacher, 'PUT', f"/api/groups/{group['id']}/members/student", {'status': 'removed'})
        self.assertEqual(self.call(self.student, 'GET', '/api/exams')['joined'], [])
        self.call(self.teacher, 'PUT', f"/api/groups/{group['id']}/members/student", {'status': 'active'})
        self.assertEqual(len(self.call(self.student, 'GET', '/api/exams')['joined']), 1)

    def test_results_only_include_group_recipients_and_pending_students(self):
        group = self.group()
        self.join(group)
        self.join(group, self.other)
        exam = self.draft()
        self.deliver(group, exam)
        self.complete(exam)
        self.complete(exam, 'outsider', (1, 1))
        path = f"/api/groups/{group['id']}/exams/{exam['id']}/results"
        self.call(self.student, 'GET', path, status=403)
        stats = self.call(self.teacher, 'GET', path)['analytics']
        self.assertEqual((stats['assigned'], stats['started'], stats['completed'], stats['not_started']), (2, 1, 1, 1))
        self.assertEqual(stats['average'], 50)
        self.assertEqual(stats['completion_rate'], 50)
        self.assertEqual({s['user_id'] for s in stats['students']}, {'student', 'other'})
        info = self.call(self.teacher, 'GET', f"/api/groups/{group['id']}/members/student")['member']
        self.assertEqual(info['exams'][0]['score'], 50)
        self.assertNotIn('email', info)
        self.call(self.student, 'GET', f"/api/groups/{group['id']}/members/other", status=404)

    def test_same_exam_in_multiple_groups_has_one_assignment_tile_and_attempt(self):
        first, second = self.group('A'), self.group('B')
        self.join(first)
        self.join(second)
        exam = self.draft()
        self.deliver(first, exam)
        self.deliver(second, exam)
        rows = self.call(self.student, 'GET', '/api/exams')['joined']
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]['group_names']), {'A', 'B'})
        self.complete(exam)
        for group in (first, second):
            self.assertEqual(self.groups.results(group['id'], 'teacher', exam['id'])['completed'], 1)

    def test_concurrent_join_and_publication_do_not_miss_delivery(self):
        group = self.group()
        exam = self.draft()
        token = group['invite_url'].rsplit('/', 1)[1]
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(self.groups.publish, group['id'], 'teacher', exam['id'], exam['version'], True)]
            futures += [pool.submit(self.groups.join, token, f'member{i}', f'Member {i}') for i in range(8)]
            for future in futures:
                future.result()
        with self.exams.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM exam_assignments').fetchone()[0], 8)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM exam_attempts').fetchone()[0], 0)

    def test_group_scores_normalize_custom_marks_and_keep_removed_history(self):
        group = self.group()
        self.join(group)
        exam = self.draft()
        exam['questions'][0]['points'], exam['questions'][1]['points'] = 5, 15
        exam = self.call(self.teacher, 'PUT', f"/api/exams/{exam['id']}", exam)['exam']
        self.deliver(group, exam)
        self.complete(exam)
        self.call(self.teacher, 'PUT', f"/api/groups/{group['id']}/members/student", {'status': 'removed'})
        stats = self.groups.results(group['id'], 'teacher', exam['id'])
        self.assertEqual((stats['total'], stats['average'], stats['students'][0]['score']), (20, 25, 5))
        self.assertEqual(stats['students'][0]['member_status'], 'removed')
        self.assertEqual(self.groups.member_info(group['id'], 'teacher', 'student')['exams'][0]['score'], 25)
        self.assertEqual(self.call(self.student, 'GET', '/api/exams')['joined'][0]['status'], 'completed')

    def test_reinitialization_preserves_data_and_sensitive_responses_are_uncached(self):
        group = self.group()
        self.join(group)
        exam = self.draft()
        self.deliver(group, exam)
        restarted = GroupStore(ExamStore(self.exams.path))
        self.assertEqual(restarted.detail(group['id'], 'teacher')['member_count'], 1)
        self.assertEqual(len(restarted.detail(group['id'], 'student')['exams']), 1)
        response = self.teacher.get('/api/groups/'+group['id'])
        self.assertEqual(response.headers['Cache-Control'], 'private, no-store')


if __name__ == '__main__':
    unittest.main()
