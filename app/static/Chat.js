  const toggleBtn = document.getElementById('toggleBtn');
  const closeBtn = document.getElementById('closeBtn');
  const dialog = document.getElementById('dialog');

  let isOpen = false;

  function toggleDialog() {
    isOpen = !isOpen;
    dialog.classList.toggle('active', isOpen);
  }

  toggleBtn.addEventListener('click', toggleDialog);
  closeBtn.addEventListener('click', toggleDialog);

  // 點擊對話框外部關閉
  document.addEventListener('click', (e) => {
    if (isOpen && !dialog.contains(e.target) && !toggleBtn.contains(e.target)) {
      toggleDialog();
    }
  });

