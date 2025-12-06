import sqlite3
from flask import Flask, render_template, request, jsonify
import os
import json
from fuzzywuzzy import fuzz

app = Flask(__name__, template_folder='templates', static_folder='static')

# Файл для хранения настроек видимости лет
VISIBLE_YEARS_FILE = 'data/visible_years.json'

def get_db_connection():
    conn = sqlite3.connect('data/questions.db')
    conn.row_factory = sqlite3.Row
    return conn

def load_visible_years():
    """Загрузка настроек видимости лет из файла"""
    if os.path.exists(VISIBLE_YEARS_FILE):
        with open(VISIBLE_YEARS_FILE, 'r') as f:
            return json.load(f)
    else:
        # Если файл не существует, возвращаем все года как видимые
        conn = get_db_connection()
        query = '''
            SELECT DISTINCT substr(game_date, 7, 4) as year 
            FROM questions 
            WHERE game_date IS NOT NULL 
            AND game_date != '' 
            ORDER BY year DESC
        '''
        results = conn.execute(query).fetchall()
        conn.close()
        return [row['year'] for row in results]

def save_visible_years(visible_years):
    """Сохранение настроек видимости лет в файл"""
    # Убедимся, что директория существует
    os.makedirs(os.path.dirname(VISIBLE_YEARS_FILE), exist_ok=True)
    
    with open(VISIBLE_YEARS_FILE, 'w') as f:
        json.dump(visible_years, f)

def extract_correct_answer(answer_text):
    """Extract only the correct answer part from the answer text"""
    if not answer_text:
        return 'Ответ недоступен'
    
    # Convert to lowercase for case-insensitive matching
    lower_text = answer_text.lower()
    
    # Possible variations of "correct answer" phrases
    answer_patterns = [
        'дан правильный ответ',
        'дал правильный ответ',
        'дан правельный ответ',
        'дал правельный ответ',
        'правильный ответ',
        'правельный ответ'
    ]
    
    # Find the first occurrence of any correct answer phrase
    earliest_index = -1
    matched_phrase = ''
    
    for pattern in answer_patterns:
        index = lower_text.find(pattern)
        if index != -1 and (earliest_index == -1 or index < earliest_index):
            earliest_index = index
            matched_phrase = pattern
    
    # If we found a correct answer phrase, extract everything from that point
    if earliest_index != -1:
        # Get the original case version of the phrase
        original_case_phrase = answer_text[earliest_index:earliest_index + len(matched_phrase)]
        rest_of_text = answer_text[earliest_index + len(matched_phrase):]
        return original_case_phrase + rest_of_text
    
    # If no pattern found, return the original text
    return answer_text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/years')
def get_years():
    conn = get_db_connection()
    
    # Load visible years
    visible_years = load_visible_years()
    
    # Get distinct years from game_date column (format DD.MM.YYYY)
    if visible_years:
        # If we have visible years configured, only return those
        placeholders = ','.join(['?' for _ in visible_years])
        query = f'''
            SELECT DISTINCT substr(game_date, 7, 4) as year 
            FROM questions 
            WHERE game_date IS NOT NULL 
            AND game_date != '' 
            AND substr(game_date, 7, 4) IN ({placeholders})
            ORDER BY year DESC
        '''
        years_result = conn.execute(query, visible_years).fetchall()
    else:
        # If no visible years configured, return all years
        query = '''
            SELECT DISTINCT substr(game_date, 7, 4) as year 
            FROM questions 
            WHERE game_date IS NOT NULL 
            AND game_date != '' 
            ORDER BY year DESC
        '''
        years_result = conn.execute(query).fetchall()
    
    conn.close()
    
    # Extract years from result
    years = [str(year['year']) for year in years_result]
    
    return jsonify({
        'years': years
    })

