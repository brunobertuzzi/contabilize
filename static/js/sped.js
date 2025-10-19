// Funções de utilidade
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}



// List of error messages for which the global toast should be suppressed,
// as they are handled by specific warning elements on the page.
const SUPPRESS_TOAST_ERROR_MESSAGES = ["produto(s) sem acumulador"];

// Variável para controlar se o spinner deve ser mostrado automaticamente
let autoSpinnerEnabled = true;

// Funções de API
async function fetchApi(endpoint, method = 'GET', data = null) {
    if (autoSpinnerEnabled) {
        showSpinner();
    }
    let shouldShowGlobalToast = true; // Flag para controlar a exibição do toast global
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        console.log(`Fazendo requisição ${method} para ${endpoint}`, data);
        const response = await fetch(endpoint, options);
        console.log('Status da resposta:', response.status);

        const result = await response.json();
        console.log('Resultado da resposta:', result);

        if (!response.ok) {
            const errorMessage = result.message || result.error || 'Erro na requisição';
            // Check if the error message should suppress the global toast
            if (SUPPRESS_TOAST_ERROR_MESSAGES.some(pattern => errorMessage.includes(pattern))) {
                shouldShowGlobalToast = false;
            }
            throw new Error(errorMessage); // Re-throw for specific handling in calling functions
        }

        return result;
    } catch (error) {
        // Este bloco catch lida com erros de rede ou erros lançados pelo bloco try.
        // O toast global só será exibido se a flag `shouldShowGlobalToast` for verdadeira.
        if (shouldShowGlobalToast) {
            console.error('Erro na requisição API:', error);
            showToast(error.message, 'danger');
        }
        throw error; // Re-lança o erro para que a função que chamou possa tratá-lo
    } finally {
        if (autoSpinnerEnabled) {
            hideSpinner();
        }
    }
}

// Função de debounce para otimizar inputs de pesquisa
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function getPagination(currentPage, totalPages) {
    const delta = 2;
    const left = currentPage - delta;
    const right = currentPage + delta + 1;
    const range = [];
    const rangeWithDots = [];
    let l;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= left && i < right)) {
            range.push(i);
        }
    }

    for (let i of range) {
        if (l) {
            if (i - l === 2) {
                rangeWithDots.push(l + 1);
            } else if (i - l !== 1) {
                rangeWithDots.push('...');
            }
        }
        rangeWithDots.push(i);
        l = i;
    }

    return rangeWithDots;
}

// Gerenciamento de CFOPs
async function loadCfops() {
    const search = document.getElementById('searchCfops').value;

    const cfops = await fetchApi('/sped/cfops');
    const tbody = document.getElementById('cfopsBody');
    tbody.innerHTML = '';

    cfops.forEach(cfop => {
        const tr = document.createElement('tr');
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

    // Atualiza os selects de CFOP nos outros modais
    const cfopSelects = document.querySelectorAll('select[id$="Cfop"]');
    cfopSelects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '<option value="">Selecione...</option>';
        cfops.forEach(cfop => {
            const option = document.createElement('option');
            option.value = cfop.cfop;
            option.textContent = `${cfop.cfop}`;
            select.appendChild(option);
        });
        select.value = currentValue;
    });
}

async function saveCfop() {
    const form = document.getElementById('cfopForm');
    const submitButton = document.getElementById('saveCfopButton');

    // Remove classes de validação anteriores
    form.classList.remove('was-validated');

    // Adiciona classe para mostrar feedback de validação
    form.classList.add('was-validated');

    if (!form.checkValidity()) {
        return;
    }

    const codigoInput = document.getElementById('cfopCodigo');
    const originalCfop = document.getElementById('cfopOriginal').value;
    const isEdit = originalCfop !== '';

    const data = {
        cfop: codigoInput.value.trim()
    };

    console.log('Dados do CFOP a serem enviados:', data);
    console.log('É edição?', isEdit);
    console.log('CFOP original:', originalCfop);

    try {
        // Desabilita o botão durante o envio
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Salvando...';
        }

        console.log('Enviando dados do CFOP:', data);
        const method = isEdit ? 'PUT' : 'POST';
        const endpoint = isEdit ? `/sped/cfops/${originalCfop}` : '/sped/cfops';
        console.log('Método:', method);
        console.log('Endpoint:', endpoint);
        const response = await fetchApi(endpoint, method, data);
        console.log('Resposta recebida:', response);

        if (response.success) {
            showToast(response.message, 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('novoCfopModal'));
            modal.hide();
            form.reset();
            form.classList.remove('was-validated');
            document.getElementById('cfopOriginal').value = '';
            // Recarrega a lista de CFOPs
            await loadCfops();
        } else {
            showToast(response.message, 'danger');
        }
    } catch (error) {
        console.error('Erro ao salvar CFOP:', error);
        showToast('Erro ao cadastrar CFOP. Tente novamente.', 'danger');
    } finally {
        // Reabilita o botão após o envio
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = 'Salvar';
        }
    }
}

async function editCfop(codigo) {
    try {
        const cfop = await fetchApi(`/sped/cfops/${codigo}`);
        if (!cfop) {
            showToast('CFOP não encontrado.', 'danger');
            return;
        }

        // Limpa o formulário primeiro
        const form = document.getElementById('cfopForm');
        form.reset();
        form.classList.remove('was-validated');

        // Preenche os campos
        document.getElementById('cfopModalTitle').innerHTML = '<i class="bi bi-pencil me-2"></i>Editar CFOP';
        document.getElementById('cfopCodigo').value = cfop.cfop;
        document.getElementById('cfopOriginal').value = cfop.cfop; // Armazena o código original


        // Abre o modal
        const modal = new bootstrap.Modal(document.getElementById('novoCfopModal'));
        modal.show();
    } catch (error) {
        console.error('Erro ao editar CFOP:', error);
        showToast('Erro ao carregar dados do CFOP.', 'danger');
    }
}

async function deleteCfop(codigo) {
    const message = `Tem certeza que deseja excluir o CFOP <strong>${codigo}</strong>?`;
    showConfirmModal(message, async () => {
        const response = await fetchApi(`/sped/cfops/${codigo}`, 'DELETE');
        showToast(response.message || 'CFOP excluído com sucesso!', response.success ? 'success' : 'danger');
        if (response.success) await loadCfops();
    });
}

