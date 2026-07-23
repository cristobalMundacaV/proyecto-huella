(() => {
  const logoPath = '/brand/carbono-zero-logo.svg';

  const applyOfficialLogo = () => {
    document
      .querySelectorAll('.cz-brand img, .cz-footer-brand img')
      .forEach((image) => {
        if (image.getAttribute('src') !== logoPath) {
          image.setAttribute('src', logoPath);
        }
      });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyOfficialLogo, { once: true });
  } else {
    applyOfficialLogo();
  }

  const observer = new MutationObserver(applyOfficialLogo);
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
