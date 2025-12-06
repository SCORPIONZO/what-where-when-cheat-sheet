document.addEventListener('DOMContentLoaded', function() {
    let currentPage = 1;
    let currentPerPage = 10;
    let currentSearch = '';
    let currentYearFilter = 'all';
    let currentViewMode = localStorage.getItem('viewMode') || 'grid'; // 'grid' or 'card'
    let cardQuestions = []; // Хранит вопросы для режима карточек
    let currentCardIndex = 0; // Текущий индекс вопроса в режиме карточек
    let openedQuestions = new Set(); // Хранит ID открытых вопросов

    // DOM Elements
    const questionsContainer = document.getElementById('questionsContainer');
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const perPageSelect = document.getElementById('perPage');
    const yearFilterSelect = document.getElementById('filterYear');
    const viewModeSelect = document.getElementById('viewMode');
    const prevPageButton = document.getElementById('prevPage');
    const nextPageButton = document.getElementById('nextPage');
    const pageNumberInput = document.getElementById('pageNumberInput');
    const goToPageButton = document.getElementById('goToPage');
    const pageInfo = document.getElementById('pageInfo');
    const totalCount = document.getElementById('totalCount');
    const themeToggle = document.getElementById('themeToggle');

    // Set initial view mode
    viewModeSelect.value = currentViewMode;

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

    // Load available years
    loadAvailableYears();

    // Event Listeners
    searchButton.addEventListener('click', () => {
        currentSearch = searchInput.value.trim();
        currentPage = 1;
        updatePageNumberInput();
        if (currentViewMode === 'card') {
            loadCardView();
        } else {
            loadQuestions();
        }
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentSearch = searchInput.value.trim();
            currentPage = 1;
            updatePageNumberInput();
            if (currentViewMode === 'card') {
                loadCardView();
            } else {
                loadQuestions();
            }
        }
    });

    perPageSelect.addEventListener('change', () => {
        currentPerPage = parseInt(perPageSelect.value);
        currentPage = 1;
        updatePageNumberInput();
        if (currentViewMode === 'card') {
            loadCardView();
        } else {
            loadQuestions();
        }
    });

    yearFilterSelect.addEventListener('change', () => {
        currentYearFilter = yearFilterSelect.value;
        currentPage = 1;
        updatePageNumberInput();
        if (currentViewMode === 'card') {
            loadCardView();
        } else {
            loadQuestions();
        }
    });

    viewModeSelect.addEventListener('change', () => {
        currentViewMode = viewModeSelect.value;
        localStorage.setItem('viewMode', currentViewMode);
        currentPage = 1;
        updatePageNumberInput();
        if (currentViewMode === 'card') {
            currentCardIndex = 0;
            loadCardView();
        } else {
            loadQuestions();
        }
    });

    prevPageButton.addEventListener('click', () => {
        if (currentViewMode === 'card') {
            if (currentPage > 1) {
                currentPage--;
                updatePageNumberInput();
                loadCardView();
            }
        } else {
            if (currentPage > 1) {
                currentPage--;
                updatePageNumberInput();
                loadQuestions();
            }
        }
    });

    nextPageButton.addEventListener('click', () => {
        if (currentViewMode === 'card') {
            // Get total pages from page info text
            const totalPagesMatch = pageInfo.textContent.match(/из\s+(\d+)/);
            const totalPages = totalPagesMatch ? parseInt(totalPagesMatch[1]) : 1;
            if (currentPage < totalPages) {
                currentPage++;
                updatePageNumberInput();
                loadCardView();
            }
        } else {
            const totalPages = parseInt(pageInfo.textContent.match(/из\s+(\d+)/)?.[1] || '1');
            if (currentPage < totalPages) {
                currentPage++;
                updatePageNumberInput();
                loadQuestions();
            }
        }
    });

    // Page number input events
    goToPageButton.addEventListener('click', () => {
        goToPage();
    });

    pageNumberInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            goToPage();
        }
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        // Check if focused element is not an input to avoid interfering with typing
        if (document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'SELECT') {
            if (e.key === 'ArrowLeft') {
                // Left arrow - go to previous page/card
                if (currentViewMode === 'card') {
                    if (currentPage > 1) {
                        currentPage--;
                        updatePageNumberInput();
                        loadCardView();
                    }
                } else {
                    if (currentPage > 1) {
                        currentPage--;
                        updatePageNumberInput();
                        loadQuestions();
                    }
                }
            } else if (e.key === 'ArrowRight') {
                // Right arrow - go to next page/card
                if (currentViewMode === 'card') {
                    // Get total pages from page info text
                    const totalPagesMatch = pageInfo.textContent.match(/из\s+(\d+)/);
                    const totalPages = totalPagesMatch ? parseInt(totalPagesMatch[1]) : 1;
                    if (currentPage < totalPages) {
                        currentPage++;
                        updatePageNumberInput();
                        loadCardView();
                    }
                } else {
                    const totalPages = parseInt(pageInfo.textContent.match(/из\s+(\d+)/)?.[1] || '1');
                    if (currentPage < totalPages) {
                        currentPage++;
                        updatePageNumberInput();
                        loadQuestions();
                    }
                }
            }
        }
    });

    // Load available years for filter
    function loadAvailableYears() {
        fetch('/api/years')
            .then(response => response.json())
            .then(data => {
                data.years.forEach(year => {
                    const option = document.createElement('option');
                    option.value = year;
                    option.textContent = year;
                    yearFilterSelect.appendChild(option);
                });
                
                // Load initial data based on saved view mode
                if (currentViewMode === 'card') {
                    loadCardView();
                } else {
                    loadQuestions();
                }
            })
            .catch(error => {
                console.error('Error loading years:', error);
            });
    }

    // Load questions for card view
    function loadCardView() {
        // Save current view mode
        localStorage.setItem('viewMode', 'card');
        currentViewMode = 'card';
        viewModeSelect.value = 'card';

        // Show loading state
        questionsContainer.innerHTML = '<div class="loading">Загрузка вопросов...</div>';

        // Build query parameters for questions with pagination
        const params = new URLSearchParams({
            page: currentPage,
            per_page: currentPerPage,
            sort_by: 'year',
            sort_order: 'desc'
        });

        if (currentSearch) {
            params.append('search', currentSearch);
        }

        if (currentYearFilter !== 'all') {
            params.append('year', currentYearFilter);
        }

        fetch(`/api/questions?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                // Filter questions to only show those with valid answers
                cardQuestions = filterValidQuestions(data.questions);
                currentCardIndex = 0;
                if (cardQuestions.length > 0) {
                    renderCardView();
                    updatePagination(data);
                } else {
                    questionsContainer.innerHTML = '<div class="no-questions">Вопросы не найдены</div>';
                    // Update pagination even when no questions found
                    updatePagination({...data, questions: []});
                }
            })
            .catch(error => {
                console.error('Error loading questions:', error);
                questionsContainer.innerHTML = '<div class="error">Ошибка загрузки вопросов. Попробуйте позже.</div>';
            });
    }

    // Render card view
    function renderCardView() {
        if (cardQuestions.length === 0) {
            questionsContainer.innerHTML = '<div class="no-questions">Вопросы не найдены</div>';
            return;
        }

        // Make sure currentCardIndex is within bounds
        if (currentCardIndex < 0) currentCardIndex = 0;
        if (currentCardIndex >= cardQuestions.length) currentCardIndex = cardQuestions.length - 1;

        const question = cardQuestions[currentCardIndex];
        const isQuestionOpened = openedQuestions.has(question.id);

        // Ensure we have both question and answer text
        const questionText = question.question_text || 'Текст вопроса недоступен';
        const fullAnswerText = question.answer_text || 'Ответ недоступен';
        const correctAnswerText = extractCorrectAnswer(fullAnswerText);

        questionsContainer.innerHTML = `
            <div class="card-view-container">
                <div class="card-view" id="cardView">
                    <div class="card-view-front">
                        <div class="card-header">
                            <div>Дата игры: ${question.game_date || 'Не указана'}</div>
                            <div>Тема: ${question.round_title || 'Не указана'}${isQuestionOpened ? ' <span class="read-indicator">(просмотрен)</span>' : ''}</div>
                        </div>
                        <div class="card-question">
                            Вопрос: ${questionText}
                        </div>
                        <button class="card-button" onclick="flipCard()">
                            Показать ответ
                        </button>
                        <div class="flip-indicator">
                            Карточка ${currentCardIndex + 1} из ${cardQuestions.length}
                        </div>
                    </div>
                    <div class="card-view-back">
                        <div class="card-header">
                            <div>Дата игры: ${question.game_date || 'Не указана'}</div>
                            <div>Тема: ${question.round_title || 'Не указана'}${isQuestionOpened ? ' <span class="read-indicator">(просмотрен)</span>' : ''}</div>
                        </div>
                        <div class="card-answer">
                            ${correctAnswerText}
                        </div>
                        <button class="card-button" onclick="flipCard()">
                            Скрыть ответ
                        </button>
                        <div class="flip-indicator">
                            Карточка ${currentCardIndex + 1} из ${cardQuestions.length}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Force reflow to reset animations when question changes
        if (document.getElementById('cardView')) {
            void document.getElementById('cardView').offsetWidth;
        }
    }

    // Flip card function
    window.flipCard = function() {
        const card = document.querySelector('.card-view');
        if (card) {
            card.classList.toggle('flipped');
            
            // Mark question as opened
            const question = cardQuestions[currentCardIndex];
            if (question && question.id) {
                openedQuestions.add(question.id);
                
                // Update the indicator if it's not already there
                const headers = document.querySelectorAll('.card-header div:last-child');
                headers.forEach(header => {
                    if (header && !header.innerHTML.includes('(просмотрен)')) {
                        header.innerHTML += ' <span class="read-indicator">(просмотрен)</span>';
                    }
                });
            }
            
            // Change button text based on flip state
            const buttons = document.querySelectorAll('.card-button');
            if (card.classList.contains('flipped')) {
                buttons.forEach(btn => btn.textContent = 'Скрыть ответ');
            } else {
                buttons.forEach(btn => btn.textContent = 'Показать ответ');
            }
            
            // Add animation for flip transition
            card.classList.add('flip-animation');
            setTimeout(() => {
                card.classList.remove('flip-animation');
            }, 600); // Match CSS transition duration
        }
    };

    // Go to specific page
    function goToPage() {
        const totalPages = parseInt(pageInfo.textContent.match(/из\s+(\d+)/)?.[1] || '1');
        const pageNumber = parseInt(pageNumberInput.value);
        
        if (!isNaN(pageNumber) && pageNumber >= 1 && pageNumber <= totalPages) {
            currentPage = pageNumber;
            if (currentViewMode === 'card') {
                loadCardView();
            } else {
                loadQuestions();
            }
        } else {
            // Reset to current page if invalid input
            updatePageNumberInput();
        }
    }

    // Update page number input value
    function updatePageNumberInput() {
        pageNumberInput.value = currentPage;
    }

    // Load questions from API
    function loadQuestions() {
        // Show loading state
        questionsContainer.innerHTML = '<div class="loading">Загрузка вопросов...</div>';

        // Build query parameters
        const params = new URLSearchParams({
            page: currentPage,
            per_page: currentPerPage,
            sort_by: 'year',
            sort_order: 'desc'
        });

        if (currentSearch) {
            params.append('search', currentSearch);
        }

        if (currentYearFilter !== 'all') {
            params.append('year', currentYearFilter);
        }

        fetch(`/api/questions?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                renderQuestions(data.questions);
                updatePagination(data);
                totalCount.textContent = data.total;
                updatePageNumberInput();
                
                // Scroll to top when new page loads
                window.scrollTo({ top: 0, behavior: 'smooth' });
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
            
            // Check if question was opened
            const isQuestionOpened = openedQuestions.has(question.id);
            
            // Extract only the correct answer part
            const fullAnswerText = question.answer_text || 'Ответ недоступен';
            const correctAnswerText = extractCorrectAnswer(fullAnswerText);
            
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
                    <div>Тема: ${question.round_title || 'Не указана'}${isQuestionOpened ? ' <span class="read-indicator">(просмотрен)</span>' : ''}</div>
                </div>
                <div class="question-text">
                    Вопрос: ${question.question_text || 'Текст вопроса недоступен'}
                </div>
                ${imagesHtml}
                <div class="answer-container" style="display:none;">
                    <div class="answer-text">
                        <span class="answer-label">Ответ:</span> 
                        ${correctAnswerText}
                    </div>
                </div>
                <button class="show-answer" data-question-id="${question.id}" onclick="toggleAnswer(this)">
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
        if (currentViewMode === 'card') {
            // In card mode, we show current page info like grid mode
            pageInfo.textContent = `Страница ${data.page} из ${data.total_pages || 1}`;
            
            prevPageButton.disabled = data.page <= 1;
            nextPageButton.disabled = data.page >= (data.total_pages || 1);
            
            // Update page number input max value
            pageNumberInput.max = data.total_pages || 1;
            pageNumberInput.min = 1;
        } else {
            pageInfo.textContent = `Страница ${data.page} из ${data.total_pages || 1}`;
            
            prevPageButton.disabled = data.page <= 1;
            nextPageButton.disabled = data.page >= (data.total_pages || 1);
            
            // Update page number input max value
            pageNumberInput.max = data.total_pages || 1;
            pageNumberInput.min = 1;
        }
    }

    // Toggle answer visibility with animation
    window.toggleAnswer = function(button) {
        const answerContainer = button.previousElementSibling;
        const isVisible = answerContainer.style.display === 'block' || 
                         (!answerContainer.style.display && answerContainer.offsetHeight > 0);
        const questionId = button.getAttribute('data-question-id');
        
        if (isVisible) {
            answerContainer.style.display = 'none';
            button.textContent = 'Показать ответ';
        } else {
            answerContainer.style.display = 'block';
            button.textContent = 'Скрыть ответ';
            
            // Mark question as opened
            if (questionId) {
                openedQuestions.add(parseInt(questionId));
            }
            
            // Update the question card to show it's been read
            const questionHeader = button.parentElement.querySelector('.question-header div:last-child');
            if (questionHeader && !questionHeader.innerHTML.includes('(просмотрен)')) {
                questionHeader.innerHTML += ' <span class="read-indicator">(просмотрен)</span>';
            }
            
            // Add animation effect
            answerContainer.style.opacity = '0';
            answerContainer.style.transition = 'opacity 0.3s';
            setTimeout(() => {
                answerContainer.style.opacity = '1';
            }, 10);
        }
    };

    // Function to extract only the correct answer part from the answer text
    function extractCorrectAnswer(answerText) {
        if (!answerText) return 'Ответ недоступен';
        
        // Convert to lowercase for case-insensitive matching
        const lowerText = answerText.toLowerCase();
        
        // Possible variations of "correct answer" phrases
        const answerPatterns = [
            'дан правильный ответ',
            'дал правильный ответ',
            'дан правельный ответ',
            'дал правельный ответ',
            'правильный ответ',
            'правельный ответ'
        ];
        
        // Find the first occurrence of any correct answer phrase
        let earliestIndex = -1;
        let matchedPhrase = '';
        
        for (const pattern of answerPatterns) {
            const index = lowerText.indexOf(pattern);
            if (index !== -1 && (earliestIndex === -1 || index < earliestIndex)) {
                earliestIndex = index;
                matchedPhrase = pattern;
            }
        }
        
        // If we found a correct answer phrase, extract everything from that point
        if (earliestIndex !== -1) {
            // Get the original case version of the phrase
            const originalCasePhrase = answerText.substring(earliestIndex, earliestIndex + matchedPhrase.length);
            const restOfText = answerText.substring(earliestIndex + matchedPhrase.length);
            return originalCasePhrase + restOfText;
        }
        
        // If no pattern found, return the original text
        return answerText;
    }

    // Filter questions to only show those with valid answers (case insensitive and with typos)
    function filterValidQuestions(questions) {
        return questions.filter(question => {
            const answerText = question.answer_text ? question.answer_text.toLowerCase() : '';
            return answerText.includes('дан правильный ответ') || 
                   answerText.includes('дал правильный ответ') ||
                   answerText.includes('дан правельный ответ') ||
                   answerText.includes('дал правельный ответ') ||
                   answerText.includes('правильный ответ') ||
                   answerText.includes('правельный ответ');
        });
    }

    // Initial load
    loadQuestions();
});