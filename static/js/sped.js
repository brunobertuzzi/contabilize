"use strict";
(() => {
  // src/sped.ts
  (function initializeDebug() {
    try {
      if (!window.SPED_DEBUG) {
      }
    } catch {
    }
  })();
  function formatDate(date) {
    return date.toISOString().split("T")[0];
  }
  function formatCurrency(value) {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL"
    }).format(value);
  }
  var SUPPRESS_TOAST_ERROR_MESSAGES = ["produto(s) sem acumulador"];
  var autoSpinnerEnabled = true;
  window.sugestoesPendentes = [];
  function getSugestao(codigoItem) {
    if (!window.sugestoesPendentes) return void 0;
    return window.sugestoesPendentes.find((s) => s.codigo_item === codigoItem);
  }
  async function fetchApi(endpoint, method = "GET", data = null) {
    if (autoSpinnerEnabled && window.showSpinner) {
      window.showSpinner();
    }
    let shouldShowGlobalToast = true;
    try {
      const options = {
        method,
        headers: {
          "Content-Type": "application/json"
        }
      };
      if (data) {
        options.body = JSON.stringify(data);
      }
      const response = await fetch(endpoint, options);
      const result = await response.json();
      if (!response.ok) {
        const errorMessage = result.message || result.error || "Erro na requisi\xE7\xE3o";
        if (SUPPRESS_TOAST_ERROR_MESSAGES.some((pattern) => errorMessage.includes(pattern))) {
          shouldShowGlobalToast = false;
        }
        throw new Error(errorMessage);
      }
      return result;
    } catch (error) {
      if (shouldShowGlobalToast && window.showToast) {
        console.error("Erro na requisi\xE7\xE3o API:", error);
        window.showToast(error.message || "Erro inesperado", "danger");
      }
      throw error;
    } finally {
      if (autoSpinnerEnabled && window.hideSpinner) {
        window.hideSpinner();
      }
    }
  }
  function debounce(func, wait) {
    let timeout = null;
    return function(...args) {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        func(...args);
      }, wait);
    };
  }
  function getPagination(currentPage2, totalPages) {
    const delta = 2;
    const left = currentPage2 - delta;
    const right = currentPage2 + delta + 1;
    const range = [];
    const rangeWithDots = [];
    let l;
    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || i >= left && i < right) {
        range.push(i);
      }
    }
    for (const i of range) {
      if (l !== void 0) {
        if (i - l === 2) {
          rangeWithDots.push(l + 1);
        } else if (i - l !== 1) {
          rangeWithDots.push("...");
        }
      }
      rangeWithDots.push(i);
      l = i;
    }
    return rangeWithDots;
  }
  async function loadCfops() {
    const tbody = document.getElementById("cfopsBody");
    if (!tbody) return;
    const cfops = await fetchApi("/sped/cfops");
    tbody.innerHTML = "";
    cfops.forEach((cfop) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
      <td>${cfop.cfop}</td>
      <td>
        <div class="d-flex justify-content-center gap-1">
          <button type="button" class="btn btn-sm btn-warning edit-cfop" data-codigo="${cfop.cfop}" title="Editar CFOP">
            <i class="bi bi-pencil"></i>
          </button>
          <button type="button" class="btn btn-sm btn-danger delete-cfop" data-codigo="${cfop.cfop}" title="Excluir CFOP">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </td>
    `;
      tbody.appendChild(tr);
    });
    const cfopSelects = document.querySelectorAll('select[id$="Cfop"]');
    cfopSelects.forEach((select) => {
      const currentValue = select.value;
      select.innerHTML = '<option value="">Selecione...</option>';
      cfops.forEach((cfop) => {
        const option = document.createElement("option");
        option.value = cfop.cfop;
        option.textContent = `${cfop.cfop}`;
        select.appendChild(option);
      });
      select.value = currentValue;
    });
  }
  async function saveCfop() {
    const form = document.getElementById("cfopForm");
    const submitButton = document.getElementById("saveCfopButton");
    if (!form) return;
    form.classList.remove("was-validated");
    form.classList.add("was-validated");
    if (!form.checkValidity()) {
      return;
    }
    const codigoInput = document.getElementById("cfopCodigo");
    const originalCfopInput = document.getElementById("cfopOriginal");
    if (!codigoInput) return;
    const originalCfop = originalCfopInput?.value || "";
    const isEdit = originalCfop !== "";
    const data = {
      cfop: codigoInput.value.trim()
    };
    try {
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Salvando...';
      }
      const method = isEdit ? "PUT" : "POST";
      const endpoint = isEdit ? `/sped/cfops/${originalCfop}` : "/sped/cfops";
      const response = await fetchApi(endpoint, method, data);
      if (response.success) {
        window.showToast(response.message || "CFOP salvo com sucesso!", "success");
        const modalEl = document.getElementById("novoCfopModal");
        const modal = modalEl && window.bootstrap ? window.bootstrap.Modal.getInstance(modalEl) : null;
        if (modal) modal.hide();
        form.reset();
        form.classList.remove("was-validated");
        if (originalCfopInput) originalCfopInput.value = "";
        await loadCfops();
      } else {
        window.showToast(response.message || "Erro ao salvar CFOP", "danger");
      }
    } catch (error) {
      console.error("Erro ao salvar CFOP:", error);
      window.showToast("Erro ao cadastrar CFOP. Tente novamente.", "danger");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.innerHTML = "Salvar";
      }
    }
  }
  async function editCfop(codigo) {
    try {
      const cfop = await fetchApi(`/sped/cfops/${codigo}`);
      if (!cfop) {
        window.showToast("CFOP n\xE3o encontrado.", "danger");
        return;
      }
      const form = document.getElementById("cfopForm");
      if (form) {
        form.reset();
        form.classList.remove("was-validated");
      }
      const titleEl = document.getElementById("cfopModalTitle");
      const codigoInput = document.getElementById("cfopCodigo");
      const originalInput = document.getElementById("cfopOriginal");
      if (titleEl) titleEl.innerHTML = '<i class="bi bi-pencil me-2"></i>Editar CFOP';
      if (codigoInput) codigoInput.value = cfop.cfop;
      if (originalInput) originalInput.value = cfop.cfop;
      const modalEl = document.getElementById("novoCfopModal");
      if (modalEl && window.bootstrap) {
        const modal = new window.bootstrap.Modal(modalEl);
        modal.show();
      }
    } catch (error) {
      console.error("Erro ao editar CFOP:", error);
      window.showToast("Erro ao carregar dados do CFOP.", "danger");
    }
  }
  async function deleteCfop(codigo) {
    const message = `Voc\xEA tem certeza que deseja excluir o CFOP <strong>${codigo}</strong>?`;
    window.showConfirmModal(message, async () => {
      const response = await fetchApi(`/sped/cfops/${codigo}`, "DELETE");
      window.showToast(
        response.message || "CFOP exclu\xEDdo com sucesso!",
        response.success ? "success" : "danger"
      );
      if (response.success) await loadCfops();
    });
  }
  var listaAcumuladores = [];
  async function loadAcumuladores() {
    const searchInput = document.getElementById("searchAcumuladores");
    const search = searchInput ? searchInput.value : "";
    const acumuladores = await fetchApi(`/sped/acumuladores?search=${encodeURIComponent(search)}`);
    listaAcumuladores = acumuladores;
    const tbody = document.getElementById("acumuladoresBody");
    if (tbody) {
      tbody.innerHTML = "";
      acumuladores.forEach((acumulador) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
        <td>${acumulador.codigo}</td>
        <td>${acumulador.descricao}</td>
        <td>${acumulador.cfop || "-"}</td>
        <td>
          <div class="d-flex justify-content-center gap-1">
            <button type="button" class="btn btn-sm btn-warning edit-acumulador" data-codigo="${acumulador.codigo}" title="Editar Acumulador">
              <i class="bi bi-pencil"></i>
            </button>
            <button type="button" class="btn btn-sm btn-danger delete-acumulador" data-codigo="${acumulador.codigo}" title="Excluir Acumulador">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      `;
        tbody.appendChild(tr);
      });
    }
    const acumuladorSelects = document.querySelectorAll('select[id$="Acumulador"]');
    acumuladorSelects.forEach((select) => {
      const currentValue = select.value;
      select.innerHTML = '<option value="">Selecione...</option>';
      acumuladores.forEach((acumulador) => {
        const option = document.createElement("option");
        option.value = acumulador.codigo;
        option.textContent = `${acumulador.codigo} - ${acumulador.descricao}`;
        select.appendChild(option);
      });
      select.value = currentValue;
    });
    const bulkSelect = document.getElementById("bulkAcumuladorSelect");
    if (bulkSelect) {
      const currentValue = bulkSelect.value;
      bulkSelect.innerHTML = '<option value="">Selecione...</option>';
      acumuladores.forEach((acumulador) => {
        const option = document.createElement("option");
        option.value = acumulador.codigo;
        option.textContent = `${acumulador.codigo} - ${acumulador.descricao}`;
        bulkSelect.appendChild(option);
      });
      bulkSelect.value = currentValue;
    }
  }
  async function saveAcumulador(event) {
    if (event) event.preventDefault();
    const form = document.getElementById("acumuladorForm");
    if (!form) return;
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    const codigoInput = document.getElementById("acumuladorCodigo");
    const descInput = document.getElementById("acumuladorDescricao");
    const cfopInput = document.getElementById("acumuladorCfop");
    if (!codigoInput || !descInput || !cfopInput) return;
    const isEdit = codigoInput.readOnly;
    const data = {
      codigo: codigoInput.value.trim(),
      descricao: descInput.value.trim(),
      cfop: cfopInput.value.trim()
    };
    const method = isEdit ? "PUT" : "POST";
    const endpoint = isEdit ? `/sped/acumuladores/${data.codigo}` : "/sped/acumuladores";
    try {
      const response = await fetchApi(endpoint, method, data);
      window.showToast(response.message || "Acumulador salvo com sucesso!", response.success ? "success" : "danger");
      if (response.success) {
        const modalEl = document.getElementById("novoAcumuladorModal");
        const modal = modalEl && window.bootstrap ? window.bootstrap.Modal.getInstance(modalEl) : null;
        if (modal) modal.hide();
        form.reset();
        codigoInput.readOnly = false;
        await loadAcumuladores();
        await loadProdutos(currentPage);
      }
    } catch {
      window.showToast("Erro ao salvar acumulador.", "danger");
    }
  }
  async function editAcumulador(codigo) {
    try {
      const acumulador = await fetchApi(`/sped/acumuladores/${codigo}`);
      if (!acumulador) {
        window.showToast("Acumulador n\xE3o encontrado.", "danger");
        return;
      }
      const form = document.getElementById("acumuladorForm");
      if (form) {
        form.reset();
        form.classList.remove("was-validated");
      }
      const titleEl = document.getElementById("acumuladorModalTitle");
      const codigoInput = document.getElementById("acumuladorCodigo");
      const descInput = document.getElementById("acumuladorDescricao");
      const cfopSelect = document.getElementById("acumuladorCfop");
      if (titleEl) titleEl.innerHTML = '<i class="bi bi-pencil me-2"></i>Editar Acumulador';
      if (codigoInput) {
        codigoInput.value = acumulador.codigo;
        codigoInput.readOnly = true;
      }
      if (descInput) descInput.value = acumulador.descricao;
      if (cfopSelect && acumulador.cfop) cfopSelect.value = acumulador.cfop;
      const modalEl = document.getElementById("novoAcumuladorModal");
      if (modalEl && window.bootstrap) {
        const modal = new window.bootstrap.Modal(modalEl);
        modal.show();
      }
    } catch (error) {
      console.error("Erro ao editar acumulador:", error);
      window.showToast("Erro ao carregar dados do acumulador.", "danger");
    }
  }
  async function deleteAcumulador(codigo) {
    const message = `Voc\xEA tem certeza que deseja excluir o acumulador <strong>${codigo}</strong>?`;
    window.showConfirmModal(message, async () => {
      const response = await fetchApi(`/sped/acumuladores/${codigo}`, "DELETE");
      window.showToast(
        response.message || "Acumulador exclu\xEDdo com sucesso!",
        response.success ? "success" : "danger"
      );
      if (response.success) await loadAcumuladores();
    });
  }
  var currentPage = 1;
  var itemsPerPage = 30;
  var selectedProducts = /* @__PURE__ */ new Set();
  function updateBulkActionUI() {
    const bulkActionContainer = document.getElementById("bulkActionContainer");
    const selectedCountSpan = document.getElementById("selectedCount");
    const count = selectedProducts.size;
    if (count > 0 && selectedCountSpan && bulkActionContainer) {
      selectedCountSpan.textContent = `${count} produto(s) selecionado(s)`;
      bulkActionContainer.classList.remove("d-none");
    } else if (bulkActionContainer) {
      bulkActionContainer.classList.add("d-none");
    }
    updateSelectAllCheckbox();
  }
  function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById("selectAllProducts");
    const checkboxesOnPage = document.querySelectorAll(".product-checkbox");
    if (selectAllCheckbox) {
      selectAllCheckbox.checked = checkboxesOnPage.length > 0 && Array.from(checkboxesOnPage).every((cb) => cb.checked);
    }
  }
  async function loadProdutos(page = 1) {
    selectedProducts.clear();
    updateBulkActionUI();
    const selectAll = document.getElementById("selectAllProducts");
    if (selectAll) selectAll.checked = false;
    const filterElement = document.querySelector(
      'input[name="acumuladorFilter"]:checked'
    );
    const filter = filterElement ? filterElement.value : "todos";
    const searchInput = document.getElementById("searchProdutos");
    const search = searchInput ? searchInput.value : "";
    const response = await fetchApi(
      `/sped/produtos?page=${page}&per_page=${itemsPerPage}&filter=${encodeURIComponent(
        filter
      )}&search=${encodeURIComponent(search)}`
    );
    const tbody = document.getElementById("produtosBody");
    if (tbody) {
      tbody.innerHTML = "";
      response.items.forEach((produto) => {
        const isChecked = selectedProducts.has(produto.codigo_item);
        const tr = document.createElement("tr");
        tr.className = `${!produto.acumulador ? "table-warning" : ""}`;
        tr.dataset.codigo = produto.codigo_item;
        const acumuladorOptions = listaAcumuladores.map(
          (a) => `
          <option value="${a.codigo}" ${produto.acumulador === a.codigo ? "selected" : ""}>
              ${a.codigo} - ${a.descricao}
          </option>`
        ).join("");
        tr.innerHTML = `
        <td class="text-center">
          <input class="form-check-input product-checkbox" type="checkbox" data-codigo="${produto.codigo_item}" ${isChecked ? "checked" : ""}>
        </td>
        <td>${produto.codigo_item}</td>
        <td>${produto.descricao_item}</td>
        <td>${produto.unidade}</td>
        <td>${produto.ncm}</td>
        <td>
          <select class="form-select form-select-sm acumulador-select" data-codigo="${produto.codigo_item}">
            <option value="">Selecione...</option>
            ${acumuladorOptions}
          </select>
        </td>
      `;
        tbody.appendChild(tr);
      });
    }
    updateSelectAllCheckbox();
    const pagination = document.getElementById("produtosPagination");
    if (pagination) {
      pagination.innerHTML = "";
      const totalPages = Math.ceil(response.total / itemsPerPage);
      currentPage = page;
      if (totalPages > 1) {
        const pages = getPagination(currentPage, totalPages);
        const prevLi = document.createElement("li");
        prevLi.className = `page-item ${currentPage === 1 ? "disabled" : ""}`;
        prevLi.innerHTML = `<button class="page-link" onclick="loadProdutos(${currentPage - 1})">Anterior</button>`;
        pagination.appendChild(prevLi);
        pages.forEach((p) => {
          const li = document.createElement("li");
          if (p === "...") {
            li.className = "page-item disabled";
            li.innerHTML = '<span class="page-link">...</span>';
          } else {
            li.className = `page-item ${p === currentPage ? "active" : ""}`;
            li.innerHTML = `<button class="page-link" onclick="loadProdutos(${p})">${p}</button>`;
          }
          pagination.appendChild(li);
        });
        const nextLi = document.createElement("li");
        nextLi.className = `page-item ${currentPage === totalPages ? "disabled" : ""}`;
        nextLi.innerHTML = `<button class="page-link" onclick="loadProdutos(${currentPage + 1})">Pr\xF3ximo</button>`;
        pagination.appendChild(nextLi);
      }
    }
  }
  async function deleteProduto(codigo) {
    const message = `Voc\xEA tem certeza que deseja inativar o produto <strong>${codigo}</strong>?`;
    window.showConfirmModal(message, async () => {
      const response = await fetchApi(`/sped/produtos/${codigo}`, "DELETE");
      window.showToast(
        response.message || "Produto inativado com sucesso!",
        response.success ? "success" : "danger"
      );
      if (response.success) await loadProdutos(currentPage);
    });
  }
  async function loadVendas() {
    const vendasTable = document.getElementById("vendasTable");
    const warningDiv = document.getElementById("vendasReportWarning");
    const warningText = document.getElementById("vendasReportWarningText");
    const tbody = document.getElementById("vendasBody");
    if (!vendasTable || !tbody) return;
    tbody.innerHTML = "";
    if (warningDiv) warningDiv.classList.add("d-none");
    vendasTable.classList.remove("d-none");
    if (!window.empresaSelecionada) {
      return;
    }
    const compFilter = document.getElementById("competenciaVendasFilter");
    const competencia = compFilter ? compFilter.value : "";
    try {
      const data = await fetchApi(`/sped/vendas?competencia=${encodeURIComponent(competencia)}`);
      if (!data || data.vendas_a_vista === 0 && data.vendas_a_prazo === 0 && data.total_vendas === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center">Nenhum dado dispon\xEDvel para a compet\xEAncia selecionada.</td></tr>';
        return;
      }
      let row = tbody.insertRow();
      row.insertCell().textContent = "Vendas \xE0 Vista";
      row.insertCell().textContent = formatCurrency(data.vendas_a_vista);
      row = tbody.insertRow();
      row.insertCell().textContent = "Vendas a Prazo";
      row.insertCell().textContent = formatCurrency(data.vendas_a_prazo);
      const totalRow = tbody.insertRow();
      totalRow.className = "fw-bold";
      totalRow.insertCell().textContent = "Total de Vendas";
      totalRow.insertCell().textContent = formatCurrency(data.total_vendas);
    } catch (error) {
      if (error.message.includes("produto(s) sem acumulador") && warningDiv && warningText) {
        warningText.textContent = error.message;
        warningDiv.classList.remove("d-none");
      } else {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center">Nenhum dado dispon\xEDvel para a compet\xEAncia selecionada.</td></tr>';
        console.error("Erro ao carregar relat\xF3rio de vendas:", error);
      }
    }
  }
  function loadVendasReport() {
    const compFilter = document.getElementById("competenciaFilter");
    const competencia = compFilter ? compFilter.value : "";
    return fetchApi(`/sped/relatorio_vendas?competencia=${encodeURIComponent(competencia)}`).then((data) => {
      renderVendasTable(data);
    }).catch((error) => {
      console.error("Erro ao carregar relat\xF3rio:", error);
      renderVendasTable(null, error.message);
    });
  }
  function renderVendasTable(data, errorMessage = null) {
    const table = document.getElementById("relatorioAcumuladorTable");
    if (!table) return;
    const tbody = table.querySelector("tbody");
    const tfoot = table.querySelector("tfoot");
    const warning = document.getElementById("relatorioAcumuladorWarning");
    const warningText = document.getElementById("relatorioAcumuladorWarningText");
    table.style.display = "table";
    table.classList.remove("d-none");
    if (tbody) tbody.innerHTML = "";
    if (tfoot) tfoot.innerHTML = "";
    if (warning) warning.classList.add("d-none");
    if (errorMessage) {
      if (errorMessage.includes("produto(s) sem acumulador") && warning && warningText) {
        warningText.textContent = errorMessage;
        warning.classList.remove("d-none");
      }
      return;
    }
    if (!data || !data.acumuladores || data.acumuladores.length === 0) {
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center">Nenhum dado dispon\xEDvel para a compet\xEAncia selecionada.</td></tr>';
      }
      return;
    }
    let bodyHtml = "";
    data.acumuladores.forEach((acumulador, index) => {
      const qtdVendas = acumulador.vendas_por_data.length;
      const rowClass = index % 2 === 0 ? "table-light" : "";
      bodyHtml += `
      <tr class="acumulador-row ${rowClass}">
        <td>
          <strong>${acumulador.codigo} - ${acumulador.descricao}</strong>
          <br><small class="text-muted">${qtdVendas} dia(s) com vendas</small>
        </td>
        <td><strong>${formatCurrency(acumulador.total)}</strong></td>
        <td>
          <button class="btn btn-sm btn-outline-primary" onclick="toggleDetalhes(${index})">
            <i class="bi bi-eye"></i> Ver Detalhes
          </button>
        </td>
      </tr>
    `;
      const detailsBg = index % 2 === 0 ? "bg-light" : "bg-white";
      let detailsRows = "";
      acumulador.vendas_por_data.forEach((venda) => {
        detailsRows += `
        <tr>
          <td>${venda.data}</td>
          <td>${formatCurrency(venda.valor)}</td>
        </tr>
      `;
      });
      bodyHtml += `
      <tr id="detalhes-${index}" class="d-none detalhes-row">
        <td colspan="3" class="p-0">
          <div class="${detailsBg} border-top border-2 border-secondary">
            <div class="p-3">
              <h6 class="mb-2 text-dark"><i class="bi bi-calendar-event me-1"></i>Detalhes de Vendas por Data:</h6>
              <div class="table-responsive">
                <table class="table table-sm table-striped mb-0">
                  <thead class="table-secondary">
                    <tr><th><i class="bi bi-calendar3 me-1"></i>Data</th><th><i class="bi bi-currency-dollar me-1"></i>Valor</th></tr>
                  </thead>
                  <tbody>${detailsRows}</tbody>
                </table>
              </div>
            </div>
          </div>
        </td>
      </tr>
    `;
    });
    if (tbody) tbody.innerHTML = bodyHtml;
    if (tfoot) {
      tfoot.innerHTML = `
      <tr>
        <td colspan="2"><strong>Total Geral</strong></td>
        <td><strong>${formatCurrency(data.total_geral)}</strong></td>
      </tr>
    `;
    }
  }
  function toggleDetalhes(index) {
    const detalhesRow = document.getElementById(`detalhes-${index}`);
    const button = document.querySelector(`button[onclick="toggleDetalhes(${index})"]`);
    if (!detalhesRow || !button) return;
    if (detalhesRow.classList.contains("d-none")) {
      detalhesRow.classList.remove("d-none");
      button.innerHTML = '<i class="bi bi-eye-slash"></i> Ocultar Detalhes';
      button.classList.remove("btn-outline-primary");
      button.classList.add("btn-outline-secondary");
    } else {
      detalhesRow.classList.add("d-none");
      button.innerHTML = '<i class="bi bi-eye"></i> Ver Detalhes';
      button.classList.remove("btn-outline-secondary");
      button.classList.add("btn-outline-primary");
    }
  }
  function showCompetenciaLoading() {
    const overlay = document.getElementById("competenciaLoadingOverlay");
    if (overlay) {
      overlay.style.display = "flex";
      document.body.style.overflow = "hidden";
    }
  }
  function hideCompetenciaLoading() {
    const overlay = document.getElementById("competenciaLoadingOverlay");
    if (overlay) {
      overlay.style.display = "none";
      document.body.style.overflow = "";
    }
  }
  async function syncCompetencias(changedSelectId, newValue) {
    showCompetenciaLoading();
    const competenciaSelects = ["competenciaVendasFilter", "competenciaFilter", "competenciaCfopFilter"];
    competenciaSelects.forEach((selectId) => {
      if (selectId !== changedSelectId) {
        const select = document.getElementById(selectId);
        if (select && select.value !== newValue) {
          select.value = newValue;
        }
      }
    });
    try {
      autoSpinnerEnabled = false;
      await Promise.all([loadVendas(), loadVendasReport(), loadCfopReport()]);
    } catch (error) {
      console.error("Erro ao sincronizar compet\xEAncias:", error);
    } finally {
      hideCompetenciaLoading();
      autoSpinnerEnabled = true;
    }
  }
  async function loadCfopReport() {
    const cfopTable = document.getElementById("cfopTable");
    const warningDiv = document.getElementById("cfopReportWarning");
    const warningText = document.getElementById("cfopReportWarningText");
    const compFilter = document.getElementById("competenciaCfopFilter");
    const competencia = compFilter ? compFilter.value : "";
    if (cfopTable) {
      cfopTable.style.display = "table";
      cfopTable.classList.remove("d-none");
    }
    if (warningDiv) warningDiv.classList.add("d-none");
    const tbody = document.getElementById("cfopBody");
    const tfoot = cfopTable?.querySelector("tfoot");
    if (tbody) tbody.innerHTML = "";
    if (tfoot) tfoot.innerHTML = "";
    try {
      const timestamp = Date.now();
      const url = `/sped/relatorio_cfop?competencia=${encodeURIComponent(competencia)}&_t=${timestamp}`;
      const data = await fetchApi(url);
      if (!data || data.length === 0) {
        if (tbody) {
          tbody.innerHTML = '<tr><td colspan="2" class="text-center">Nenhum dado dispon\xEDvel para a compet\xEAncia selecionada.</td></tr>';
        }
        return;
      }
      let totalGeral = 0;
      if (tbody) {
        data.forEach((item) => {
          const row = tbody.insertRow();
          row.insertCell().textContent = `${item.cfop}`;
          row.insertCell().textContent = formatCurrency(item.total);
          totalGeral += item.total;
        });
      }
      if (tfoot) {
        const totalRow = tfoot.insertRow();
        totalRow.innerHTML = `<td>Total Geral</td><td>${formatCurrency(totalGeral)}</td>`;
      }
    } catch (error) {
      if (error.message.includes("produto(s) sem acumulador") && warningDiv && warningText) {
        warningText.textContent = error.message;
        warningDiv.classList.remove("d-none");
      } else if (tbody) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center">Erro ao carregar dados. Tente novamente.</td></tr>';
      }
    }
  }
  async function loadCompetencias() {
    try {
      const competencias = await fetchApi("/sped/competencias");
      if (!competencias || competencias.length === 0) {
        return;
      }
      const selects = ["competenciaVendasFilter", "competenciaFilter", "competenciaCfopFilter"];
      selects.forEach((selectId) => {
        const select = document.getElementById(selectId);
        if (select) {
          select.innerHTML = "";
          competencias.forEach((comp) => {
            const option = document.createElement("option");
            option.value = comp;
            option.textContent = comp;
            select.appendChild(option);
          });
        }
      });
      if (competencias.length > 0) {
        loadVendas();
        loadVendasReport();
        loadCfopReport();
      }
    } catch (error) {
      console.error("Erro ao carregar compet\xEAncias:", error);
    }
  }
  async function loadAllReports() {
    await Promise.all([loadVendas(), loadVendasReport(), loadCfopReport()]);
  }
  async function abrirModalClassificacao() {
    const modalEl = document.getElementById("classificacaoAutoModal");
    if (!modalEl || !window.bootstrap) return;
    const modal = new window.bootstrap.Modal(modalEl);
    const loadingDiv = document.getElementById("classificacaoLoading");
    const resultadoDiv = document.getElementById("classificacaoResultado");
    const alertaDiv = document.getElementById("classificacaoAlerta");
    const contadorSpan = document.getElementById("classificacaoContador");
    const tbody = document.getElementById("classificacaoBody");
    if (loadingDiv) loadingDiv.classList.remove("d-none");
    if (resultadoDiv) resultadoDiv.classList.add("d-none");
    if (alertaDiv) alertaDiv.classList.add("d-none");
    if (tbody) tbody.innerHTML = "";
    modal.show();
    try {
      const response = await fetch("/sped/classificar_produtos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const result = await response.json();
      if (loadingDiv) loadingDiv.classList.add("d-none");
      if (resultadoDiv) resultadoDiv.classList.remove("d-none");
      if (result.success) {
        if (!result.sugestoes || result.sugestoes.length === 0) {
          if (alertaDiv) {
            alertaDiv.className = "alert alert-info";
            alertaDiv.innerHTML = '<i class="bi bi-info-circle me-2"></i>Nenhuma sugest\xE3o encontrada. Cadastre mais produtos com acumuladores para criar uma base de refer\xEAncia.';
            alertaDiv.classList.remove("d-none");
          }
          document.getElementById("btnAprovarTodas")?.classList.add("d-none");
        } else {
          window.sugestoesPendentes = result.sugestoes;
          if (alertaDiv) {
            alertaDiv.className = "alert alert-success";
            alertaDiv.innerHTML = `<i class="bi bi-check-circle me-2"></i>Encontradas <strong>${result.total_sugestoes}</strong> sugest\xF5es de classifica\xE7\xE3o.`;
            alertaDiv.classList.remove("d-none");
          }
          if (contadorSpan) contadorSpan.textContent = `${result.sugestoes.length} produtos`;
          document.getElementById("btnAprovarTodas")?.classList.remove("d-none");
          renderizarTabelaClassificacao();
          loadProdutos(currentPage);
        }
      } else if (alertaDiv) {
        alertaDiv.className = "alert alert-danger";
        alertaDiv.innerHTML = `<i class="bi bi-x-circle me-2"></i>Erro: ${result.error}`;
        alertaDiv.classList.remove("d-none");
      }
    } catch (error) {
      if (loadingDiv) loadingDiv.classList.add("d-none");
      if (resultadoDiv) resultadoDiv.classList.remove("d-none");
      if (alertaDiv) {
        alertaDiv.className = "alert alert-danger";
        alertaDiv.innerHTML = `<i class="bi bi-x-circle me-2"></i>Erro ao analisar: ${error.message}`;
        alertaDiv.classList.remove("d-none");
      }
    }
  }
  function renderizarTabelaClassificacao() {
    const tbody = document.getElementById("classificacaoBody");
    if (!tbody || !window.sugestoesPendentes) return;
    tbody.innerHTML = "";
    window.sugestoesPendentes.forEach((sug) => {
      const tr = document.createElement("tr");
      tr.id = `sug-${sug.codigo_item}`;
      tr.className = "table-warning";
      tr.innerHTML = `
      <td>${sug.codigo_item}</td>
      <td>${sug.descricao}</td>
      <td>${sug.ncm || "-"}</td>
      <td>
        <div class="d-flex align-items-center gap-2">
          <span class="badge bg-secondary">Vazio</span>
          <i class="bi bi-arrow-right text-muted"></i>
          <span class="badge bg-info text-dark">
            <i class="bi bi-lightbulb me-1"></i>${sug.acumulador_sugerido}
          </span>
        </div>
        <small class="text-muted d-block mt-1">${sug.motivo || ""}</small>
      </td>
      <td>
        <div class="d-flex gap-1 justify-content-center">
          <button type="button" class="btn btn-sm btn-success" 
                  onclick="aprovarSugestaoModal('${sug.codigo_item}', '${sug.acumulador_sugerido}')"
                  title="Aprovar">
            <i class="bi bi-check-lg"></i>
          </button>
          <button type="button" class="btn btn-sm btn-danger" 
                  onclick="rejeitarSugestaoModal('${sug.codigo_item}')"
                  title="Rejeitar">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
      </td>
    `;
      tbody.appendChild(tr);
    });
    atualizarContadorModal();
  }
  async function aprovarSugestaoModal(codigoItem, acumulador) {
    try {
      const response = await fetch("/sped/aprovar_sugestao", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codigo_item: codigoItem, acumulador })
      });
      const result = await response.json();
      if (result.success) {
        if (window.sugestoesPendentes) {
          window.sugestoesPendentes = window.sugestoesPendentes.filter((s) => s.codigo_item !== codigoItem);
        }
        document.getElementById(`sug-${codigoItem}`)?.remove();
        atualizarContadorModal();
      } else {
        window.showToast(result.error, "danger");
      }
    } catch (error) {
      window.showToast("Erro ao aprovar: " + error.message, "danger");
    }
  }
  function rejeitarSugestaoModal(codigoItem) {
    if (window.sugestoesPendentes) {
      window.sugestoesPendentes = window.sugestoesPendentes.filter((s) => s.codigo_item !== codigoItem);
    }
    document.getElementById(`sug-${codigoItem}`)?.remove();
    atualizarContadorModal();
  }
  async function aprovarTodasSugestoes() {
    if (!window.sugestoesPendentes) return;
    const sugestoes = [...window.sugestoesPendentes];
    let aprovadas = 0;
    for (const sug of sugestoes) {
      try {
        const response = await fetch("/sped/aprovar_sugestao", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            codigo_item: sug.codigo_item,
            acumulador: sug.acumulador_sugerido
          })
        });
        const result = await response.json();
        if (result.success) {
          aprovadas++;
          window.sugestoesPendentes = window.sugestoesPendentes.filter(
            (s) => s.codigo_item !== sug.codigo_item
          );
        }
      } catch (error) {
        console.error("Erro ao aprovar sugest\xE3o:", sug.codigo_item, error);
      }
    }
    window.showToast(`${aprovadas} produtos classificados com sucesso!`, "success");
    renderizarTabelaClassificacao();
    await loadProdutos(1);
  }
  function atualizarContadorModal() {
    const contadorSpan = document.getElementById("classificacaoContador");
    const alertaDiv = document.getElementById("classificacaoAlerta");
    const btnAprovarTodas = document.getElementById("btnAprovarTodas");
    if (!window.sugestoesPendentes || window.sugestoesPendentes.length === 0) {
      if (contadorSpan) contadorSpan.textContent = "Todas as sugest\xF5es processadas";
      if (alertaDiv) {
        alertaDiv.className = "alert alert-info";
        alertaDiv.innerHTML = '<i class="bi bi-check-circle me-2"></i>Todas as sugest\xF5es foram processadas!';
      }
      btnAprovarTodas?.classList.add("d-none");
    } else if (contadorSpan) {
      contadorSpan.textContent = `${window.sugestoesPendentes.length} produtos pendentes`;
    }
  }
  async function aprovarSugestao(codigoItem, acumulador) {
    try {
      const response = await fetch("/sped/aprovar_sugestao", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codigo_item: codigoItem, acumulador })
      });
      const result = await response.json();
      if (result.success) {
        if (window.sugestoesPendentes) {
          window.sugestoesPendentes = window.sugestoesPendentes.filter((s) => s.codigo_item !== codigoItem);
        }
        atualizarBotaoClassificar();
        const row = document.querySelector(`tr[data-codigo="${codigoItem}"]`);
        if (row) {
          row.classList.remove("table-warning");
          const acumuladorCell = row.querySelector("td:last-child");
          if (acumuladorCell) {
            const acumuladorOptions = listaAcumuladores.map(
              (a) => `
              <option value="${a.codigo}" ${acumulador === a.codigo ? "selected" : ""}>
                  ${a.codigo} - ${a.descricao}
              </option>`
            ).join("");
            acumuladorCell.innerHTML = `
            <select class="form-select form-select-sm acumulador-select" data-codigo="${codigoItem}">
              <option value="">Selecione...</option>
              ${acumuladorOptions}
            </select>`;
          }
        }
        await Promise.all([loadVendasReport(), loadCfopReport()]);
      } else {
        window.showToast(result.error, "danger");
      }
    } catch (error) {
      window.showToast("Erro ao aprovar: " + error.message, "danger");
    }
  }
  function rejeitarSugestao(codigoItem) {
    if (window.sugestoesPendentes) {
      window.sugestoesPendentes = window.sugestoesPendentes.filter((s) => s.codigo_item !== codigoItem);
    }
    window.showToast("Sugest\xE3o rejeitada", "warning");
    atualizarBotaoClassificar();
    loadProdutos(currentPage);
  }
  function atualizarBotaoClassificar() {
    const btn = document.getElementById("btnClassificarAuto");
    if (!btn) return;
    if (window.sugestoesPendentes && window.sugestoesPendentes.length > 0) {
      btn.innerHTML = `<i class="bi bi-magic me-2"></i>Pendentes (${window.sugestoesPendentes.length})`;
      btn.classList.remove("btn-success");
      btn.classList.add("btn-warning");
    } else {
      btn.innerHTML = '<i class="bi bi-magic me-2"></i>Classificar Autom\xE1tico';
      btn.classList.remove("btn-warning");
      btn.classList.add("btn-success");
    }
  }
  async function analisarInconsistencias() {
    const modalEl = document.getElementById("inconsistenciasModal");
    if (!modalEl || !window.bootstrap) return;
    const modal = new window.bootstrap.Modal(modalEl);
    const loadingDiv = document.getElementById("inconsistenciasLoading");
    const resultadoDiv = document.getElementById("inconsistenciasResultado");
    const alertaDiv = document.getElementById("inconsistenciasAlerta");
    const tbody = document.getElementById("inconsistenciasBody");
    if (loadingDiv) loadingDiv.classList.remove("d-none");
    if (resultadoDiv) resultadoDiv.classList.add("d-none");
    if (alertaDiv) alertaDiv.classList.add("d-none");
    if (tbody) tbody.innerHTML = "";
    modal.show();
    try {
      const response = await fetch("/sped/analisar_inconsistencias");
      const result = await response.json();
      if (loadingDiv) loadingDiv.classList.add("d-none");
      if (resultadoDiv) resultadoDiv.classList.remove("d-none");
      if (result.success) {
        if (result.total === 0) {
          if (alertaDiv) {
            alertaDiv.className = "alert alert-success";
            alertaDiv.innerHTML = '<i class="bi bi-check-circle me-2"></i>Nenhuma inconsist\xEAncia encontrada! Todos os produtos similares possuem o mesmo acumulador.';
            alertaDiv.classList.remove("d-none");
          }
        } else {
          if (alertaDiv) {
            alertaDiv.className = "alert alert-warning";
            alertaDiv.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>Encontradas <strong>${result.total}</strong> poss\xEDveis inconsist\xEAncias.`;
            alertaDiv.classList.remove("d-none");
          }
          const contadorSpan = document.getElementById("inconsistenciasContador");
          if (contadorSpan) {
            contadorSpan.textContent = `${result.total} produtos com inconsist\xEAncia`;
          }
          if (tbody) {
            result.inconsistencias.forEach((inc, index) => {
              const tr = document.createElement("tr");
              tr.className = "table-warning";
              tr.id = `inc-${index}`;
              tr.innerHTML = `
              <td>${inc.produto2_codigo}</td>
              <td>${inc.produto2_descricao}</td>
              <td>${inc.produto2_ncm || "-"}</td>
              <td>
                <div class="d-flex align-items-center gap-2">
                  <span class="badge bg-danger">${inc.produto2_acumulador}</span>
                  <i class="bi bi-arrow-right text-muted"></i>
                  <span class="badge bg-info text-dark">
                    <i class="bi bi-lightbulb me-1"></i>${inc.produto1_acumulador}
                  </span>
                </div>
                <small class="text-muted d-block mt-1">${inc.similaridade}% similar a "${inc.produto1_descricao.substring(0, 30)}..."</small>
              </td>
              <td>
                <div class="d-flex gap-1 justify-content-center">
                  <button type="button" class="btn btn-sm btn-success" 
                          onclick="trocarAcumuladorInconsistencia('${inc.produto2_codigo}', '${inc.produto1_acumulador}', ${index})"
                          title="Usar ${inc.produto1_acumulador}">
                    <i class="bi bi-check-lg"></i>
                  </button>
                  <button type="button" class="btn btn-sm btn-danger" 
                          onclick="ignorarInconsistencia(${index})"
                          title="Ignorar">
                    <i class="bi bi-x-lg"></i>
                  </button>
                </div>
              </td>
            `;
              tbody.appendChild(tr);
            });
          }
        }
      } else if (alertaDiv) {
        alertaDiv.className = "alert alert-danger";
        alertaDiv.innerHTML = `<i class="bi bi-x-circle me-2"></i>Erro ao analisar: ${result.error}`;
        alertaDiv.classList.remove("d-none");
      }
    } catch (error) {
      if (loadingDiv) loadingDiv.classList.add("d-none");
      if (resultadoDiv) resultadoDiv.classList.remove("d-none");
      if (alertaDiv) {
        alertaDiv.className = "alert alert-danger";
        alertaDiv.innerHTML = `<i class="bi bi-x-circle me-2"></i>Erro ao analisar: ${error.message}`;
        alertaDiv.classList.remove("d-none");
      }
    }
  }
  async function trocarAcumuladorInconsistencia(codigoProduto, novoAcumulador, index) {
    try {
      const response = await fetch("/sped/produtos/atualizar_acumulador", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codigo: codigoProduto, acumulador: novoAcumulador })
      });
      const result = await response.json();
      if (result.success) {
        document.getElementById(`inc-${index}`)?.remove();
        const tbody = document.getElementById("inconsistenciasBody");
        const linhasRestantes = tbody ? tbody.querySelectorAll("tr.table-warning").length : 0;
        const contadorSpan = document.getElementById("inconsistenciasContador");
        if (linhasRestantes === 0) {
          const alertaDiv = document.getElementById("inconsistenciasAlerta");
          if (alertaDiv) {
            alertaDiv.className = "alert alert-success";
            alertaDiv.innerHTML = '<i class="bi bi-check-circle me-2"></i>Todas as inconsist\xEAncias foram resolvidas!';
          }
          if (contadorSpan) contadorSpan.textContent = "";
        } else if (contadorSpan) {
          contadorSpan.textContent = `${linhasRestantes} produtos restantes`;
        }
        window.showToast(`Acumulador de ${codigoProduto} alterado para ${novoAcumulador}`, "success");
      } else {
        window.showToast(result.error || "Erro ao atualizar", "danger");
      }
    } catch (error) {
      window.showToast("Erro ao trocar acumulador: " + error.message, "danger");
    }
  }
  function ignorarInconsistencia(index) {
    document.getElementById(`inc-${index}`)?.remove();
    const tbody = document.getElementById("inconsistenciasBody");
    const linhasRestantes = tbody ? tbody.querySelectorAll("tr.table-warning").length : 0;
    const contadorSpan = document.getElementById("inconsistenciasContador");
    if (linhasRestantes === 0) {
      const alertaDiv = document.getElementById("inconsistenciasAlerta");
      if (alertaDiv) {
        alertaDiv.className = "alert alert-success";
        alertaDiv.innerHTML = '<i class="bi bi-check-circle me-2"></i>Todas as inconsist\xEAncias foram processadas!';
      }
      if (contadorSpan) contadorSpan.textContent = "";
    } else if (contadorSpan) {
      contadorSpan.textContent = `${linhasRestantes} produtos restantes`;
    }
  }
  function setupCompetenciaNavigation(selectId, prevBtnId, nextBtnId) {
    const select = document.getElementById(selectId);
    const prevBtn = document.getElementById(prevBtnId);
    const nextBtn = document.getElementById(nextBtnId);
    if (!select || !prevBtn || !nextBtn) return;
    prevBtn.addEventListener("click", () => {
      if (select.selectedIndex > 0) {
        select.selectedIndex--;
        syncCompetencias(selectId, select.value);
      }
    });
    nextBtn.addEventListener("click", () => {
      if (select.selectedIndex < select.options.length - 1) {
        select.selectedIndex++;
        syncCompetencias(selectId, select.value);
      }
    });
    select.addEventListener("change", () => {
      syncCompetencias(selectId, select.value);
    });
  }
  function setupFilterListeners() {
    const searchProdutos = document.getElementById("searchProdutos");
    const searchAcumuladores = document.getElementById("searchAcumuladores");
    if (searchProdutos) {
      searchProdutos.addEventListener(
        "input",
        debounce(() => {
          loadProdutos(1);
        }, 300)
      );
    }
    const filterContainer = document.querySelector('.btn-group[role="group"]');
    if (filterContainer) {
      filterContainer.addEventListener("click", (e) => {
        const target = e.target;
        let radio = null;
        if (target.tagName === "INPUT" && target.name === "acumuladorFilter") {
          radio = target;
        } else if (target.tagName === "LABEL") {
          const forAttr = target.getAttribute("for");
          if (forAttr) radio = document.getElementById(forAttr);
        }
        if (radio) {
          setTimeout(() => {
            loadProdutos(1);
          }, 50);
        }
      });
    }
    if (searchAcumuladores) {
      searchAcumuladores.addEventListener(
        "input",
        debounce(() => {
          loadAcumuladores();
        }, 300)
      );
    }
  }
  window.formatDate = formatDate;
  window.formatCurrency = formatCurrency;
  window.loadCfops = loadCfops;
  window.saveCfop = saveCfop;
  window.editCfop = editCfop;
  window.deleteCfop = deleteCfop;
  window.loadAcumuladores = loadAcumuladores;
  window.saveAcumulador = saveAcumulador;
  window.editAcumulador = editAcumulador;
  window.deleteAcumulador = deleteAcumulador;
  window.loadProdutos = loadProdutos;
  window.deleteProduto = deleteProduto;
  window.loadVendas = loadVendas;
  window.loadVendasReport = loadVendasReport;
  window.loadCfopReport = loadCfopReport;
  window.loadCompetencias = loadCompetencias;
  window.loadAllReports = loadAllReports;
  window.toggleDetalhes = toggleDetalhes;
  window.abrirModalClassificacao = abrirModalClassificacao;
  window.aprovarSugestaoModal = aprovarSugestaoModal;
  window.rejeitarSugestaoModal = rejeitarSugestaoModal;
  window.aprovarTodasSugestoes = aprovarTodasSugestoes;
  window.aprovarSugestao = aprovarSugestao;
  window.rejeitarSugestao = rejeitarSugestao;
  window.analisarInconsistencias = analisarInconsistencias;
  window.trocarAcumuladorInconsistencia = trocarAcumuladorInconsistencia;
  window.ignorarInconsistencia = ignorarInconsistencia;
  document.addEventListener("DOMContentLoaded", async () => {
    const produtosBody = document.getElementById("produtosBody");
    if (produtosBody) {
      produtosBody.addEventListener("change", async (e) => {
        const target = e.target;
        if (target.classList.contains("product-checkbox")) {
          const input = target;
          const codigo = input.dataset.codigo;
          if (codigo) {
            if (input.checked) {
              selectedProducts.add(codigo);
            } else {
              selectedProducts.delete(codigo);
            }
            updateBulkActionUI();
          }
        }
        if (target.classList.contains("acumulador-select")) {
          const select = target;
          const codigo = select.dataset.codigo;
          const acumulador = select.value;
          if (!codigo) return;
          try {
            const response = await fetchApi(
              "/sped/produtos/atualizar_acumulador",
              "POST",
              { codigo, acumulador }
            );
            if (response.success) {
              window.showToast(response.message || "Acumulador atualizado", "success");
              const row = select.closest("tr");
              if (row) {
                if (acumulador) {
                  row.classList.remove("table-warning");
                } else {
                  row.classList.add("table-warning");
                }
              }
              await Promise.all([loadVendasReport(), loadCfopReport()]);
            }
          } catch (error) {
            console.error("Erro ao atualizar acumulador:", error);
          }
        }
      });
    }
    const selectAllCheckbox = document.getElementById("selectAllProducts");
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener("change", (e) => {
        const target = e.target;
        const checkboxes = document.querySelectorAll(".product-checkbox");
        checkboxes.forEach((cb) => {
          const codigo = cb.dataset.codigo;
          cb.checked = target.checked;
          if (codigo) {
            if (target.checked) selectedProducts.add(codigo);
            else selectedProducts.delete(codigo);
          }
        });
        updateBulkActionUI();
      });
    }
    const applyBulkBtn = document.getElementById("applyBulkAction");
    if (applyBulkBtn) {
      applyBulkBtn.addEventListener("click", async () => {
        const bulkSelect = document.getElementById("bulkAcumuladorSelect");
        const acumulador = bulkSelect ? bulkSelect.value : "";
        const productCodes = Array.from(selectedProducts);
        if (!acumulador) {
          window.showToast("Por favor, selecione um acumulador para aplicar.", "warning");
          return;
        }
        if (productCodes.length === 0) {
          window.showToast("Nenhum produto selecionado.", "warning");
          return;
        }
        try {
          const response = await fetchApi(
            "/sped/produtos/bulk_update_acumulador",
            "POST",
            { product_codes: productCodes, acumulador_code: acumulador }
          );
          window.showToast(response.message || "Produtos atualizados com sucesso!", "success");
          selectedProducts.clear();
          updateBulkActionUI();
          await Promise.all([loadProdutos(currentPage), loadVendasReport(), loadCfopReport()]);
        } catch (error) {
          console.error("Erro na atualiza\xE7\xE3o em massa:", error);
        }
      });
    }
    await Promise.all([loadCfops(), loadAcumuladores(), loadCompetencias()]);
    setupFilterListeners();
    await loadProdutos(1);
    setupCompetenciaNavigation("competenciaVendasFilter", "prevVendas", "nextVendas");
    setupCompetenciaNavigation("competenciaFilter", "prevAcumulador", "nextAcumulador");
    setupCompetenciaNavigation("competenciaCfopFilter", "prevCfop", "nextCfop");
    const submitSpedButton = document.getElementById("submitSped");
    if (submitSpedButton) {
      submitSpedButton.addEventListener("click", async () => {
        const fileInput = document.getElementById("arquivo_sped");
        if (!fileInput || !fileInput.files || !fileInput.files.length) {
          window.showToast("Por favor, selecione um arquivo SPED.", "warning");
          return;
        }
        submitSpedButton.disabled = true;
        const originalText = submitSpedButton.innerHTML;
        submitSpedButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Importando...';
        if (window.showSpinner) window.showSpinner();
        try {
          const formData = new FormData();
          formData.append("arquivo_sped", fileInput.files[0]);
          const response = await fetch("/sped/importar", {
            method: "POST",
            body: formData
          });
          const data = await response.json();
          window.showToast(data.message || data.error, data.success ? "success" : "danger");
          if (data.success) {
            const empresaSelect = document.getElementById("empresaSelect");
            const currentEmpresaId = empresaSelect ? empresaSelect.value : "";
            if (data.empresa_id && String(data.empresa_id) !== String(currentEmpresaId)) {
              window.showToast("Nova empresa identificada. Atualizando a p\xE1gina...", "success");
              setTimeout(() => {
                window.location.reload();
              }, 1500);
              return;
            }
            await Promise.all([loadCompetencias(), loadProdutos(1), loadAcumuladores()]);
            setTimeout(async () => {
              try {
                await Promise.all([loadVendas(), loadVendasReport(), loadCfopReport()]);
              } catch {
              }
            }, 1e3);
          }
          fileInput.value = "";
        } catch (error) {
          console.error("Erro ao importar arquivo:", error);
        } finally {
          if (window.hideSpinner) window.hideSpinner();
          submitSpedButton.disabled = false;
          submitSpedButton.innerHTML = originalText;
        }
      });
    }
    document.addEventListener("click", async (e) => {
      const target = e.target;
      const editCfopBtn = target.closest(".edit-cfop");
      if (editCfopBtn && editCfopBtn.dataset.codigo) {
        await editCfop(editCfopBtn.dataset.codigo);
      }
      const delCfopBtn = target.closest(".delete-cfop");
      if (delCfopBtn && delCfopBtn.dataset.codigo) {
        await deleteCfop(delCfopBtn.dataset.codigo);
      }
      const editAcumBtn = target.closest(".edit-acumulador");
      if (editAcumBtn && editAcumBtn.dataset.codigo) {
        await editAcumulador(editAcumBtn.dataset.codigo);
      }
      const delAcumBtn = target.closest(".delete-acumulador");
      if (delAcumBtn && delAcumBtn.dataset.codigo) {
        await deleteAcumulador(delAcumBtn.dataset.codigo);
      }
    });
    document.getElementById("btnClassificarAuto")?.addEventListener("click", () => {
      abrirModalClassificacao();
    });
    document.getElementById("btnAprovarTodas")?.addEventListener("click", () => {
      aprovarTodasSugestoes();
    });
    document.getElementById("btnAnalisarInconsistencias")?.addEventListener("click", () => {
      analisarInconsistencias();
    });
    const toggleFullscreenBtn = document.getElementById("toggleFullscreen");
    if (toggleFullscreenBtn) {
      toggleFullscreenBtn.addEventListener("click", () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch((err) => {
            console.error("Erro ao entrar em fullscreen:", err);
          });
          toggleFullscreenBtn.innerHTML = '<i class="bi bi-fullscreen-exit"></i>';
        } else if (document.exitFullscreen) {
          document.exitFullscreen();
          toggleFullscreenBtn.innerHTML = '<i class="bi bi-arrows-fullscreen"></i>';
        }
      });
    }
  });
})();
//# sourceMappingURL=sped.js.map