let listaAcumuladores = [];

// Gerenciamento de Acumuladores
async function loadAcumuladores() {
    const search = document.getElementById('searchAcumuladores').value;
    const acumuladores = await fetchApi(`/sped/acumuladores?search=${search}`);
    listaAcumuladores = acumuladores; // Armazena na variável global
    const tbody = document.getElementById('acumuladoresBody');
    tbody.innerHTML = '';

    acumuladores.forEach(acumulador => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${acumulador.codigo}</td>
            <td>${acumulador.descricao}</td>
            <td>${acumulador.cfop}</td>
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

    // Atualiza os selects de Acumulador em toda a página (modais e ações em massa)
    const acumuladorSelects = document.querySelectorAll('select[id$="Acumulador"]');
    acumuladorSelects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = '<option value="">Selecione...</option>';
        acumuladores.forEach(acumulador => {
            const option = document.createElement('option');
            option.value = acumulador.codigo;
            option.textContent = `${acumulador.codigo} - ${acumulador.descricao}`;
            select.appendChild(option);
        });
        select.value = currentValue;
    });

    // Explicitamente atualiza o select de ação em massa
    const bulkAcumuladorSelect = document.getElementById('bulkAcumuladorSelect');
    if (bulkAcumuladorSelect) {
        const currentValue = bulkAcumuladorSelect.value;
        bulkAcumuladorSelect.innerHTML = '<option value="">Selecione...</option>';
        acumuladores.forEach(acumulador => {
            const option = document.createElement('option');
            option.value = acumulador.codigo;
            option.textContent = `${acumulador.codigo} - ${acumulador.descricao}`;
            bulkAcumuladorSelect.appendChild(option);
        });
        bulkAcumuladorSelect.value = currentValue;
    }
}

async function saveAcumulador(event) {
    event.preventDefault();
    const form = document.getElementById('acumuladorForm');

    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const codigoInput = document.getElementById('acumuladorCodigo');
    const isEdit = codigoInput.readOnly;

    const data = {
        codigo: codigoInput.value,
        descricao: document.getElementById('acumuladorDescricao').value,
        cfop: document.getElementById('acumuladorCfop').value
    };

    const method = isEdit ? 'PUT' : 'POST';
    const endpoint = isEdit ? `/sped/acumuladores/${data.codigo}` : '/sped/acumuladores';

    try {
        const response = await fetchApi(endpoint, method, data);
        showToast(response.message, response.success ? 'success' : 'danger');

        if (response.success) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('novoAcumuladorModal'));
            modal.hide();
            form.reset();
            codigoInput.readOnly = false;

            await loadAcumuladores();
            await loadProdutos(currentPage);
        }
    } catch (error) {
        showToast('Erro ao salvar acumulador.', 'danger');
    }
}

async function editAcumulador(codigo) {
    try {
        const acumulador = await fetchApi(`/sped/acumuladores/${codigo}`);
        if (!acumulador) {
            showToast('Acumulador não encontrado.', 'danger');
            return;
        }

        // Limpa o formulário primeiro
        const form = document.getElementById('acumuladorForm');
        form.reset();
        form.classList.remove('was-validated');

        // Preenche os campos
        document.getElementById('acumuladorModalTitle').innerHTML = '<i class="bi bi-pencil me-2"></i>Editar Acumulador';
        document.getElementById('acumuladorCodigo').value = acumulador.codigo;
        document.getElementById('acumuladorCodigo').readOnly = true;
        document.getElementById('acumuladorDescricao').value = acumulador.descricao;
        document.getElementById('acumuladorCfop').value = acumulador.cfop;

        // Abre o modal
        const modal = new bootstrap.Modal(document.getElementById('novoAcumuladorModal'));
        modal.show();
    } catch (error) {
        console.error('Erro ao editar acumulador:', error);
        showToast('Erro ao carregar dados do acumulador.', 'danger');
    }
}
async function deleteAcumulador(codigo) {
    const message = `Tem certeza que deseja excluir o acumulador <strong>${codigo}</strong>?`;
    showConfirmModal(message, async () => {
        const response = await fetchApi(`/sped/acumuladores/${codigo}`, 'DELETE');
        showToast(response.message || 'Acumulador excluído com sucesso!', response.success ? 'success' : 'danger');
        if (response.success) await loadAcumuladores();
        // loadProdutos() é chamado dentro de loadAcumuladores se necessário
    });
}

// Gerenciamento de Produtos
let currentPage = 1;
const itemsPerPage = 30;

