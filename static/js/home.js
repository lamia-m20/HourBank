(() => {
  const hero = document.querySelector('.hero');
  const visual = document.querySelector('.visual');
  if (hero) {
    hero.style.setProperty(
      'background',
      "#1689dc url('/static/images/hourbank-hero.png') center center / cover no-repeat",
      'important'
    );
  }
  if (visual) visual.style.display = 'none';

  const header = document.getElementById('header');
  const menu = document.querySelector('.menu');
  const links = document.querySelector('.links');
  const sticky = () => header.classList.toggle('fixed', scrollY > 24);
  addEventListener('scroll', sticky, {passive:true}); sticky();
  menu?.addEventListener('click', () => { links.classList.toggle('open'); menu.setAttribute('aria-expanded', links.classList.contains('open')); });
  links?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));
  const observer = new IntersectionObserver(items => items.forEach(item => {if(item.isIntersecting){item.target.classList.add('show');observer.unobserve(item.target)}}), {threshold:.12});
  document.querySelectorAll('.reveal').forEach(item => observer.observe(item));
  document.getElementById('year').textContent = new Date().getFullYear();
})();
