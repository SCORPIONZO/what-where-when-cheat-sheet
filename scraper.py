import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re
import os
from urllib.parse import urljoin, urlparse

# Create database and table
def init_db():
    conn = sqlite3.connect('data/questions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS questions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  game_date TEXT,
                  round_title TEXT,
                  question_text TEXT,
                  answer_text TEXT,
                  source_url TEXT,
                  images TEXT)''')
    
    # Create images table
    c.execute('''CREATE TABLE IF NOT EXISTS question_images
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question_id INTEGER,
                  image_url TEXT,
                  local_path TEXT,
                  FOREIGN KEY (question_id) REFERENCES questions (id))''')
    
    conn.commit()
    conn.close()

def extract_questions_from_page(url):
    """Extract questions from a game page"""
    questions = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract round title
        round_title_elem = soup.find('h1')
        round_title = round_title_elem.get_text(strip=True) if round_title_elem else "Неизвестный раунд"
        
        # Extract date from URL or page
        date_match = re.search(r'/(\d{8})-', url)
        game_date = date_match.group(1) if date_match else "Неизвестная дата"
        
        # Get the raw HTML text
        html_text = str(soup)
        
        # Find all occurrences of "ВОПРОС" and "ОТВЕТ"
        question_positions = []
        answer_positions = []
        
        for match in re.finditer(r'<strong[^>]*>ВОПРОС</strong>', html_text):
            question_positions.append(match.start())
            
        for match in re.finditer(r'<strong[^>]*>ОТВЕТ</strong>', html_text):
            answer_positions.append(match.start())
        
        # Pair questions with answers
        for i, q_pos in enumerate(question_positions):
            # Find the next answer position after this question
            a_pos = None
            for pos in answer_positions:
                if pos > q_pos:
                    a_pos = pos
                    break
            
            if a_pos is not None:
                # Find the next question position after this answer to limit extraction
                next_q_pos = None
                for pos in question_positions[i+1:]:
                    if pos > a_pos:
                        next_q_pos = pos
                        break
                
                # Extract text between question and answer
                question_html = html_text[q_pos:a_pos]
                # Extract text between answer and next question (or end of text)
                answer_end = next_q_pos if next_q_pos is not None else len(html_text)
                answer_html = html_text[a_pos:answer_end]
                
                # Parse the HTML fragments to extract text
                q_soup = BeautifulSoup(question_html, 'html.parser')
                a_soup = BeautifulSoup(answer_html, 'html.parser')
                
                # Get all text after the question marker
                question_text = ""
                found_question_marker = False
                for elem in q_soup.descendants:
                    if isinstance(elem, str) and "ВОПРОС" in elem:
                        found_question_marker = True
                        continue
                    if found_question_marker and isinstance(elem, str):
                        question_text += elem
                
                # Get all text after the answer marker
                answer_text = ""
                found_answer_marker = False
                for elem in a_soup.descendants:
                    if isinstance(elem, str) and "ОТВЕТ" in elem:
                        found_answer_marker = True
                        continue
                    if found_answer_marker and isinstance(elem, str):
                        answer_text += elem
                
                # Clean up text
                question_text = re.sub(r'\s+', ' ', question_text.strip())
                answer_text = re.sub(r'\s+', ' ', answer_text.strip())
                
                # Only save if both question and answer have content
                if len(question_text) > 10 and len(answer_text) > 10:
                    questions.append({
                        'game_date': game_date,
                        'round_title': round_title,
                        'question_text': question_text,
                        'answer_text': answer_text,
                        'source_url': url,
                        'images': ''
                    })
                
    except Exception as e:
        print(f"Ошибка при извлечении вопросов из {url}: {str(e)}")
    
    return questions

def save_questions(questions):
    """Save questions to database"""
    if not questions:
        return
    
    conn = sqlite3.connect('data/questions.db')
    c = conn.cursor()
    
    for q in questions:
        c.execute('''INSERT INTO questions 
                     (game_date, round_title, question_text, answer_text, source_url, images)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (q['game_date'], q['round_title'], q['question_text'], 
                   q['answer_text'], q['source_url'], q['images']))
    
    conn.commit()
    conn.close()