async function loadProdutos(page = 1) {
    console.log('=== loadProdutos chamada ===');
    console.log('Página:', page);

    // Limpa a seleção ao carregar uma nova página ou aplicar um filtro
    selectedProducts.clear();
    updateBulkActionUI();
    document.getElementById('selectAllProducts').checked = false;

    const filterElement = document.querySelector('input[name="acumuladorFilter"]:checked');
    const filter = filterElement ? filterElement.value : 'todos';
    const search = document.getElementById('searchProdutos').value;

    console.log('Filtro selecionado:', filter);
    console.log('Pesquisa:', search);

    const response = await fetchApi(`/sped/produtos?page=${page}&per_page=${itemsPerPage}&filter=${filter}&search=${search}`);
    const tbody = document.getElementById('produtosBody');
    tbody.innerHTML = '';

    response.items.forEach(produto => {
        const isChecked = selectedProducts.has(produto.codigo_item);
        const tr = document.createElement('tr');
        tr.className = `${!produto.acumulador ? 'table-warning' : ''}`;
        tr.innerHTML = `
            <td class="text-center"><input class="form-check-input product-checkbox" type="checkbox" data-codigo="${produto.codigo_item}" ${isChecked ? 'checked' : ''}></td>
            <td>${produto.codigo_item}</td>
            <td>${produto.descricao_item}</td>
            <td>${produto.unidade}</td>
            <td>${produto.ncm}</td>
            <td>
                <select class="form-select form-select-sm acumulador-select" 
                        data-codigo="${produto.codigo_item}">
                    <option value="">Selecione...</option>
                    ${listaAcumuladores.map(a => `
                        <option value="${a.codigo}" ${produto.acumulador === a.codigo ? 'selected' : ''}>
                            ${a.codigo} - ${a.descricao}
                        </option>
                    `).join('')}
                </select>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Garante que o estado do "selecionar todos" reflita a página atual
    updateSelectAllCheckbox();

    // Atualiza a paginação
    const pagination = document.getElementById('produtosPagination');
    pagination.innerHTML = '';
    const totalPages = Math.ceil(response.total / itemsPerPage);
    currentPage = page;

    if (totalPages > 1) {
        const pages = getPagination(currentPage, totalPages);

        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `<button class="page-link" onclick="loadProdutos(${currentPage - 1})">Anterior</button>`;
        pagination.appendChild(prevLi);

        pages.forEach(p => {
            const li = document.createElement('li');
            if (p === '...') {
                li.className = 'page-item disabled';
                li.innerHTML = `<span class="page-link">...</span>`;
            } else {
                li.className = `page-item ${p === currentPage ? 'active' : ''}`;
                li.innerHTML = `<button class="page-link" onclick="loadProdutos(${p})">${p}</button>`;
            }
            pagination.appendChild(li);
        });

        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = `<button class="page-link" onclick="loadProdutos(${currentPage + 1})">Próximo</button>`;
        pagination.appendChild(nextLi);
    }
}

async function deleteProduto(codigo) {
    const message = `Tem certeza que deseja inativar o produto <strong>${codigo}</strong>?`;
    showConfirmModal(message, async () => {
        const response = await fetchApi(`/sped/produtos/${codigo}`, 'DELETE');
        showToast(response.message || 'Produto inativado com sucesso!', response.success ? 'success' : 'danger');
        if (response.success) await loadProdutos(currentPage);
    });
}

// --- Lógica de Seleção em Massa de Produtos ---
const selectedProducts = new Set();
const bulkActionContainer = document.getElementById('bulkActionContainer');
const selectedCountSpan = document.getElementById('selectedCount');
const selectAllCheckbox = document.getElementById('selectAllProducts');

function updateBulkActionUI() {
    const count = selectedProducts.size;
    if (count > 0) {
        selectedCountSpan.textContent = `${count} produto(s) selecionado(s)`;
        bulkActionContainer.classList.remove('d-none');
    } else {
        bulkActionContainer.classList.add('d-none');
    }
    updateSelectAllCheckbox();
}

function updateSelectAllCheckbox() {
    const checkboxesOnPage = document.querySelectorAll('.product-checkbox');
    const allOnPageChecked = checkboxesOnPage.length > 0 && Array.from(checkboxesOnPage).every(cb => cb.checked);
    selectAllCheckbox.checked = allOnPageChecked;
}

// Event listener unificado para o tbody de produtos
document.getElementById('produtosBody').addEventListener('change', async (e) => {
    // Gerencia checkboxes de seleção de produtos
    if (e.target.classList.contains('product-checkbox')) {
        const codigo = e.target.dataset.codigo;
        if (e.target.checked) {
            selectedProducts.add(codigo);
        } else {
            selectedProducts.delete(codigo);
        }
        updateBulkActionUI();
    }

    // Gerencia mudanças nos selects de acumulador
    if (e.target.classList.contains('acumulador-select')) {
        const codigo = e.target.dataset.codigo;
        const acumulador = e.target.value;

        try {
            const response = await fetchApi('/sped/produtos/atualizar_acumulador', 'POST', {
                codigo: codigo,
                acumulador: acumulador
            });
            if (response.success) {
                showToast(response.message, 'success');
                // Atualiza a linha para remover/adicionar o destaque de aviso
                const row = e.target.closest('tr');
                if (acumulador) {
                    row.classList.remove('table-warning');
                } else {
                    row.classList.add('table-warning');
                }
                // Recarrega os relatórios
                await Promise.all([
                    loadVendasReport(),
                    loadCfopReport()
                ]);
            }
        } catch (error) {
            console.error('Erro ao atualizar acumulador:', error);
            // Reverte a seleção em caso de erro
            e.target.value = e.target.dataset.originalValue || '';
        }
    }
});

selectAllCheckbox.addEventListener('change', (e) => {
    const checkboxes = document.querySelectorAll('.product-checkbox');
    checkboxes.forEach(checkbox => {
        const codigo = checkbox.dataset.codigo;
        checkbox.checked = e.target.checked;
        if (e.target.checked) {
            selectedProducts.add(codigo);
        } else {
            selectedProducts.delete(codigo);
        }
    });
    updateBulkActionUI();
});

document.getElementById('applyBulkAction').addEventListener('click', async () => {
    const acumulador = document.getElementById('bulkAcumuladorSelect').value;
    const productCodes = Array.from(selectedProducts);

    if (!acumulador) {
        showToast('Por favor, selecione um acumulador para aplicar.', 'warning');
        return;
    }
    if (productCodes.length === 0) {
        showToast('Nenhum produto selecionado.', 'warning');
        return;
    }

    try {
        const response = await fetchApi('/sped/produtos/bulk_update_acumulador', 'POST', { product_codes: productCodes, acumulador_code: acumulador });
        showToast(response.message, 'success');
        selectedProducts.clear();
        updateBulkActionUI();
        // Recarrega a página atual e os relatórios
        await Promise.all([
            loadProdutos(currentPage),
            loadVendasReport(),
            loadCfopReport()
        ]);
    } catch (error) {
        console.error('Erro na atualização em massa:', error);
        // fetchApi já mostra o toast de erro
    }
});

// Gerenciamento de Vendas
async function loadVendas(page = 1) {
    console.log('loadVendas called');
    const competencia = document.getElementById('competenciaVendasFilter').value;
    const vendasTable = document.getElementById('vendasTable');
    const warningDiv = document.getElementById('vendasReportWarning');
    const warningText = document.getElementById('vendasReportWarningText');

    vendasTable.classList.add('d-none');
    warningDiv.classList.add('d-none');

    try {
        const data = await fetchApi(`/sped/vendas?competencia=${competencia}`);
        vendasTable.classList.remove('d-none');

        const tbody = document.getElementById('vendasBody');
        tbody.innerHTML = '';

        if (!data || (data.vendas_a_vista === 0 && data.vendas_a_prazo === 0 && data.total_vendas === 0)) {
            // Mostra mensagem quando não há dados ou quando todos os valores são zero
            tbody.innerHTML = '<tr><td colspan="2" class="text-center">Nenhum dado disponível para a competência selecionada.</td></tr>';
            return;
        }

        // Preenche a tabela com os dados do relatório
        let row = tbody.insertRow();
        row.insertCell().textContent = 'Vendas à Vista';
        row.insertCell().textContent = formatCurrency(data.vendas_a_vista);

        row = tbody.insertRow();
        row.insertCell().textContent = 'Vendas a Prazo';
        row.insertCell().textContent = formatCurrency(data.vendas_a_prazo);

        // Adiciona o total como uma linha destacada no tbody
        const totalRow = tbody.insertRow();
        totalRow.className = 'fw-bold';
        totalRow.insertCell().textContent = 'Total de Vendas';
        totalRow.insertCell().textContent = formatCurrency(data.total_vendas);

        // Limpa o tfoot para evitar confusão
        const tfoot = vendasTable.querySelector('tfoot');
        tfoot.innerHTML = '';

    } catch (error) {
        if (error.message.includes("produto(s) sem acumulador")) {
            warningText.textContent = error.message;
            warningDiv.classList.remove('d-none');
        } else {
            // Para outros erros, mostra mensagem de dados não disponíveis
            const tbody = document.getElementById('vendasBody');
            tbody.innerHTML = '<tr><td colspan="2" class="text-center">Nenhum dado disponível para a competência selecionada.</td></tr>';
            vendasTable.classList.remove('d-none');
            console.error("Erro ao carregar relatório de vendas:", error);
        }
    }
}

// Função simplificada para carregar relatório de vendas por acumulador
function loadVendasReport() {
    const competencia = document.getElementById('competenciaFilter').value;
    
    // Busca dados do servidor sem mostrar spinner (controlado pela syncCompetencias)
    return fetchApi(`/sped/relatorio_vendas?competencia=${competencia}`)
        .then(data => {
            renderVendasTable(data);
        })
        .catch(error => {
            console.error('Erro ao carregar relatório:', error);
            renderVendasTable(null, error.message);
        });
}



// Função para renderizar a tabela de vendas agrupada por acumulador
function renderVendasTable(data, errorMessage = null) {
    const table = document.getElementById('salesTable');
    const warning = document.getElementById('salesReportWarning');
    const warningText = document.getElementById('salesReportWarningText');
    
    // Sempre mostra a tabela
    table.style.display = 'table';
    table.classList.remove('d-none');
    
    // Esconde warning por padrão
    warning.classList.add('d-none');
    
    // Se há erro, oculta a tabela e mostra warning
    if (errorMessage) {
        if (errorMessage.includes("produto(s) sem acumulador")) {
            // Oculta a tabela completamente quando há produtos sem acumulador
            table.style.display = 'none';
            table.classList.add('d-none');
            warningText.textContent = errorMessage;
            warning.classList.remove('d-none');
        } else {
            // Para outros erros, mostra tabela vazia
            table.innerHTML = `
                <thead class="table-dark">
                    <tr><th>Acumulador</th><th>Total de Vendas</th><th>Ações</th></tr>
                </thead>
                <tbody></tbody>
                <tfoot></tfoot>
            `;
        }
        return;
    }
    
    // Se não há dados, mostra tabela vazia
    if (!data || !data.acumuladores || data.acumuladores.length === 0) {
        table.innerHTML = `
            <thead class="table-dark">
                <tr><th>Acumulador</th><th>Total de Vendas</th><th>Ações</th></tr>
            </thead>
            <tbody>
                <tr><td colspan="3" class="text-center">Nenhum dado disponível para a competência selecionada.</td></tr>
            </tbody>
            <tfoot></tfoot>
        `;
        return;
    }
    
    // Constrói corpo da tabela
    let bodyHtml = '';
    
    data.acumuladores.forEach((acumulador, index) => {
        // Linha principal do acumulador
        const qtdVendas = acumulador.vendas_por_data.length;
        const rowClass = index % 2 === 0 ? 'table-light' : '';
        
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
        
        // Linhas de detalhes (inicialmente ocultas)
        const detailsBg = index % 2 === 0 ? 'bg-light' : 'bg-white';
        bodyHtml += `
            <tr id="detalhes-${index}" class="d-none detalhes-row">
                <td colspan="3" class="p-0">
                    <div class="${detailsBg} border-top border-2 border-secondary">
                        <div class="p-3">
                            <h6 class="mb-2 text-dark">
                                <i class="bi bi-calendar-event me-1"></i>
                                Detalhes de Vendas por Data:
                            </h6>
                            <div class="table-responsive">
                                <table class="table table-sm table-striped mb-0">
                                    <thead class="table-secondary">
                                        <tr>
                                            <th><i class="bi bi-calendar3 me-1"></i>Data</th>
                                            <th><i class="bi bi-currency-dollar me-1"></i>Valor</th>
                                        </tr>
                                    </thead>
                                    <tbody>
        `;
        
        acumulador.vendas_por_data.forEach(venda => {
            bodyHtml += `
                <tr>
                    <td>${venda.data}</td>
                    <td>${formatCurrency(venda.valor)}</td>
                </tr>
            `;
        });
        
        bodyHtml += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
        `;
    });
    
    // Monta tabela completa
    table.innerHTML = `
        <thead class="table-dark">
            <tr>
                <th style="width: 50%;">Acumulador</th>
                <th style="width: 30%;">Total de Vendas</th>
                <th style="width: 20%;">Ações</th>
            </tr>
        </thead>
        <tbody>
            ${bodyHtml}
        </tbody>
        <tfoot class="table-group-divider fw-bold bg-primary text-white">
            <tr>
                <td colspan="2"><strong>Total Geral</strong></td>
                <td><strong>${formatCurrency(data.total_geral)}</strong></td>
            </tr>
        </tfoot>
    `;
    
    // Adiciona classes CSS para melhor visualização
    table.className = 'table table-hover table-bordered';
}

