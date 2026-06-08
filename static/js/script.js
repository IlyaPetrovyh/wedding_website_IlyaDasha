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
        if (dist <= 0) { countdownEl.textContent = "Свадьба уже началась!"; return; }
        const d = Math.floor(dist / 86_400_000);
        const h = Math.floor((dist % 86_400_000) / 3_600_000);
        const m = Math.floor((dist % 3_600_000)  /    60_000);
        countdownEl.textContent = `${d}д ${h}ч ${m}м`;
    };
    updateTimer();
    setInterval(updateTimer, 60_000);


    // ══════════════════════════════════════════
    // 3. ЛАЙТБОКС
    //    Единый для обеих каруселей.
    //    allItems[] — плоский массив всех карточек
    //    текущей сессии (заполняется при открытии).
    // ══════════════════════════════════════════
    const lightbox        = document.getElementById('lightbox');
    const lbContent       = document.getElementById('lightbox-content');
    const lbCloseBtn      = document.getElementById('lightbox-close');
    const lbPrev          = document.getElementById('lightbox-prev');
    const lbNext          = document.getElementById('lightbox-next');
    const lbCounter       = document.getElementById('lightbox-counter');

    let lbItems  = [];   // [{thumb_api, orig_api, type, name}, ...]
    let lbIndex  = 0;

    function lbOpen(items, index) {
        lbItems = items;
        lbIndex = index;
        lightbox.classList.add('open');
        document.body.style.overflow = 'hidden';
        lbRender();
    }

    function lbClose() {
        lightbox.classList.remove('open');
        document.body.style.overflow = '';
        lbContent.innerHTML = '';
        // Останавливаем видео если было
        const video = lbContent.querySelector('video');
        if (video) video.pause();
    }

    function lbRender() {
        const item = lbItems[lbIndex];
        lbContent.innerHTML = '';

        // Счётчик
        lbCounter.textContent = `${lbIndex + 1} / ${lbItems.length}`;

        // Стрелки
        lbPrev.disabled = lbIndex === 0;
        lbNext.disabled = lbIndex === lbItems.length - 1;

        if (item.type === 'video') {
            // Видео: Загружаем через модифицированный orig_api (стриминг inline)
            const video = document.createElement('video');
            video.src      = item.orig_api;
            video.controls = true;
            video.autoplay = true;
            video.playsInline = true; // Критично для корректного открытия на iOS в самом лайтбоксе

            // Стилизация для максимального заполнения контейнера лайтбокса
            video.style.maxWidth  = '100%';
            video.style.maxHeight = '82vh';
            video.style.display   = 'block';
            video.style.margin    = 'auto';

            lbContent.appendChild(video);
        } else {
            // Спиннер пока идет загрузка картинки высокого разрешения
            const spinner = document.createElement('div');
            spinner.className = 'lightbox-spinner';
            lbContent.appendChild(spinner);

            const img = document.createElement('img');
            img.alt = item.name;
            img.style.maxWidth  = '100%';
            img.style.maxHeight = '82vh';
            img.style.objectFit = 'contain';
            img.style.display   = 'block';
            img.style.margin    = 'auto';

            // Шаг 1: Сразу выводим маленькую версию (она мгновенно берется из кэша)
            img.src = item.thumb_api;
            spinner.remove();
            img.classList.add('ready');

            // Шаг 2: Параллельно загружаем оптимизированную Яндексом HD-версию (2048px)
            const fullImg = new Image();
            fullImg.src = item.large_api;
            fullImg.addEventListener('load', () => {
                img.src = fullImg.src; // Бесшовная и плавная подмена на высокое разрешение
            });

            lbContent.appendChild(img);
        }
    }

    function lbGo(delta) {
        const next = lbIndex + delta;
        if (next < 0 || next >= lbItems.length) return;
        lbIndex = next;
        lbRender();
    }

    // Кнопки
    lbCloseBtn.addEventListener('click', lbClose);
    lbPrev.addEventListener('click',  () => lbGo(-1));
    lbNext.addEventListener('click',  () => lbGo(+1));

    // Клик на фон закрывает
    lightbox.addEventListener('click', e => {
        if (e.target === lightbox || e.target === lbContent) lbClose();
    });

    // Клавиатура
    document.addEventListener('keydown', e => {
        if (!lightbox.classList.contains('open')) return;
        if (e.key === 'Escape')      lbClose();
        if (e.key === 'ArrowLeft')   lbGo(-1);
        if (e.key === 'ArrowRight')  lbGo(+1);
    });

    // Свайп в лайтбоксе
    let lbTouchX = 0;
    lightbox.addEventListener('touchstart', e => { lbTouchX = e.touches[0].clientX; }, { passive: true });
    lightbox.addEventListener('touchend',   e => {
        const dx = e.changedTouches[0].clientX - lbTouchX;
        if (Math.abs(dx) > 50) lbGo(dx < 0 ? +1 : -1);
    });


    // ══════════════════════════════════════════
    // 4. Универсальная фабрика каруселей
    // ══════════════════════════════════════════
    function createCarousel({ trackId, viewportId, prevId, nextId, dotsId, wrapperId, apiUrl, autoplayDelay = 4000 }) {

        const track    = document.getElementById(trackId);
        const viewport = document.getElementById(viewportId);
        const prevBtn  = document.getElementById(prevId);
        const nextBtn  = document.getElementById(nextId);
        const dotsEl   = document.getElementById(dotsId);

        if (!track || !viewport) {
            console.warn(`[Carousel] Не найдены элементы: track=${trackId}, viewport=${viewportId}`);
            return null;
        }

        let carouselItems = [];       // DOM-элементы карточек
        let carouselData  = [];       // исходные данные [{thumb_api, orig_api, type, ...}]
        let currentIndex  = 0;
        let itemsPerPage  = 3;
        let autoplayTimer = null;

        // ── Размеры ──────────────────────────
        function calcItemsPerPage() {
            const vw = viewport.offsetWidth;
            if (vw < 400) return 1;
            if (vw < 700) return 2;
            return 3;
        }

        function resizeItems() {
            itemsPerPage    = calcItemsPerPage();
            const gap       = 16;
            const cardWidth = (viewport.offsetWidth - gap * (itemsPerPage - 1)) / itemsPerPage;
            carouselItems.forEach(item => {
                item.style.width    = `${cardWidth}px`;
                item.style.minWidth = `${cardWidth}px`;
            });
            const maxIndex = Math.max(0, carouselItems.length - itemsPerPage);
            if (currentIndex > maxIndex) currentIndex = maxIndex;
            goTo(currentIndex, false);
            renderDots();
        }

        // ── Навигация ────────────────────────
        function goTo(index, animate = true) {
            if (!carouselItems.length) return;
            const maxIndex = Math.max(0, carouselItems.length - itemsPerPage);
            currentIndex   = Math.max(0, Math.min(index, maxIndex));
            const gap       = 16;
            const cardWidth = carouselItems[0].offsetWidth || (viewport.offsetWidth - gap * (itemsPerPage - 1)) / itemsPerPage;
            const offset    = currentIndex * (cardWidth + gap);
            track.style.transition = animate ? 'transform 0.55s cubic-bezier(0.4,0,0.2,1)' : 'none';
            track.style.transform  = `translateX(-${offset}px)`;
            if (prevBtn) prevBtn.disabled = currentIndex === 0;
            if (nextBtn) nextBtn.disabled = currentIndex >= maxIndex;
            updateDots();
        }

        // ── Точки ────────────────────────────
        function renderDots() {
            if (!dotsEl) return;
            const total = Math.max(1, carouselItems.length - itemsPerPage + 1);
            dotsEl.innerHTML = '';
            for (let i = 0; i < total; i++) {
                const dot = document.createElement('button');
                dot.className = 'carousel-dot' + (i === currentIndex ? ' active' : '');
                dot.ariaLabel = `Слайд ${i + 1}`;
                dot.addEventListener('click', () => goTo(i));
                dotsEl.appendChild(dot);
            }
        }
        function updateDots() {
            if (!dotsEl) return;
            dotsEl.querySelectorAll('.carousel-dot').forEach((d, i) =>
                d.classList.toggle('active', i === currentIndex));
        }

        // ── Автопрокрутка ────────────────────
        function startAutoplay() {
            stopAutoplay();
            autoplayTimer = setInterval(() => {
                const maxIndex = Math.max(0, carouselItems.length - itemsPerPage);
                goTo(currentIndex >= maxIndex ? 0 : currentIndex + 1);
            }, autoplayDelay);
        }
        function stopAutoplay() {
            if (autoplayTimer) { clearInterval(autoplayTimer); autoplayTimer = null; }
        }

        // ── События карусели ─────────────────
        if (prevBtn) prevBtn.addEventListener('click', () => { goTo(currentIndex - 1); stopAutoplay(); startAutoplay(); });
        if (nextBtn) nextBtn.addEventListener('click', () => { goTo(currentIndex + 1); stopAutoplay(); startAutoplay(); });

        let touchStartX = 0;
        viewport.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; stopAutoplay(); }, { passive: true });
        viewport.addEventListener('touchend',   e => {
            const dx = e.changedTouches[0].clientX - touchStartX;
            if (Math.abs(dx) > 50) goTo(dx < 0 ? currentIndex + 1 : currentIndex - 1);
            startAutoplay();
        });
        viewport.addEventListener('mouseenter', stopAutoplay);
        viewport.addEventListener('mouseleave', startAutoplay);
        window.addEventListener('resize', () => resizeItems());

        // ── Построение карточки ──────────────
        function buildCard(item, idx) {
            // DIV вместо <a> — клик открывает лайтбокс, не скачивание
            const card = document.createElement('div');
            card.className = 'gallery-item';
            card.style.cursor = 'pointer';

            // Ориентация по метаданным
            const w = item.width  || 0;
            const h = item.height || 0;
            if (w && h) card.classList.add(h > w * 1.05 ? 'portrait' : 'landscape');

            // Клик → открыть лайтбокс на нужном индексе
            card.addEventListener('click', () => lbOpen(carouselData, idx));

            const img = document.createElement('img');
            img.src           = item.thumb_api;
            img.alt           = item.name;
            img.loading       = idx < 3 ? 'eager' : 'lazy';
            img.fetchPriority = idx < 3 ? 'high'  : 'low';

            img.addEventListener('load', () => {
                card.classList.add('loaded');
                if (!w || !h) {
                    card.classList.add(img.naturalHeight > img.naturalWidth * 1.05 ? 'portrait' : 'landscape');
                    resizeItems();
                }
            }, { once: true });

            img.addEventListener('error', () => {
                card.classList.add('loaded');
                card.style.background = '#e8eee8';
                card.innerHTML += '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:2rem;opacity:.35">🖼️</div>';
            }, { once: true });

            card.appendChild(img);

            if (item.type === 'video') {
                const icon = document.createElement('div');
                icon.className = 'video-icon';
                card.appendChild(icon);
            }
            return card;
        }

        // ── Рендер галереи ───────────────────
        function renderItems(data) {
            carouselData = data;
            track.innerHTML = '';
            data.forEach((item, idx) => track.appendChild(buildCard(item, idx)));
            carouselItems = Array.from(track.querySelectorAll('.gallery-item'));
            resizeItems();
            startAutoplay();
        }

        // ── Загрузка с API ───────────────────
        async function load() {
            track.innerHTML = `
                <div class="gallery-item skeleton"></div>
                <div class="gallery-item skeleton"></div>
                <div class="gallery-item skeleton"></div>`;

            try {
                const resp   = await fetch(apiUrl);
                const result = await resp.json();

                console.log(`[Carousel ${apiUrl}] items:`, result.items?.length ?? 0);

                if (result.success && result.items && result.items.length > 0) {
                    renderItems(result.items);
                } else {
                    track.innerHTML = '';
                    const msg = document.createElement('p');
                    msg.style.cssText = 'text-align:center;color:#999;padding:60px 20px;width:100%;font-family:inherit;';
                    msg.textContent   = 'Фотографии появятся здесь в день свадьбы';
                    track.appendChild(msg);
                    if (prevBtn) prevBtn.style.display = 'none';
                    if (nextBtn) nextBtn.style.display = 'none';
                }
            } catch (err) {
                track.innerHTML = '';
                const msg = document.createElement('p');
                msg.style.cssText = 'text-align:center;color:#c00;padding:60px 20px;width:100%;';
                msg.textContent   = 'Не удалось загрузить галерею';
                track.appendChild(msg);
                console.error(`[Carousel ${apiUrl}] Ошибка:`, err);
            }
        }

        load();
        return { reload: load };
    }


    // ══════════════════════════════════════════
    // 5. Инициализация каруселей
    // ══════════════════════════════════════════

    const guestsCarousel = createCarousel({
        trackId:      'gallery-track',
        viewportId:   'carousel-viewport',
        prevId:       'prev-btn',
        nextId:       'next-btn',
        dotsId:       'carousel-dots',
        wrapperId:    'gallery-wrapper',
        apiUrl:       '/api/gallery',
        autoplayDelay: 4000,
    });

    createCarousel({
        trackId:      'couple-gallery-track',
        viewportId:   'couple-carousel-viewport',
        prevId:       'couple-prev-btn',
        nextId:       'couple-next-btn',
        dotsId:       'couple-carousel-dots',
        wrapperId:    'couple-gallery-wrapper',
        apiUrl:       '/api/gallery/couple',
        autoplayDelay: 5000,
    });


    // ══════════════════════════════════════════
    // 6. Модалка загрузки
    // ══════════════════════════════════════════
    const modal     = document.getElementById('upload-modal');
    const fileInput = document.getElementById('file-input');
    const dropZone  = document.getElementById('drop-zone');
    const queueEl   = document.getElementById('upload-queue');
    const submitBtn = document.getElementById('upload-submit');

    let pendingFiles = [];

    window.openUploadModal = function () {
        modal.classList.add('open');
        document.body.style.overflow = 'hidden';
    };
    window.closeUploadModal = function (event) {
        if (event && event.target !== modal) return;
        modal.classList.remove('open');
        document.body.style.overflow = '';
    };

    fileInput.addEventListener('change', () => { addFiles(Array.from(fileInput.files)); fileInput.value = ''; });
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
            if (pendingFiles.some(p => p.name === f.name && p.size === f.size)) return;
            pendingFiles.push(f);
            renderQueueItem(f, 'pending');
        });
        submitBtn.disabled = pendingFiles.length === 0;
    }

    function renderQueueItem(file, status) {
        const id   = `qi-${file.name.replace(/\W/g, '_')}`;
        let el     = document.getElementById(id);
        const icon = { pending: '📄', loading: '⏳', ok: '✅', error: '❌' }[status] || '📄';
        if (!el) {
            el = document.createElement('div');
            el.id        = id;
            el.className = 'queue-item';
            el.innerHTML = `<span class="queue-item-status">${icon}</span><span class="queue-item-name">${file.name}</span>`;
            queueEl.appendChild(el);
        } else {
            el.querySelector('.queue-item-status').textContent = icon;
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
        setTimeout(() => { if (guestsCarousel) guestsCarousel.reload(); }, 1500);
    };
});