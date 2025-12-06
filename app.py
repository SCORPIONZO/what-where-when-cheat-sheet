import sqlite3
from flask import Flask, render_template, request, jsonify
import os
from fuzzywuzzy import fuzz

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
    allowed_sort_columns = ['game_date', 'id', 'round_title', 'year']
    if sort_by not in allowed_sort_columns:
        return jsonify({'error': 'Invalid sort column'}), 400
        
    allowed_sort_orders = ['asc', 'desc']
    if sort_order not in allowed_sort_orders:
        return jsonify({'error': 'Invalid sort order'}), 400
    
    # Build base query for filtering out questions without answers
    base_conditions = '''answer_text IS NOT NULL 
                         AND trim(answer_text) != '' 
                         AND answer_text NOT LIKE '%не найден%' '''
    
    if search:
        # First, get all questions that meet our criteria for fuzzy search
        base_query = f'''SELECT * FROM questions 
                         WHERE {base_conditions}'''
        all_questions = conn.execute(base_query).fetchall()
        
        # Apply fuzzy search
        search_results = []
        search_lower = search.lower()
        
        for question in all_questions:
            # Check for fuzzy matches in question_text, answer_text, and round_title
            question_text_ratio = fuzz.partial_ratio(search_lower, question['question_text'].lower())
            answer_text_ratio = fuzz.partial_ratio(search_lower, question['answer_text'].lower())
            round_title_ratio = fuzz.partial_ratio(search_lower, question['round_title'].lower())
            
            # Use highest ratio among the three fields
            max_ratio = max(question_text_ratio, answer_text_ratio, round_title_ratio)
            
            # Only include results with a similarity score above threshold
            if max_ratio >= 60:  # Threshold for fuzzy matching
                search_results.append((dict(question), max_ratio))
        
        # Sort results by similarity score (descending)
        search_results.sort(key=lambda x: x[1], reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = search_results[start_idx:end_idx]
        
        # Extract just the question data (without similarity scores)
        questions_list = []
        for question_tuple, _ in paginated_results:
            # Process images
            if question_tuple['images']:
                question_tuple['images'] = question_tuple['images'].split(',')
            else:
                question_tuple['images'] = []
            questions_list.append(question_tuple)
        
        total = len(search_results)
    else:
        # Regular query without search
        # Handle year sorting specially
        if sort_by == 'year':
            order_clause = f"substr(game_date, 1, 4) {sort_order.upper()}, game_date DESC, id ASC"
        else:
            order_clause = f"{sort_by} {sort_order.upper()}, id ASC"
            
        query = f'''
            SELECT * FROM questions 
            WHERE {base_conditions}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        '''
        questions = conn.execute(query, (per_page, (page-1)*per_page)).fetchall()
        
        # Get total count for pagination
        count_query = f'''SELECT COUNT(*) as count FROM questions 
                          WHERE {base_conditions}'''
        total = conn.execute(count_query).fetchone()['count']
        
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
    
    conn.close()
    
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
    question = conn.execute('''SELECT * FROM questions 
                               WHERE id = ? 
                               AND answer_text IS NOT NULL 
                               AND trim(answer_text) != '' 
                               AND answer_text NOT LIKE '%не найден%' ''', (id,)).fetchone()
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