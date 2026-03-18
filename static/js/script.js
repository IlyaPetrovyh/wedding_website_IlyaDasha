document.addEventListener("DOMContentLoaded", () => {

    // 1. Анимация появления блоков при скроллинге (ТЗ пункт 3)
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

    // 2. Таймер обратного отсчета (ТЗ пункт 6)
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

// 3. Отправка формы RSVP
    const rsvpForm = document.getElementById("rsvp-form");
    const successBlock = document.getElementById("success-block");

    rsvpForm.addEventListener("submit", async (e) => {
        e.preventDefault(); // Предотвращаем перезагрузку страницы

        // 1. БЕЗОПАСНОЕ ПОЛУЧЕНИЕ СТАТУСА
        const statusElement = document.querySelector('input[name="status"]:checked');

        // Если статус не выбран, останавливаем отправку и просим выбрать
        if (!statusElement) {
            alert('Пожалуйста, выберите статус присутствия!');
            return;
        }

        const formData = {
            firstName: document.getElementById("firstName").value,
            lastName: document.getElementById("lastName").value,
            status: statusElement.value
        };

        try {
            const response = await fetch('/api/rsvp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            // 2. ЧИТАЕМ ОТВЕТ ОТ СЕРВЕРА (чтобы получить текст ошибки из app.py)
            const result = await response.json();

            if (response.ok) {
                // Если статус 200 OK
                rsvpForm.style.display = 'none'; // Прячем форму
                successBlock.style.display = 'block'; // Показываем кнопку ТГ-бота
            } else {
                // Если сервер вернул 400 (например, дубль по IP или пустые поля)
                // Выводим именно ту ошибку, которую мы написали в app.py
                alert(result.error || 'Произошла ошибка при отправке.');
            }
        } catch (error) {
            // Эта ошибка сработает только если сервер вообще "упал" или нет интернета
            console.error("Ошибка сети:", error);
            alert('Ошибка соединения с сервером. Проверьте интернет.');
        }
    });
});
