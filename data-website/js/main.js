function toggleMenu() {
  const menu = document.getElementById('hiddenMenu');
  if (menu.style.right === '0px') {
    menu.style.right = '-250px';
  } else {
    menu.style.right = '0px';
  }
}

// document.querySelector('.scroll-down').addEventListener('click', function() {
//   window.scrollTo({
//     top: window.innerHeight,
//     behavior: 'smooth'
//   });
// });

// window.addEventListener('scroll', function() {
//   const scrollDown = document.querySelector('.scroll-down');
//   if (window.scrollY > 0) {
//     scrollDown.style.display = 'none';
//   } else {
//     scrollDown.style.display = 'block';
//   }
// });
document.addEventListener('DOMContentLoaded', () => {
  const cursor = document.getElementById('circle-cursor');

  let mouseX = 0, mouseY = 0;
  let cursorX = 0, cursorY = 0;

  document.addEventListener('mousemove', (event) => {
      mouseX = event.pageX;
      mouseY = event.pageY;
      cursor.classList.add('trail');
      setTimeout(() => {
        cursor.classList.remove('trail');
      }, 100);
  });

  function animateCursor() {
      cursorX += (mouseX - cursorX) * 0.05; // Ajustez ce facteur pour déplacer le curseur plus lentement
      cursorY += (mouseY - cursorY) * 0.05; // Ajustez ce facteur pour déplacer le curseur plus lentement

      cursor.style.left = `${cursorX}px`;
      cursor.style.top = `${cursorY}px`;

      requestAnimationFrame(animateCursor);
  }

  animateCursor();
});