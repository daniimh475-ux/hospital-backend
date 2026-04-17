const API_BASE_URL = '/api';
const STORAGE_TOKEN = 'portal_token';
const STORAGE_ROLE = 'portal_role';

const state = {
    token: sessionStorage.getItem(STORAGE_TOKEN) || '',
    role: sessionStorage.getItem(STORAGE_ROLE) || '',
    profile: null,
    areas: [],
    citas: [],
    currentView: 'citas',
    editingCitaId: null,
};

const elements = {
    heroPanel: document.querySelector('.hero-panel'),
    authView: document.getElementById('auth-view'),
    dashboardView: document.getElementById('dashboard-view'),
    loginPanel: document.getElementById('login-panel'),
    resetPanel: document.getElementById('reset-panel'),
    registerPanel: document.getElementById('register-panel'),
    loginForm: document.getElementById('login-form'),
    resetForm: document.getElementById('reset-form'),
    registerForm: document.getElementById('register-form'),
    tabLogin: document.getElementById('tab-login'),
    tabRegister: document.getElementById('tab-register'),
    forgotPasswordBtn: document.getElementById('forgot-password-btn'),
    backLoginBtn: document.getElementById('back-login-btn'),
    messageBox: document.getElementById('message-box'),
    contentView: document.getElementById('content-view'),
    welcomeName: document.getElementById('welcome-name'),
    profileSummary: document.getElementById('profile-summary'),
    logoutBtn: document.getElementById('logout-btn'),
    navButtons: Array.from(document.querySelectorAll('.nav-btn')),
};

function setPortalMode(mode) {
    document.body.classList.toggle('in-dashboard', mode === 'dashboard');
    if (elements.heroPanel) {
        elements.heroPanel.classList.toggle('hidden', mode === 'dashboard');
    }
}

function showMessage(message, type = 'info') {
    elements.messageBox.textContent = message;
    elements.messageBox.className = `message-box ${type}`;
    clearTimeout(showMessage.timer);
    showMessage.timer = setTimeout(() => {
        elements.messageBox.className = 'message-box hidden';
    }, 5000);
}

function apiErrorMessage(error, fallback) {
    if (error && typeof error === 'object' && error.detail) {
        return error.detail;
    }
    if (typeof error === 'string' && error.trim()) {
        return error;
    }
    return fallback;
}

async function request(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers,
    });

    const text = await response.text();
    let data = null;
    try {
        data = text ? JSON.parse(text) : null;
    } catch {
        data = text;
    }

    if (!response.ok) {
        throw data || { detail: 'Ocurrió un error en la solicitud' };
    }
    return data;
}

function switchAuthTab(tab) {
    const isLogin = tab === 'login';
    elements.tabLogin.classList.toggle('active', isLogin);
    elements.tabRegister.classList.toggle('active', !isLogin);
    elements.loginPanel.classList.toggle('hidden', !isLogin);
    elements.resetPanel.classList.add('hidden');
    elements.registerPanel.classList.toggle('hidden', isLogin);
}

function showResetPanel() {
    elements.tabLogin.classList.remove('active');
    elements.tabRegister.classList.remove('active');
    elements.loginPanel.classList.add('hidden');
    elements.registerPanel.classList.add('hidden');
    elements.resetPanel.classList.remove('hidden');
}

function setSession(token, role) {
    state.token = token;
    state.role = role;
    sessionStorage.setItem(STORAGE_TOKEN, token);
    sessionStorage.setItem(STORAGE_ROLE, role);
}

function clearSession() {
    state.token = '';
    state.role = '';
    state.profile = null;
    state.areas = [];
    state.citas = [];
    state.editingCitaId = null;
    sessionStorage.removeItem(STORAGE_TOKEN);
    sessionStorage.removeItem(STORAGE_ROLE);
}

function setActiveView(view) {
    state.currentView = view;
    elements.navButtons.forEach((button) => {
        button.classList.toggle('active', button.dataset.view === view);
    });
}

async function loadAreas() {
    const data = await request('/areas');
    state.areas = Array.isArray(data) ? data : [];
}

