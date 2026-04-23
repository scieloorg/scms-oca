/** Selected search result cards: hidden iframe + print(). Requires Django gettext on page. */
(function (global) {
  function printSelectedCards() {
    const rows = Array.from(document.querySelectorAll('.result-item-row')).filter(row => {
      const input = row.querySelector('.result-item__select-input');
      return input && input.checked;
    });

    if (!rows.length) {
      return;
    }

    const cards = rows
      .map(row => row.querySelector('.result-item'))
      .filter(Boolean);

    const lang = document.documentElement.getAttribute('lang') || 'pt-BR';
    const titleText = gettext('Selected results');

    const existingFrame = document.getElementById('search-print-selected-frame');
    if (existingFrame) {
      existingFrame.remove();
    }

    const frame = document.createElement('iframe');
    frame.id = 'search-print-selected-frame';
    frame.setAttribute('title', titleText);
    frame.setAttribute('aria-hidden', 'true');
    frame.style.cssText =
      'position:fixed;right:0;bottom:0;width:0;height:0;border:0;visibility:hidden;pointer-events:none;';
    document.body.appendChild(frame);

    const printWin = frame.contentWindow;
    const doc = frame.contentDocument;
    if (!printWin || !doc) {
      frame.remove();
      return;
    }

    doc.open();
    doc.write('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body></body></html>');
    doc.close();

    doc.documentElement.setAttribute('lang', lang);
    const titleEl = doc.createElement('title');
    titleEl.textContent = titleText;
    doc.head.appendChild(titleEl);

    document.querySelectorAll('link[rel="stylesheet"]').forEach(link => {
      if (!link.href) return;
      const copy = doc.createElement('link');
      copy.rel = 'stylesheet';
      copy.href = link.href;
      doc.head.appendChild(copy);
    });

    const extraStyle = doc.createElement('style');
    extraStyle.textContent = `
      body { margin: 0; padding: 1rem; background: #fff; }
      .print-selected-stack { display: flex; flex-direction: column; gap: 1rem; max-width: 100%; }
      .print-selected-stack .result-item { break-inside: avoid; page-break-inside: avoid; }
      @media print { body { padding: 0.5rem; } }
    `;
    doc.head.appendChild(extraStyle);

    const stack = doc.createElement('div');
    stack.className = 'print-selected-stack';
    cards.forEach(card => {
      stack.appendChild(doc.importNode(card, true));
    });
    doc.body.appendChild(stack);

    const removeFrame = () => {
      if (frame.parentNode) {
        frame.remove();
      }
    };

    printWin.addEventListener('afterprint', removeFrame, { once: true });
    setTimeout(removeFrame, 120000);

    let printDone = false;
    const runPrintOnce = () => {
      if (printDone) return;
      printDone = true;
      printWin.focus();
      printWin.print();
    };

    const sheetCount = doc.querySelectorAll('link[rel="stylesheet"]').length;
    if (sheetCount === 0) {
      setTimeout(runPrintOnce, 0);
      return;
    }

    let pending = sheetCount;
    const onSheetDone = () => {
      pending -= 1;
      if (pending <= 0) {
        setTimeout(runPrintOnce, 100);
      }
    };

    doc.querySelectorAll('link[rel="stylesheet"]').forEach(link => {
      link.addEventListener('load', onSheetDone);
      link.addEventListener('error', onSheetDone);
    });

    setTimeout(() => {
      if (pending > 0) {
        runPrintOnce();
      }
    }, 2000);
  }

  global.SearchResultsPrint = {
    printSelectedCards,
  };
})(typeof window !== 'undefined' ? window : this);