// Função para expandir/recolher detalhes de um acumulador
function toggleDetalhes(index) {
    const detalhesRow = document.getElementById(`detalhes-${index}`);
    const button = document.querySelector(`button[onclick="toggleDetalhes(${index})"]`);
    
    if (detalhesRow.classList.contains('d-none')) {
        // Mostrar detalhes
        detalhesRow.classList.remove('d-none');
        button.innerHTML = '<i class="bi bi-eye-slash"></i> Ocultar Detalhes';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-outline-secondary');
    } else {
        // Ocultar detalhes
        detalhesRow.classList.add('d-none');
        button.innerHTML = '<i class="bi bi-eye"></i> Ver Detalhes';
        button.classList.remove('btn-outline-secondary');
        button.classList.add('btn-outline-primary');
    }
}

// Função para sincronizar competências entre todos os relatórios
async function syncCompetencias(changedSelectId, newValue) {
    console.log(`Sincronizando competência: ${changedSelectId} = ${newValue}`);
    
    // Mostra o overlay de carregamento e desabilita interações
    showCompetenciaLoading();
    
    const competenciaSelects = [
        'competenciaVendasFilter',
        'competenciaFilter',
        'competenciaCfopFilter'
    ];

    // Atualiza todos os outros selects com o novo valor
    competenciaSelects.forEach(selectId => {
        if (selectId !== changedSelectId) {
            const select = document.getElementById(selectId);
            if (select && select.value !== newValue) {
                select.value = newValue;
            }
        }
    });

    try {
        // Desabilita o spinner automático para evitar conflitos
        autoSpinnerEnabled = false;
        
        // Recarrega todos os relatórios com a nova competência
        await Promise.all([
            loadVendas(),
            loadVendasReport(),
            loadCfopReport()
        ]);
        
        // Esconde o overlay quando todos os relatórios terminarem de carregar
        hideCompetenciaLoading();
    } catch (error) {
        console.error('Erro ao recarregar relatórios:', error);
        // Esconde o overlay mesmo em caso de erro
        hideCompetenciaLoading();
    } finally {
        // Reabilita o spinner automático
        autoSpinnerEnabled = true;
    }
}

