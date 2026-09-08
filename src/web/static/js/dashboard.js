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
    slotsMap: new Map(),
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
  const elAgendaFilters = document.getElementById('agenda-filters');

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

  // Gestión de Canchas
  const elBtnGestionarCanchas = document.getElementById('btn-gestionar-canchas');
  const elModalCanchas = document.getElementById('modal-canchas');
  const elBtnCloseCanchas = document.getElementById('btn-close-canchas');
  const elBtnCloseCanchasAction = document.getElementById('btn-close-canchas-action');
  const elCanchasListContainer = document.getElementById('canchas-list-container');
  const elCanchasTotalBadge = document.getElementById('canchas-total-badge');
  const elBtnNuevaCancha = document.getElementById('btn-nueva-cancha');

  // Formulario Cancha
  const elModalFormCancha = document.getElementById('modal-form-cancha');
  const elFormCancha = document.getElementById('form-cancha');
  const elCanchaEditId = document.getElementById('cancha-edit-id');
  const elFormCanchaTitle = document.getElementById('form-cancha-title');
  const elFormCanchaSubtitle = document.getElementById('form-cancha-subtitle');
  const elCanchaNombre = document.getElementById('cancha-nombre');
  const elCanchaTipo = document.getElementById('cancha-tipo');
  const elCanchaDuracion = document.getElementById('cancha-duracion');
  const elCanchaPrecio = document.getElementById('cancha-precio');
  const elCanchaActiva = document.getElementById('cancha-activa');
  const elBtnCloseFormCancha = document.getElementById('btn-close-form-cancha');
  const elBtnCancelFormCancha = document.getElementById('btn-cancel-form-cancha');

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

    // Gestión de Canchas
    elBtnGestionarCanchas.addEventListener('click', openModalCanchas);
    elBtnCloseCanchas.addEventListener('click', () => closeModal(elModalCanchas));
    elBtnCloseCanchasAction.addEventListener('click', () => closeModal(elModalCanchas));
    elBtnNuevaCancha.addEventListener('click', () => openModalFormCancha(null));

    // Formulario Cancha
    elBtnCloseFormCancha.addEventListener('click', () => closeModal(elModalFormCancha));
    elBtnCancelFormCancha.addEventListener('click', () => closeModal(elModalFormCancha));
    elFormCancha.addEventListener('submit', handleFormCanchaSubmit);

    // Cerrar modales con tecla ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeModal(elModalReserva);
        closeModal(elModalBloqueo);
        closeModal(elModalDetalle);
        closeModal(elModalCanchas);
        closeModal(elModalFormCancha);
      }
    });

    // Cerrar al hacer clic en el fondo del modal
    [elModalReserva, elModalBloqueo, elModalDetalle, elModalCanchas, elModalFormCancha].forEach((modal) => {
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

      updateFilterChips();
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
  // HELPER DE DEPORTES Y FILTROS DINÁMICOS
  // =========================================================================

  function getSportClassAndEmoji(tipoRaw) {
    const tipo = (tipoRaw || '').toLowerCase();
    if (tipo.includes('fútbol') || tipo.includes('futbol')) {
      return { sportClass: 'futbol', emoji: '⚽', label: 'Fútbol' };
    }
    if (tipo.includes('pádel') || tipo.includes('padel')) {
      return { sportClass: 'padel', emoji: '🎾', label: 'Pádel' };
    }
    if (tipo.includes('tenis')) {
      return { sportClass: 'tenis', emoji: '🎾', label: 'Tenis' };
    }
    if (tipo.includes('básquet') || tipo.includes('basquet') || tipo.includes('basket')) {
      return { sportClass: 'basquet', emoji: '🏀', label: 'Básquet' };
    }
    const cleanLabel = tipoRaw ? tipoRaw.charAt(0).toUpperCase() + tipoRaw.slice(1) : 'Otro';
    return { sportClass: 'otro', emoji: '🏆', label: cleanLabel };
  }

  function updateFilterChips() {
    if (!elAgendaFilters) return;

    // Obtener los deportes únicos presentes en las canchas de la agenda
    const availableSports = new Map(); // key: sportClass, value: displayLabel

    if (state.agendaData && state.agendaData.canchas_agenda) {
      state.agendaData.canchas_agenda.forEach((ca) => {
        const { sportClass, label } = getSportClassAndEmoji(ca.cancha.tipo);
        if (!availableSports.has(sportClass)) {
          availableSports.set(sportClass, label);
        }
      });
    }

    // Si el filtro activo ya no existe entre las canchas disponibles, volver a "todas"
    if (state.activeFilter !== 'todas' && !availableSports.has(state.activeFilter)) {
      state.activeFilter = 'todas';
    }

    let chipsHtml = `
      <button class="filter-chip ${state.activeFilter === 'todas' ? 'active' : ''}" data-filter="todas">
        Todas las canchas
      </button>
    `;

    availableSports.forEach((label, sportKey) => {
      const isActive = state.activeFilter === sportKey;
      chipsHtml += `
        <button class="filter-chip ${isActive ? 'active' : ''}" data-filter="${sportKey}">
          ${escapeHtml(label)}
        </button>
      `;
    });

    elAgendaFilters.innerHTML = chipsHtml;

    // Conectar eventos click a los chips generados
    elAgendaFilters.querySelectorAll('.filter-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        elAgendaFilters.querySelectorAll('.filter-chip').forEach((c) => c.classList.remove('active'));
        chip.classList.add('active');
        state.activeFilter = chip.dataset.filter;
        renderAgenda();
      });
    });
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
      const { sportClass } = getSportClassAndEmoji(ca.cancha.tipo);
      return sportClass === state.activeFilter;
    });

    if (!canchasFiltradas.length) {
      elAgendaGrid.style.display = 'none';
      elEmptyState.style.display = 'flex';
      return;
    }

    elEmptyState.style.display = 'none';
    elAgendaGrid.style.display = 'flex';

    if (canchasFiltradas.length <= 3) {
      elAgendaGrid.classList.add('few-courts');
    } else {
      elAgendaGrid.classList.remove('few-courts');
    }

    state.slotsMap.clear();

    elAgendaGrid.innerHTML = canchasFiltradas
      .map((ca) => {
        const c = ca.cancha;
        const { sportClass } = getSportClassAndEmoji(c.tipo);

        const slotsHtml = ca.slots
          .map((slot) => {
            const estado = slot.estado; // "libre", "confirmada", "bloqueada"

            if (slot.reserva_id) {
              state.slotsMap.set(String(slot.reserva_id), {
                slot,
                canchaNombre: c.nombre,
                canchaTipo: c.tipo,
              });
            }

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
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                    Reservar
                  </button>
                  <button class="btn-slot-action btn-action-block" 
                    onclick="window.quickBlock(${c.id}, '${escapeHtml(c.nombre)}', '${slot.fecha_inicio_iso}', '${slot.hora_inicio} a ${slot.hora_fin}')"
                    title="Bloquear este horario por mantenimiento o clima">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                    Bloquear
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
              actionButtons = `
                <div class="slot-actions-row">
                  <button class="btn-slot-action btn-action-detail" 
                    onclick="window.openTurnoPorId(${slot.reserva_id})">
                    Detalles / Cancelar
                  </button>
                </div>
              `;
            } else if (estado === 'bloqueada') {
              bodyHtml = `
                <div class="slot-info-row">
                  <span class="slot-client-name" style="color: #fcd34d;">🔒 ${escapeHtml(slot.notas || 'Bloqueado')}</span>
                </div>
              `;
              actionButtons = `
                <div class="slot-actions-row">
                  <button class="btn-slot-action btn-action-unblock" 
                    onclick="window.quickUnblock(event, ${slot.reserva_id})">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>
                    Desbloquear Horario
                  </button>
                </div>
              `;
            }

            const clickAttr =
              estado !== 'libre' && slot.reserva_id
                ? `onclick="window.openTurnoPorId(${slot.reserva_id})"`
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

  window.quickUnblock = async function (event, reservaId) {
    if (event) event.stopPropagation();
    try {
      const resp = await fetch(`/api/v1/bloqueos/${reservaId}/desbloquear`, { method: 'POST' });
      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.detail || 'Error al desbloquear');
      }
      showToast('Horario desbloqueado correctamente', 'info');
      await loadAgendaAndKpis();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.openTurnoPorId = function (reservaId) {
    const data = state.slotsMap.get(String(reservaId));
    if (!data) return;
    window.openTurnoDetalle(data.slot, data.canchaNombre, data.canchaTipo);
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

    const isBloqueo = slot.estado === 'bloqueada';
    const elBtnIcon = document.getElementById('btn-cancelar-turno-icon');

    if (isBloqueo) {
      document.getElementById('detalle-titulo').textContent = 'Turno Bloqueado';
      document.getElementById('detalle-subtitulo').textContent = 'Horario inhabilitado por el complejo';
      elBtnCancelarTurnoText.textContent = 'Desbloquear Horario';
      elBtnCancelarTurnoAction.className = 'btn-action-dialog action-warning';
      if (elBtnIcon) {
        elBtnIcon.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>`;
      }
    } else {
      document.getElementById('detalle-titulo').textContent = 'Detalle de Reserva';
      document.getElementById('detalle-subtitulo').textContent = 'Información registrada en el sistema';
      elBtnCancelarTurnoText.textContent = 'Cancelar Reserva';
      elBtnCancelarTurnoAction.className = 'btn-action-dialog action-danger';
      if (elBtnIcon) {
        elBtnIcon.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
      }
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

    const url = isBloqueo
      ? `/api/v1/bloqueos/${reservaId}/desbloquear`
      : `/api/v1/reservas/${reservaId}/cancelar`;

    elBtnCancelarTurnoAction.disabled = true;
    elBtnCancelarTurnoText.textContent = isBloqueo ? 'Desbloqueando...' : 'Cancelando...';

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
    } finally {
      elBtnCancelarTurnoAction.disabled = false;
      elBtnCancelarTurnoText.textContent = isBloqueo ? 'Desbloquear Horario' : 'Cancelar Reserva';
    }
  }


  // =========================================================================
  // GESTIÓN DE CANCHAS
  // =========================================================================

  async function openModalCanchas() {
    openModal(elModalCanchas);
    elCanchasListContainer.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-dim);">Cargando canchas...</div>';

    try {
      const resp = await fetch('/api/v1/canchas');
      if (!resp.ok) throw new Error('Error al obtener lista de canchas');
      const canchas = await resp.json();
      state.allCanchas = canchas;
      renderCanchasList(canchas);
    } catch (err) {
      console.error(err);
      elCanchasListContainer.innerHTML = `<div style="padding: 2rem; text-align: center; color: var(--danger);">Error al cargar canchas</div>`;
      showToast(err.message, 'error');
    }
  }

  function renderCanchasList(canchas) {
    if (!canchas || !canchas.length) {
      elCanchasListContainer.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: var(--text-dim);">
          No hay canchas registradas en el complejo. Crea la primera haciendo clic en "Nueva Cancha".
        </div>
      `;
      elCanchasTotalBadge.textContent = '0 canchas';
      return;
    }

    elCanchasTotalBadge.textContent = `${canchas.length} cancha${canchas.length === 1 ? '' : 's'} configurada${canchas.length === 1 ? '' : 's'}`;

    elCanchasListContainer.innerHTML = canchas
      .map((c) => {
        const { sportClass, emoji } = getSportClassAndEmoji(c.tipo);

        return `
          <div class="cancha-item-card ${c.activa ? '' : 'is-inactive'}" id="cancha-card-${c.id}">
            <div class="cancha-item-left">
              <div class="cancha-item-icon ${sportClass}">${emoji}</div>
              <div class="cancha-item-details">
                <div class="cancha-item-title-row">
                  <span class="cancha-item-name">${escapeHtml(c.nombre)}</span>
                  <span class="sport-tag ${sportClass}">${escapeHtml(c.tipo)}</span>
                </div>
                <div class="cancha-item-meta">
                  <span class="cancha-meta-chip">⏱️ ${c.duracion_minutos} min</span>
                  <span class="cancha-meta-chip">💲 $${formatCurrency(c.precio)}</span>
                </div>
              </div>
            </div>
            <div class="cancha-item-right">
              <div class="toggle-switch-wrapper" title="Habilitar o inhabilitar cancha en la agenda">
                <label class="toggle-switch">
                  <input type="checkbox" id="toggle-cancha-${c.id}" ${c.activa ? 'checked' : ''} onchange="window.handleToggleCancha(event, ${c.id})">
                  <span class="toggle-slider"></span>
                </label>
                <span class="toggle-status-label ${c.activa ? 'active' : 'inactive'}" id="toggle-label-${c.id}">
                  ${c.activa ? 'Activa' : 'Inactiva'}
                </span>
              </div>
              <button class="btn-edit-cancha" onclick="window.handleEditCancha(${c.id})" title="Editar tarifa o especificaciones">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                Editar
              </button>
            </div>
          </div>
        `;
      })
      .join('');
  }

  window.handleToggleCancha = async function (event, canchaId) {
    const checkbox = event.target;
    const card = document.getElementById(`cancha-card-${canchaId}`);
    const label = document.getElementById(`toggle-label-${canchaId}`);

    checkbox.disabled = true;

    try {
      const resp = await fetch(`/api/v1/canchas/${canchaId}/toggle`, { method: 'PATCH' });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Error al cambiar estado de la cancha');
      }
      const updated = await resp.json();

      // Actualizar estado en memoria
      const idx = state.allCanchas?.findIndex((c) => c.id === canchaId);
      if (idx !== undefined && idx !== -1) {
        state.allCanchas[idx] = updated;
      }

      checkbox.checked = updated.activa;
      if (updated.activa) {
        card.classList.remove('is-inactive');
        label.className = 'toggle-status-label active';
        label.textContent = 'Activa';
        showToast(`Cancha "${updated.nombre}" activada`, 'success');
      } else {
        card.classList.add('is-inactive');
        label.className = 'toggle-status-label inactive';
        label.textContent = 'Inactiva';
        showToast(`Cancha "${updated.nombre}" desactivada de la agenda`, 'info');
      }

      // Sincronizar selectores y agenda en tiempo real
      await loadComplejoInfo();
      await loadAgendaAndKpis();
    } catch (err) {
      checkbox.checked = !checkbox.checked; // revertir en caso de fallo
      showToast(err.message, 'error');
    } finally {
      checkbox.disabled = false;
    }
  };

  window.handleEditCancha = function (canchaId) {
    const cancha = state.allCanchas?.find((c) => c.id === canchaId);
    if (!cancha) return;
    openModalFormCancha(cancha);
  };

  function openModalFormCancha(cancha = null) {
    if (cancha) {
      elFormCanchaTitle.textContent = 'Editar Cancha';
      elFormCanchaSubtitle.textContent = `Modifica las especificaciones de ${cancha.nombre}`;
      elCanchaEditId.value = cancha.id;
      elCanchaNombre.value = cancha.nombre;
      elCanchaTipo.value = cancha.tipo;
      elCanchaDuracion.value = cancha.duracion_minutos;
      elCanchaPrecio.value = cancha.precio;
      elCanchaActiva.checked = cancha.activa;
    } else {
      elFormCanchaTitle.textContent = 'Nueva Cancha';
      elFormCanchaSubtitle.textContent = 'Configura los parámetros del espacio deportivo';
      elFormCancha.reset();
      elCanchaEditId.value = '';
      elCanchaDuracion.value = '60';
      elCanchaActiva.checked = true;
    }
    openModal(elModalFormCancha);
  }

  async function handleFormCanchaSubmit(e) {
    e.preventDefault();
    const id = elCanchaEditId.value;
    const isEdit = Boolean(id);

    const payload = {
      nombre: elCanchaNombre.value.trim(),
      tipo: elCanchaTipo.value,
      duracion_minutos: parseInt(elCanchaDuracion.value),
      precio: parseFloat(elCanchaPrecio.value),
      activa: elCanchaActiva.checked,
    };

    const submitBtn = document.getElementById('btn-submit-cancha');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Guardando...';

    try {
      const url = isEdit ? `/api/v1/canchas/${id}` : '/api/v1/canchas';
      const method = isEdit ? 'PUT' : 'POST';

      const resp = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Error al guardar la cancha');
      }

      closeModal(elModalFormCancha);
      showToast(isEdit ? 'Cancha actualizada con éxito' : 'Cancha creada con éxito', 'success');

      // Actualizar listado en modal de canchas si está activo
      await openModalCanchas();
      // Actualizar agenda y KPIs
      await loadComplejoInfo();
      await loadAgendaAndKpis();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Guardar Cancha';
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
