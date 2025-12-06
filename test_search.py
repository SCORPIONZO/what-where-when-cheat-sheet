#!/usr/bin/env python3
"""
Скрипт для тестирования нечеткого поиска
"""

import sqlite3
from fuzzywuzzy import fuzz

def get_db_connection():
    conn = sqlite3.connect('data/questions.db')
    conn.row_factory = sqlite3.Row
    return conn

def fuzzy_search(query, limit=10):
    """
    Выполняет нечеткий поиск по вопросам, ответам и заголовкам раундов
    """
    conn = get_db_connection()
    
    # Базовые условия для фильтрации вопросов без ответов
    base_conditions = '''answer_text IS NOT NULL 
                         AND trim(answer_text) != '' 
                         AND answer_text NOT LIKE '%не найден%' '''
    
    # Получаем все вопросы, удовлетворяющие базовым условиям
    base_query = f'''SELECT * FROM questions 
                     WHERE {base_conditions}'''
    all_questions = conn.execute(base_query).fetchall()
    conn.close()
    
    # Применяем нечеткий поиск
    search_results = []
    query_lower = query.lower()
    
    for question in all_questions:
        # Проверяем нечеткие совпадения в тексте вопроса, ответа и заголовке раунда
        question_text_ratio = fuzz.partial_ratio(query_lower, question['question_text'].lower())
        answer_text_ratio = fuzz.partial_ratio(query_lower, question['answer_text'].lower())
        round_title_ratio = fuzz.partial_ratio(query_lower, question['round_title'].lower())
        
        # Используем максимальное значение среди трех полей
        max_ratio = max(question_text_ratio, answer_text_ratio, round_title_ratio)
        
        # Включаем результаты с уровнем схожести выше порога
        if max_ratio >= 60:  # Порог для нечеткого сопоставления
            search_results.append((dict(question), max_ratio))
    
    # Сортируем результаты по уровню схожести (по убыванию)
    search_results.sort(key=lambda x: x[1], reverse=True)
    
    # Ограничиваем количество результатов
    return search_results[:limit]

if __name__ == "__main__":
    # Тестирование нечеткого поиска
    test_queries = [
        "столица Франции",
        "Париж",
        "Эйнштейн",
        "физика"
    ]
    
    for query in test_queries:
        print(f"\nРезультаты поиска для '{query}':")
        print("-" * 50)
        results = fuzzy_search(query, limit=5)
        for i, (question, score) in enumerate(results, 1):
            print(f"{i}. [{score}%] {question['question_text'][:100]}...")
            print(f"   Ответ: {question['answer_text'][:100]}...")
            print()