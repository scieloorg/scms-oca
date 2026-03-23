(function () {
  function initRankingTopScroll(dataTableContainer) {
    if (!dataTableContainer) return;

    const scrollBody = dataTableContainer.querySelector('.dt-scroll-body');
    const scrollWrapper = dataTableContainer.querySelector('.dt-scroll');
    if (!scrollBody || !scrollWrapper) return;

    const existingTopScroll = dataTableContainer.querySelector('.dt-scroll-top');
    if (existingTopScroll) {
      existingTopScroll.remove();
    }

    const topScroll = document.createElement('div');
    topScroll.className = 'dt-scroll-top';

    const topScrollContent = document.createElement('div');
    topScrollContent.className = 'dt-scroll-top__content';
    topScroll.appendChild(topScrollContent);

    scrollWrapper.parentNode.insertBefore(topScroll, scrollWrapper);

    let isSyncing = false;

    const syncTopFromBody = () => {
      if (isSyncing) return;
      isSyncing = true;
      topScroll.scrollLeft = scrollBody.scrollLeft;
      isSyncing = false;
    };

    const syncBodyFromTop = () => {
      if (isSyncing) return;
      isSyncing = true;
      scrollBody.scrollLeft = topScroll.scrollLeft;
      isSyncing = false;
    };

    const updateTopScroll = () => {
      const tableElement = scrollBody.querySelector('table');
      const scrollWidth = tableElement ? tableElement.scrollWidth : scrollBody.scrollWidth;
      topScrollContent.style.width = `${scrollWidth}px`;
      topScroll.classList.toggle('dt-scroll-top--hidden', scrollWidth <= scrollBody.clientWidth);
      topScroll.scrollLeft = scrollBody.scrollLeft;
    };

    topScroll.addEventListener('scroll', syncBodyFromTop);
    scrollBody.addEventListener('scroll', syncTopFromBody);

    if (typeof ResizeObserver !== 'undefined') {
      const resizeObserver = new ResizeObserver(updateTopScroll);
      resizeObserver.observe(scrollBody);
      const tableElement = scrollBody.querySelector('table');
      if (tableElement) {
        resizeObserver.observe(tableElement);
      }
    } else {
      window.addEventListener('resize', updateTopScroll, { passive: true });
    }

    updateTopScroll();
    window.requestAnimationFrame(updateTopScroll);
  }

  function initRankingDataTable() {
    const tableContainer = document.getElementById('ranking-container');

    if (typeof $ === 'undefined' || !$.fn || !$.fn.DataTable) {
      if (tableContainer) {
        tableContainer.classList.remove('is-invisible');
      }
      return;
    }

    $('#ranking-table').DataTable({
      columns: [
        { type: 'num' },
        { type: 'num' },
        { type: 'string' },
        { type: 'string' },
        { type: 'string' },
        { type: 'string' },
        { type: 'string' },
        { type: 'num' },
        { type: 'num' },
        { type: 'num' },
        { type: 'num' },
        { type: 'num' },
        { type: 'num' },
      ],
      order: [[0, 'asc']],
      scrollX: true,
      pageLength: 25,
      layout: {
        topStart: {
          buttons: ['copy', 'csv'],
        },
        bottomStart: 'pageLength',
      },
      initComplete: function () {
        initRankingTopScroll(this.api().table().container());
        if (tableContainer) {
          tableContainer.classList.remove('is-invisible');
        }
      },
    });
  }

  function initJournalMetricsAppliedFiltersAutoSubmit() {
    const form = document.getElementById('journal-metrics-filter-form');
    if (!form || form.dataset.appliedFiltersAutoSubmitBound === 'true') return;

    form.addEventListener('search-gateway:filters-changed', event => {
      const reason = String(event?.detail?.reason || '').trim();
      if (reason !== 'remove-applied-filter') return;

      if (typeof form.requestSubmit === 'function') {
        form.requestSubmit();
        return;
      }

      form.submit();
    });

    form.dataset.appliedFiltersAutoSubmitBound = 'true';
  }

  document.addEventListener('DOMContentLoaded', () => {
    initRankingDataTable();
    initJournalMetricsAppliedFiltersAutoSubmit();
  });
})();
