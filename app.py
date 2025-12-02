import sqlite3
from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

def get_db_connection():
    conn = sqlite3.connect('data/questions.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/questions')
def get_questions():
    conn = get_db_connection()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get search parameter
    search = request.args.get('search', '', type=str)
    
    # Get sort parameters
    sort_by = request.args.get('sort_by', 'game_date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Validate sort parameters
    allowed_sort_columns = ['game_date', 'id', 'round_title']
    if sort_by not in allowed_sort_columns:
        return jsonify({'error': 'Invalid sort column'}), 400
        
    allowed_sort_orders = ['asc', 'desc']
    if sort_order not in allowed_sort_orders:
        return jsonify({'error': 'Invalid sort order'}), 400
    
    # Build query
    if search:
        query = f'''
            SELECT * FROM questions 
            WHERE question_text LIKE ? OR answer_text LIKE ? OR round_title LIKE ?
            ORDER BY {sort_by} {sort_order}, id ASC
            LIMIT ? OFFSET ?
        '''
        search_term = f'%{search}%'
        questions = conn.execute(query, (search_term, search_term, search_term, per_page, (page-1)*per_page)).fetchall()
        
        # Get total count for pagination
        count_query = '''
            SELECT COUNT(*) as count FROM questions 
            WHERE question_text LIKE ? OR answer_text LIKE ? OR round_title LIKE ?
        '''
        total = conn.execute(count_query, (search_term, search_term, search_term)).fetchone()['count']
    else:
        query = f'''
            SELECT * FROM questions 
            ORDER BY {sort_by} {sort_order}, id ASC
            LIMIT ? OFFSET ?
        '''
        questions = conn.execute(query, (per_page, (page-1)*per_page)).fetchall()
        
        # Get total count for pagination
        count_query = 'SELECT COUNT(*) as count FROM questions'
        total = conn.execute(count_query).fetchone()['count']
    
    conn.close()
    
    # Convert rows to dictionaries and process images
    questions_list = []
    for question in questions:
        q_dict = dict(question)
        # Convert images string to list
        if q_dict['images']:
            q_dict['images'] = q_dict['images'].split(',')
        else:
            q_dict['images'] = []
        questions_list.append(q_dict)
    
    return jsonify({
        'questions': questions_list,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/question/<int:id>')
def get_question(id):
    conn = get_db_connection()
    question = conn.execute('SELECT * FROM questions WHERE id = ?', (id,)).fetchone()
    conn.close()
    
    if question is None:
        return jsonify({'error': 'Question not found'}), 404
    
    # Convert to dictionary and process images
    q_dict = dict(question)
    if q_dict['images']:
        q_dict['images'] = q_dict['images'].split(',')
    else:
        q_dict['images'] = []
    
    return jsonify(q_dict)

if __name__ == '__main__':
    app.run(debug=True, port=5001)