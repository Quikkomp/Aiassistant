"""Group membership and exam delivery share the exam database for atomic publication."""
import secrets
from exam_store import ExamError, now, text


class GroupStore:
    def __init__(self, exams):
        self.exams = exams
        self.connect = exams.connect

    def access(self, db, group_id, user, owner=False):
        group = db.execute('SELECT * FROM study_groups WHERE id=?', (group_id,)).fetchone()
        member = db.execute("SELECT * FROM group_members WHERE group_id=? AND user_id=? AND status='active'", (group_id, user)).fetchone()
        if not group or not member or (owner and group['owner'] != user):
            raise ExamError('小组不存在或无权访问。', 404)
        return dict(group)

    def create(self, user, username, data):
        name = text(data.get('name'), 100, True)
        description = text(data.get('description', ''), 2000)
        group_id = secrets.token_hex(16)
        with self.connect() as db:
            db.execute('INSERT INTO study_groups VALUES(?,?,?,?,?,?,?)',
                       (group_id, user, username, name, description, secrets.token_hex(24), now()))
            db.execute('INSERT INTO group_members(group_id,user_id,username,joined_at) VALUES(?,?,?,?)',
                       (group_id, user, username, now()))
        return self.detail(group_id, user)

    def catalog(self, user):
        with self.connect() as db:
            rows = db.execute("""SELECT g.id,g.name,g.description,g.owner,g.owner_name,g.created_at,
                (SELECT COUNT(*) FROM group_members m WHERE m.group_id=g.id AND m.status='active' AND m.user_id!=g.owner) AS member_count,
                (SELECT COUNT(*) FROM group_exams e WHERE e.group_id=g.id) AS exam_count
                FROM study_groups g JOIN group_members m ON m.group_id=g.id
                WHERE m.user_id=? AND m.status='active' ORDER BY g.created_at DESC""", (user,)).fetchall()
        return [{**dict(r), 'role': 'owner' if r['owner'] == user else 'member'} for r in rows]

    def preview(self, token, user):
        with self.connect() as db:
            group = db.execute('SELECT * FROM study_groups WHERE token=?', (token,)).fetchone()
            if not group:
                raise ExamError('邀请链接已失效或小组不存在。', 404)
            member = db.execute('SELECT status FROM group_members WHERE group_id=? AND user_id=?', (group['id'], user)).fetchone()
            return {k: group[k] for k in ('id', 'name', 'description', 'owner_name')} | {
                'joined': bool(member and member['status'] == 'active'),
                'blocked': bool(member and member['status'] == 'removed')}

    def join(self, token, user, username):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            group = db.execute('SELECT * FROM study_groups WHERE token=?', (token,)).fetchone()
            if not group:
                raise ExamError('邀请链接已失效或小组不存在。', 404)
            existing = db.execute('SELECT status FROM group_members WHERE group_id=? AND user_id=?', (group['id'], user)).fetchone()
            if existing and existing['status'] == 'removed':
                raise ExamError('你已被移出小组，请联系群主恢复成员资格。', 403)
            db.execute("""INSERT INTO group_members(group_id,user_id,username,joined_at) VALUES(?,?,?,?)
                ON CONFLICT(group_id,user_id) DO UPDATE SET username=excluded.username,status='active'""",
                       (group['id'], user, username, now()))
            if user != group['owner']:
                self.deliver(db, group['id'], user)
        return self.detail(group['id'], user)

    @staticmethod
    def deliver(db, group_id, user):
        db.execute("""INSERT OR IGNORE INTO exam_assignments(group_id,exam_id,user_id,assigned_at)
            SELECT x.group_id,x.exam_id,?,? FROM group_exams x JOIN exams e ON e.id=x.exam_id
            WHERE x.group_id=? AND e.status='published'""", (user, now(), group_id))

    def detail(self, group_id, user):
        with self.connect() as db:
            group = self.access(db, group_id, user)
            owner = group['owner'] == user
            rows = db.execute("""SELECT e.id,e.title,e.status,e.token,x.published_at,
                (SELECT COUNT(*) FROM exam_assignments a WHERE a.group_id=x.group_id AND a.exam_id=e.id) AS assigned_count,
                a.id AS attempt_id,a.status AS attempt_status,e.questions
                FROM group_exams x JOIN exams e ON e.id=x.exam_id
                LEFT JOIN exam_attempts a ON a.exam_id=e.id AND a.user_id=?
                WHERE x.group_id=? AND (? OR EXISTS (
                    SELECT 1 FROM exam_assignments z WHERE z.group_id=x.group_id AND z.exam_id=e.id AND z.user_id=?
                )) ORDER BY x.published_at DESC""", (user, group_id, owner, user)).fetchall()
            members = db.execute('SELECT user_id,username,status,joined_at FROM group_members WHERE group_id=? ORDER BY joined_at', (group_id,)).fetchall()
        import json
        result = {k: group[k] for k in ('id', 'name', 'description', 'owner_name', 'created_at')}
        result.update(role='owner' if owner else 'member', member_count=sum(m['status'] == 'active' and m['user_id'] != group['owner'] for m in members))
        result['members'] = [{**dict(m), 'role': 'owner' if m['user_id'] == group['owner'] else 'member'} for m in members if owner or m['user_id'] == user]
        result['exams'] = [{k: r[k] for k in ('id', 'title', 'status', 'token', 'published_at', 'assigned_count', 'attempt_id', 'attempt_status')} | {'question_count': len(json.loads(r['questions']))} for r in rows]
        if owner:
            result['token'] = group['token']
        return result

    def update(self, group_id, user, data):
        name = text(data.get('name'), 100, True)
        description = text(data.get('description', ''), 2000)
        with self.connect() as db:
            self.access(db, group_id, user, True)
            db.execute('UPDATE study_groups SET name=?,description=? WHERE id=?', (name, description, group_id))
        return self.detail(group_id, user)

    def rotate(self, group_id, user):
        with self.connect() as db:
            self.access(db, group_id, user, True)
            db.execute('UPDATE study_groups SET token=? WHERE id=?', (secrets.token_hex(24), group_id))
        return self.detail(group_id, user)

    def member(self, group_id, user, target, status):
        if status not in {'active', 'removed'}:
            raise ExamError('成员状态无效。')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            group = self.access(db, group_id, user, True)
            if target == group['owner']:
                raise ExamError('不能移除群主。')
            changed = db.execute('UPDATE group_members SET status=? WHERE group_id=? AND user_id=?', (status, group_id, target)).rowcount
            if not changed:
                raise ExamError('组员不存在。', 404)
            if status == 'active':
                self.deliver(db, group_id, target)
        return self.detail(group_id, user)

    def publish(self, group_id, user, exam_id, version, reviewed):
        if reviewed is not True:
            raise ExamError('请确认已审核所有题目的答案与解析。')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.access(db, group_id, user, True)
            exam = self.exams.decode(db.execute('SELECT * FROM exams WHERE id=? AND owner=?', (exam_id, user)).fetchone())
            if exam['status'] == 'closed':
                raise ExamError('考试已关闭，不能再发布给小组。', 409)
            if exam['status'] == 'draft':
                if version != exam['version']:
                    raise ExamError('草稿已更新，请重新审核。', 409)
                if any(not q['answer'] or not q['explanation'] or not q['rubric'] for q in exam['questions']):
                    raise ExamError('请审核并填写每题参考答案、解析和评分要点。')
                db.execute("UPDATE exams SET status='published',token=?,version=version+1 WHERE id=?", (secrets.token_hex(24), exam_id))
            db.execute('INSERT OR IGNORE INTO group_exams VALUES(?,?,?)', (group_id, exam_id, now()))
            members = db.execute("SELECT user_id FROM group_members WHERE group_id=? AND status='active' AND user_id!=?", (group_id, user)).fetchall()
            for member in members:
                self.deliver(db, group_id, member['user_id'])
        return {'exam_id': exam_id, 'delivered_count': len(members), 'group': self.detail(group_id, user)}

    def results(self, group_id, user, exam_id):
        with self.connect() as db:
            self.access(db, group_id, user, True)
            if not db.execute('SELECT 1 FROM group_exams WHERE group_id=? AND exam_id=?', (group_id, exam_id)).fetchone():
                raise ExamError('本小组未发布这场考试。', 404)
            recipients = [dict(r) for r in db.execute("""SELECT m.user_id,m.username,m.status AS member_status
                FROM exam_assignments a JOIN group_members m ON m.group_id=a.group_id AND m.user_id=a.user_id
                WHERE a.group_id=? AND a.exam_id=? ORDER BY m.joined_at""", (group_id, exam_id))]
        stats = self.exams.analytics(exam_id, user, [r['user_id'] for r in recipients])
        # Include not-started students and do not silently truncate a group roster.
        points = [q['points'] for q in self.exams.owned(exam_id, user)['questions']]
        with self.connect() as db:
            attempts = {r['user_id']: dict(r) for r in db.execute('SELECT id,user_id,status,completed_at FROM exam_attempts WHERE exam_id=?', (exam_id,))}
            graded = {}
            for row in db.execute("""SELECT s.attempt_id,s.idx,s.ratio FROM exam_answers s
                    JOIN exam_attempts a ON a.id=s.attempt_id WHERE a.exam_id=? AND s.status='graded'""", (exam_id,)):
                graded.setdefault(row['attempt_id'], []).append((row['idx'], row['ratio']))
            for recipient in recipients:
                attempt = attempts.get(recipient['user_id'])
                recipient.update(status=attempt['status'] if attempt else 'assigned', done=0, score=None, completed_at=None)
                if attempt:
                    answers = graded.get(attempt['id'], [])
                    score = round(sum(points[idx]*ratio for idx, ratio in answers), 2) if attempt['status'] == 'completed' else None
                    recipient.update(done=len(answers), score=score, completed_at=attempt['completed_at'], attempt_id=attempt['id'])
        stats.update(assigned=len(recipients), not_started=len(recipients)-stats['started'], students=recipients,
                     completion_rate=round(stats['completed']/len(recipients)*100, 1) if recipients else None)
        return stats

    def member_info(self, group_id, user, target):
        detail = self.detail(group_id, user)
        if detail['role'] != 'owner' and target != user:
            raise ExamError('无权查看其他组员的信息。', 404)
        with self.connect() as db:
            member = db.execute('SELECT user_id,username,status,joined_at FROM group_members WHERE group_id=? AND user_id=?', (group_id, target)).fetchone()
            if not member:
                raise ExamError('组员不存在。', 404)
            exams = db.execute("""SELECT e.id,e.title,a.id AS attempt_id,a.status,a.completed_at
                FROM exam_assignments x JOIN exams e ON e.id=x.exam_id
                LEFT JOIN exam_attempts a ON a.exam_id=e.id AND a.user_id=x.user_id
                WHERE x.group_id=? AND x.user_id=? ORDER BY x.assigned_at DESC""", (group_id, target)).fetchall()
        records = []
        for row in exams:
            packet = self.exams.packet(row['attempt_id'], target) if row['attempt_id'] else None
            records.append({'title': row['title'], 'status': row['status'] or 'assigned', 'completed_at': row['completed_at'],
                            'score': round(packet['score']/packet['total']*100, 1) if packet and packet['score'] is not None else None})
        return {**dict(member), 'exams': records}
