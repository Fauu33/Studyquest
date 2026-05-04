// StudyQuest – main.js
// Global utilities yang dipakai di semua halaman

// Auto-dismiss flash message setelah 4 detik
document.addEventListener('DOMContentLoaded', () => {
  const flash = document.getElementById('flash-msg');
  if (flash) {
    setTimeout(() => {
      flash.style.transition = 'opacity .5s';
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 500);
    }, 4000);
  }
});