// Funções para controlar o overlay de carregamento
function showCompetenciaLoading() {
    const overlay = document.getElementById('competenciaLoadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
        // Desabilita scroll da página
        document.body.style.overflow = 'hidden';
    }
}

function hideCompetenciaLoading() {
    const overlay = document.getElementById('competenciaLoadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
        // Reabilita scroll da página
        document.body.style.overflow = '';
    }
}

function resetCfopTableState(cfopTable, warningDiv) {
    console.log('Resetando estado da tabela CFOP...');
    
    // Remove todos os estilos inline que podem estar ocultando a tabela
    cfopTable.style.display = 'table';
    cfopTable.style.visibility = 'visible';
    
    // Remove classes que ocultam a tabela
    cfopTable.classList.remove('d-none');
    
    // Oculta o aviso
    warningDiv.classList.add('d-none');
    
    // Limpa o conteúdo da tabela
    const tbody = document.getElementById('cfopBody');
    const tfoot = cfopTable.querySelector('tfoot');
    if (tbody) tbody.innerHTML = '';
    if (tfoot) tfoot.innerHTML = '';
    
    console.log('Estado da tabela CFOP resetado');
}

async function loadCfopReport() {
    console.log('=== loadCfopReport chamada ===');
    const competencia = document.getElementById('competenciaCfopFilter').value;
    console.log('Competência selecionada:', competencia);
    
    const cfopTable = document.getElementById('cfopTable');
    const warningDiv = document.getElementById('cfopReportWarning');
    const warningText = document.getElementById('cfopReportWarningText');

    // CORREÇÃO: Limpa completamente o estado anterior e garante visibilidade
    resetCfopTableState(cfopTable, warningDiv);

    try {
        // Adiciona timestamp para evitar cache
        const timestamp = new Date().getTime();
        const url = `/sped/relatorio_cfop?competencia=${competencia}&_t=${timestamp}`;
        console.log('URL da requisição:', url);
        
        const data = await fetchApi(url);
        console.log('Dados recebidos do relatório CFOP:', data);

        const tbody = document.getElementById('cfopBody');
        const tfoot = cfopTable.querySelector('tfoot');
        tbody.innerHTML = '';
        tfoot.innerHTML = '';

        if (!data || data.length === 0) {
            console.log('Nenhum dado encontrado para a competência');
            tbody.innerHTML = '<tr><td colspan="2" class="text-center">Nenhum dado disponível para a competência selecionada.</td></tr>';
            cfopTable.classList.remove('d-none');
            return;
        }

        let totalGeral = 0;
        console.log(`Processando ${data.length} CFOPs`);

        // Preenche a tabela com os dados do relatório
        data.forEach((item, index) => {
            console.log(`CFOP ${index + 1}: ${item.cfop} = R$ ${item.total}`);
            const row = tbody.insertRow();
            row.insertCell().textContent = `${item.cfop}`;
            row.insertCell().textContent = formatCurrency(item.total);
            totalGeral += item.total;
        });

        // Adiciona linha de total
        const totalRow = tfoot.insertRow();
        totalRow.innerHTML = `
            <td>Total Geral</td>
            <td>${formatCurrency(totalGeral)}</td>
        `;

        console.log(`Total geral do relatório CFOP: R$ ${totalGeral}`);
        // CORREÇÃO: Garante que a tabela esteja sempre visível após carregar dados
        cfopTable.style.display = 'table';
        cfopTable.classList.remove('d-none');

    } catch (error) {
        console.error('Erro ao carregar relatório CFOP:', error);
        
        if (error.message.includes("produto(s) sem acumulador")) {
            console.log('Erro: produtos sem acumulador detectados');
            cfopTable.style.display = 'none';
            cfopTable.classList.add('d-none');
            warningText.textContent = error.message;
            warningDiv.classList.remove('d-none');
        } else {
            console.log('Erro genérico, mostrando tabela vazia');
            const tbody = document.getElementById('cfopBody');
            const tfoot = cfopTable.querySelector('tfoot');
            tbody.innerHTML = '<tr><td colspan="2" class="text-center">Erro ao carregar dados. Tente novamente.</td></tr>';
            tfoot.innerHTML = '';
            // CORREÇÃO: Garante que a tabela esteja visível mesmo com erro genérico
            cfopTable.style.display = 'table';
            cfopTable.classList.remove('d-none');
        }
    }
}

