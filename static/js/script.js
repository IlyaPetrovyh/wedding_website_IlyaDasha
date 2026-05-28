document.addEventListener("DOMContentLoaded", () => {


    // 1. Анимация появления блоков при скроллинге
    const fadeElements = document.querySelectorAll('.fade-element');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target); // Анимируем только один раз
            }
        });
    }, { threshold: 0.1 }); // Срабатывает, когда 10% элемента видно

    fadeElements.forEach(el => observer.observe(el));

    // 2. Таймер обратного отсчета
    const targetDate = new Date("June 20, 2026 15:30:00").getTime();
    const countdownEl = document.getElementById("countdown");

    const updateTimer = () => {
        const now = new Date().getTime();
        const distance = targetDate - now;

        if (distance < 0) {
            countdownEl.innerHTML = "Свадьба уже началась!";
            return;
        }

        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));

        countdownEl.innerHTML = `Осталось: ${days}д ${hours}ч ${minutes}м`;
    };

    setInterval(updateTimer, 60000); // Обновляем раз в минуту для экономии ресурсов
    updateTimer(); // Запуск сразу при загрузке



    async function initGallery() {
        const track = document.getElementById('gallery-track');
        if (!track) return;

        try {
            const response = await fetch('/api/gallery');
            const result = await response.json();

            if (result.success && result.items.length > 0) {
                renderInfiniteGallery(result.items, track);
            } else {
                // Фолбэк, если файлов в папке пока нет
                document.getElementById('gallery-wrapper').style.display = 'none';
            }
        } catch (error) {
            console.error('Network Error: Не удалось загрузить галерею', error);
            document.getElementById('gallery-wrapper').style.display = 'none';
        }
    }

    function renderInfiniteGallery(items, trackElement) {
        trackElement.innerHTML = ''; // Очистка DOM узла

        // Генерация HTML-строки на основе массива данных
        const buildNodes = () => {
            let htmlString = '';
            items.forEach(item => {
                const isVideo = item.type === 'video';
                const iconOverlay = isVideo ? '<div class="video-icon">▶</div>' : '';

                // Ссылка ведет на полноразмерный оригинал
                htmlString += `
                    <a href="${item.original}" target="_blank" class="gallery-item">
                        <img src="${item.preview}" alt="${item.name}" loading="lazy">
                        ${iconOverlay}
                    </a>
                `;
            });
            return htmlString;
        };

        const originalContent = buildNodes();

        /* Дублируем контент. Если элементов мало (ширина меньше ширины экрана),
          свойство flexbox не сможет создать непрерывный поток.
          Для надежности дублируем контент дважды.
        */
        trackElement.innerHTML = originalContent + originalContent;
    }
});