@app.route('/api/questions')
def get_questions():
    conn = get_db_connection()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get search parameter
    search = request.args.get('search', '', type=str)
    
    # Get year filter
    year_filter = request.args.get('year', 'all', type=str)
    
    # Load visible years from file
    visible_years = load_visible_years()
    
    # Get sort parameters (default to year desc)
    sort_by = request.args.get('sort_by', 'year')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Validate sort parameters
    allowed_sort_columns = ['game_date', 'id', 'round_title', 'year']
    if sort_by not in allowed_sort_columns:
        sort_by = 'year'
        
    allowed_sort_orders = ['asc', 'desc']
    if sort_order not in allowed_sort_orders:
        sort_order = 'desc'
    
    # Build base query for filtering out questions without answers
    base_conditions = '''answer_text IS NOT NULL 
                         AND trim(answer_text) != '' 
                         AND answer_text NOT LIKE '%не найден%' 
                         AND (LOWER(answer_text) LIKE '%дан правильный ответ%' 
                              OR LOWER(answer_text) LIKE '%дал правильный ответ%'
                              OR LOWER(answer_text) LIKE '%дан правельный ответ%'
                              OR LOWER(answer_text) LIKE '%дал правельный ответ%'
                              OR LOWER(answer_text) LIKE '%правильный ответ%'
                              OR LOWER(answer_text) LIKE '%правельный ответ%')'''
    
    # Add year condition if specified (year extracted from DD.MM.YYYY format)
    if year_filter != 'all':
        base_conditions += f" AND substr(game_date, 7, 4) = '{year_filter}'"
    elif visible_years:
        # Apply visible years filter
        years_placeholder = ','.join(['?' for _ in visible_years])
        base_conditions += f" AND substr(game_date, 7, 4) IN ({years_placeholder})"
    
    if search:
        # First, get all questions that meet our criteria for fuzzy search
        base_query = f'''SELECT * FROM questions 
                         WHERE {base_conditions}'''
        
        # Prepare parameters for query
        query_params = visible_years if year_filter == 'all' and visible_years else []
        
        all_questions = conn.execute(base_query, query_params).fetchall()
        
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
                
            # Extract only the correct answer part
            question_tuple['answer_text'] = extract_correct_answer(question_tuple['answer_text'])
            questions_list.append(question_tuple)
        
        total = len(search_results)
    else:
        # Regular query without search
        # Handle year sorting specially (year extracted from DD.MM.YYYY format)
        if sort_by == 'year':
            order_clause = f"substr(game_date, 7, 4) {sort_order.upper()}, game_date DESC, id ASC"
        else:
            order_clause = f"{sort_by} {sort_order.upper()}, id ASC"
            
        query = f'''
            SELECT * FROM questions 
            WHERE {base_conditions}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        '''
        
        # Prepare parameters for query
        query_params = []
        if year_filter == 'all' and visible_years:
            query_params.extend(visible_years)
        query_params.extend([per_page, (page-1)*per_page])
            
        questions = conn.execute(query, query_params).fetchall()
        
        # Get total count for pagination (with visible years filter)
        count_query = f'''SELECT COUNT(*) as count FROM questions 
                          WHERE {base_conditions}'''
        
        # Prepare parameters for count query
        count_params = []
        if year_filter == 'all' and visible_years:
            count_params.extend(visible_years)
            
        total = conn.execute(count_query, count_params).fetchone()['count']
        
        # Convert rows to dictionaries and process images
        questions_list = []
        for question in questions:
            q_dict = dict(question)
            # Convert images string to list
            if q_dict['images']:
                q_dict['images'] = q_dict['images'].split(',')
            else:
                q_dict['images'] = []
                
            # Extract only the correct answer part
            q_dict['answer_text'] = extract_correct_answer(q_dict['answer_text'])
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

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')

@app.route('/api/admin/questions-by-year')
def get_questions_by_year():
    conn = get_db_connection()
    
    # Получаем количество вопросов по годам
    query = '''
        SELECT substr(game_date, 7, 4) as year, COUNT(*) as count
        FROM questions 
        WHERE game_date IS NOT NULL 
        AND game_date != '' 
        GROUP BY substr(game_date, 7, 4)
        ORDER BY year DESC
    '''
    results = conn.execute(query).fetchall()
    conn.close()
    
    # Преобразуем результаты в словарь
    questions_by_year = {}
    total_questions = 0
    for row in results:
        questions_by_year[row['year']] = row['count']
        total_questions += row['count']
    
    return jsonify({
        'questions_by_year': questions_by_year,
        'total_questions': total_questions
    })

@app.route('/api/admin/visible-years', methods=['GET'])
def get_visible_years():
    # Загружаем настройки видимости лет из файла
    visible_years = load_visible_years()
    
    return jsonify({
        'visible_years': visible_years
    })

@app.route('/api/admin/visible-years', methods=['POST'])
def update_visible_years():
    # Получаем данные из запроса
    data = request.get_json()
    visible_years = data.get('visible_years', [])
    
    # Сохраняем настройки видимости лет в файл
    save_visible_years(visible_years)
    
    return jsonify({
        'status': 'success',
        'message': f'Updated visibility for {len(visible_years)} years',
        'visible_years': visible_years
    })

if __name__ == '__main__':
    app.run(debug=True, port=5002)
