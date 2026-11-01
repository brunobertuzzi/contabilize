// ==========================================================================
// CONTABILIZE - Main TypeScript Application
// Utilitários de interface, componentes interativos e feedbacks visuais
// ==========================================================================

import { ToastType } from './types/common';

// 1. Notificações Toast com Ícones
export function showToast(message: string, type: ToastType = 'success'): void {
  let toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toastContainer';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '1100';
    document.body.appendChild(toastContainer);
  }

  const toastId = `toast-${Date.now()}`;
  const bgClass =
    type === 'success'
      ? 'bg-success'
      : type === 'danger'
        ? 'bg-danger'
        : type === 'warning'
          ? 'bg-warning text-dark'
          : 'bg-info';

  const iconClass =
    type === 'success'
      ? 'bi-check-circle-fill'
      : type === 'danger'
        ? 'bi-exclamation-octagon-fill'
        : 'bi-exclamation-triangle-fill';

  const toastHTML = `
    <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex p-2">
            <div class="toast-body d-flex align-items-center gap-2">
                <i class="bi ${iconClass} fs-5"></i>
                <span>${message}</span>
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
        </div>
    </div>`;

  toastContainer.insertAdjacentHTML('beforeend', toastHTML);
  const toastElement = document.getElementById(toastId);

  if (toastElement && window.bootstrap && typeof window.bootstrap.Toast === 'function') {
    const toast = new window.bootstrap.Toast(toastElement, { delay: 4500 });
    toast.show();
    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
  }
}