async function loadCompetencias() {
    try {
        const competencias = await fetchApi('/sped/competencias');

        if (!competencias || competencias.length === 0) {
            // Inicializa todas as abas com mensagem de dados não disponíveis
            initializeAllReportsWithMessage();
            return;
        }

        // Preenche todos os selects de competência
        const selects = [
            'competenciaVendasFilter',
            'competenciaFilter', 
            'competenciaCfopFilter'
        ];

        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                select.innerHTML = '';
                competencias.forEach(comp => {
                    const option = document.createElement('option');
                    option.value = comp;
                    option.textContent = comp;
                    select.appendChild(option);
                });
            }
        });

        // Carrega relatórios iniciais
        if (competencias.length > 0) {
            loadVendas();
            loadVendasReport();
            loadCfopReport();
        }
    } catch (error) {
        console.error('Erro ao carregar competências:', error);
        renderVendasTable(null, 'Erro ao carregar competências');
    }
}



// Função para carregar todos os relatórios
async function loadAllReports() {
    try {
        await Promise.all([
            loadVendas(),
            loadVendasReport(),
            loadCfopReport()
        ]);
    } catch (error) {
        console.error('Erro ao carregar relatórios:', error);
        
        // Em caso de erro, inicializa todas as abas com mensagem padrão
        initializeAllReportsWithMessage();
    }
}

// Função simples para garantir visibilidade da tabela
function showSalesTable() {
    const table = document.getElementById('salesTable');
    if (table) {
        table.style.display = 'table';
        table.classList.remove('d-none');
    }
}

// Função para inicializar todas as abas de relatórios com mensagem padrão
function initializeAllReportsWithMessage() {
    // Inicializa aba de vendas
    const vendasBody = document.getElementById('vendasBody');
    if (vendasBody) {
        vendasBody.innerHTML = '<tr><td colspan="2" class="text-center">Nenhum dado disponível para a competência selecionada.</td></tr>';
        const vendasTable = document.getElementById('vendasTable');
        if (vendasTable) {
            vendasTable.classList.remove('d-none');
        }
    }
    
    // Inicializa aba de CFOP
    const cfopBody = document.getElementById('cfopBody');
    if (cfopBody) {
        cfopBody.innerHTML = '<tr><td colspan="2" class="text-center">Nenhum dado disponível para a competência selecionada.</td></tr>';
        const cfopTable = document.getElementById('cfopTable');
        if (cfopTable) {
            cfopTable.classList.remove('d-none');
        }
    }
    
    // Inicializa aba de acumulador
    renderVendasTable(null);
}

function setupCompetenciaNavigation(selectId, prevBtnId, nextBtnId) {
    const select = document.getElementById(selectId);
    const prevBtn = document.getElementById(prevBtnId);
    const nextBtn = document.getElementById(nextBtnId);

    console.log(`Setting up navigation for ${selectId}`);

    prevBtn.addEventListener('click', () => {
        console.log(`Button ${prevBtnId} clicked.`);
        if (select.selectedIndex > 0) {
            console.log(`  - Before: selectedIndex = ${select.selectedIndex}`);
            select.selectedIndex--;
            console.log(`  - After: selectedIndex = ${select.selectedIndex}`);

            // Sincroniza com outros selects
            syncCompetencias(selectId, select.value);

            // Carrega todos os relatórios
            loadAllReports();
        }
    });

    nextBtn.addEventListener('click', () => {
        console.log(`Button ${nextBtnId} clicked.`);
        if (select.selectedIndex < select.options.length - 1) {
            console.log(`  - Before: selectedIndex = ${select.selectedIndex}`);
            select.selectedIndex++;
            console.log(`  - After: selectedIndex = ${select.selectedIndex}`);

            // Sincroniza com outros selects
            syncCompetencias(selectId, select.value);

            // Carrega todos os relatórios
            loadAllReports();
        }
    });

    select.addEventListener('change', () => {
        // Sincroniza com outros selects
        syncCompetencias(selectId, select.value);

        // CORREÇÃO: Garante que a tabela esteja visível antes de carregar
        ensureAccumulatorTableVisible();

        // Carrega todos os relatórios
        loadAllReports();
    });
}

async function initializeSpedPage() {
    console.log('Iniciando página SPED...');

    // Inicializa todas as abas com mensagem padrão primeiro
    initializeAllReportsWithMessage();

    // Carrega dados básicos
    await Promise.all([
        loadCfops(),
        loadAcumuladores(),
        loadCompetencias()
    ]);

    // Configura listeners
    setupFilterListeners();

    // Carrega produtos
    await loadProdutos(1);

    console.log('Página SPED inicializada');
}



// Flag para evitar múltiplas configurações
let filterListenersConfigured = false;

