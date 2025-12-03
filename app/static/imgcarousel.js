document.addEventListener("DOMContentLoaded", () => {
  const carousel = document.querySelector(".relative.w-full.overflow-hidden > .flex");
  const slides = carousel.querySelectorAll(".min-w-full");
  const dots = document.querySelectorAll(".absolute.bottom-5 button");
  let current = 0;
  let timer;

  // 🔧 確保所有幻燈片都可見
  slides.forEach(slide => slide.classList.remove("hidden"));

  // 更新畫面
  function updateCarousel() {
    const offset = -current * 100;
    carousel.style.transform = `translateX(${offset}%)`;
    carousel.style.transition = "transform 0.7s ease-in-out";

    dots.forEach((dot, i) => {
      dot.classList.toggle("opacity-100", i === current);
      dot.classList.toggle("opacity-50", i !== current);
    });
  }

  // 下一張
  function nextSlide() {
    current = (current + 1) % slides.length;
    updateCarousel();
  }

  // 上一張
  function prevSlide() {
    current = (current - 1 + slides.length) % slides.length;
    updateCarousel();
  }

  // 點擊圓點切換
  dots.forEach((dot, i) => {
    dot.addEventListener("click", () => {
      current = i;
      updateCarousel();
      resetTimer();
    });
  });

  // 自動輪播計時器
  function resetTimer() {
    clearInterval(timer);
    timer = setInterval(nextSlide, 5000);
  }

  // ✅ 滑鼠拖曳與手機滑動支援
  let startX = 0;
  let isDragging = false;

  function startDrag(e) {
    isDragging = true;
    startX = e.type.includes("mouse") ? e.pageX : e.touches[0].clientX;
    carousel.style.transition = "none"; // 暫停動畫
    clearInterval(timer);
  }

  function moveDrag(e) {
    if (!isDragging) return;
    const x = e.type.includes("mouse") ? e.pageX : e.touches[0].clientX;
    const diff = x - startX;
    const offset = -current * 100 + (diff / carousel.offsetWidth) * 100;
    carousel.style.transform = `translateX(${offset}%)`;
  }

  function endDrag(e) {
    if (!isDragging) return;
    isDragging = false;
    const endX = e.type.includes("mouse") ? e.pageX : e.changedTouches[0].clientX;
    const diff = endX - startX;
    if (diff > 50) {
      prevSlide();
    } else if (diff < -50) {
      nextSlide();
    } else {
      updateCarousel();
    }
    resetTimer();
  }

  // 滑鼠事件
  carousel.addEventListener("mousedown", startDrag);
  carousel.addEventListener("mousemove", moveDrag);
  carousel.addEventListener("mouseup", endDrag);
  carousel.addEventListener("mouseleave", endDrag);

  // 觸控事件（手機）
  carousel.addEventListener("touchstart", startDrag);
  carousel.addEventListener("touchmove", moveDrag);
  carousel.addEventListener("touchend", endDrag);

  // 初始化
  updateCarousel();
  resetTimer();
});