// 2. Modal de Confirmação Genérico
export function showConfirmModal(message: string, onConfirm?: () => void): void {
  const existingModal = document.getElementById('genericConfirmModal');
  if (existingModal) existingModal.remove();

  const modalHTML = `
    <div class="modal fade" id="genericConfirmModal" tabindex="-1" aria-labelledby="genericConfirmModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content shadow-lg border-0 rounded-4">
                <div class="modal-header border-bottom">
                    <h5 class="modal-title fw-bold text-dark" id="genericConfirmModalLabel">
                        <i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Confirmar Ação
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                </div>
                <div class="modal-body py-4 fs-6 text-muted">
                    ${message}
                </div>
                <div class="modal-footer border-top">
                    <button type="button" class="btn btn-outline-secondary px-3" id="genericCancelBtn" data-bs-dismiss="modal">Cancelar</button>
                    <button type="button" class="btn btn-danger px-4" id="genericConfirmBtn">Confirmar</button>
                </div>
            </div>
        </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', modalHTML);

  const modalElement = document.getElementById('genericConfirmModal');
  if (!modalElement || !window.bootstrap) return;

  const confirmModal = new window.bootstrap.Modal(modalElement);
  const confirmBtn = document.getElementById('genericConfirmBtn');

  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      confirmModal.hide();
      if (typeof onConfirm === 'function') {
        onConfirm();
      }
    });
  }

  modalElement.addEventListener('hidden.bs.modal', () => modalElement.remove());
  confirmModal.show();
}

// 3. Controle Global de Spinner
export function showSpinner(): void {
  const spinner =
    (document.getElementById('competenciaLoadingOverlay') as HTMLElement | null) ||
    (document.getElementById('globalSpinner') as HTMLElement | null);
  if (spinner) {
    spinner.classList.add('show');
    spinner.style.display = 'flex';
  }
}

export function hideSpinner(): void {
  const spinner =
    (document.getElementById('competenciaLoadingOverlay') as HTMLElement | null) ||
    (document.getElementById('globalSpinner') as HTMLElement | null);
  if (spinner) {
    spinner.classList.remove('show');
    spinner.style.display = 'none';
  }
}

// Expor utilitários essenciais no escopo global para compatibilidade com HTML e outros scripts
window.showToast = showToast;
window.showConfirmModal = showConfirmModal;
window.showSpinner = showSpinner;
window.hideSpinner = hideSpinner;

// 4. Inicializador Principal DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  // --- A. Sidebar & Layout Responsivo ---
  const sidebar = document.getElementById('sidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');
  const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');
  const closeSidebarBtn = document.getElementById('closeSidebarBtn');
  const sidebarPinBtn = document.getElementById('sidebarPinBtn');
  const sidebarPinIcon = document.getElementById('sidebarPinIcon');

  const isCollapsed = localStorage.getItem('sidebar_collapsed') === 'true';

  function setSidebarState(collapsed: boolean): void {
    if (!sidebar) return;
    if (collapsed) {
      sidebar.classList.add('collapsed');
      if (sidebarPinIcon) {
        sidebarPinIcon.className = 'bi bi-layout-sidebar';
        if (sidebarPinBtn) sidebarPinBtn.setAttribute('title', 'Expandir menu lateral');
      }
    } else {
      sidebar.classList.remove('collapsed');
      if (sidebarPinIcon) {
        sidebarPinIcon.className = 'bi bi-layout-sidebar-inset';
        if (sidebarPinBtn) sidebarPinBtn.setAttribute('title', 'Recolher menu lateral');
      }
    }
  }

  if (sidebar) {
    if (window.innerWidth > 768) {
      setSidebarState(isCollapsed);
    }

    // Botão de recolher/expandir no desktop
    if (sidebarPinBtn) {
      sidebarPinBtn.addEventListener('click', (e: MouseEvent) => {
        e.preventDefault();
        const nowCollapsed = !sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebar_collapsed', String(nowCollapsed));
        setSidebarState(nowCollapsed);
      });
    }

    // Controles de Gaveta no Mobile
    if (mobileSidebarToggle) {
      mobileSidebarToggle.addEventListener('click', () => {
        sidebar.classList.add('show');
        if (sidebarBackdrop) sidebarBackdrop.classList.add('show');
      });
    }
    if (closeSidebarBtn) {
      closeSidebarBtn.addEventListener('click', () => {
        sidebar.classList.remove('show');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('show');
      });
    }
    if (sidebarBackdrop) {
      sidebarBackdrop.addEventListener('click', () => {
        sidebar.classList.remove('show');
        sidebarBackdrop.classList.remove('show');
      });
    }
  }

  // Marca link ativo na sidebar
  const currentPath = window.location.pathname;
  document.querySelectorAll<HTMLAnchorElement>('.sidebar .nav-link').forEach((link) => {
    link.classList.remove('active');
    const href = link.getAttribute('href');
    if (href === currentPath || (href !== '/' && href !== null && currentPath.startsWith(href))) {
      link.classList.add('active');
    }
  });

  // --- B. Botões de Alternar Visibilidade de Senha ---
  document.querySelectorAll<HTMLElement>('.password-toggle-btn').forEach((btn) => {
    btn.addEventListener('click', function (e: MouseEvent) {
      e.preventDefault();
      const targetId = this.dataset.target;
      const input = targetId
        ? (document.getElementById(targetId) as HTMLInputElement | null)
        : (this.closest('.position-relative')?.querySelector('input') as HTMLInputElement | null);
      if (!input) return;

      const icon = this.querySelector('i');
      if (input.type === 'password') {
        input.type = 'text';
        if (icon) {
          icon.classList.remove('bi-eye');
          icon.classList.add('bi-eye-slash');
        }
      } else {
        input.type = 'password';
        if (icon) {
          icon.classList.remove('bi-eye-slash');
          icon.classList.add('bi-eye');
        }
      }
    });
  });

  // --- C. Medidor de Força de Senha (Setup Admin e Formulários) ---
  const passInput = document.getElementById('password') as HTMLInputElement | null;
  const strengthBar = document.getElementById('passwordStrengthBar') as HTMLElement | null;
  const strengthText = document.getElementById('passwordStrengthText') as HTMLElement | null;

  if (passInput && strengthBar) {
    passInput.addEventListener('input', function () {
      const val = this.value;
      let score = 0;
      if (val.length >= 8) score += 1;
      if (/[A-Z]/.test(val)) score += 1;
      if (/[a-z]/.test(val)) score += 1;
      if (/[0-9]/.test(val)) score += 1;
      if (/[^A-Za-z0-9]/.test(val)) score += 1;

      if (val.length === 0) {
        strengthBar.style.width = '0%';
        strengthBar.className = 'progress-bar bg-danger';
        if (strengthText) strengthText.textContent = 'Digite a senha';
      } else if (val.length < 8) {
        strengthBar.style.width = '25%';
        strengthBar.className = 'progress-bar bg-danger';
        if (strengthText) strengthText.textContent = 'Muito curta (mín. 8 caracteres)';
      } else if (score < 3) {
        strengthBar.style.width = '50%';
        strengthBar.className = 'progress-bar bg-warning';
        if (strengthText) strengthText.textContent = 'Razoável (adicione números ou símbolos)';
      } else if (score < 5) {
        strengthBar.style.width = '75%';
        strengthBar.className = 'progress-bar bg-info';
        if (strengthText) strengthText.textContent = 'Boa';
      } else {
        strengthBar.style.width = '100%';
        strengthBar.className = 'progress-bar bg-success';
        if (strengthText) strengthText.textContent = 'Excelente / Muito Forte';
      }
    });
  }

  // --- D. Drag & Drop File Upload para SPED ---
  const dropzone = document.getElementById('dropzoneArea') as HTMLElement | null;
  const fileInput = document.getElementById('arquivo_sped') as HTMLInputElement | null;
  const fileInfo = document.getElementById('fileSelectedInfo') as HTMLElement | null;
  const fileNameSpan = document.getElementById('selectedFileName') as HTMLElement | null;
  const fileSizeSpan = document.getElementById('selectedFileSize') as HTMLElement | null;

  function updateFileInfo(file: File | null): void {
    if (!file) {
      if (fileInfo) fileInfo.classList.add('d-none');
      return;
    }
    if (fileNameSpan) fileNameSpan.textContent = file.name;
    if (fileSizeSpan) {
      const sizeInKb = (file.size / 1024).toFixed(1);
      fileSizeSpan.textContent = `(${sizeInKb} KB)`;
    }
    if (fileInfo) fileInfo.classList.remove('d-none');
  }

  if (dropzone && fileInput) {
    (['dragenter', 'dragover'] as const).forEach((eventName) => {
      dropzone.addEventListener(eventName, (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    (['dragleave', 'drop'] as const).forEach((eventName) => {
      dropzone.addEventListener(eventName, (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e: DragEvent) => {
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        fileInput.files = files;
        updateFileInfo(files[0]);
        const changeEvent = new Event('change', { bubbles: true });
        fileInput.dispatchEvent(changeEvent);
      }
    });

    fileInput.addEventListener('change', function () {
      if (this.files && this.files.length > 0) {
        updateFileInfo(this.files[0]);
      } else {
        updateFileInfo(null);
      }
    });
  }
});
