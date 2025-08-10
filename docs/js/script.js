// --- !!! هشدار امنیتی بسیار مهم !!! ---
// این کلیدها به صورت مستقیم در کد سمت کلاینت قرار گرفته‌اند.
// این روش برای تست و توسعه اولیه مناسب است، اما برای محیط عملیاتی (Production) به شدت ناامن است.
// هر کسی که به کد شما دسترسی داشته باشد، می‌تواند این کلیدها را ببیند و از آن‌ها سوءاستفاده کند.
// برای امنیت واقعی، باید از یک Backend Server استفاده کنید و کلیدها را در آنجا نگهداری کنید.
const GEMINI_API_KEYS = [
    'AIzaSyAR05hsGAEyaNTLcj05NbhM8xU7FYvmNRg',
    'AIzaSyD10Nj1jV_KEwUd9Dio62CHBdB6WeuU6ng',
    'AIzaSyDf5oMDovldeweCto6jJ2KbMZ2vqkgg9GY'
];

// تنظیمات
const GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const welcomeScreen = document.getElementById('welcome-screen');
const chatContainer = document.getElementById('chat-container');
const errorScreen = document.getElementById('error-screen');
const retryBtn = document.getElementById('retry-btn');
const settingsMenu = document.getElementById('settings-menu');
const settingsToggle = document.getElementById('settings-toggle');
const closeSettings = document.getElementById('close-settings');
const themeOptions = document.querySelectorAll('.theme-option');
const loadingScreen = document.getElementById('loading-screen');
const appHeader = document.querySelector('.app-header');
const inputArea = document.querySelector('.input-area');
const infoBtnHeader = document.getElementById('info-btn');
const infoBtnInput = document.getElementById('info-btn-input');

// وضعیت برنامه
let isOnline = true;

// شبیه‌سازی بارگذاری اولیه
setTimeout(() => {
    loadingScreen.style.opacity = '0';
    setTimeout(() => {
        loadingScreen.style.display = 'none';
        checkConnection();
    }, 500);
}, 1000);