// Função para configurar os event listeners dos filtros
function setupFilterListeners() {
    console.log('Configurando event listeners dos filtros...');

    // Se já foi configurado, remove a flag para reconfigurar
    if (filterListenersConfigured) {
        console.log('Listeners já configurados, pulando...');
        return;
    }

    // Event listeners para filtros e pesquisa
    const searchProdutos = document.getElementById('searchProdutos');
    const searchAcumuladores = document.getElementById('searchAcumuladores');

    // Verifica se os elementos existem antes de adicionar event listeners
    if (searchProdutos) {
        searchProdutos.addEventListener('input', debounce(() => {
            console.log('Pesquisa de produtos alterada');
            loadProdutos(1);
        }, 300));
        console.log('Listener de pesquisa de produtos configurado');
    }

    // Método 1: Event delegation no container dos filtros
    const filterContainer = document.querySelector('.btn-group[role="group"]');
    if (filterContainer) {
        console.log('Container de filtros encontrado, adicionando event delegation');
        filterContainer.addEventListener('click', (e) => {
            console.log('Click no container, target:', e.target.tagName, e.target.className);

            // Verifica se clicou em um input radio
            let radio = null;
            if (e.target.tagName === 'INPUT' && e.target.name === 'acumuladorFilter') {
                radio = e.target;
            } else if (e.target.tagName === 'LABEL') {
                // Se clicou na label, pega o input associado
                const forAttr = e.target.getAttribute('for');
                if (forAttr) {
                    radio = document.getElementById(forAttr);
                }
            }

            if (radio) {
                console.log('DELEGATION CLICK - Filtro identificado:', radio.value);
                // Pequeno delay para garantir que o radio foi marcado
                setTimeout(() => {
                    console.log('Carregando produtos com filtro:', radio.value);
                    loadProdutos(1);
                }, 50);
            }
        });
    }

    // Método 2: Listeners diretos nos radio buttons
    const acumuladorFilters = document.querySelectorAll('input[name="acumuladorFilter"]');
    console.log('Filtros de acumulador encontrados:', acumuladorFilters.length);

    acumuladorFilters.forEach(radio => {
        console.log('Adicionando listener para:', radio.id, radio.value, 'checked:', radio.checked);

        // Adiciona listener de change
        radio.addEventListener('change', (e) => {
            console.log('EVENT CHANGE - Filtro de acumulador mudou para:', e.target.value);
            loadProdutos(1);
        });

        // Adiciona listener de input (dispara antes do change)
        radio.addEventListener('input', (e) => {
            console.log('EVENT INPUT - Filtro de acumulador input:', e.target.value);
            loadProdutos(1);
        });
    });

    // Método 3: Listeners nas labels (Bootstrap usa labels para estilizar)
    const filterLabels = document.querySelectorAll('label[for="todos"], label[for="cadastrados"], label[for="naoCadastrados"]');
    console.log('Labels de filtro encontradas:', filterLabels.length);
    filterLabels.forEach(label => {
        label.addEventListener('click', (e) => {
            const radioId = label.getAttribute('for');
            const radio = document.getElementById(radioId);
            console.log('LABEL CLICK - Label clicada para:', radioId, 'Radio checked antes:', radio?.checked);

            // IMPORTANTE: Sempre recarrega, mesmo se o radio já estava marcado
            // Isso resolve o problema de clicar no filtro já selecionado
            setTimeout(() => {
                console.log('Radio checked depois:', radio?.checked);
                loadProdutos(1);
            }, 50);
        });
    });

    if (searchAcumuladores) {
        searchAcumuladores.addEventListener('input', debounce(() => loadAcumuladores(), 300));
    }

    // Marca como configurado
    filterListenersConfigured = true;
    console.log('Event listeners dos filtros configurados com sucesso!');

    // Debug: Listener global para verificar todos os cliques na área de filtros
    document.addEventListener('click', (e) => {
        if (e.target.closest('.btn-group[role="group"]')) {
            console.log('GLOBAL CLICK detectado na área de filtros');
            console.log('Target:', e.target.tagName, e.target.textContent, e.target.className);
            console.log('Filtro atual selecionado:', document.querySelector('input[name="acumuladorFilter"]:checked')?.value);
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM carregado, iniciando aplicação...');

    // Inicializa a página (já configura os listeners internamente)
    await initializeSpedPage();

    // Adiciona listener para carregar dados quando os modais são abertos
    const acumuladoresModal = document.getElementById('acumuladoresModal');
    if (acumuladoresModal) {
        acumuladoresModal.addEventListener('show.bs.modal', () => {
            loadAcumuladores();
        });
    }

    // Adiciona listener para quando a aba de produtos é mostrada
    const produtosTab = document.getElementById('produtos-tab');
    if (produtosTab) {
        produtosTab.addEventListener('shown.bs.tab', () => {
            console.log('Aba de produtos mostrada, reconfigurando listeners...');
            // Pequeno delay para garantir que a aba foi renderizada
            setTimeout(() => {
                setupFilterListeners();
            }, 100);
        });
    }

    // Listener simples para aba de relatório por acumulador
    const relatorioAcumuladorTab = document.getElementById('relatorio-acumulador-tab');
    if (relatorioAcumuladorTab) {
        relatorioAcumuladorTab.addEventListener('shown.bs.tab', () => {
            showSalesTable();
            loadVendasReport();
        });
    }

    // Event listener para aba do relatório por CFOP
    const relatorioCfopTab = document.getElementById('relatorio-cfop-tab');
    if (relatorioCfopTab) {
        relatorioCfopTab.addEventListener('shown.bs.tab', () => {
            console.log('Aba relatório CFOP mostrada, carregando dados...');
            loadCfopReport();
        });
    }

    setupCompetenciaNavigation('competenciaVendasFilter', 'prevVendas', 'nextVendas');
    setupCompetenciaNavigation('competenciaFilter', 'prevAcumulador', 'nextAcumulador');
    setupCompetenciaNavigation('competenciaCfopFilter', 'prevCfop', 'nextCfop');

    // CFOPs
    const searchCfops = document.getElementById('searchCfops');
    if (searchCfops) {
        searchCfops.addEventListener('input', debounce(() => loadCfops(), 300));
    }

    // Event listeners para botões de modal
    const btnNovoAcumulador = document.getElementById('btnNovoAcumulador');
    if (btnNovoAcumulador) {
        btnNovoAcumulador.addEventListener('click', () => {
            document.getElementById('acumuladorModalTitle').innerHTML = '<i class="bi bi-plus-lg me-2"></i>Novo Acumulador';
            const form = document.getElementById('acumuladorForm');
            if (form) form.reset();
            const codigoInput = document.getElementById('acumuladorCodigo');
            if (codigoInput) codigoInput.readOnly = false;
        });
    }

    const novoAcumuladorModal = document.getElementById('novoAcumuladorModal');
    if (novoAcumuladorModal) {
        novoAcumuladorModal.addEventListener('hidden.bs.modal', () => {
            const form = document.getElementById('acumuladorForm');
            if (form) {
                form.reset();
                form.classList.remove('was-validated');
            }
            const codigoInput = document.getElementById('acumuladorCodigo');
            if (codigoInput) codigoInput.readOnly = false;
            document.getElementById('acumuladorModalTitle').innerHTML = '<i class="bi bi-plus-lg me-2"></i>Novo Acumulador';
        });
    }

    const btnNovoCfop = document.querySelector('[data-bs-target="#novoCfopModal"]');
    if (btnNovoCfop) {
        btnNovoCfop.addEventListener('click', () => {
            const form = document.getElementById('cfopForm');
            document.getElementById('cfopModalTitle').innerHTML = '<i class="bi bi-plus-lg me-2"></i>Novo CFOP';
            if (form) {
                form.reset();
                form.classList.remove('was-validated');
            }
            const codigoInput = document.getElementById('cfopCodigo');
            if (codigoInput) codigoInput.readOnly = false;
        });
    }

    const novoCfopModal = document.getElementById('novoCfopModal');
    if (novoCfopModal) {
        novoCfopModal.addEventListener('hidden.bs.modal', () => {
            const form = document.getElementById('cfopForm');
            if (form) {
                form.reset();
                form.classList.remove('was-validated');
            }
            document.getElementById('cfopOriginal').value = '';
            document.getElementById('cfopModalTitle').innerHTML = '<i class="bi bi-plus-lg me-2"></i>Novo CFOP';
        });
    }

    // Event listeners para formulários
    const cfopForm = document.getElementById('cfopForm');
    if (cfopForm) {
        cfopForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveCfop();
        });
    }

    const saveCfopButton = document.getElementById('saveCfopButton');
    if (saveCfopButton) {
        saveCfopButton.addEventListener('click', async (e) => {
            e.preventDefault();
            await saveCfop();
        });
    }

    const produtoForm = document.getElementById('produtoForm');
    if (produtoForm) {
        produtoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveProduto();
        });
    }

    const acumuladorForm = document.getElementById('acumuladorForm');
    if (acumuladorForm) {
        acumuladorForm.addEventListener('submit', saveAcumulador);
    }

    // Listener para importação de arquivo SPED
    const submitSpedButton = document.getElementById('submitSped');
    if (submitSpedButton) {
        submitSpedButton.addEventListener('click', async function() {
            const fileInput = document.getElementById('arquivo_sped');
            if (!fileInput.files.length) {
                showToast('Por favor, selecione um arquivo SPED.', 'warning');
                return;
            }
            
            showSpinner();
            try {
                const formData = new FormData();
                formData.append('arquivo_sped', fileInput.files[0]);

                const response = await fetch('/sped/importar', { 
                    method: 'POST', 
                    body: formData
                });
                
                const data = await response.json();
                
                showToast(data.message || data.error, data.success ? 'success' : 'danger');
                if (data.success) {
                    console.log('Importação bem-sucedida, recarregando todos os dados...');
                    // Recarrega os dados após importação bem-sucedida
                    await Promise.all([
                        loadCompetencias(),
                        loadProdutos(1),
                        loadAcumuladores()
                    ]);
                    
                    // Força a atualização de todos os relatórios após um pequeno delay
                    setTimeout(async () => {
                        console.log('Forçando atualização dos relatórios...');
                        await Promise.all([
                            loadVendas(),
                            loadVendasReport(),
                            loadCfopReport()
                        ]);
                    }, 1000);
                }
                fileInput.value = ''; // Limpa o input do arquivo
            } catch (error) {
                console.error('Erro ao importar arquivo:', error);
                showToast('Erro ao importar o arquivo. Verifique o console para mais detalhes.', 'danger');
            } finally {
                hideSpinner();
            }
        });
    }

    // Event listeners para botões de exclusão e edição
    document.addEventListener('click', async (e) => {
        if (e.target.closest('.edit-cfop')) {
            const button = e.target.closest('.edit-cfop');
            await editCfop(button.dataset.codigo);
        }
        if (e.target.closest('.delete-cfop')) {
            const button = e.target.closest('.delete-cfop');
            await deleteCfop(button.dataset.codigo);
        }
        if (e.target.closest('.edit-acumulador')) {
            const button = e.target.closest('.edit-acumulador');
            await editAcumulador(button.dataset.codigo);
        }
        if (e.target.closest('.delete-acumulador')) {
            const button = e.target.closest('.delete-acumulador');
            await deleteAcumulador(button.dataset.codigo);
        }
    });

    // Inicializa tooltips do Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});


    // Listeners com sincronização de competências
    const competenciaFilter = document.getElementById('competenciaFilter');
    if (competenciaFilter) {
        competenciaFilter.addEventListener('change', () => {
            syncCompetencias('competenciaFilter', competenciaFilter.value);
        });
    }

    const competenciaCfopFilter = document.getElementById('competenciaCfopFilter');
    if (competenciaCfopFilter) {
        competenciaCfopFilter.addEventListener('change', () => {
            syncCompetencias('competenciaCfopFilter', competenciaCfopFilter.value);
        });
    }

    const competenciaVendasFilter = document.getElementById('competenciaVendasFilter');
    if (competenciaVendasFilter) {
        competenciaVendasFilter.addEventListener('change', () => {
            syncCompetencias('competenciaVendasFilter', competenciaVendasFilter.value);
        });
    }

// CORREÇÃO: Monitora a visibilidade da tabela de CFOP
function startCfopTableMonitoring() {
    const cfopTable = document.getElementById('cfopTable');
    if (!cfopTable) return;

    // Verifica a cada 2 segundos se a tabela está visível
    setInterval(() => {
        const isHidden = cfopTable.classList.contains('d-none') ||
            cfopTable.style.display === 'none' ||
            cfopTable.offsetParent === null;

        if (isHidden) {
            console.warn('DETECTADO: Tabela de CFOP está oculta! Forçando visibilidade...');
            ensureCfopTableVisible();
        }
    }, 2000);
}

// Inicia o monitoramento quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    startCfopTableMonitoring();
});