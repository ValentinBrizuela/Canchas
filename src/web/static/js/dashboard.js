/**
 * CANCHAS SAAS - PANEL DE ADMINISTRACIÓN (JAVASCRIPT)
 * Lógica interactiva para gestión de agenda, reservas y KPIs en tiempo real.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Estado global de la aplicación
  const state = {
    currentDate: getTodayIsoString(),
    activeFilter: 'todas',
    complejo: null,
    agendaData: null,
    selectedTurno: null, // Para modal de detalle / cancelación
  };

  // Elementos DOM principales
  const elDateInput = document.getElementById('selected-date');
  const elBtnPrev = document.getElementById('btn-prev-day');
  const elBtnNext = document.getElementById('btn-next-day');
  const elBtnToday = document.getElementById('btn-today');
  const elBtnRefresh = document.getElementById('btn-refresh');
  const elBtnNuevaReserva = document.getElementById('btn-nueva-reserva');
  const elComplejoNombre = document.getElementById('complejo-nombre');

  // KPIs
  const elKpiCanchas = document.getElementById('kpi-canchas');
  const elKpiReservas = document.getElementById('kpi-reservas');
  const elKpiOcupacion = document.getElementById('kpi-ocupacion');
  const elKpiProgressBar = document.getElementById('kpi-progress-bar');
  const elKpiIngresos = document.getElementById('kpi-ingresos');

  // Agenda container y estados
  const elAgendaGrid = document.getElementById('agenda-grid');
  const elLoadingSpinner = document.getElementById('loading-spinner');
  const elEmptyState = document.getElementById('empty-state');
  const elFilterChips = document.querySelectorAll('.filter-chip');

  // Modales
  const elModalReserva = document.getElementById('modal-reserva');
  const elFormReserva = document.getElementById('form-reserva');
  const elSelectCanchaReserva = document.getElementById('reserva-cancha');
  const elInputFechaReserva = document.getElementById('reserva-fecha');
  const elInputHoraReserva = document.getElementById('reserva-hora');
  const elInputPrecioReserva = document.getElementById('reserva-precio');
  const elBtnCloseReserva = document.getElementById('btn-close-reserva');
  const elBtnCancelReserva = document.getElementById('btn-cancel-reserva');

  const elModalBloqueo = document.getElementById('modal-bloqueo');
  const elFormBloqueo = document.getElementById('form-bloqueo');
  const elBloqueoCanchaId = document.getElementById('bloqueo-cancha-id');
  const elBloqueoFechaInicio = document.getElementById('bloqueo-fecha-inicio');
  const elBloqueoInfoDisplay = document.getElementById('bloqueo-info-display');
  const elBtnCloseBloqueo = document.getElementById('btn-close-bloqueo');
  const elBtnCancelBloqueo = document.getElementById('btn-cancel-bloqueo');

  const elModalDetalle = document.getElementById('modal-detalle');
  const elBtnCloseDetalle = document.getElementById('btn-close-detalle');
  const elBtnCloseDetalleAction = document.getElementById('btn-close-detalle-action');
  const elBtnCancelarTurnoAction = document.getElementById('btn-cancelar-turno-action');
  const elBtnCancelarTurnoText = document.getElementById('btn-cancelar-turno-text');

  // Inicialización
  init();

  async function init() {
    elDateInput.value = state.currentDate;
    setupEventListeners();
    await loadComplejoInfo();
    await loadAgendaAndKpis();
  }

  function setupEventListeners() {
    // Navegación de fecha
    elDateInput.addEventListener('change', (e) => {
      state.currentDate = e.target.value;
      loadAgendaAndKpis();
    });

    elBtnPrev.addEventListener('click', () => {
      shiftDate(-1);
    });

    elBtnNext.addEventListener('click', () => {
      shiftDate(1);
    });

    elBtnToday.addEventListener('click', () => {
      state.currentDate = getTodayIsoString();
      elDateInput.value = state.currentDate;
      loadAgendaAndKpis();
    });

    elBtnRefresh.addEventListener('click', () => {
      const icon = elBtnRefresh.querySelector('.refresh-icon');
      icon.classList.add('spinning');
      loadAgendaAndKpis().finally(() => {
        setTimeout(() => icon.classList.remove('spinning'), 500);
      });
    });

    // Filtros de deporte
    elFilterChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        elFilterChips.forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        state.activeFilter = chip.dataset.filter;
        renderAgenda();
      });
    });

    // Modal Nueva Reserva
    elBtnNuevaReserva.addEventListener('click', () => {
      openModalReserva();
    });

    elBtnCloseReserva.addEventListener('click', () => closeModal(elModalReserva));
    elBtnCancelReserva.addEventListener('click', () => closeModal(elModalReserva));

    elSelectCanchaReserva.addEventListener('change', () => {
      const canchaId = parseInt(elSelectCanchaReserva.value);
      const cancha = state.complejo?.canchas.find((c) => c.id === canchaId);
      if (cancha) {
        elInputPrecioReserva.value = cancha.precio;
      }
    });

    elFormReserva.addEventListener('submit', handleCrearReservaSubmit);

    // Modal Bloqueo
    elBtnCloseBloqueo.addEventListener('click', () => closeModal(elModalBloqueo));
    elBtnCancelBloqueo.addEventListener('click', () => closeModal(elModalBloqueo));
    elFormBloqueo.addEventListener('submit', handleBloquearSubmit);

    // Modal Detalle / Cancelación
    elBtnCloseDetalle.addEventListener('click', () => closeModal(elModalDetalle));
    elBtnCloseDetalleAction.addEventListener('click', () => closeModal(elModalDetalle));
    elBtnCancelarTurnoAction.addEventListener('click', handleCancelarTurnoClick);

    // Cerrar modales con tecla ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeModal(elModalReserva);
        closeModal(elModalBloqueo);
        closeModal(elModalDetalle);
      }
    });

    // Cerrar al hacer clic en el fondo del modal
    [elModalReserva, elModalBloqueo, elModalDetalle].forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal(modal);
      });
    });
  }

  // =========================================================================
  // CARGA DE DATOS API
  // =========================================================================

  async function loadComplejoInfo() {
    try {
      const resp = await fetch('/api/v1/complejo');
      if (!resp.ok) throw new Error('Error al cargar complejo');
      const data = await resp.json();
      state.complejo = data;
      elComplejoNombre.textContent = data.nombre;

      // Poblar selector de canchas en modal de reserva
      elSelectCanchaReserva.innerHTML = data.canchas
        .filter((c) => c.activa)
        .map((c) => `<option value="${c.id}">${c.nombre} (${c.tipo}) - $${formatCurrency(c.precio)}</option>`)
        .join('');
    } catch (err) {
      console.error(err);
      elComplejoNombre.textContent = 'Complejo Deportivo';
      showToast('No se pudo cargar la información del complejo', 'error');
    }
  }

  async function loadAgendaAndKpis() {
    elLoadingSpinner.style.display = 'flex';
    elAgendaGrid.style.display = 'none';
    elEmptyState.style.display = 'none';

    try {
      // Llamadas concurrentes a agenda y KPIs
      const [agendaResp, kpisResp] = await Promise.all([
        fetch(`/api/v1/agenda?fecha=${state.currentDate}`),
        fetch(`/api/v1/kpis?fecha=${state.currentDate}`),
      ]);

      if (!agendaResp.ok) throw new Error('Error al cargar agenda');
      state.agendaData = await agendaResp.json();

      if (kpisResp.ok) {
        const kpisData = await kpisResp.json();
        updateKpiDisplay(kpisData);
      }

      renderAgenda();
    } catch (err) {
      console.error(err);
      elLoadingSpinner.style.display = 'none';
      elEmptyState.style.display = 'flex';
      showToast('Error al obtener la agenda de turnos', 'error');
    }
  }

  function updateKpiDisplay(kpis) {
    elKpiCanchas.textContent = kpis.total_canchas;
    elKpiReservas.textContent = kpis.reservas_hoy;
    elKpiOcupacion.textContent = `${kpis.ocupacion_pct}%`;
    elKpiProgressBar.style.width = `${Math.min(kpis.ocupacion_pct, 100)}%`;
    elKpiIngresos.textContent = `$${formatCurrency(kpis.ingresos_hoy)}`;
  }

  // =========================================================================
  // RENDERIZADO DE LA AGENDA
  // =========================================================================

  function renderAgenda() {
    elLoadingSpinner.style.display = 'none';

    if (!state.agendaData || !state.agendaData.canchas_agenda.length) {
      elAgendaGrid.style.display = 'none';
      elEmptyState.style.display = 'flex';
      return;
    }

    // Filtrar canchas según chip seleccionado
    const canchasFiltradas = state.agendaData.canchas_agenda.filter((ca) => {
      if (state.activeFilter === 'todas') return true;
      return ca.cancha.tipo.toLowerCase().includes(state.activeFilter.toLowerCase());
    });

    if (!canchasFiltradas.length) {
      elAgendaGrid.style.display = 'none';
      elEmptyState.style.display = 'flex';
      return;
    }

    elEmptyState.style.display = 'none';
    elAgendaGrid.style.display = 'grid';

    elAgendaGrid.innerHTML = canchasFiltradas
      .map((ca) => {
        const c = ca.cancha;
        const sportClass = c.tipo.toLowerCase().includes('fútbol') ? 'futbol' : 'padel';

        const slotsHtml = ca.slots
          .map((slot) => {
            const estado = slot.estado; // "libre", "confirmada", "bloqueada"

            let bodyHtml = '';
            let actionButtons = '';

            if (estado === 'libre') {
              bodyHtml = `
                <div class="slot-info-row">
                  <span class="slot-client-name" style="color: var(--text-dim); font-weight: 400;">Disponible</span>
                  <span class="slot-price-tag">$${formatCurrency(slot.precio)}</span>
                </div>
              `;
              actionButtons = `
                <div class="slot-actions-row">
                  <button class="btn-slot-action btn-action-book" 
                    onclick="window.quickBook(${c.id}, '${slot.fecha_inicio_iso}', '${slot.hora_inicio}', ${slot.precio})">
                    + Reservar
                  </button>
                  <button class="btn-slot-action btn-action-block" 
                    onclick="window.quickBlock(${c.id}, '${c.nombre}', '${slot.fecha_inicio_iso}', '${slot.hora_inicio} a ${slot.hora_fin}')">
                    🔒
                  </button>
                </div>
              `;
            } else if (estado === 'confirmada') {
              bodyHtml = `
                <div class="slot-info-row">
                  <span class="slot-client-name" title="${escapeHtml(slot.cliente_nombre || '')}">
                    👤 ${escapeHtml(slot.cliente_nombre || 'Cliente')}
                  </span>
                  <span class="slot-price-tag" style="color: var(--cyan-accent);">$${formatCurrency(slot.precio)}</span>
                </div>
                ${slot.cliente_telefono ? `<div style="font-size: 0.75rem; color: var(--text-dim);">📞 ${escapeHtml(slot.cliente_telefono)}</div>` : ''}
              `;
            } else if (estado === 'bloqueada') {
              bodyHtml = `
                <div class="slot-info-row">
                  <span class="slot-client-name" style="color: #fcd34d;">🔒 ${escapeHtml(slot.notas || 'Bloqueado')}</span>
                </div>
              `;
            }

            const clickAttr =
              estado !== 'libre'
                ? `onclick="window.openTurnoDetalle(${JSON.stringify(slot).replace(/"/g, '&quot;')}, '${escapeHtml(c.nombre)}', '${c.tipo}')"`
                : '';

            return `
              <div class="slot-card slot-${estado}" ${clickAttr}>
                <div class="slot-time-row">
                  <span class="slot-time">${slot.hora_inicio} - ${slot.hora_fin}</span>
                  <span class="slot-status-pill pill-${estado}">${estado}</span>
                </div>
                ${bodyHtml}
                ${actionButtons}
              </div>
            `;
          })
          .join('');

        return `
          <div class="court-column">
            <div class="court-column-header">
              <div class="court-title-row">
                <h3 class="court-name">${escapeHtml(c.nombre)}</h3>
                <span class="sport-tag ${sportClass}">${escapeHtml(c.tipo)}</span>
              </div>
              <div class="court-meta">
                <span>⏱️ ${c.duracion_minutos} min</span>
                <span>💲 $${formatCurrency(c.precio)}</span>
              </div>
            </div>
            <div class="court-slots-list">
              ${slotsHtml}
            </div>
          </div>
        `;
      })
      .join('');
  }

  // =========================================================================
  // ACCIONES RÁPIDAS Y MODALES
  // =========================================================================

  window.quickBook = function (canchaId, fechaInicioIso, horaInicio, precio) {
    openModalReserva(canchaId, state.currentDate, horaInicio, precio);
  };

  window.quickBlock = function (canchaId, canchaNombre, fechaInicioIso, horarioTexto) {
    elBloqueoCanchaId.value = canchaId;
    elBloqueoFechaInicio.value = fechaInicioIso;
    elBloqueoInfoDisplay.textContent = `${canchaNombre} | ${state.currentDate} (${horarioTexto})`;
    openModal(elModalBloqueo);
  };

  window.openTurnoDetalle = function (slot, canchaNombre, canchaTipo) {
    state.selectedTurno = slot;

    document.getElementById('det-cancha').textContent = `${canchaNombre} (${canchaTipo})`;
    document.getElementById('det-horario').textContent = `${state.currentDate} | ${slot.hora_inicio} a ${slot.hora_fin}`;
    document.getElementById('det-cliente').textContent = slot.cliente_nombre || 'N/A';
    document.getElementById('det-telefono').textContent = slot.cliente_telefono || 'No registrado';
    document.getElementById('det-precio').textContent = `$${formatCurrency(slot.precio)}`;
    document.getElementById('det-estado').textContent = slot.estado.toUpperCase();
    document.getElementById('det-notas').textContent = slot.notas || 'Sin notas';

    if (slot.estado === 'bloqueada') {
      document.getElementById('detalle-titulo').textContent = 'Turno Bloqueado';
      document.getElementById('detalle-subtitulo').textContent = 'Horario inhabilitado por el complejo';
      elBtnCancelarTurnoText.textContent = 'Desbloquear Horario';
      elBtnCancelarTurnoAction.className = 'btn-warning';
    } else {
      document.getElementById('detalle-titulo').textContent = 'Detalle de Reserva';
      document.getElementById('detalle-subtitulo').textContent = 'Información registrada en el sistema';
      elBtnCancelarTurnoText.textContent = 'Cancelar Reserva';
      elBtnCancelarTurnoAction.className = 'btn-danger';
    }

    openModal(elModalDetalle);
  };

  function openModalReserva(canchaId = null, fecha = null, hora = null, precio = null) {
    elFormReserva.reset();

    if (canchaId) elSelectCanchaReserva.value = canchaId;
    elInputFechaReserva.value = fecha || state.currentDate;
    if (hora) elInputHoraReserva.value = hora;

    const selectedCancha = state.complejo?.canchas.find((c) => c.id === parseInt(elSelectCanchaReserva.value));
    elInputPrecioReserva.value = precio !== null ? precio : selectedCancha?.precio || '';

    openModal(elModalReserva);
  }

  async function handleCrearReservaSubmit(e) {
    e.preventDefault();
    const canchaId = parseInt(elSelectCanchaReserva.value);
    const fecha = elInputFechaReserva.value;
    const hora = elInputHoraReserva.value;
    const nombre = document.getElementById('reserva-cliente').value.trim();
    const telefono = document.getElementById('reserva-telefono').value.trim() || null;
    const precio = parseFloat(elInputPrecioReserva.value) || null;
    const notas = document.getElementById('reserva-notas').value.trim() || null;

    if (!fecha || !hora || !nombre) {
      showToast('Por favor completa los campos obligatorios', 'error');
      return;
    }

    const fechaInicioIso = `${fecha}T${hora}:00Z`;

    const submitBtn = document.getElementById('btn-submit-reserva');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Guardando...';

    try {
      const resp = await fetch('/api/v1/reservas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cancha_id: canchaId,
          fecha_inicio: fechaInicioIso,
          cliente_nombre: nombre,
          cliente_telefono: telefono,
          precio: precio,
          notas: notas,
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || 'Error al crear la reserva');
      }

      closeModal(elModalReserva);
      showToast(`¡Reserva confirmada para ${nombre}!`, 'success');
      await loadAgendaAndKpis();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Confirmar Reserva';
    }
  }

  async function handleBloquearSubmit(e) {
    e.preventDefault();
    const canchaId = parseInt(elBloqueoCanchaId.value);
    const fechaInicioIso = elBloqueoFechaInicio.value;
    const motivo = document.getElementById('bloqueo-motivo').value;

    const submitBtn = document.getElementById('btn-submit-bloqueo');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Bloqueando...';

    try {
      const resp = await fetch('/api/v1/bloqueos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cancha_id: canchaId,
          fecha_inicio: fechaInicioIso,
          motivo: motivo,
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || 'Error al bloquear horario');
      }

      closeModal(elModalBloqueo);
      showToast('Horario bloqueado con éxito', 'info');
      await loadAgendaAndKpis();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Bloquear Horario';
    }
  }

  async function handleCancelarTurnoClick() {
    if (!state.selectedTurno || !state.selectedTurno.reserva_id) return;
    const isBloqueo = state.selectedTurno.estado === 'bloqueada';
    const reservaId = state.selectedTurno.reserva_id;

    const confirmMsg = isBloqueo
      ? '¿Confirmas que deseas desbloquear este turno para que vuelva a estar libre?'
      : '¿Seguro que deseas cancelar esta reserva? El turno quedará disponible de inmediato.';

    if (!confirm(confirmMsg)) return;

    const url = isBloqueo
      ? `/api/v1/bloqueos/${reservaId}/desbloquear`
      : `/api/v1/reservas/${reservaId}/cancelar`;

    try {
      const resp = await fetch(url, { method: 'POST' });
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || 'Error al procesar la acción');
      }

      closeModal(elModalDetalle);
      showToast(isBloqueo ? 'Horario desbloqueado' : 'Reserva cancelada con éxito', 'info');
      await loadAgendaAndKpis();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // =========================================================================
  // UTILIDADES
  // =========================================================================

  function shiftDate(days) {
    const [y, m, d] = state.currentDate.split('-').map(Number);
    const dateObj = new Date(Date.UTC(y, m - 1, d));
    dateObj.setUTCDate(dateObj.getUTCDate() + days);

    const newIso = dateObj.toISOString().split('T')[0];
    state.currentDate = newIso;
    elDateInput.value = newIso;
    loadAgendaAndKpis();
  }

  function getTodayIsoString() {
    const today = new Date();
    const y = today.getFullYear();
    const m = String(today.getMonth() + 1).padStart(2, '0');
    const d = String(today.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  function formatCurrency(val) {
    if (val === undefined || val === null || isNaN(val)) return '0';
    return Number(val).toLocaleString('es-AR');
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function openModal(modalEl) {
    modalEl.classList.add('active');
    modalEl.setAttribute('aria-hidden', 'false');
  }

  function closeModal(modalEl) {
    modalEl.classList.remove('active');
    modalEl.setAttribute('aria-hidden', 'true');
  }

  function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = '✓';
    if (type === 'error') icon = '✕';
    if (type === 'info') icon = 'ℹ';

    toast.innerHTML = `<span style="font-weight: bold;">${icon}</span> <span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
});