# Main scraping function for 2020 season
def scrape_season_2020():
    base_url = "https://xn----etbqgrg5bs.xn--p1ai"
    season_url = "https://xn----etbqgrg5bs.xn--p1ai/igry-2020-yh/sezon-2020"
    
    # Initialize database
    init_db()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(season_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all game links
        game_links = soup.find_all('a', href=re.compile(r'/igry-2020-yh/sezon-2020/'))
        
        urls_to_scrape = []
        for link in game_links:
            href = link.get('href')
            # Проверяем, что это ссылка на конкретную игру (содержит дату в формате DDMMYYYY)
            if href and re.search(r'/\d{8}-', href):
                full_url = urljoin(base_url, href)
                urls_to_scrape.append(full_url)
        
        # Remove duplicates
        urls_to_scrape = list(set(urls_to_scrape))
        
        print(f"Найдено {len(urls_to_scrape)} игр для сбора данных")
        
        # Scrape each game
        for i, url in enumerate(urls_to_scrape):
            print(f"Обработка игры {i+1}/{len(urls_to_scrape)}: {url}")
            questions = extract_questions_from_page(url)
            save_questions(questions)
            print(f"Сохранено {len(questions)} вопросов из этой игры")
            # Be respectful to the server
            time.sleep(1)
            
    except Exception as e:
        print(f"Ошибка при сборе данных: {str(e)}")

# Main scraping function for 2014 season
def scrape_season_2014():
    base_url = "https://xn----etbqgrg5bs.xn--p1ai"
    season_url = "https://xn----etbqgrg5bs.xn--p1ai/igry-2010-yh/sezon-2014"
    
    # Initialize database
    init_db()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(season_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all game links
        game_links = soup.find_all('a', href=re.compile(r'/igry-2010-yh/sezon-2014/'))
        
        urls_to_scrape = []
        for link in game_links:
            href = link.get('href')
            # Проверяем, что это ссылка на конкретную игру (содержит дату в формате DDMMYYYY)
            if href and re.search(r'/\d{8}-', href):
                full_url = urljoin(base_url, href)
                urls_to_scrape.append(full_url)
        
        # Remove duplicates
        urls_to_scrape = list(set(urls_to_scrape))
        
        print(f"Найдено {len(urls_to_scrape)} игр для сбора данных")
        
        # Scrape each game
        for i, url in enumerate(urls_to_scrape):
            print(f"Обработка игры {i+1}/{len(urls_to_scrape)}: {url}")
            questions = extract_questions_from_page(url)
            save_questions(questions)
            print(f"Сохранено {len(questions)} вопросов из этой игры")
            # Be respectful to the server
            time.sleep(1)
            
    except Exception as e:
        print(f"Ошибка при сборе данных: {str(e)}")

# Main scraping function for 2008 season
def scrape_season_2008():
    base_url = "https://xn----etbqgrg5bs.xn--p1ai"
    season_url = "https://xn----etbqgrg5bs.xn--p1ai/igry-2000-yh/sezon-2008"
    
    # Initialize database
    init_db()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(season_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all game links
        game_links = soup.find_all('a', href=re.compile(r'/igry-2000-yh/sezon-2008/'))
        
        urls_to_scrape = []
        for link in game_links:
            href = link.get('href')
            # Проверяем, что это ссылка на конкретную игру (содержит дату в формате DDMMYYYY)
            if href and re.search(r'/\d{8}-', href):
                full_url = urljoin(base_url, href)
                urls_to_scrape.append(full_url)
        
        # Remove duplicates
        urls_to_scrape = list(set(urls_to_scrape))
        
        print(f"Найдено {len(urls_to_scrape)} игр для сбора данных")
        
        # Scrape each game
        for i, url in enumerate(urls_to_scrape):
            print(f"Обработка игры {i+1}/{len(urls_to_scrape)}: {url}")
            questions = extract_questions_from_page(url)
            save_questions(questions)
            print(f"Сохранено {len(questions)} вопросов из этой игры")
            # Be respectful to the server
            time.sleep(1)
            
    except Exception as e:
        print(f"Ошибка при сборе данных: {str(e)}")

# Main scraping function for 2002 season
def scrape_season_2002():
    base_url = "https://xn----etbqgrg5bs.xn--p1ai"
    season_url = "https://xn----etbqgrg5bs.xn--p1ai/igry-2000-yh/sezon-2002"
    
    # Initialize database
    init_db()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(season_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all game links
        game_links = soup.find_all('a', href=re.compile(r'/igry-2000-yh/sezon-2002/'))
        
        urls_to_scrape = []
        for link in game_links:
            href = link.get('href')
            # Проверяем, что это ссылка на конкретную игру (содержит дату в формате DDMMYYYY)
            if href and re.search(r'/\d{8}-', href):
                full_url = urljoin(base_url, href)
                urls_to_scrape.append(full_url)
        
        # Remove duplicates
        urls_to_scrape = list(set(urls_to_scrape))
        
        print(f"Найдено {len(urls_to_scrape)} игр для сбора данных")
        
        # Scrape each game
        for i, url in enumerate(urls_to_scrape):
            print(f"Обработка игры {i+1}/{len(urls_to_scrape)}: {url}")
            questions = extract_questions_from_page(url)
            save_questions(questions)
            print(f"Сохранено {len(questions)} вопросов из этой игры")
            # Be respectful to the server
            time.sleep(1)
            
    except Exception as e:
        print(f"Ошибка при сборе данных: {str(e)}")

# Main scraping function for 1996 season
def scrape_season_1996():
    base_url = "https://xn----etbqgrg5bs.xn--p1ai"
    season_url = "https://xn----etbqgrg5bs.xn--p1ai/igry-1990-yh/sezon-1996"
    
    # Initialize database
    init_db()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(season_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all game links
        game_links = soup.find_all('a', href=re.compile(r'/igry-1990-yh/sezon-1996/'))
        
        urls_to_scrape = []
        for link in game_links:
            href = link.get('href')
            # Проверяем, что это ссылка на конкретную игру (содержит дату в формате DDMMYYYY)
            if href and re.search(r'/\d{8}-', href):
                full_url = urljoin(base_url, href)
                urls_to_scrape.append(full_url)
        
        # Remove duplicates
        urls_to_scrape = list(set(urls_to_scrape))
        
        print(f"Найдено {len(urls_to_scrape)} игр для сбора данных")
        
        # Scrape each game
        for i, url in enumerate(urls_to_scrape):
            print(f"Обработка игры {i+1}/{len(urls_to_scrape)}: {url}")
            questions = extract_questions_from_page(url)
            save_questions(questions)
            print(f"Сохранено {len(questions)} вопросов из этой игры")
            # Be respectful to the server
            time.sleep(1)
            
    except Exception as e:
        print(f"Ошибка при сборе данных: {str(e)}")

# Main scraping function for 1990 season
def scrape_season_1990():
    base_url = "https://xn----etbqgrg5bs.xn--p1ai"
    season_url = "https://xn----etbqgrg5bs.xn--p1ai/igry-1990-yh/sezon-1990"
    
    # Initialize database
    init_db()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(season_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all game links
        game_links = soup.find_all('a', href=re.compile(r'/igry-1990-yh/sezon-1990/'))
        
        urls_to_scrape = []
        for link in game_links:
            href = link.get('href')
            # Проверяем, что это ссылка на конкретную игру (содержит дату в формате DDMMYYYY)
            if href and re.search(r'/\d{8}-', href):
                full_url = urljoin(base_url, href)
                urls_to_scrape.append(full_url)
        
        # Remove duplicates
        urls_to_scrape = list(set(urls_to_scrape))
        
        print(f"Найдено {len(urls_to_scrape)} игр для сбора данных")
        
        # Scrape each game
        for i, url in enumerate(urls_to_scrape):
            print(f"Обработка игры {i+1}/{len(urls_to_scrape)}: {url}")
            questions = extract_questions_from_page(url)
            save_questions(questions)
            print(f"Сохранено {len(questions)} вопросов из этой игры")
            # Be respectful to the server
            time.sleep(1)
            
    except Exception as e:
        print(f"Ошибка при сборе данных: {str(e)}")

if __name__ == "__main__":
    scrape_season_1990()
    print("Сбор данных завершен!")