async function loadProfile() {
    state.profile = await request('/mi-perfil');
    const fullName = `${state.profile.nombre} ${state.profile.apellido}`.trim();
    elements.welcomeName.textContent = `Bienvenido, ${fullName}`;
    elements.profileSummary.textContent = `${state.profile.email} · ${state.profile.fecha_nacimiento}`;
}

async function loadCitas() {
    state.citas = await request('/mis-citas');
}

async function loadDashboard() {
    await Promise.all([loadProfile(), loadAreas(), loadCitas()]);
    setPortalMode('dashboard');
    elements.authView.classList.add('hidden');
    elements.dashboardView.classList.remove('hidden');
    await renderView(state.currentView);
}

function renderLoading(title, text) {
    elements.contentView.innerHTML = `
        <section class="card section-card">
            <h3>${title}</h3>
            <p>${text}</p>
        </section>
    `;
}

function createAppointmentRows() {
    if (!state.citas.length) {
        return '<div class="empty-state">No tienes citas activas registradas.</div>';
    }

    return `
        <div class="table-wrap">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Hora</th>
                        <th>Área</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    ${state.citas.map((cita) => {
                        const when = new Date(cita.fecha);
                        const date = when.toLocaleDateString('es-MX');
                        const time = when.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
                        return `
                            <tr>
                                <td>${date}</td>
                                <td>${time}</td>
                                <td>${cita.area}</td>
                                <td class="actions-cell">
                                    <button class="ghost-btn" type="button" onclick="window.portalApp.editCita('${cita.id}')">Modificar</button>
                                    <button class="danger-btn" type="button" onclick="window.portalApp.deleteCita('${cita.id}')">Cancelar</button>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function areaOptions() {
    return state.areas.map((area) => `<option value="${area.nombre}">${area.nombre}</option>`).join('');
}

function buildAppointmentDate(date, time) {
    if (!date || !time) {
        return null;
    }
    const when = new Date(`${date}T${time}:00`);
    if (Number.isNaN(when.getTime())) {
        return null;
    }
    return when;
}

function validateAppointmentRules(when, editingId = null) {
    const now = new Date();
    if (when < now) {
        return 'No se pueden agendar citas en fechas pasadas.';
    }

    const activeAppointments = state.citas.filter((cita) => String(cita.id) !== String(editingId));
    if (!editingId && activeAppointments.length >= 3) {
        return 'No puedes tener más de 3 citas activas.';
    }

    const existsAtSameTime = activeAppointments.some((cita) => {
        const citaDate = new Date(cita.fecha);
        return citaDate.getTime() === when.getTime();
    });

    if (existsAtSameTime) {
        return 'Ya tienes una cita en ese mismo horario.';
    }

    return null;
}

function getCitaById(citaId) {
    return state.citas.find((cita) => String(cita.id) === String(citaId)) || null;
}

function renderCitasView() {
    const editing = state.editingCitaId ? getCitaById(state.editingCitaId) : null;
    const dateValue = editing ? new Date(editing.fecha).toISOString().slice(0, 10) : '';
    const timeValue = editing ? new Date(editing.fecha).toISOString().slice(11, 16) : '';

    elements.contentView.innerHTML = `
        <section class="card section-card">
            <div class="section-head">
                <div>
                    <span class="eyebrow">Gestión de citas</span>
                    <h3>Mis citas</h3>
                </div>
                <button class="secondary-btn" type="button" onclick="window.portalApp.newCita()">Nueva cita</button>
            </div>
            <p class="section-copy">Puedes agendar, modificar o cancelar tus citas. El sistema bloquea duplicados, más de 3 citas activas y fechas pasadas.</p>
            ${createAppointmentRows()}
        </section>

        <section class="card section-card">
            <div class="section-head compact">
                <h3>${editing ? 'Modificar cita' : 'Agendar cita'}</h3>
            </div>
            <form id="appointment-form" class="form-grid two-columns">
                <label>
                    <span>Fecha</span>
                    <input type="date" id="appointment-date" value="${dateValue}" required>
                </label>
                <label>
                    <span>Hora</span>
                    <input type="time" id="appointment-time" value="${timeValue}" required>
                </label>
                <label class="full-width">
                    <span>Área</span>
                    <select id="appointment-area" required>
                        <option value="">Selecciona un área</option>
                        ${areaOptions()}
                    </select>
                </label>
                <div class="full-width form-actions">
                    <button class="primary-btn" type="submit">${editing ? 'Guardar cambios' : 'Agendar cita'}</button>
                    ${editing ? '<button class="secondary-btn" type="button" id="cancel-edit-btn">Cancelar edición</button>' : ''}
                </div>
            </form>
        </section>
    `;

    if (editing) {
        document.getElementById('appointment-area').value = editing.area;
        document.getElementById('cancel-edit-btn').addEventListener('click', () => {
            state.editingCitaId = null;
            renderCitasView();
        });
    }

    document.getElementById('appointment-form').addEventListener('submit', submitAppointmentForm);
}

function renderHistoryRows(items) {
    if (!items.length) {
        return '<div class="empty-state">Aún no tienes registros en tu historial.</div>';
    }

    return items.map((item) => `
        <article class="timeline-item">
            <div class="timeline-date">${item.fecha}</div>
            <div class="timeline-body">
                <strong>${item.tipo}</strong>
                <p>${item.descripcion}</p>
            </div>
        </article>
    `).join('');
}

async function renderHistorialView() {
    renderLoading('Historial médico', 'Cargando historial...');
    const historial = await request('/mi-historial');
    elements.contentView.innerHTML = `
        <section class="card section-card">
            <div class="section-head compact">
                <div>
                    <span class="eyebrow">Seguimiento clínico</span>
                    <h3>Historial médico</h3>
                </div>
            </div>
            <div class="timeline">${renderHistoryRows(historial)}</div>
        </section>
    `;
}

function renderPerfilView() {
    const p = state.profile;
    elements.contentView.innerHTML = `
        <section class="card section-card">
            <div class="section-head compact">
                <div>
                    <span class="eyebrow">Datos del paciente</span>
                    <h3>Mi perfil</h3>
                </div>
            </div>
            <div class="profile-grid">
                <div><span>Nombre</span><strong>${p.nombre} ${p.apellido}</strong></div>
                <div><span>Correo</span><strong>${p.email}</strong></div>
                <div><span>Fecha de nacimiento</span><strong>${p.fecha_nacimiento}</strong></div>
                <div><span>Sexo</span><strong>${p.sexo}</strong></div>
                <div><span>Teléfono</span><strong>${p.telefono || 'No registrado'}</strong></div>
                <div><span>Dirección</span><strong>${p.direccion || 'No registrada'}</strong></div>
            </div>
        </section>
    `;
}

async function renderView(view) {
    setActiveView(view);

    try {
        if (view === 'citas') {
            await loadCitas();
            renderCitasView();
            return;
        }
        if (view === 'historial') {
            await renderHistorialView();
            return;
        }
        if (view === 'perfil') {
            renderPerfilView();
        }
    } catch (error) {
        showMessage(apiErrorMessage(error, 'No se pudo cargar la información.'), 'error');
    }
}

async function submitLogin(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-pass').value.trim();

    const body = new URLSearchParams();
    body.set('username', email);
    body.set('password', password);

    try {
        const data = await request('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body,
        });

        if (data.rol !== 'paciente') {
            throw { detail: 'Este portal es exclusivo para cuentas de paciente.' };
        }

        setSession(data.access_token, data.rol);
        showMessage('Sesión iniciada correctamente.', 'success');
        await loadDashboard();
    } catch (error) {
        showMessage(apiErrorMessage(error, 'No se pudo iniciar sesión.'), 'error');
    }
}

