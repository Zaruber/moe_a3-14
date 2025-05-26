document.addEventListener('DOMContentLoaded', function() {
    // Добавляем плавную прокрутку к внутренним ссылкам
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Добавляем подсветку кода в примерах
    document.querySelectorAll('pre code').forEach(block => {
        // Простая подсветка ключевых слов (можно заменить на библиотеку вроде highlight.js)
        const jsKeywords = ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'import', 'export', 'class', 'new', 'this', 'async', 'await', 'true', 'false', 'null'];
        
        jsKeywords.forEach(keyword => {
            const regex = new RegExp(`\\b${keyword}\\b`, 'g');
            block.innerHTML = block.innerHTML.replace(
                regex, 
                `<span class="keyword">${keyword}</span>`
            );
        });
        
        // Подсветка строк
        block.innerHTML = block.innerHTML.replace(
            /(["'])(.*?)\1/g,
            '<span class="string">$&</span>'
        );
        
        // Подсветка комментариев
        block.innerHTML = block.innerHTML.replace(
            /(\/\/.*?)(?:\n|$)/g,
            '<span class="comment">$1</span>\n'
        );
    });
    
    // Добавляем интерактивность к разделам документации
    document.querySelectorAll('.endpoint h3').forEach(header => {
        header.addEventListener('click', function() {
            const details = this.nextElementSibling;
            
            if (details.style.display === 'none' || !details.style.display) {
                details.style.display = 'block';
                this.classList.add('active');
            } else {
                details.style.display = 'none';
                this.classList.remove('active');
            }
        });
        
        // Инициализация: показываем первый раздел, скрываем остальные
        if (header === document.querySelector('.endpoint h3')) {
            header.classList.add('active');
            header.nextElementSibling.style.display = 'block';
        } else {
            header.nextElementSibling.style.display = 'none';
        }
    });
}); 