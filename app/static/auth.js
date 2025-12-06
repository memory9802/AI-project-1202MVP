// Toggle password visibility
function togglePasswordVisibility(fieldId) {
    const field = document.getElementById(fieldId);
    field.type = field.type === 'password' ? 'text' : 'password';
}

// Tab and view switching helpers
const loginTab = document.getElementById('login-tab');
const registerTab = document.getElementById('register-tab');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const recoveryForm = document.getElementById('recovery-form');
const forgotPasswordLink = document.getElementById('forgot-password-link');
const backToLogin = document.getElementById('back-to-login');
const authMessage = document.getElementById('auth-message');
const loggedInPanel = document.getElementById('logged-in-panel');
const loggedInEmail = document.getElementById('logged-in-email');
const logoutButton = document.getElementById('logout-button');
const rememberMe = document.getElementById('remember-me');
const stateKey = 'styleRecAuthState';
const tabBar = document.getElementById('tab-bar');
const authTitle = document.getElementById('auth-title');
const authSubtitle = document.getElementById('auth-subtitle');

const copy = {
    welcome: {
        title: '歡迎回來！',
        subtitle: '登入以繼續探索您的穿搭靈感',
    },
    recovery: {
        title: '找回密碼',
        subtitle: '輸入註冊電子郵件',
    }
};

const setCopy = (variant) => {
    const data = copy[variant];
    if (!data) return;
    authTitle.textContent = data.title;
    authSubtitle.textContent = data.subtitle;
};

const setTabState = (active) => {
    const activeClasses = ['border-b-primary', 'text-primary'];
    const inactiveClasses = ['border-b-transparent', 'text-subtle-light', 'dark:text-subtle-dark'];

    [loginTab, registerTab].forEach((tab) => {
        tab.classList.remove(...activeClasses, ...inactiveClasses);
        tab.classList.add('tab-link');
    });

    if (active === 'login') {
        loginTab.classList.add(...activeClasses);
        registerTab.classList.add(...inactiveClasses);
    } else if (active === 'register') {
        registerTab.classList.add(...activeClasses);
        loginTab.classList.add(...inactiveClasses);
    } else {
        loginTab.classList.add(...inactiveClasses);
        registerTab.classList.add(...inactiveClasses);
    }
};

const tabs = {
    showLogin() {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        recoveryForm.classList.add('hidden');
        loggedInPanel.classList.add('hidden');
        setTabState('login');
        setCopy('welcome');
        tabBar.classList.remove('invisible', 'h-0');
        hideMessage();
    },
    showRegister() {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        recoveryForm.classList.add('hidden');
        loggedInPanel.classList.add('hidden');
        setTabState('register');
        setCopy('welcome');
        tabBar.classList.remove('invisible', 'h-0');
        hideMessage();
    },
    showRecovery() {
        loginForm.classList.add('hidden');
        registerForm.classList.add('hidden');
        recoveryForm.classList.remove('hidden');
        loggedInPanel.classList.add('hidden');
        setTabState('none');
        setCopy('recovery');
        tabBar.classList.add('invisible', 'h-0');
        hideMessage();
    },
    showLoggedIn(email) {
        loginForm.classList.add('hidden');
        registerForm.classList.add('hidden');
        recoveryForm.classList.add('hidden');
        loggedInPanel.classList.remove('hidden');
        setTabState('none');
        setCopy('welcome');
        loggedInEmail.textContent = email;
        hideMessage();
    }
};

const persistState = (email) => {
    const payload = { email, timestamp: Date.now(), remember: rememberMe.checked };
    if (payload.remember) {
        localStorage.setItem(stateKey, JSON.stringify(payload));
        sessionStorage.removeItem(stateKey);
    } else {
        sessionStorage.setItem(stateKey, JSON.stringify(payload));
        localStorage.removeItem(stateKey);
    }
};

const readState = () => {
    const raw = localStorage.getItem(stateKey) || sessionStorage.getItem(stateKey);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch {
        return null;
    }
};

const clearState = () => {
    localStorage.removeItem(stateKey);
    sessionStorage.removeItem(stateKey);
};

const showMessage = (text, type = 'info') => {
    authMessage.textContent = text;
    const color = type === 'error' ? 'text-red-600 dark:text-red-400' : 'text-text-light dark:text-text-dark';
    authMessage.className = `rounded-lg border border-secondary-light dark:border-secondary-dark bg-white dark:bg-secondary-dark px-4 py-3 text-sm ${color}`;
    authMessage.classList.remove('hidden');
};

const hideMessage = () => {
    authMessage.classList.add('hidden');
};

loginTab.addEventListener('click', tabs.showLogin);
registerTab.addEventListener('click', tabs.showRegister);
forgotPasswordLink.addEventListener('click', tabs.showRecovery);
backToLogin.addEventListener('click', tabs.showLogin);

loginForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const email = loginForm.email.value.trim();
    const password = loginForm.password.value.trim();
    if (!email || !password) {
        showMessage('請填寫完整的登入資料。', 'error');
        return;
    }
    if (password.length < 6) {
        showMessage('密碼至少需要 6 碼。', 'error');
        return;
    }
    persistState(email);
    showMessage('登入成功，正在導向您的空間。');
    setTimeout(() => tabs.showLoggedIn(email), 400);
});

registerForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const email = registerForm.email.value.trim();
    const password = registerForm.password.value.trim();
    const confirmPassword = registerForm.confirmPassword.value.trim();
    if (!email || !password || !confirmPassword) {
        showMessage('請完成所有註冊欄位。', 'error');
        return;
    }
    if (password.length < 6) {
        showMessage('密碼長度需至少 6 碼。', 'error');
        return;
    }
    if (password !== confirmPassword) {
        showMessage('兩次輸入的密碼不一致。', 'error');
        return;
    }
    persistState(email);
    showMessage('註冊成功，已自動登入。');
    setTimeout(() => tabs.showLoggedIn(email), 400);
});

recoveryForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const email = recoveryForm.email.value.trim();
    if (!email) {
        showMessage('請輸入用來重設的電子郵件。', 'error');
        return;
    }
    showMessage('已寄出重設密碼連結，請檢查您的信箱。');
    setTimeout(() => tabs.showLogin(), 800);
});

logoutButton.addEventListener('click', () => {
    clearState();
    showMessage('您已登出，下次登入時可勾選保持登入。');
    tabs.showLogin();
});

const saved = readState();
if (saved?.email) {
    rememberMe.checked = !!saved.remember;
    tabs.showLoggedIn(saved.email);
} else {
    tabs.showLogin();
}
