// main.js — логика отправки RSVP и таймер
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("rsvp-form");
  const after = document.getElementById("after-submit");
  const botLinkEl = document.getElementById("bot-link");
  const countdownEl = document.getElementById("countdown");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const first = document.getElementById("first_name").value.trim();
    const last = document.getElementById("last_name").value.trim();
    const status = form.querySelector('input[name="status"]:checked').value;

    if(!first || !last) return alert("Введите имя и фамилию");

    try {
      const res = await fetch("/rsvp", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({first_name:first, last_name:last, status:status})
      });
      const data = await res.json();
      if(data.ok){
        after.classList.remove("hidden");
        botLinkEl.href = data.bot_link;
        form.reset();
        window.scrollTo({top: after.offsetTop - 20, behavior: "smooth"});
      } else {
        alert("Ошибка: " + (data.error || "unknown"));
      }
    } catch (err) {
      alert("Ошибка сети");
      console.error(err);
    }
  });

  // Countdown
  function updateCountdown(){
    const target = new Date(CEREMONY_DATE);
    const now = new Date();
    const diff = target - now;
    if(diff <= 0){
      countdownEl.textContent = "Событие началось";
      return;
    }
    const days = Math.floor(diff / (1000*60*60*24));
    const hours = Math.floor((diff / (1000*60*60)) % 24);
    const minutes = Math.floor((diff / (1000*60)) % 60);
    const seconds = Math.floor((diff / 1000) % 60);
    countdownEl.textContent = `${days}д ${hours}ч ${minutes}м ${seconds}с`;
  }
  updateCountdown();
  setInterval(updateCountdown, 1000);

  // Подсказка: подставьте ваш iframe Яндекс в #yandex-map-iframe.src
  // пример: document.getElementById('yandex-map-iframe').src = "https://yandex.ru/map-widget/v1/?um=constructor%3A...&amp;...";

});