// تابع ایمن برای ارتباط با API Gemini
async function secureFetchGemini(messageContent, attempt = 0) {
    if (attempt >= GEMINI_API_KEYS.length) {
        console.error('All Gemini API keys failed after multiple attempts.');
        return { error: 'تمام کلیدهای API نامعتبر هستند یا به حد مجاز رسیده‌اند. لطفاً با مدیر سایت تماس بگیرید.' };
    }

    const currentKey = GEMINI_API_KEYS[attempt];
    if (!currentKey || currentKey.trim() === '') {
        console.error(`API Key at index ${attempt} is empty or invalid.`);
        return secureFetchGemini(messageContent, attempt + 1);
    }

    const url = `${GEMINI_BASE_URL}?key=${currentKey}`;
    const requestBody = {
        contents: [{
            role: "user",
            parts: [{
                text: messageContent
            }]
        }],
        generationConfig: {}
    };

    const headers = {
        'Content-Type': 'application/json'
    };
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: response.statusText }));
            console.error(`Gemini API Error (Key ${attempt + 1}): Status ${response.status}, Error: ${JSON.stringify(errorData)}`);
            
            if (response.status >= 400 && response.status < 500) {
                return secureFetchGemini(messageContent, attempt + 1);
            }
            throw new Error(`خطای سرور: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        const replyText = data.candidates && data.candidates.length > 0 &&
                          data.candidates[0].content && data.candidates[0].content.parts &&
                          data.candidates[0].content.parts.length > 0 ?
                          data.candidates[0].content.parts[0].text : 'پاسخی از هوش مصنوعی دریافت نشد.';
        
        return { reply: replyText };
    } catch (error) {
        console.error('Network or Gemini API processing error:', error);
        return { error: `خطا در ارتباط با هوش مصنوعی: ${error.message || 'خطای ناشناخته.'}` };
    }
}
        
// بررسی وضعیت اتصال اینترنت
function checkConnection() {
    isOnline = navigator.onLine;
    updateUI();
    if (isOnline) {
        userInput.focus();
        adjustChatLayout();
    }
}
        
// به‌روزرسانی UI بر اساس وضعیت
function updateUI() {
    if (isOnline) {
        welcomeScreen.style.display = 'flex';
        errorScreen.style.display = 'none';
        chatContainer.style.display = 'none';
        showStatus('آنلاین', 'online');
    } else {
        welcomeScreen.style.display = 'none';
        chatContainer.style.display = 'none';
        errorScreen.style.display = 'flex';
        showStatus('آفلاین', 'offline');
    }
}
        
// نمایش وضعیت آنلاین/آفلاین
function showStatus(text, type) {
    const existingStatus = document.querySelector('.status-indicator');
    if (existingStatus) existingStatus.remove();
            
    const statusDiv = document.createElement('div');
    statusDiv.className = `status-indicator ${type}`;
    statusDiv.textContent = text;
    document.body.appendChild(statusDiv);
            
    setTimeout(() => {
        statusDiv.style.opacity = '0';
        setTimeout(() => statusDiv.remove(), 500);
    }, 3000);
}
        
// تابع نمایش پیام جدید
function addMessage(role, content) {
    const now = new Date();
    const timeString = now.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
            
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
            
    let headerIcon, headerText;
    if (role === 'user') {
        headerIcon = '<i class="fas fa-user"></i>';
        headerText = 'شما';
    } else {
        headerIcon = '<i class="fas fa-robot"></i>';
        headerText = 'AysChat';
    }
            
    messageDiv.innerHTML = `
        <div class="message-header">
            ${headerIcon}
            ${headerText}
        </div>
        ${content}
        <div class="timestamp">${timeString}</div>
    `;
            
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}
        
// تابع نمایش وضعیت تایپ
function showTyping() {
    if (!document.getElementById('smart-typing').checked) {
        return;
    }
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    chatBox.appendChild(typingDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}
        
// تابع مخفی کردن وضعیت تایپ
function hideTyping() {
    const typing = document.getElementById('typing-indicator');
    if (typing) typing.remove();
}
        
// تابع پخش اثرات صوتی (اگر فعال باشد)
function playSoundEffect(soundUrl) {
    if (document.getElementById('sound-effects').checked) {
        try {
            const audio = new Audio(soundUrl);
            audio.play().catch(e => console.warn('Audio playback failed:', e));
        } catch (e) {
            console.error('Error creating audio object:', e);
        }
    }
}

// تابع ارسال پیام
async function sendMessage() {
    if (!isOnline) {
        showStatus('شما آفلاین هستید!', 'offline');
        return;
    }

    const message = userInput.value.trim();
    if (!message) return;
            
    addMessage('user', message);
    userInput.value = '';
    sendButton.disabled = true;
            
    showTyping();
            
    welcomeScreen.style.display = 'none';
    chatContainer.style.display = 'flex';
            
    adjustChatLayout();

    const response = await secureFetchGemini(message);
            
    hideTyping();
    if (response.error) {
        addMessage('bot', `<strong>خطا:</strong> ${response.error}`);
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-sci-fi-bleep-error-1961.mp3');
    } else {
        addMessage('bot', response.reply);
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-sci-fi-confirmation-909.mp3');
    }
            
    sendButton.disabled = false;
    userInput.focus();
}
        
// فعال کردن ارسال با Enter
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
});
        
// رویدادهای دکمه‌ها
retryBtn.addEventListener('click', checkConnection);
        
settingsToggle.addEventListener('click', () => {
    settingsMenu.classList.add('open');
    playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-button-click-1123.mp3');
});
        
closeSettings.addEventListener('click', () => {
    settingsMenu.classList.remove('open');
    playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-fast-reverse-sweep-transition-2559.mp3');
});

// مدیریت دکمه‌های اطلاعات/راهنما
infoBtnHeader.addEventListener('click', () => {
    alert('AysChat هوش مصنوعی شماست! برای اطلاعات بیشتر، به بخش "درباره برنامه" در تنظیمات مراجعه کنید.');
    playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-game-alarm-1003.mp3');
});
infoBtnInput.addEventListener('click', () => {
    alert('AysChat هوش مصنوعی شماست! برای اطلاعات بیشتر، به بخش "درباره برنامه" در تنظیمات مراجعه کنید.');
    playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-game-alarm-1003.mp3');
});
        
// تغییر تم
themeOptions.forEach(option => {
    option.addEventListener('click', () => {
        themeOptions.forEach(opt => opt.classList.remove('selected'));
        option.classList.add('selected');
        document.body.className = '';
        document.body.classList.add(`${option.dataset.theme}-theme`);
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-unlock-game-notification-253.mp3');
    });
});

// رویدادهای وضعیت شبکه
window.addEventListener('online', () => {
    isOnline = true;
    updateUI();
});
        
window.addEventListener('offline', () => {
    isOnline = false;
    updateUI();
});
        
// بررسی اولیه وضعیت شبکه
checkConnection();
        
// فوکوس خودکار روی فیلد ورودی در شروع
window.onload = () => {
    userInput.focus();
    adjustChatLayout();
};

// تابع برای به‌روزرسانی ابعاد چت‌باکس
function adjustChatLayout() {
    const headerHeight = appHeader.offsetHeight;
    const inputAreaHeight = inputArea.offsetHeight + parseFloat(getComputedStyle(inputArea).marginBottom) + parseFloat(getComputedStyle(inputArea).marginTop);
    chatContainer.style.top = `${headerHeight}px`;
    chatContainer.style.bottom = `${inputAreaHeight}px`;
}

// Add event listener for window resize
window.addEventListener('resize', adjustChatLayout);

// Initial adjustment after loading screen
setTimeout(adjustChatLayout, 1000);
