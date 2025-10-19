// Função para exibir notificações (toasts)
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        console.error('Toast container not found!');
        return;
    }
    const toastId = `toast-${Date.now()}`;
    const bgClass = type === 'success' ? 'bg-success' : (type === 'danger' ? 'bg-danger' : 'bg-warning');
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0 show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
            </div>
        </div>`;
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
}

// Função para exibir um modal de confirmação genérico
function showConfirmModal(message, onConfirm) {
    // Remove qualquer modal de confirmação existente para evitar duplicatas
    const existingModal = document.getElementById('genericConfirmModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Cria o HTML do modal
    const modalHTML = `
        <div class="modal fade" id="genericConfirmModal" tabindex="-1" aria-labelledby="genericConfirmModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="genericConfirmModalLabel"><i class="bi bi-exclamation-triangle-fill text-danger me-2"></i>Confirmar Ação</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                    </div>
                    <div class="modal-body">
                        ${message}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" id="genericCancelBtn" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-danger" id="genericConfirmBtn">Confirmar</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    const modalElement = document.getElementById('genericConfirmModal');
    const confirmModal = new bootstrap.Modal(modalElement);
    
    const confirmBtn = document.getElementById('genericConfirmBtn');
    const cancelBtn = document.getElementById('genericCancelBtn');

    const confirmHandler = () => {
        confirmModal.hide();
        onConfirm();
    };

    confirmBtn.addEventListener('click', confirmHandler);

    modalElement.addEventListener('hidden.bs.modal', () => modalElement.remove());
    confirmModal.show();
}

// Funções para o spinner de carregamento global
function showSpinner() {
    const spinner = document.getElementById('globalSpinner');
    if (spinner) {
        spinner.style.display = 'flex';
    }
}

function hideSpinner() {
    const spinner = document.getElementById('globalSpinner');
    if (spinner) {
        spinner.style.display = 'none';
    }
}

// Lógica de toggle da Sidebar
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    function toggleSidebar(expand) {
        sidebar.classList.toggle('collapsed', !expand);
        mainContent.classList.toggle('expanded', !expand);
    }
    sidebar.addEventListener('mouseenter', () => { if (window.innerWidth > 768) toggleSidebar(true); });
    sidebar.addEventListener('mouseleave', () => { if (window.innerWidth > 768) toggleSidebar(false); });
    if (window.innerWidth <= 768) toggleSidebar(false);

    // Set active link in sidebar
    const currentPath = window.location.pathname;
    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link');

    sidebarLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});