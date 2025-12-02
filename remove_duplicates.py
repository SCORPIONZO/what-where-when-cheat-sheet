import sqlite3

# Подключаемся к базе данных
conn = sqlite3.connect('data/questions.db')
cursor = conn.cursor()

# Находим все полностью дублирующиеся записи
cursor.execute("""
    SELECT question_text, game_date, source_url, images, COUNT(*) as count 
    FROM questions 
    GROUP BY question_text, game_date, source_url, images 
    HAVING COUNT(*) > 1
""")

duplicate_groups = cursor.fetchall()

print(f"Найдено {len(duplicate_groups)} групп полностью дублирующихся вопросов")

total_deleted = 0

for group in duplicate_groups:
    question_text, game_date, source_url, images, count = group
    
    # Получаем все записи в этой группе
    cursor.execute("""
        SELECT id 
        FROM questions 
        WHERE question_text = ? AND game_date = ? AND source_url = ? AND images = ?
        ORDER BY id
    """, (question_text, game_date, source_url, images))
    
    records = cursor.fetchall()
    
    # Оставляем только первую запись, остальные удаляем
    if len(records) > 1:
        ids_to_delete = [str(record[0]) for record in records[1:]]
        ids_to_delete_str = ",".join(ids_to_delete)
        
        # Удаляем дубликаты
        cursor.execute(f"DELETE FROM questions WHERE id IN ({ids_to_delete_str})")
        deleted_count = cursor.rowcount
        total_deleted += deleted_count
        
        print(f"Удалено {deleted_count} полностью дублирующихся записей для вопроса: {question_text[:50]}...")

# Фиксируем изменения
conn.commit()
conn.close()

print(f"Всего удалено {total_deleted} полностью дублирующихся записей")