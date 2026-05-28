/* ═══════════════════════════════════════════════
   wedding_website_IlyaDasha — script.js
═══════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {

    // ──────────────────────────────────────────
    // 1. Анимации появления при скролле
    // ──────────────────────────────────────────
    const fadeObserver = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.classList.add('visible');
                fadeObserver.unobserve(e.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.fade-element').forEach(el => fadeObserver.observe(el));


    // ──────────────────────────────────────────
    // 2. Таймер обратного отсчёта
    // ──────────────────────────────────────────
    const targetDate  = new Date("June 20, 2026 15:30:00").getTime();
    const countdownEl = document.getElementById("countdown");

    const updateTimer = () => {
        const dist = targetDate - Date.now();
        if (dist <= 0) {
            countdownEl.textContent = "Свадьба уже началась!";
            return;
        }
        const d = Math.floor(dist / 86_400_000);
        const h = Math.floor((dist % 86_400_000) / 3_600_000);
        const m = Math.floor((dist % 3_600_000)  /    60_000);
        countdownEl.textContent = `${d}д ${h}ч ${m}м`;
    };

    updateTimer();
    setInterval(updateTimer, 60_000);


    // ──────────────────────────────────────────
    // 3. Карусель
    // ──────────────────────────────────────────
    const track      = document.getElementById('gallery-track');
    const viewport   = document.getElementById('carousel-viewport');
    const prevBtn    = document.getElementById('prev-btn');
    const nextBtn    = document.getElementById('next-btn');
    const dotsEl     = document.getElementById('carousel-dots');

    let items        = [];   // массив DOM-элементов .gallery-item
    let currentIndex = 0;    // индекс первой видимой карточки
    let itemsPerPage = 3;    // количество видимых карточек (меняется при resize)

    /** Возвращает количество карточек, помещающихся в viewport */
    function calcItemsPerPage() {
        const vw = viewport.offsetWidth;
        if (vw < 400) return 1;
        if (vw < 700) return 2;
        return 3;
    }

    /** Пересчитывает ширину каждой карточки под текущий viewport */
    function resizeItems() {
        itemsPerPage    = calcItemsPerPage();
        const gap       = 16;
        const cardWidth = (viewport.offsetWidth - gap * (itemsPerPage - 1)) / itemsPerPage;

        items.forEach(item => {
            item.style.width     = `${cardWidth}px`;
            item.style.minWidth  = `${cardWidth}px`;
        });

        // Корректируем индекс, чтобы не выйти за границы
        const maxIndex = Math.max(0, items.length - itemsPerPage);
        if (currentIndex > maxIndex) currentIndex = maxIndex;

        goTo(currentIndex, false);
        renderDots();
    }

    /** Перемещает трек к нужному индексу */
    function goTo(index, animate = true) {
        if (!items.length) return;

        const maxIndex = Math.max(0, items.length - itemsPerPage);
        currentIndex   = Math.max(0, Math.min(index, maxIndex));

        const gap       = 16;
        const cardWidth = items[0].offsetWidth || (viewport.offsetWidth - gap * (itemsPerPage - 1)) / itemsPerPage;
        const offset    = currentIndex * (cardWidth + gap);

        track.style.transition = animate ? 'transform 0.55s cubic-bezier(0.4,0,0.2,1)' : 'none';
        track.style.transform  = `translateX(-${offset}px)`;

        prevBtn.disabled = currentIndex === 0;
        nextBtn.disabled = currentIndex >= maxIndex;

        updateDots();
    }

    /** Рендерит точки-индикаторы */
    function renderDots() {
        if (!dotsEl) return;
        const total = Math.max(1, items.length - itemsPerPage + 1);
        dotsEl.innerHTML = '';
        for (let i = 0; i < total; i++) {
            const dot = document.createElement('button');
            dot.className     = 'carousel-dot' + (i === currentIndex ? ' active' : '');
            dot.ariaLabel     = `Слайд ${i + 1}`;
            dot.addEventListener('click', () => goTo(i));
            dotsEl.appendChild(dot);
        }
    }

    function updateDots() {
        if (!dotsEl) return;
        dotsEl.querySelectorAll('.carousel-dot').forEach((d, i) => {
            d.classList.toggle('active', i === currentIndex);
        });
    }

    // Кнопки-стрелки
    prevBtn.addEventListener('click', () => goTo(currentIndex - 1));
    nextBtn.addEventListener('click', () => goTo(currentIndex + 1));

    // Свайп на мобилках
    let touchStartX = 0;
    viewport.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; }, { passive: true });
    viewport.addEventListener('touchend',   e => {
        const dx = e.changedTouches[0].clientX - touchStartX;
        if (Math.abs(dx) > 50) goTo(dx < 0 ? currentIndex + 1 : currentIndex - 1);
    });

    // Адаптация при изменении размера окна
    window.addEventListener('resize', () => resizeItems());


    // ──────────────────────────────────────────
    // 4. Загрузка данных галереи с /api/gallery
    // ──────────────────────────────────────────
    async function initGallery() {
        try {
            const resp   = await fetch('/api/gallery');
            const result = await resp.json();

            if (result.success && result.items.length > 0) {
                renderGallery(result.items);
            } else {
                document.getElementById('gallery-wrapper').style.display = 'none';
            }
        } catch (err) {
            console.error('[Gallery] Ошибка загрузки:', err);
            document.getElementById('gallery-wrapper').style.display = 'none';
        }
    }

    function renderGallery(data) {
        // Убираем скелетоны
        track.innerHTML = '';

        data.forEach(item => {
            const link = document.createElement('a');
            link.href        = item.original || '#';
            link.target      = '_blank';
            link.className   = 'gallery-item';
            link.rel         = 'noopener noreferrer';

            const img = document.createElement('img');
            img.src     = item.preview;
            img.alt     = item.name;
            img.loading = 'lazy';
            img.style.opacity = '0';
            img.addEventListener('load',  () => { img.style.opacity = '1'; });
            img.addEventListener('error', () => { link.style.background = '#dde5dd'; });

            link.appendChild(img);

            if (item.type === 'video') {
                const icon = document.createElement('div');
                icon.className = 'video-icon';
                link.appendChild(icon);
            }

            track.appendChild(link);
        });

        // Собираем массив items и инициализируем карусель
        items = Array.from(track.querySelectorAll('.gallery-item'));
        resizeItems();
    }

    initGallery();


    // ──────────────────────────────────────────
    // 5. Модалка загрузки
    // ──────────────────────────────────────────
    const modal       = document.getElementById('upload-modal');
    const fileInput   = document.getElementById('file-input');
    const dropZone    = document.getElementById('drop-zone');
    const queueEl     = document.getElementById('upload-queue');
    const submitBtn   = document.getElementById('upload-submit');

    let pendingFiles  = [];  // File[]

    window.openUploadModal = function () {
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
    };

    window.closeUploadModal = function (event) {
        // Закрываем только по клику на backdrop или крестик
        if (event && event.target !== modal) return;
        modal.classList.remove('open');
        document.body.style.overflow = '';
    };

    // Выбор файла через <input>
    fileInput.addEventListener('change', () => {
        addFiles(Array.from(fileInput.files));
        fileInput.value = '';   // сброс, чтобы можно было выбрать снова
    });

    // Drag & Drop
    dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        addFiles(Array.from(e.dataTransfer.files));
    });

    function addFiles(files) {
        const allowed = /\.(jpe?g|png|gif|webp|mp4|mov|avi|heic)$/i;
        files.forEach(f => {
            if (!allowed.test(f.name)) return;
            if (pendingFiles.some(p => p.name === f.name && p.size === f.size)) return; // дедупликация
            pendingFiles.push(f);
            renderQueueItem(f, 'pending');
        });
        submitBtn.disabled = pendingFiles.length === 0;
    }

    function renderQueueItem(file, status) {
        const id   = `qi-${file.name.replace(/\W/g, '_')}`;
        let el     = document.getElementById(id);
        const icon = status === 'pending' ? '📄' : status === 'loading' ? '⏳' : status === 'ok' ? '✅' : '❌';

        if (!el) {
            el            = document.createElement('div');
            el.id         = id;
            el.className  = 'queue-item';
            el.innerHTML  = `<span class="queue-item-status">${icon}</span>
                             <span class="queue-item-name">${file.name}</span>`;
            queueEl.appendChild(el);
        } else {
            el.querySelector('.queue-item-status').textContent = icon;
            el.querySelector('.queue-item-status').className   = `queue-item-status ${status}`;
        }
    }

    window.submitFiles = async function () {
        if (!pendingFiles.length) return;

        submitBtn.disabled = true;

        const toUpload = [...pendingFiles];
        pendingFiles   = [];

        for (const file of toUpload) {
            renderQueueItem(file, 'loading');
            try {
                const fd = new FormData();
                fd.append('file', file);

                const resp   = await fetch('/api/upload', { method: 'POST', body: fd });
                const result = await resp.json();
                renderQueueItem(file, result.success ? 'ok' : 'error');
            } catch {
                renderQueueItem(file, 'error');
            }
        }

        // Обновляем галерею после загрузки
        setTimeout(() => { initGallery(); }, 1000);
    };
});