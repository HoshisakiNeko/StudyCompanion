"""
研途搭子 - AI 考研复习智能体
Team AAA
"""
import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yantu-dazi-aaa-2026'

DB_PATH = os.path.join(os.path.dirname(__file__), 'study.db')

# ---------- 数据库初始化 ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS materials
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS questions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, material_id INTEGER,
                  question TEXT, answer TEXT, analysis TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS answers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, question_id INTEGER,
                  user_answer TEXT, score REAL, feedback TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

# ---------- 模拟题库（无 API Key 时兜底）----------
MOCK_QUESTIONS = [
    {
        "question": "考研政治中，\"物质\"的唯一特性是什么？",
        "answer": "客观实在性。物质是标志客观实在的哲学范畴，这种客观实在是人通过感觉感知的，它不依赖于我们的感觉而存在。",
        "analysis": "考察马哲唯物论核心概念。物质的唯一特性是客观实在性，不是运动、不是可知性。"
    },
    {
        "question": "英语长难句分析：指出以下句子的主干结构\n'The researchers, who had spent three years collecting data from over 200 universities, finally published their findings in a leading journal.'",
        "answer": "主干：The researchers published their findings. 其中who引导的定语从句修饰researchers，from over 200 universities是地点状语，in a leading journal是方式/地点状语。",
        "analysis": "长难句核心是找主干（主谓宾），把定语从句、插入语、状语先剥离。"
    },
    {
        "question": "数学：求函数 f(x) = x³ - 3x 的极值。",
        "answer": "f'(x) = 3x² - 3 = 0，得 x = ±1。f''(x) = 6x。x=1时f''=6>0为极小值f(1)=-2；x=-1时f''=-6<0为极大值f(-1)=2。",
        "analysis": "三步：求导找驻点→二阶导判断凹凸→代回求极值。注意区分极大/极小。"
    },
    {
        "question": "操作系统：什么是死锁？产生死锁的四个必要条件是什么？",
        "answer": "死锁是多个进程因竞争资源而造成的僵局。四个必要条件：互斥、占有且等待、不可剥夺、循环等待。",
        "analysis": "死锁四条件是高频考点，必须全部答出，且要理解每个条件的含义。"
    },
    {
        "question": "计算机网络：TCP 三次握手的过程是什么？为什么需要三次而不是两次？",
        "answer": "第一次：客户端发SYN；第二次：服务端回SYN+ACK；第三次：客户端发ACK。三次是为了确认双方的收发能力都正常，防止已失效的连接请求突然传到服务端造成错误。",
        "analysis": "三次握手是考研408必考点，要能画时序图并解释为什么不是两次。"
    }
]

# ---------- 路由 ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/material', methods=['POST'])
def save_material():
    data = request.json
    title = data.get('title', '未命名资料')
    content = data.get('content', '')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO materials (title, content, created_at) VALUES (?,?,?)',
              (title, content, datetime.now().isoformat()))
    material_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'material_id': material_id})

@app.route('/api/generate_questions', methods=['POST'])
def generate_questions():
    """生成题目：有 API Key 调大模型，没有则用模拟题库"""
    data = request.json
    material_id = data.get('material_id')
    use_mock = data.get('use_mock', True)

    questions_to_save = MOCK_QUESTIONS if use_mock else MOCK_QUESTIONS  # 暂时都用mock

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    q_ids = []
    for q in questions_to_save:
        c.execute('INSERT INTO questions (material_id, question, answer, analysis, created_at) VALUES (?,?,?,?,?)',
                  (material_id, q['question'], q['answer'], q['analysis'], datetime.now().isoformat()))
        q_ids.append(c.lastrowid)
    conn.commit()
    conn.close()

    return jsonify({'ok': True, 'questions': questions_to_save, 'count': len(questions_to_save)})

@app.route('/api/answer', methods=['POST'])
def submit_answer():
    data = request.json
    question_id = data.get('question_id')
    user_answer = data.get('user_answer', '')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT answer, analysis FROM questions WHERE id=?', (question_id,))
    row = c.fetchone()
    if not row:
        return jsonify({'ok': False, 'msg': '题目不存在'})

    ref_answer, analysis = row

    # 简易评分：根据回答长度和关键词匹配（演示用）
    score = 0
    feedback_parts = []
    if len(user_answer.strip()) >= 10:
        score += 30
        feedback_parts.append('回答有一定内容')
    else:
        feedback_parts.append('回答过短，建议展开论述')

    # 简单关键词匹配
    key_terms = [w for w in ref_answer.split('。')[0].split() if len(w) >= 2]
    matched = sum(1 for t in key_terms if t in user_answer)
    score += min(50, matched * 15)

    if score >= 60:
        score += 20
        feedback_parts.append('核心知识点覆盖较好')
    else:
        feedback_parts.append('建议对照参考答案补充关键点')

    c.execute('INSERT INTO answers (question_id, user_answer, score, feedback, created_at) VALUES (?,?,?,?,?)',
              (question_id, user_answer, score, '；'.join(feedback_parts), datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return jsonify({
        'ok': True,
        'score': score,
        'reference': ref_answer,
        'analysis': analysis,
        'feedback': '；'.join(feedback_parts)
    })

@app.route('/api/stats')
def stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM questions')
    total_q = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM answers')
    total_a = c.fetchone()[0]
    c.execute('SELECT AVG(score) FROM answers')
    avg = c.fetchone()[0] or 0
    conn.close()
    return jsonify({'total_questions': total_q, 'total_answers': total_a, 'avg_score': round(avg, 1)})

if __name__ == '__main__':
    init_db()
    print('='*50)
    print('  研途搭子 - AI 考研复习智能体')
    print('  Team AAA')
    print('  访问 http://127.0.0.1:5000')
    print('='*50)
    app.run(debug=True, host='127.0.0.1', port=5000)
