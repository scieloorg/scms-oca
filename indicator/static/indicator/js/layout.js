(function () {
  const STORAGE_KEY = 'indicator:filters_hidden';

  function isDesktopViewport() {
    try {
      return !window.matchMedia || window.matchMedia('(min-width: 992px)').matches;
    } catch (error) {
      return true;
    }
  }

  function getStoredHiddenState() {
    try {
      return window.localStorage && window.localStorage.getItem(STORAGE_KEY) === '1';
    } catch (error) {
      return false;
    }
  }

  function storeHiddenState(hidden) {
    try {
      if (!window.localStorage) return;
      window.localStorage.setItem(STORAGE_KEY, hidden ? '1' : '0');
    } catch (error) {
      // Ignore storage errors (private mode, blocked cookies, etc.)
    }
  }

  function getLayoutElements() {
    const layout = document.getElementById('mainContent');
    const toggleButton = document.getElementById('indicator-filters-toggle');
    const filtersCol = document.getElementById('indicator-filters-col');
    const menuContainer = document.getElementById('menu-container');
    return { layout, toggleButton, filtersCol, menuContainer };
  }

  function isHidden(layout) {
    return !!(layout && layout.classList.contains('indicator-layout--filters-hidden'));
  }

  function resolveToggleLabels(toggleButton) {
    const showLabel = toggleButton?.dataset?.labelShow || 'Show filters';
    const hideLabel = toggleButton?.dataset?.labelHide || 'Hide filters';
    return { showLabel, hideLabel };
  }

  function updateToggleText(toggleButton, nextLabel) {
    if (!toggleButton) return;
    const labelElement = toggleButton.querySelector('.indicator-filters-toggle__text');
    if (labelElement) {
      labelElement.textContent = nextLabel;
    } else {
      toggleButton.textContent = nextLabel;
    }
    toggleButton.setAttribute('aria-label', nextLabel);
  }

  function updateToggleButton(toggleButton, hidden) {
    if (!toggleButton) return;
    const { showLabel, hideLabel } = resolveToggleLabels(toggleButton);
    const nextLabel = hidden ? showLabel : hideLabel;
    updateToggleText(toggleButton, nextLabel);
    toggleButton.setAttribute('aria-expanded', hidden ? 'false' : 'true');
  }

  function dispatchResizeSoon() {
    // Resize charts/tables after the layout changes.
    window.requestAnimationFrame(() => {
      window.setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
      }, 80);
    });
  }

  function setFiltersHidden(hidden, { persist = true, dispatchResize = true } = {}) {
    const { layout, toggleButton, filtersCol, menuContainer } = getLayoutElements();
    if (!layout) return;

    layout.classList.toggle('indicator-layout--filters-hidden', hidden);

    if (filtersCol) {
      filtersCol.setAttribute('aria-expanded', hidden ? 'false' : 'true');
    }

    if (menuContainer) {
      menuContainer.setAttribute('aria-hidden', hidden ? 'true' : 'false');
    }

    updateToggleButton(toggleButton, hidden);

    if (persist) {
      storeHiddenState(hidden);
    }

    if (dispatchResize) {
      dispatchResizeSoon();
    }
  }

  function toggleFilters() {
    if (!isDesktopViewport()) return;
    const { layout } = getLayoutElements();
    setFiltersHidden(!isHidden(layout));
  }

  document.addEventListener('DOMContentLoaded', () => {
    const { toggleButton } = getLayoutElements();
    if (!toggleButton) return;

    toggleButton.disabled = true;

    toggleButton.addEventListener('click', () => {
      toggleFilters();
    });

    const storedHidden = getStoredHiddenState();

    let readyHandled = false;
    const handleReady = () => {
      if (readyHandled) return;
      readyHandled = true;

      toggleButton.disabled = false;
      const { layout } = getLayoutElements();
      const beforeHidden = isHidden(layout);
      const nextHidden = isDesktopViewport() ? (storedHidden || beforeHidden) : false;
      setFiltersHidden(nextHidden, { persist: false, dispatchResize: nextHidden && !beforeHidden });
    };

    document.addEventListener('indicator:filters-ready', handleReady, { once: true });

    // Fallback in case the page doesn't dispatch the event.
    window.setTimeout(handleReady, 10000);

    window.addEventListener('resize', () => {
      const { layout } = getLayoutElements();
      if (!layout || isDesktopViewport()) return;
      if (isHidden(layout)) {
        setFiltersHidden(false, { persist: false });
      }
    });
  });

  window.IndicatorLayout = {
    setFiltersHidden: (hidden, opts) => setFiltersHidden(!!hidden, opts),
    hideFilters: (opts) => setFiltersHidden(true, opts),
    showFilters: (opts) => setFiltersHidden(false, opts),
    toggleFilters: (opts = {}) => {
      const { layout } = getLayoutElements();
      setFiltersHidden(!isHidden(layout), opts);
    },
  };
})();
