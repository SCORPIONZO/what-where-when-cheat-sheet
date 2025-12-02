import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# Test with a specific game page
test_url = "https://xn----etbqgrg5bs.xn--p1ai/igry-2020-yh/sezon-2025/30032025-pervaya-igra-vesenney-serii"

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(test_url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    soup.base_url = test_url
    
    # Find all images
    images = soup.find_all('img')
    print(f"Total images found: {len(images)}")
    
    # Print all image URLs and alt texts
    for i, img in enumerate(images):
        src = img.get('src', 'No src')
        alt = img.get('alt', 'No alt')
        print(f"Image {i+1}: {src} - Alt: {alt}")
    
    # Find questions with "внимание" phrases
    question_headers = soup.find_all(string=re.compile(r"ВОПРОС"))
    print(f"\nFound {len(question_headers)} question headers")
    
    for i, q_header in enumerate(question_headers):
        print(f"\nQuestion {i+1}:")
        parent = q_header.parent
        print(f"Header text: {q_header.strip()}")
        
        # Look for images near this question
        current = parent
        img_count = 0
        print("Images near this question:")
        for _ in range(20):
            if current.next_sibling:
                sibling = current.next_sibling
                if hasattr(sibling, 'find_all'):
                    imgs = sibling.find_all('img')
                    for img in imgs:
                        src = img.get('src')
                        alt = img.get('alt', '').lower()
                        if src:
                            full_url = urljoin(soup.base_url, src)
                            print(f"  Found image: {full_url} - Alt: {alt}")
                            img_count += 1
                current = sibling
            else:
                break
                
        if img_count == 0:
            print("  No images found near this question")

except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()