async function submitRegister(event) {
    event.preventDefault();
    const payload = {
        nombre: document.getElementById('reg-nombre').value.trim(),
        apellido: document.getElementById('reg-apellido').value.trim(),
        fecha_nacimiento: document.getElementById('reg-fecha').value,
        sexo: document.getElementById('reg-sexo').value,
        telefono: document.getElementById('reg-telefono').value.trim(),
        direccion: document.getElementById('reg-direccion').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        password: document.getElementById('reg-pass').value.trim(),
    };

    try {
        await request('/portal/registro-paciente', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        elements.registerForm.reset();
        switchAuthTab('login');
        showMessage('Cuenta creada correctamente. Ya puedes iniciar sesión.', 'success');
    } catch (error) {
        showMessage(apiErrorMessage(error, 'No se pudo registrar la cuenta.'), 'error');
    }
}

async function submitPasswordReset(event) {
    event.preventDefault();
    const newPassword = document.getElementById('reset-pass').value.trim();
    const confirmPassword = document.getElementById('reset-pass-confirm').value.trim();

    if (newPassword.length < 8) {
        showMessage('La nueva contraseña debe tener al menos 8 caracteres.', 'error');
        return;
    }

    if (newPassword !== confirmPassword) {
        showMessage('La confirmación de contraseña no coincide.', 'error');
        return;
    }

    const payload = {
        email: document.getElementById('reset-email').value.trim(),
        nombre: document.getElementById('reset-nombre').value.trim(),
        new_password: newPassword,
    };

    try {
        await request('/portal/restablecer-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        elements.resetForm.reset();
        switchAuthTab('login');
        showMessage('Contraseña restablecida. Inicia sesión con tu nueva contraseña.', 'success');
    } catch (error) {
        showMessage(apiErrorMessage(error, 'No se pudo restablecer la contraseña.'), 'error');
    }
}

async function submitAppointmentForm(event) {
    event.preventDefault();
    const date = document.getElementById('appointment-date').value;
    const time = document.getElementById('appointment-time').value;
    const area = document.getElementById('appointment-area').value;

    const when = buildAppointmentDate(date, time);
    if (!when) {
        showMessage('Selecciona una fecha y hora válidas.', 'error');
        return;
    }

    const ruleError = validateAppointmentRules(when, state.editingCitaId);
    if (ruleError) {
        showMessage(ruleError, 'error');
        return;
    }

    const payload = {
        fecha: `${date}T${time}:00`,
        area,
    };

    try {
        if (state.editingCitaId) {
            await request(`/mis-citas/${state.editingCitaId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            showMessage('Cita modificada correctamente.', 'success');
        } else {
            await request('/mis-citas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            showMessage('Cita agendada correctamente.', 'success');
        }
        state.editingCitaId = null;
        await renderView('citas');
    } catch (error) {
        showMessage(apiErrorMessage(error, 'No se pudo guardar la cita.'), 'error');
    }
}

async function deleteCita(citaId) {
    if (!window.confirm('¿Deseas cancelar esta cita?')) {
        return;
    }
    try {
        await request(`/mis-citas/${citaId}`, { method: 'DELETE' });
        showMessage('Cita cancelada correctamente.', 'success');
        if (state.editingCitaId === citaId) {
            state.editingCitaId = null;
        }
        await renderView('citas');
    } catch (error) {
        showMessage(apiErrorMessage(error, 'No se pudo cancelar la cita.'), 'error');
    }
}

function editCita(citaId) {
    state.editingCitaId = citaId;
    renderCitasView();
}

function newCita() {
    state.editingCitaId = null;
    renderCitasView();
}

function logout() {
    clearSession();
    setPortalMode('auth');
    elements.dashboardView.classList.add('hidden');
    elements.authView.classList.remove('hidden');
    switchAuthTab('login');
    showMessage('Sesión cerrada.', 'info');
}

elements.tabLogin.addEventListener('click', () => switchAuthTab('login'));
elements.tabRegister.addEventListener('click', () => switchAuthTab('register'));
elements.loginForm.addEventListener('submit', submitLogin);
elements.resetForm.addEventListener('submit', submitPasswordReset);
elements.registerForm.addEventListener('submit', submitRegister);
elements.forgotPasswordBtn.addEventListener('click', showResetPanel);
elements.backLoginBtn.addEventListener('click', () => switchAuthTab('login'));
elements.logoutBtn.addEventListener('click', logout);
elements.navButtons.forEach((button) => {
    button.addEventListener('click', () => renderView(button.dataset.view));
});

window.portalApp = {
    editCita,
    deleteCita,
    newCita,
};

(async function init() {
    setPortalMode('auth');
    switchAuthTab('login');
    if (state.token && state.role === 'paciente') {
        try {
            await loadDashboard();
            return;
        } catch (error) {
            clearSession();
            showMessage(apiErrorMessage(error, 'Tu sesión expiró. Inicia sesión de nuevo.'), 'error');
        }
    }
})();
