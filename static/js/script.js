document.addEventListener('DOMContentLoaded', function() {
    let currentPage = 1;
    let currentPerPage = 10;
    let currentSearch = '';
    let currentSort = 'date_desc';

    // DOM Elements
    const questionsContainer = document.getElementById('questionsContainer');
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const perPageSelect = document.getElementById('perPage');
    const sortBySelect = document.getElementById('sortBy');
    const prevPageButton = document.getElementById('prevPage');
    const nextPageButton = document.getElementById('nextPage');
    const pageInfo = document.getElementById('pageInfo');
    const totalCount = document.getElementById('totalCount');
    const themeToggle = document.getElementById('themeToggle');

    // Theme toggle
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
        localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
        themeToggle.textContent = document.body.classList.contains('dark-theme') ? '☀️' : '🌙';
    });

    // Check for saved theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        themeToggle.textContent = '☀️';
    }

    // Event Listeners
    searchButton.addEventListener('click', () => {
        currentSearch = searchInput.value.trim();
        currentPage = 1;
        loadQuestions();
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentSearch = searchInput.value.trim();
            currentPage = 1;
            loadQuestions();
        }
    });

    perPageSelect.addEventListener('change', () => {
        currentPerPage = parseInt(perPageSelect.value);
        currentPage = 1;
        loadQuestions();
    });

    sortBySelect.addEventListener('change', () => {
        currentSort = sortBySelect.value;
        currentPage = 1;
        loadQuestions();
    });

    prevPageButton.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadQuestions();
        }
    });

    nextPageButton.addEventListener('click', () => {
        currentPage++;
        loadQuestions();
    });

    // Load questions from API
    function loadQuestions() {
        // Show loading state
        questionsContainer.innerHTML = '<div class="loading">Загрузка вопросов...</div>';

        // Build query parameters
        const params = new URLSearchParams({
            page: currentPage,
            per_page: currentPerPage
        });

        if (currentSearch) {
            params.append('search', currentSearch);
        }

        // Add sorting parameter
        let sortColumn = 'game_date';
        let sortOrder = 'desc';
        
        switch(currentSort) {
            case 'date_asc':
                sortColumn = 'game_date';
                sortOrder = 'asc';
                break;
            case 'date_desc':
                sortColumn = 'game_date';
                sortOrder = 'desc';
                break;
            case 'year_asc':
                sortColumn = 'year';
                sortOrder = 'asc';
                break;
            case 'year_desc':
                sortColumn = 'year';
                sortOrder = 'desc';
                break;
            case 'round_asc':
                sortColumn = 'round_title';
                sortOrder = 'asc';
                break;
        }

        params.append('sort_by', sortColumn);
        params.append('sort_order', sortOrder);

        fetch(`/api/questions?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                renderQuestions(data.questions);
                updatePagination(data);
                totalCount.textContent = data.total;
            })
            .catch(error => {
                console.error('Error loading questions:', error);
                questionsContainer.innerHTML = '<div class="error">Ошибка загрузки вопросов. Попробуйте позже.</div>';
            });
    }

    // Render questions to the page with staggered animations
    function renderQuestions(questions) {
        if (questions.length === 0) {
            questionsContainer.innerHTML = '<div class="no-questions">Вопросы не найдены</div>';
            return;
        }

        questionsContainer.innerHTML = '';
        
        questions.forEach((question, index) => {
            // Create card element
            const card = document.createElement('div');
            card.className = 'question-card';
            card.style.animationDelay = `${index * 0.1}s`;
            
            // Generate images HTML
            let imagesHtml = '';
            if (question.images && question.images.length > 0) {
                imagesHtml = `
                    <div class="question-images">
                        ${question.images.map(imgUrl => `
                            <div class="image-container">
                                <img src="${imgUrl}" alt="Изображение к вопросу" onload="this.classList.add('loaded')">
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            
            card.innerHTML = `
                <div class="question-header">
                    <div>Дата игры: ${question.game_date || 'Не указана'}</div>
                    <div>Тема: ${question.round_title || 'Не указана'}</div>
                </div>
                <div class="question-text">
                    Вопрос: ${question.question_text || 'Текст вопроса недоступен'}
                </div>
                ${imagesHtml}
                <div class="answer-container" style="display:none;">
                    <div class="answer-text">
                        <span class="answer-label">Ответ:</span> 
                        ${question.answer_text || 'Ответ недоступен'}
                    </div>
                </div>
                <button class="show-answer" onclick="toggleAnswer(this)">
                    Показать ответ
                </button>
            `;
            
            questionsContainer.appendChild(card);
            
            // Trigger animation
            setTimeout(() => {
                card.classList.add('appear');
            }, 50);
        });
    }

    // Update pagination controls
    function updatePagination(data) {
        pageInfo.textContent = `Страница ${data.page} из ${data.total_pages || 1}`;
        
        prevPageButton.disabled = data.page <= 1;
        nextPageButton.disabled = data.page >= (data.total_pages || 1);
    }

    // Toggle answer visibility with animation
    window.toggleAnswer = function(button) {
        const answerContainer = button.previousElementSibling;
        const isVisible = answerContainer.style.display === 'block';
        
        if (isVisible) {
            answerContainer.style.display = 'none';
            button.textContent = 'Показать ответ';
        } else {
            answerContainer.style.display = 'block';
            button.textContent = 'Скрыть ответ';
            
            // Add animation effect
            answerContainer.style.opacity = '0';
            answerContainer.style.transition = 'opacity 0.3s';
            setTimeout(() => {
                answerContainer.style.opacity = '1';
            }, 10);
        }
    };

    // Initial load
    loadQuestions();
});