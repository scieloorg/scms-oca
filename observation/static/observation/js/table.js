/* Observation table - DataTables, modals, copy, compare, CSV */
(function () {
  "use strict";

  function getDimensions() {
    const config = window.searchPageConfig || {};
    return Array.isArray(config.dimensions) ? config.dimensions : [];
  }

  function getDefaultDimension() {
    const config = window.searchPageConfig || {};
    return config.defaultDimension || getDimensions()[0] || {};
  }

  function getActiveDimension() {
    const config = window.searchPageConfig || {};
    const dimensions = getDimensions();
    const slug = config.activeDimensionSlug || (getDefaultDimension().slug || "");
    return dimensions.find(function (item) { return item.slug === slug; }) || getDefaultDimension();
  }

  function setActiveDimension(slug) {
    const config = window.searchPageConfig || {};
    config.activeDimensionSlug = slug;
  }

  function applyDimensionLabels() {
    const dimension = getActiveDimension();
    const rowLabel = getDisplayRowLabel(dimension.row_label || "Country");
    const colLabel = dimension.col_label || "Year";
    const tableTitle = dimension.table_title || "";
    const kpiLabel = dimension.kpi_label || "Documents";

    var titleEl = document.getElementById("observation-table-title");
    if (titleEl && tableTitle) titleEl.textContent = tableTitle;
    var kpiEl = document.getElementById("observation-kpi-label");
    if (kpiEl) kpiEl.textContent = kpiLabel;
    var rowHeader = document.getElementById("observation-row-header");
    if (rowHeader) rowHeader.textContent = rowLabel;
    var colHeader = document.getElementById("observation-col-header");
    if (colHeader) colHeader.setAttribute("data-placeholder", colLabel);
  }

  function getDisplayRowLabel(label) {
    const raw = String(label || "").trim();
    if (!raw) return "Country";
    const parts = raw.split(/\s+and\s+/i);
    return (parts[0] || raw).trim();
  }

  function buildTableParams() {
    const config = window.searchPageConfig || {};
    const dimension = getActiveDimension();
    const params = new URLSearchParams();
    if (config.dataSourceName) params.append("index_name", config.dataSourceName);
    if (config.observationPageId) params.append("page_id", config.observationPageId);
    if (dimension && dimension.slug) params.append("dimension_slug", dimension.slug);

    const searchInput = document.querySelector('.advanced-search-row[data-row-index="0"] .search-text-input');
    const fallbackSearch = searchInput ? String(searchInput.value || "").trim() : "";
    if (fallbackSearch) {
      params.append("search", fallbackSearch);
    } else if (config.initialSearchQuery) {
      params.append("search", config.initialSearchQuery);
    }

    const clauses = (typeof config.getSearchClauses === "function") ? config.getSearchClauses() : [];
    if (clauses.length > 0) params.append("search_clauses", JSON.stringify(clauses));

    const filterForm = document.getElementById("observation-filter-form");
    if (filterForm) {
      const formData = new FormData(filterForm);
      formData.forEach(function (value, key) {
        if (
          key === "csrfmiddlewaretoken" ||
          key === "search" ||
          key === "search_clauses" ||
          key === "index_name"
        ) {
          return;
        }
        if (value !== null && value !== undefined && String(value).trim() !== "") {
          params.append(key, value);
        }
      });
    }

    return params;
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString("en-US");
  }

  function parseDisplayNumber(value) {
    const normalized = String(value || "").replace(/,/g, "").replace(/[^\d-]/g, "");
    return Number(normalized) || 0;
  }

  function loadAndInitObservationTable() {
    if (!$("#observation-table").length) return;

    const tableApiEndpoint = (window.searchPageConfig || {}).tableApiEndpoint || "/observation/api/country-year-table/";
    const $loading = $("#observation-table-loading");
    const $table = $("#observation-table");
    const $error = $("#observation-table-error");

    $loading.show();
    $table.hide();
    $error.hide();

    applyDimensionLabels();
    const params = buildTableParams();
    fetch(tableApiEndpoint + "?" + params.toString())
      .then(function (r) { if (!r.ok) throw new Error("Network error"); return r.json(); })
      .then(function (data) {
        if (data.error) throw new Error(data.error);
        populateAndInitTable(data);
        $loading.hide();
        $table.show();
      })
      .catch(function (err) {
        $loading.hide();
        $error.text(err.message || "Error loading table data").show();
        $table.show();
        populateAndInitTable({ columns: [], rows: [], grand_total: 0 });
      });
  }

  function populateAndInitTable(data) {
    const columns = data.columns || [];
    const rows = data.rows || [];
    const grandTotal = data.grand_total || 0;

    const $table = $("#observation-table");
    if (typeof jQuery !== "undefined" && jQuery.fn.DataTable && $table.length && $table.hasClass("dataTable")) {
      try { $table.DataTable().destroy(); } catch (e) {}
    }

    const $kpiTotal = $("#observation-kpi-total");
    if ($kpiTotal.length) $kpiTotal.text(formatNumber(grandTotal));

    const $theadTr = $("#observation-table thead tr:first");
    const $tfootTr = $("#observation-table tfoot tr");
    const $tbody = $("#observation-table tbody");

    $theadTr.find("th.observation-year-col").remove();
    $tfootTr.find("th.observation-total-col").remove();

    const yearThs = columns.map(function (col) { return '<th class="observation-year-col">' + col + "</th>"; }).join("");
    const totalThs = columns.map(function (col) { return '<th class="observation-total-col" data-col-key="' + col + '">-</th>'; }).join("");
    $theadTr.find("th").eq(1).after(yearThs);
    $tfootTr.find("th").eq(1).after(totalThs);

    $tbody.empty();
    rows.forEach(function (row) {
      const values = row.values || {};
      let cells = '<td class="observation-select-col"><input type="checkbox" class="form-check-input observation-row-checkbox compare-row-checkbox"></td>';
      cells += '<td>' + (row.label || row.key || "") + "</td>";
      columns.forEach(function (col) {
        const v = values[col];
        cells += "<td>" + (v === 0 || v === "0" ? "-" : formatNumber(v)) + "</td>";
      });
      $tbody.append("<tr>" + cells + "</tr>");
    });

    const numberColumns = [];
    for (let i = 2; i < 2 + columns.length; i++) numberColumns.push(i);

    initObservationTableDataTable(numberColumns, columns);
  }

  function initObservationTableDataTable(numberColumns, yearColumns) {
    const activeDimension = getActiveDimension() || {};
    const rowLabel = getDisplayRowLabel(activeDimension.row_label || "Country");
    const colLabel = activeDimension.col_label || "Year";
    const valueLabel = activeDimension.value_label || "Documents";
    const rowLabelLower = String(rowLabel).toLowerCase();

    function parseDisplayNumber(value) {
      const normalized = String(value || "")
        .replace(/,/g, "")
        .replace(/[^\d-]/g, "");
      return Number(normalized) || 0;
    }

    function formatNumber(value) {
      return Number(value || 0).toLocaleString("en-US");
    }

    function normalizeRowDisplay() {
      $("#observation-table tbody tr").each(function () {
        $(this).find("td").each(function (index) {
          if (index < 2) return;
          const raw = parseDisplayNumber($(this).text());
          $(this).text(raw === 0 ? "-" : formatNumber(raw));
        });
      });
    }

    function getRowValues($row) {
      const $cells = $row.find("td");
      const country = $cells.eq(1).find(".country-name").text().trim() || $cells.eq(1).text().trim();
      const years = [];
      for (let i = 2; i < 2 + yearColumns.length; i += 1) {
        years.push($cells.eq(i).text().trim());
      }
      return [country].concat(years);
    }

    function copyRowDataToClipboard($row) {
      const values = getRowValues($row);
      if (!values.length) return;
      const parts = [rowLabel + ": " + values[0]];
      yearColumns.forEach(function (y, i) { parts.push(y + ": " + (values[i + 1] || "-")); });
      const line = parts.join(" | ");
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(line).catch(function () {});
        return;
      }
      const $temp = $("<textarea>").css({ position: "fixed", top: "-9999px", left: "-9999px" }).val(line).appendTo("body");
      $temp[0].select();
      try { document.execCommand("copy"); } catch (e) {}
      $temp.remove();
    }

    function injectCountryActions() {
      $("#observation-table tbody tr").each(function () {
        const $countryCell = $(this).find("td:eq(1)");
        if ($countryCell.find(".country-name").length) return;
        $countryCell.addClass("observation-country-cell");
        const countryName = $countryCell.text().trim();
        $countryCell.html(
          '<span class="country-name">' + countryName + '</span><button type="button" class="observation-detail-icon-btn detail-icon-btn" title="View details" aria-label="View details">&#9432;</button><button type="button" class="observation-copy-icon-btn copy-icon-btn" title="Copy row" aria-label="Copy row"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"></rect><path d="M5 15V5a2 2 0 0 1 2-2h10"></path></svg></button><span class="observation-copied-tooltip" aria-hidden="true">Copied</span>'
        );
      });
    }

    function addMissingCountries() {
      const existingCountries = new Set();
      $("#observation-table tbody tr").each(function () {
        const country = $(this).find("td:eq(1)").text().trim();
        if (country) existingCountries.add(country);
      });
      ALL_COUNTRIES.forEach(function (country, idx) {
        if (existingCountries.has(country)) return;
        const base = 60000 + (idx * 1700);
        const y2019 = base;
        const y2020 = Math.round(base * 1.08);
        const y2021 = Math.round(base * 1.16);
        const y2022 = Math.round(base * 1.23);
        const y2023 = Math.round(base * 1.31);
        const y2024 = Math.round(base * 1.39);
        const y2025 = Math.round(base * 1.47);
        $("#observation-table tbody").append(
          "<tr><td class=\"observation-select-col\"><input type=\"checkbox\" class=\"form-check-input observation-row-checkbox compare-row-checkbox\"></td><td>" + country + "</td><td>" + y2019 + "</td><td>" + y2020 + "</td><td>" + y2021 + "</td><td>" + y2022 + "</td><td>" + y2023 + "</td><td>" + y2024 + "</td><td>" + y2025 + "</td></tr>"
        );
      });
    }

    normalizeRowDisplay();
    injectCountryActions();

    const pageLength = 50;
    const columnDefs = [{ targets: 0, orderable: false, width: "48px" }, { targets: 1, width: "220px" }];
    numberColumns.forEach(function (idx) {
      columnDefs.push({ targets: idx, width: "92px" });
    });

    const table = $("#observation-table").DataTable({
      pageLength: pageLength,
      autoWidth: false,
      lengthChange: false,
      bLengthChange: false,
      layout: {
        topStart: null,
        topEnd: "search",
        bottomStart: "info",
        bottomEnd: "paging",
      },
      order: [[1, "asc"]],
      orderMulti: true,
      paging: true,
      info: true,
      columnDefs: columnDefs,
      language: {
        search: "",
        searchPlaceholder: "Type to search " + rowLabelLower + "...",
        lengthMenu: "_MENU_",
        info: "Showing _START_ to _END_ of _TOTAL_",
        paginate: { first: "First", previous: "Previous", next: "Next", last: "Last" }
      },
      infoCallback: function (settings, start, end, max, total) {
        return "Showing " + start + " to " + end + " of " + total;
      },
      footerCallback: function () {
        const api = this.api();
        numberColumns.forEach(function (columnIndex) {
          const total = api.column(columnIndex, { search: "applied" }).data().toArray().reduce(function (sum, value) {
            return sum + parseDisplayNumber(value);
          }, 0);
          $(api.column(columnIndex).footer()).html(formatNumber(total));
        });
      }
    });

    function updateInfoText() {
      const info = table.page.info();
      const $info = $("#observation-table_info, #observation-table_wrapper .dt-info").first();
      if (!$info.length) return;
      const start = info.recordsDisplay === 0 ? 0 : info.start + 1;
      const end = info.end;
      const total = info.recordsDisplay;
      $info.text("Showing " + start + " to " + end + " of " + total);
    }

    function closeColumnMenus() {
      $("#observation-table thead .observation-col-menu").removeClass("show");
    }

    function setupColumnMenus(api) {
      const defaultOrder = [1, "asc"];
      function isDefaultOrder() {
        const currentOrder = api.order() || [];
        return currentOrder.length === 1 && Number(currentOrder[0][0]) === defaultOrder[0] && currentOrder[0][1] === defaultOrder[1];
      }
      function updateClearSortButtons() {
        const disabled = isDefaultOrder();
        $("#observation-table thead .observation-col-menu-action[data-action='clear-sort']")
          .prop("disabled", disabled)
          .toggleClass("is-disabled", disabled);
      }
      function updateSortToggleButtons() {
        const currentOrder = api.order() || [];
        const orderedColumn = currentOrder.length ? Number(currentOrder[0][0]) : defaultOrder[0];
        const orderedDir = currentOrder.length ? currentOrder[0][1] : defaultOrder[1];
        $("#observation-table thead .observation-col-sort-toggle").removeClass("is-active-asc is-active-desc");
        const $active = $("#observation-table thead tr:first th").eq(orderedColumn).find(".observation-col-sort-toggle");
        if ($active.length) $active.addClass(orderedDir === "asc" ? "is-active-asc" : "is-active-desc");
      }

      const $headers = $("#observation-table thead tr:first th");
      $headers.each(function (index) {
        if (index === 0) return;
        const $th = $(this);
        if ($th.find(".observation-col-menu-toggle").length) return;
        const title = $th.text().trim();
      const isRowLabelCol = index === 1;
      const menuSearchBlock = isRowLabelCol
          ? '<div class="observation-col-menu-row"><span class="observation-col-menu-icon" aria-hidden="true">&#8645;</span><select class="observation-col-menu-select"><option value="contains">Contains</option><option value="starts">Starts with</option><option value="equals">Equals</option></select></div><div class="observation-col-menu-row"><span class="observation-col-menu-icon" aria-hidden="true">&#128269;</span><input type="text" class="observation-col-menu-input" placeholder="Search..."></div>'
          : '';
        $th.html(
          '<div class="observation-col-head">' +
            '<span class="observation-col-label">' + title + '</span>' +
            '<button type="button" class="observation-col-sort-toggle" title="Sort column" aria-label="Sort ascending">' +
              '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 13V3"></path><path d="M1.5 4.5L3 3l1.5 1.5"></path><path d="M6.5 5H13"></path><path d="M6.5 8H11.5"></path><path d="M6.5 11H10"></path></svg>' +
            '</button>' +
            '<button type="button" class="observation-col-menu-toggle" title="Column options" aria-label="Column options">&#9776;</button>' +
          '</div>' +
          '<div class="observation-col-menu">' +
            menuSearchBlock +
            '<button type="button" class="observation-col-menu-action" data-action="sort-asc"><span class="observation-col-menu-icon" aria-hidden="true">&#8593;</span><span>Sort Ascending</span></button>' +
            '<button type="button" class="observation-col-menu-action" data-action="sort-desc"><span class="observation-col-menu-icon" aria-hidden="true">&#8595;</span><span>Sort Descending</span></button>' +
            '<button type="button" class="observation-col-menu-action" data-action="clear-sort"><span class="observation-col-menu-icon" aria-hidden="true">&#10005;</span><span>Clear sort</span></button>' +
          '</div>'
        );
      });

      $("#observation-table thead").on("click", ".observation-col-menu-toggle", function (event) {
        event.preventDefault();
        event.stopPropagation();
        const $menu = $(this).closest("th").find(".observation-col-menu");
        const willOpen = !$menu.hasClass("show");
        closeColumnMenus();
        updateClearSortButtons();
        $menu.toggleClass("show", willOpen);
      });
      $("#observation-table thead").on("click", ".observation-col-menu", function (event) { event.stopPropagation(); });
      $("#observation-table thead").on("click", ".observation-col-sort-toggle", function (event) {
        event.preventDefault();
        event.stopPropagation();
        const columnIndex = $(this).closest("th").index();
        const currentOrder = api.order() || [];
        const currentColumn = currentOrder.length ? Number(currentOrder[0][0]) : defaultOrder[0];
        const currentDir = currentOrder.length ? currentOrder[0][1] : defaultOrder[1];
        if (currentColumn !== columnIndex) api.order([[columnIndex, "asc"]]).draw();
        else if (currentDir === "asc") api.order([[columnIndex, "desc"]]).draw();
        else api.order([[defaultOrder[0], defaultOrder[1]]]).draw();
      });
      $("#observation-table thead").on("keyup change", ".observation-col-menu-input, .observation-col-menu-select", function () {
        const $th = $(this).closest("th");
        const columnIndex = $th.index();
        const $input = $th.find(".observation-col-menu-input");
        const $operator = $th.find(".observation-col-menu-select");
        const rawValue = $input.val().trim();
        const operator = $operator.val();
        if (!rawValue) {
          api.column(columnIndex).search("").draw();
          return;
        }
        const escaped = $.fn.dataTable.util.escapeRegex(rawValue);
        if (operator === "equals") api.column(columnIndex).search("^" + escaped + "$", true, false).draw();
        else if (operator === "starts") api.column(columnIndex).search("^" + escaped, true, false).draw();
        else api.column(columnIndex).search(rawValue, false, true).draw();
      });
      $("#observation-table thead").on("click", ".observation-col-menu-action", function () {
        const action = $(this).data("action");
        const columnIndex = $(this).closest("th").index();
        if (action === "sort-asc") api.order([[columnIndex, "asc"]]).draw();
        else if (action === "sort-desc") api.order([[columnIndex, "desc"]]).draw();
        else if (action === "clear-sort" && !isDefaultOrder()) api.order([[1, "asc"]]).draw();
        updateClearSortButtons();
        updateSortToggleButtons();
        closeColumnMenus();
      });
      $(api.table().node()).on("order.dt", function () {
        updateClearSortButtons();
        updateSortToggleButtons();
      });
      $(document).on("click", function () { closeColumnMenus(); });
      updateClearSortButtons();
      updateSortToggleButtons();
    }
    setupColumnMenus(table);

    function updateHeaderSelectAllState() {
      const $selectAll = $("#select-all-checkbox");
      const $checkboxes = $(table.rows({ search: "applied" }).nodes()).find(".compare-row-checkbox");
      if (!$checkboxes.length) {
        $selectAll.prop("checked", false).prop("indeterminate", false).prop("disabled", true);
        return;
      }
      const checkedCount = $checkboxes.filter(":checked").length;
      $selectAll.prop("disabled", false);
      $selectAll.prop("checked", checkedCount === $checkboxes.length);
      $selectAll.prop("indeterminate", checkedCount > 0 && checkedCount < $checkboxes.length);
    }

    $("#select-all-checkbox").on("change", function () {
      const checked = $(this).is(":checked");
      $(table.rows({ search: "applied" }).nodes()).find(".compare-row-checkbox").prop("checked", checked);
      $(this).prop("indeterminate", false);
    });

    $("#observation-table tbody").on("change", ".compare-row-checkbox", function () {
      updateHeaderSelectAllState();
    });

    table.on("draw", function () {
      injectCountryActions();
      updateHeaderSelectAllState();
      updateInfoText();
    });
    updateHeaderSelectAllState();
    updateInfoText();

    const $pageLen = $("#observation-page-length");
    if ($pageLen.length) {
      $pageLen.val(String(table.page.len()));
      $pageLen.off("change.observationPageLen").on("change.observationPageLen", function () {
        const v = parseInt($(this).val(), 10);
        if (!v || v < 1) return;
        table.page.len(v).draw();
      });
    }

    const $toolbar = $("#observation-top-toolbar");
    const $searchContainer = $("#observation-table_wrapper .dt-search, #observation-table_wrapper .dataTables_filter").first();
    if ($toolbar.length) {
      $toolbar.find(".observation-search-wrap").remove();
      const $searchInput = $searchContainer.find("input[type='search']").first();
      if ($searchInput.length) {
        const $searchWrap = $("<div class=\"observation-search-wrap\"></div>");
        $searchInput.addClass("form-control");
        $searchWrap.append($searchInput);
        $toolbar.find(".observation-actions").after($searchWrap);
      }
      $searchContainer.hide();
    }

    const detailsModalEl = document.getElementById("country-detail-modal");
    const compareModalEl = document.getElementById("country-compare-modal");
    const detailsModal = detailsModalEl && window.bootstrap ? new bootstrap.Modal(detailsModalEl) : null;
    const compareModal = compareModalEl && window.bootstrap ? new bootstrap.Modal(compareModalEl) : null;

    function renderEvolutionChart(labels, values) {
      const canvas = document.getElementById("country-detail-chart");
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const dpr = window.devicePixelRatio || 1;
      const cssWidth = canvas.clientWidth || 560;
      const cssHeight = canvas.clientHeight || 220;
      canvas.width = Math.floor(cssWidth * dpr);
      canvas.height = Math.floor(cssHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cssWidth, cssHeight);

      const left = 56, right = cssWidth - 18, top = 24, bottom = cssHeight - 34;
      const width = right - left, height = bottom - top;
      const maxValue = Math.max.apply(null, values.concat([1]));
      const xStep = labels.length > 1 ? width / (labels.length - 1) : width;
      const yTicks = 5;
      const yStepValue = Math.max(1, Math.ceil((maxValue - 0) / yTicks));
      const yMax = yStepValue * yTicks;

      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, cssWidth, cssHeight);

      for (let i = 0; i <= yTicks; i += 1) {
        const yValue = i * yStepValue;
        const y = bottom - (yValue / (yMax || 1)) * height;
        ctx.strokeStyle = "#e2e8f0";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(left, y);
        ctx.lineTo(right, y);
        ctx.stroke();
        ctx.fillStyle = "#64748b";
        ctx.font = "10px Arial";
        ctx.textAlign = "right";
        ctx.fillText(formatNumber(yValue), left - 6, y + 3);
      }

      ctx.fillStyle = "#475569";
      ctx.font = "10px Arial";
      ctx.textAlign = "center";
      ctx.fillText(colLabel, (left + right) / 2, cssHeight - 4);
      ctx.save();
      ctx.translate(10, (top + bottom) / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(valueLabel, 0, 0);
      ctx.restore();

      ctx.fillStyle = "rgba(13, 110, 253, 0.10)";
      ctx.beginPath();
      values.forEach(function (value, i) {
        const x = left + i * xStep;
        const y = bottom - (value / (yMax || 1)) * height;
        if (i === 0) {
          ctx.moveTo(x, bottom);
          ctx.lineTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.lineTo(right, bottom);
      ctx.closePath();
      ctx.fill();

      ctx.strokeStyle = "#0d6efd";
      ctx.lineWidth = 2.25;
      ctx.beginPath();
      values.forEach(function (value, i) {
        const x = left + i * xStep;
        const y = bottom - (value / (yMax || 1)) * height;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();

      ctx.fillStyle = "#0d6efd";
      values.forEach(function (value, i) {
        const x = left + i * xStep;
        const y = bottom - (value / (yMax || 1)) * height;
        ctx.beginPath();
        ctx.arc(x, y, 3.1, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = "#0f172a";
        ctx.font = "10px Arial";
        ctx.textAlign = "center";
        ctx.fillText(formatNumber(value), x, y - 7);
        ctx.fillStyle = "#0d6efd";
      });

      ctx.fillStyle = "#334155";
      ctx.font = "10px Arial";
      labels.forEach(function (label, i) {
        const x = left + i * xStep;
        ctx.textAlign = "center";
        ctx.fillText(label, x, bottom + 12);
      });
    }

    function downloadDetailChartImage() {
      const canvas = document.getElementById("country-detail-chart");
      if (!canvas) return;
      const title = ($("#country-detail-title").text() || "").replace(/^Details:\s*/i, "").trim();
      const safe = title.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "");
      const filename = safe ? "detail_" + safe + ".png" : "detail_chart.png";
      const dpr = window.devicePixelRatio || 1;
      const exportScale = Math.min(6, Math.max(4, Math.ceil(dpr * 3)));
      const exportCanvas = document.createElement("canvas");
      const exportCtx = exportCanvas.getContext("2d");
      const cssWidth = canvas.clientWidth || 560;
      const cssHeight = canvas.clientHeight || 220;
      exportCanvas.width = Math.floor(cssWidth * exportScale);
      exportCanvas.height = Math.floor(cssHeight * exportScale);
      exportCtx.setTransform(exportScale, 0, 0, exportScale, 0, 0);
      exportCtx.imageSmoothingEnabled = true;
      exportCtx.imageSmoothingQuality = "high";
      exportCtx.fillStyle = "#ffffff";
      exportCtx.fillRect(0, 0, cssWidth, cssHeight);

      const labelOrder = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"];
      const modalText = $("#country-detail-body").text();
      const values = labelOrder.map(function (year) {
        const match = modalText.match(new RegExp(year + ":\\s*([0-9,.-]+)"));
        if (!match) return 0;
        return parseDisplayNumber(match[1]);
      });

      (function renderTo(ctx, labels, values, w, h) {
        const left = 56, right = w - 18, top = 24, bottom = h - 34;
        const wid = right - left, hei = bottom - top;
        const maxVal = Math.max.apply(null, values.concat([1]));
        const xStep = labels.length > 1 ? wid / (labels.length - 1) : wid;
        const yTicks = 5;
        const yStepVal = Math.max(1, Math.ceil(maxVal / yTicks));
        const yMax = yStepVal * yTicks;

        for (let i = 0; i <= yTicks; i += 1) {
          const yValue = i * yStepVal;
          const y = bottom - (yValue / (yMax || 1)) * hei;
          ctx.strokeStyle = "#e2e8f0";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(left, y);
          ctx.lineTo(right, y);
          ctx.stroke();
          ctx.fillStyle = "#64748b";
          ctx.font = "10px Arial";
          ctx.textAlign = "right";
          ctx.fillText(formatNumber(yValue), left - 6, y + 3);
        }

        ctx.fillStyle = "rgba(13, 110, 253, 0.10)";
        ctx.beginPath();
        values.forEach(function (value, i) {
          const x = left + i * xStep;
          const y = bottom - (value / (yMax || 1)) * hei;
          if (i === 0) { ctx.moveTo(x, bottom); ctx.lineTo(x, y); } else ctx.lineTo(x, y);
        });
        ctx.lineTo(right, bottom);
        ctx.closePath();
        ctx.fill();

        ctx.strokeStyle = "#0d6efd";
        ctx.lineWidth = 2.25;
        ctx.beginPath();
        values.forEach(function (value, i) {
          const x = left + i * xStep;
          const y = bottom - (value / (yMax || 1)) * hei;
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();

        ctx.fillStyle = "#0d6efd";
        values.forEach(function (value, i) {
          const x = left + i * xStep;
          const y = bottom - (value / (yMax || 1)) * hei;
          ctx.beginPath();
          ctx.arc(x, y, 3.1, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "#0f172a";
          ctx.font = "10px Arial";
          ctx.textAlign = "center";
          ctx.fillText(formatNumber(value), x, y - 7);
          ctx.fillStyle = "#0d6efd";
        });

        ctx.fillStyle = "#334155";
        ctx.font = "10px Arial";
        ctx.textAlign = "center";
        labels.forEach(function (label, i) {
          const x = left + i * xStep;
          ctx.fillText(label, x, bottom + 12);
        });
      })(exportCtx, labelOrder, values, cssWidth, cssHeight);

      exportCanvas.toBlob(function (blob) {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
      }, "image/png");
    }

    function renderComparisonChart(labels, seriesList) {
      const canvas = document.getElementById("comparison-chart");
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const dpr = window.devicePixelRatio || 1;
      const cssWidth = canvas.clientWidth || 900;
      const cssHeight = canvas.clientHeight || 260;
      canvas.width = Math.floor(cssWidth * dpr);
      canvas.height = Math.floor(cssHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cssWidth, cssHeight);

      const left = 56, right = cssWidth - 20, top = 26, bottom = cssHeight - 44;
      const width = right - left, height = bottom - top;
      const allValues = [];
      seriesList.forEach(function (s) { s.values.forEach(function (v) { allValues.push(v); }); });
      const maxValue = Math.max.apply(null, allValues.concat([1]));
      const xStep = labels.length > 1 ? width / (labels.length - 1) : width;
      const yTicks = 5;
      const yStepValue = Math.max(1, Math.ceil(maxValue / yTicks));
      const yMax = yStepValue * yTicks;

      for (let i = 0; i <= yTicks; i += 1) {
        const yValue = i * yStepValue;
        const y = bottom - (yValue / (yMax || 1)) * height;
        ctx.strokeStyle = "#e2e8f0";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(left, y);
        ctx.lineTo(right, y);
        ctx.stroke();
        ctx.fillStyle = "#64748b";
        ctx.font = "10px Arial";
        ctx.textAlign = "right";
        ctx.fillText(formatNumber(yValue), left - 6, y + 3);
      }

      labels.forEach(function (_, i) {
        const x = left + i * xStep;
        ctx.strokeStyle = "#eef2f7";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, top);
        ctx.lineTo(x, bottom);
        ctx.stroke();
      });

      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(left, top);
      ctx.lineTo(left, bottom);
      ctx.lineTo(right, bottom);
      ctx.stroke();

      const palette = ["#0d6efd", "#dc3545", "#198754", "#f59e0b", "#7c3aed", "#0ea5e9"];
      seriesList.forEach(function (series, idx) {
        const color = palette[idx % palette.length];
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        series.values.forEach(function (value, i) {
          const x = left + i * xStep;
          const y = bottom - (value / (yMax || 1)) * height;
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        });
        ctx.stroke();
        ctx.fillStyle = color;
        series.values.forEach(function (value, i) {
          const x = left + i * xStep;
          const y = bottom - (value / (yMax || 1)) * height;
          ctx.beginPath();
          ctx.arc(x, y, 2.4, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "#0f172a";
          ctx.font = "9px Arial";
          ctx.textAlign = "center";
          const yOffset = (idx % 2 === 0 ? 10 : 18);
          ctx.fillText(formatNumber(value), x, y - yOffset);
          ctx.fillStyle = color;
        });
        const peakValue = Math.max.apply(null, series.values);
        const peakIndex = series.values.indexOf(peakValue);
        const peakX = left + peakIndex * xStep;
        const peakY = bottom - (peakValue / (yMax || 1)) * height;
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(peakX, peakY, 4.2, 0, Math.PI * 2);
        ctx.stroke();
      });

      ctx.fillStyle = "#334155";
      ctx.font = "10px Arial";
      ctx.textAlign = "center";
      labels.forEach(function (label, i) {
        const x = left + i * xStep;
        ctx.fillText(label, x, bottom + 14);
      });

      ctx.fillStyle = "#475569";
      ctx.font = "10px Arial";
      ctx.textAlign = "center";
      ctx.fillText(colLabel, (left + right) / 2, cssHeight - 8);
      ctx.save();
      ctx.translate(10, (top + bottom) / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText(valueLabel, 0, 0);
      ctx.restore();

      ctx.textAlign = "left";
      ctx.font = "11px Arial";
      seriesList.forEach(function (series, idx) {
        const color = palette[idx % palette.length];
        const lastValue = series.values[series.values.length - 1] || 0;
        ctx.fillStyle = color;
        ctx.fillText("●", left + (idx * 170), 14);
        ctx.fillStyle = "#334155";
        ctx.fillText(series.country + ": " + formatNumber(lastValue), left + 10 + (idx * 170), 14);
      });
    }

    function renderComparisonInsights(labels, seriesList) {
      const $insights = $("#comparison-chart-insights");
      if (!$insights.length) return;
      const cards = seriesList.map(function (series) {
        const first = series.values[0] || 0;
        const last = series.values[series.values.length - 1] || 0;
        const peak = Math.max.apply(null, series.values);
        const low = Math.min.apply(null, series.values);
        const avg = Math.round(series.values.reduce(function (sum, v) { return sum + v; }, 0) / (series.values.length || 1));
        const growthPct = first > 0 ? (((last - first) / first) * 100) : 0;
        return '<div class="observation-comparison-insight"><strong>' + series.country + '</strong><div>Peak: ' + formatNumber(peak) + '</div><div>Lowest: ' + formatNumber(low) + '</div><div>Average: ' + formatNumber(avg) + '</div><div>Growth (' + labels[0] + '-' + labels[labels.length - 1] + '): ' + growthPct.toFixed(1) + '%</div></div>';
      }).join("");
      $insights.html(cards);
    }

    function getCheckedRowsForComparison() {
      const selected = [];
      $("#observation-table tbody tr").each(function () {
        const $row = $(this);
        if ($row.find(".compare-row-checkbox").is(":checked")) {
          const values = getRowValues($row);
          if (values.length) selected.push({ country: values[0], values: values.slice(1) });
        }
      });
      return selected;
    }

    function downloadComparisonChartImage() {
      const canvas = document.getElementById("comparison-chart");
      if (!canvas) return;
      const dpr = window.devicePixelRatio || 1;
      const exportScale = Math.min(6, Math.max(4, Math.ceil(dpr * 3)));
      const exportCanvas = document.createElement("canvas");
      const exportCtx = exportCanvas.getContext("2d");
      const cssWidth = canvas.clientWidth || 900;
      const cssHeight = canvas.clientHeight || 260;
      exportCanvas.width = Math.floor(cssWidth * exportScale);
      exportCanvas.height = Math.floor(cssHeight * exportScale);
      exportCtx.setTransform(exportScale, 0, 0, exportScale, 0, 0);
      exportCtx.imageSmoothingEnabled = true;
      exportCtx.imageSmoothingQuality = "high";
      exportCtx.fillStyle = "#ffffff";
      exportCtx.fillRect(0, 0, cssWidth, cssHeight);

      const selected = getCheckedRowsForComparison();
      const labels = yearColumns.slice();
      const series = selected.map(function (item) {
        return { country: item.country, values: item.values.map(parseDisplayNumber) };
      });

      (function renderToCtx(labels, seriesList, ctx, w, h) {
        ctx.clearRect(0, 0, w, h);
        const left = 56, right = w - 20, top = 26, bottom = h - 44;
        const wid = right - left, hei = bottom - top;
        const allV = [];
        seriesList.forEach(function (s) { s.values.forEach(function (v) { allV.push(v); }); });
        const maxVal = Math.max.apply(null, allV.concat([1]));
        const xStep = labels.length > 1 ? wid / (labels.length - 1) : wid;
        const yTicks = 5;
        const yStepVal = Math.max(1, Math.ceil(maxVal / yTicks));
        const yMax = yStepVal * yTicks;

        for (let i = 0; i <= yTicks; i += 1) {
          const yValue = i * yStepVal;
          const y = bottom - (yValue / (yMax || 1)) * hei;
          ctx.strokeStyle = "#e2e8f0";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(left, y);
          ctx.lineTo(right, y);
          ctx.stroke();
          ctx.fillStyle = "#64748b";
          ctx.font = "10px Arial";
          ctx.textAlign = "right";
          ctx.fillText(formatNumber(yValue), left - 6, y + 3);
        }

        labels.forEach(function (_, i) {
          const x = left + i * xStep;
          ctx.strokeStyle = "#eef2f7";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(x, top);
          ctx.lineTo(x, bottom);
          ctx.stroke();
        });

        ctx.strokeStyle = "#cbd5e1";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(left, top);
        ctx.lineTo(left, bottom);
        ctx.lineTo(right, bottom);
        ctx.stroke();

        const palette = ["#0d6efd", "#dc3545", "#198754", "#f59e0b", "#7c3aed", "#0ea5e9"];
        seriesList.forEach(function (series, idx) {
          const color = palette[idx % palette.length];
          ctx.strokeStyle = color;
          ctx.lineWidth = 2;
          ctx.beginPath();
          series.values.forEach(function (value, i) {
            const x = left + i * xStep;
            const y = bottom - (value / (yMax || 1)) * hei;
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          ctx.stroke();
          ctx.fillStyle = color;
          series.values.forEach(function (value, i) {
            const x = left + i * xStep;
            const y = bottom - (value / (yMax || 1)) * hei;
            ctx.beginPath();
            ctx.arc(x, y, 2.4, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = "#0f172a";
            ctx.font = "9px Arial";
            ctx.textAlign = "center";
            const yOffset = (idx % 2 === 0 ? 10 : 18);
            ctx.fillText(formatNumber(value), x, y - yOffset);
            ctx.fillStyle = color;
          });
          const peakValue = Math.max.apply(null, series.values);
          const peakIndex = series.values.indexOf(peakValue);
          const peakX = left + peakIndex * xStep;
          const peakY = bottom - (peakValue / (yMax || 1)) * hei;
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(peakX, peakY, 4.2, 0, Math.PI * 2);
          ctx.stroke();
        });

        ctx.fillStyle = "#334155";
        ctx.font = "10px Arial";
        ctx.textAlign = "center";
        labels.forEach(function (label, i) {
          const x = left + i * xStep;
          ctx.fillText(label, x, bottom + 14);
        });

        ctx.fillStyle = "#475569";
        ctx.font = "10px Arial";
        ctx.textAlign = "center";
        ctx.fillText("Year", (left + right) / 2, h - 8);
        ctx.save();
        ctx.translate(10, (top + bottom) / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText("Documents", 0, 0);
        ctx.restore();

        ctx.textAlign = "left";
        ctx.font = "11px Arial";
        seriesList.forEach(function (series, idx) {
          const color = palette[idx % palette.length];
          const lastValue = series.values[series.values.length - 1] || 0;
          ctx.fillStyle = color;
          ctx.fillText("●", left + (idx * 170), 14);
          ctx.fillStyle = "#334155";
          ctx.fillText(series.country + ": " + formatNumber(lastValue), left + 10 + (idx * 170), 14);
        });
      })(labels, series, exportCtx, cssWidth, cssHeight);

      const compareTitle = ($("#country-compare-title").text() || "").replace(/^Comparison:\s*/i, "").trim();
      const safeCountries = compareTitle.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+vs\s+/g, "_vs_").replace(/[^a-z0-9_]+/g, "_").replace(/_+/g, "_").replace(/^_+|_+$/g, "");
      const filename = safeCountries ? "comparison_" + safeCountries + ".png" : "comparison_chart.png";

      exportCanvas.toBlob(function (blob) {
        if (!blob) {
          const link = document.createElement("a");
          link.href = exportCanvas.toDataURL("image/png");
          link.download = filename;
          link.click();
          return;
        }
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
      }, "image/png");
    }

    function openComparisonModal() {
      const selected = getCheckedRowsForComparison();
      if (selected.length < 2) {
        window.alert("Select at least 2 rows using the row checkboxes.");
        return;
      }
      const labels = yearColumns.slice();
      const series = selected.map(function (item) {
        return { country: item.country, values: item.values.map(parseDisplayNumber) };
      });
      const thCells = yearColumns.map(function (y) { return "<th>" + y + "</th>"; }).join("");
      const rowsHtml = selected.map(function (item) {
        const tdCells = item.values.map(function (v) { return "<td>" + v + "</td>"; }).join("");
        return "<tr><td>" + item.country + "</td>" + tdCells + "</tr>";
      }).join("");

      $("#country-compare-title").text("Comparison: " + selected.map(function (s) { return s.country; }).join(" vs "));
      $("#country-compare-body").html(
        '<div class="table-responsive mb-3">' +
          '<table class="table table-sm table-bordered align-middle">' +
          '<thead class="table-light"><tr><th>' + rowLabel + '</th>' + thCells + '</tr></thead>' +
          '<tbody>' + rowsHtml + '</tbody></table></div>' +
        '<div class="observation-detail-chart-wrap">' +
          '<div class="observation-chart-meta">Processing date: 2026-03-17 | Source: OpenAlex</div>' +
          '<div class="observation-detail-chart-head"><strong>Evolution comparison by year</strong><button type="button" id="download-comparison-chart-btn" class="btn btn-outline-secondary btn-sm">Download chart</button></div>' +
          '<canvas id="comparison-chart" width="900" height="260"></canvas>' +
          '<div id="comparison-chart-insights" class="observation-comparison-insights"></div></div>'
      );
      if (compareModal) compareModal.show();
      setTimeout(function () {
        renderComparisonChart(labels, series);
        renderComparisonInsights(labels, series);
      }, 50);
    }

    function getRowsForDownload() {
      const selectedRows = [];
      $("#observation-table tbody tr").each(function () {
        const $row = $(this);
        if ($row.find(".compare-row-checkbox").is(":checked")) {
          const values = getRowValues($row);
          if (values.length) selectedRows.push({ country: values[0], values: values.slice(1) });
        }
      });
      return selectedRows;
    }

    function exportTableCsv() {
      const rowsToExport = getRowsForDownload();
      if (!rowsToExport.length) {
        window.alert("Select at least one row using the checkbox in the first column.");
        return;
      }
      const headers = [rowLabel].concat(yearColumns || []);
      const rows = [];
      rows.push(headers.map(function (header) { return "\"" + String(header || "").replace(/"/g, "\"\"") + "\""; }).join(","));
      rowsToExport.forEach(function (row) {
        const cols = [row.country].concat(row.values).map(function (value) { return "\"" + String(value).trim().replace(/"/g, "\"\"") + "\""; });
        rows.push(cols.join(","));
      });
      const csvContent = "\uFEFF" + rows.join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      const selectedDimensionText = $("#observation-dimension-select option:selected").text().trim();
      const dimensionLabel = String(selectedDimensionText || activeDimension.menu_label || activeDimension.table_title || activeDimension.slug || "observation")
        .trim()
        .normalize("NFD")
        .toLowerCase()
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/_+/g, "_")
        .replace(/^_+|_+$/g, "");
      link.download = (dimensionLabel || "observation") + ".csv";
      link.click();
      URL.revokeObjectURL(link.href);
    }

    $("#actions-listbox").on("change", function () {
      const action = $(this).val();
      if (!action) return;
      if (action === "compare") openComparisonModal();
      if (action === "csv") exportTableCsv();
      $(this).val("");
    });

    $(document).on("click", "#download-comparison-chart-btn", function () {
      downloadComparisonChartImage();
    });

    $("#observation-table").on("click", ".copy-icon-btn", function () {
      const $btn = $(this);
      copyRowDataToClipboard($btn.closest("tr"));
      const $cell = $btn.closest("td");
      const $tip = $cell.find(".observation-copied-tooltip").first();
      if ($tip.length) {
        $tip.addClass("show");
        clearTimeout($tip.data("hideTimer"));
        const timer = setTimeout(function () { $tip.removeClass("show"); }, 1100);
        $tip.data("hideTimer", timer);
      }
    });

    $("#observation-table").on("click", ".detail-icon-btn", function () {
      const values = getRowValues($(this).closest("tr"));
      if (!values.length) return;
      $("#country-detail-title").text("Details: " + values[0]);
      const chartLabels = yearColumns.slice();
      const chartValues = [];
      for (let i = 1; i < values.length; i++) chartValues.push(parseDisplayNumber(values[i]));
      const peak = Math.max.apply(null, chartValues.concat([0]));
      const low = Math.min.apply(null, chartValues.concat([0]));
      const avg = Math.round(chartValues.reduce(function (sum, v) { return sum + (Number(v) || 0); }, 0) / (chartValues.length || 1));
      const first = chartValues[0] || 0;
      const last = chartValues[chartValues.length - 1] || 0;
      const growthPct = first > 0 ? (((last - first) / first) * 100) : 0;
      const yearCells = yearColumns.map(function (y, i) {
        return '<div class="col-6"><strong>' + y + ':</strong> ' + (values[i + 1] || "-") + "</div>";
      }).join("");
      $("#country-detail-body").html(
        '<div class="row g-2">' +
          yearCells +
          '<div class="col-12">' +
            '<div class="observation-detail-chart-wrap">' +
              '<div class="observation-chart-meta">Processing date: 2026-03-17 | Source: OpenAlex</div>' +
              '<div class="observation-detail-chart-head"><strong>Evolution by ' + colLabel + '</strong>' +
              '<button type="button" id="download-detail-chart-btn" class="btn btn-outline-secondary btn-sm observation-chart-download-btn">Download chart</button></div>' +
              '<canvas id="country-detail-chart" width="560" height="220"></canvas>' +
              '<div class="observation-detail-insights">' +
                '<div class="observation-detail-insight"><strong>' + values[0] + '</strong>' +
                '<div>Peak: ' + formatNumber(peak) + '</div><div>Lowest: ' + formatNumber(low) + '</div>' +
                '<div>Average: ' + formatNumber(avg) + '</div><div>Growth (' + chartLabels[0] + "-" + chartLabels[chartLabels.length - 1] + '): ' + growthPct.toFixed(1) + '%</div></div>' +
              '</div></div></div></div>'
      );
      if (detailsModal) detailsModal.show();
      setTimeout(function () { renderEvolutionChart(chartLabels, chartValues); }, 50);
    });

    $(document).on("click", "#download-detail-chart-btn", function () {
      downloadDetailChartImage();
    });
  }

  if (typeof jQuery !== "undefined" && typeof jQuery.fn.DataTable !== "undefined") {
    window.loadAndInitObservationTable = loadAndInitObservationTable;
    jQuery(function () {
      const defaultDimension = getDefaultDimension();
      if (defaultDimension && defaultDimension.slug) {
        setActiveDimension(defaultDimension.slug);
      }
      const $dimensionSelect = $("#observation-dimension-select");
      if ($dimensionSelect.length) {
        $dimensionSelect.off("change.observationDimension").on("change.observationDimension", function () {
          const selectedSlug = String($(this).val() || "").trim();
          setActiveDimension(selectedSlug);
          loadAndInitObservationTable();
        });
      }
      loadAndInitObservationTable();
    });
  }
})();
