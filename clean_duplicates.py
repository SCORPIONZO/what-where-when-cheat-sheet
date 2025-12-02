import sqlite3

# Подключаемся к базе данных
conn = sqlite3.connect('data/questions.db')
cursor = conn.cursor()

# Найдем все дубликаты вопросов
cursor.execute("""
    SELECT question_text, COUNT(*) as count 
    FROM questions 
    GROUP BY question_text 
    HAVING COUNT(*) > 1
""")

duplicates = cursor.fetchall()

print(f"Найдено {len(duplicates)} уникальных вопросов с дубликатами")

total_deleted = 0

for question_text, count in duplicates:
    # Получаем все записи с этим вопросом
    cursor.execute("""
        SELECT id, game_date, source_url 
        FROM questions 
        WHERE question_text = ? 
        ORDER BY id
    """, (question_text,))
    
    records = cursor.fetchall()
    
    # Оставляем только первую запись, остальные удаляем
    if len(records) > 1:
        ids_to_delete = [str(record[0]) for record in records[1:]]
        ids_to_delete_str = ",".join(ids_to_delete)
        
        # Удаляем дубликаты
        cursor.execute(f"DELETE FROM questions WHERE id IN ({ids_to_delete_str})")
        deleted_count = cursor.rowcount
        total_deleted += deleted_count
        
        print(f"Удалено {deleted_count} дубликатов для вопроса: {question_text[:50]}...")

# Фиксируем изменения
conn.commit()
conn.close()

print(f"Всего удалено {total_deleted} дубликатов")