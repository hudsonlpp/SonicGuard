// ============================================
// SonicGuard — Auth & Credits Logic
// ============================================

const API_LOGIN = '/api/auth/login';
const API_REGISTER = '/api/auth/register';

// ---------- DOM Elements ----------
// Header
const authUnlogged = document.getElementById('auth-unlogged');
const authLogged = document.getElementById('auth-logged');
const userEmailSpan = document.getElementById('user-email');
const userCreditsSpan = document.getElementById('user-credits');
const btnOpenLogin = document.getElementById('btn-open-login');
const btnOpenRegister = document.getElementById('btn-open-register');
const btnLogout = document.getElementById('btn-logout');

// Modals
const modalLogin = document.getElementById('modal-login');
const modalRegister = document.getElementById('modal-register');
const modalCredits = document.getElementById('modal-credits');

// Forms & Inputs
const formLogin = document.getElementById('form-login');
const loginEmail = document.getElementById('login-email');
const loginPassword = document.getElementById('login-password');
const loginError = document.getElementById('login-error');

const formRegister = document.getElementById('form-register');
const registerEmail = document.getElementById('register-email');
const registerPassword = document.getElementById('register-password');
const registerError = document.getElementById('register-error');

// Close Buttons & Links
const btnCloseLogin = document.getElementById('btn-close-login');
const btnCloseRegister = document.getElementById('btn-close-register');
const btnCloseCredits = document.getElementById('btn-close-credits');
const btnCloseCreditsBottom = document.getElementById('btn-close-credits-bottom');
const linkToRegister = document.getElementById('link-to-register');
const linkToLogin = document.getElementById('link-to-login');

// ---------- State Management ----------
export const authState = {
    token: localStorage.getItem('sg_token') || null,
    email: localStorage.getItem('sg_email') || null,
    credits: parseInt(localStorage.getItem('sg_credits') || '0', 10),

    setSession(token, email, credits) {
        this.token = token;
        this.email = email;
        this.credits = credits;
        localStorage.setItem('sg_token', token);
        localStorage.setItem('sg_email', email);
        localStorage.setItem('sg_credits', credits.toString());
        updateHeaderUI();
    },

    updateCredits(newCredits) {
        this.credits = newCredits;
        localStorage.setItem('sg_credits', newCredits.toString());
        updateHeaderUI();
    },

    clearSession() {
        this.token = null;
        this.email = null;
        this.credits = 0;
        localStorage.removeItem('sg_token');
        localStorage.removeItem('sg_email');
        localStorage.removeItem('sg_credits');
        updateHeaderUI();
    },

    isLoggedIn() {
        return !!this.token;
    }
};

// ---------- UI Updates ----------
function updateHeaderUI() {
    if (authState.isLoggedIn()) {
        authUnlogged.classList.add('hidden');
        authLogged.classList.remove('hidden');
        userEmailSpan.textContent = authState.email;
        userCreditsSpan.textContent = authState.credits;
    } else {
        authUnlogged.classList.remove('hidden');
        authLogged.classList.add('hidden');
    }
}

// ---------- Modal Helpers ----------
export function openModal(modal) {
    modal.classList.remove('hidden');
}

export function closeModal(modal) {
    modal.classList.add('hidden');
    // Clear forms and errors on close
    if (modal === modalLogin) {
        formLogin.reset();
        loginError.classList.add('hidden');
    } else if (modal === modalRegister) {
        formRegister.reset();
        registerError.classList.add('hidden');
    }
}

function showError(el, msg) {
    el.textContent = msg;
    el.classList.remove('hidden');
}

// ---------- Event Listeners ----------
// Open Modals
btnOpenLogin.addEventListener('click', () => openModal(modalLogin));
btnOpenRegister.addEventListener('click', () => openModal(modalRegister));
if (btnLogout) {
    btnLogout.addEventListener('click', () => authState.clearSession());
}

// Close Modals
btnCloseLogin.addEventListener('click', () => closeModal(modalLogin));
btnCloseRegister.addEventListener('click', () => closeModal(modalRegister));
btnCloseCredits.addEventListener('click', () => closeModal(modalCredits));
btnCloseCreditsBottom.addEventListener('click', () => closeModal(modalCredits));

// Close on click outside
[modalLogin, modalRegister, modalCredits].forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal(modal);
    });
});

// Toggle between modals
linkToRegister.addEventListener('click', (e) => {
    e.preventDefault();
    closeModal(modalLogin);
    openModal(modalRegister);
});

linkToLogin.addEventListener('click', (e) => {
    e.preventDefault();
    closeModal(modalRegister);
    openModal(modalLogin);
});

// ---------- Login Flow ----------
formLogin.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError.classList.add('hidden');
    const btn = document.getElementById('btn-submit-login');
    btn.disabled = true;
    btn.textContent = 'Entrando...';

    try {
        const formData = new URLSearchParams();
        formData.append('username', loginEmail.value);
        formData.append('password', loginPassword.value);

        // 1. Get Token
        const res = await fetch(API_LOGIN, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });

        if (!res.ok) {
            if (res.status === 401) throw new Error('Email ou senha incorretos.');
            throw new Error(`Erro ${res.status} ao fazer login`);
        }

        const data = await res.json();
        const token = data.access_token;

        // TODO: Ideally the login endpoint should return user info/credits.
        // Since api_contract.md says it only returns access_token, we will set a mock/default state 
        // for email and credits until the user does a successful action or we add a /me endpoint.
        // For now we'll set it to 0 credits, and it will update if /compare returns updated credits (if backend supports that).
        // Or we assume 0 and wait for failure.
        authState.setSession(token, loginEmail.value, 0);

        closeModal(modalLogin);
    } catch (err) {
        showError(loginError, err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Entrar';
    }
});

// ---------- Register Flow ----------
formRegister.addEventListener('submit', async (e) => {
    e.preventDefault();
    registerError.classList.add('hidden');
    const btn = document.getElementById('btn-submit-register');
    btn.disabled = true;
    btn.textContent = 'Criando...';

    try {
        const res = await fetch(API_REGISTER, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: registerEmail.value,
                password: registerPassword.value
            })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Erro ${res.status} ao criar conta`);
        }

        const data = await res.json();
        // User is created, but contract says /register doesn't return JWT.
        // So we close register and open login with pre-filled email, or auto-login.
        // Let's close register and open login.
        closeModal(modalRegister);
        loginEmail.value = data.email || registerEmail.value;
        openModal(modalLogin);

        // Show a small native alert or inline msg
        alert(`Conta criada com sucesso! Você ganhou ${data.credits || 2} créditos grátis. Faça login para continuar.`);

    } catch (err) {
        showError(registerError, err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Criar Conta';
    }
});

// Initialization
updateHeaderUI();
