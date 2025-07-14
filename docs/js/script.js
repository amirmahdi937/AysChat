const RENDER_API_BASE_URL = "https://ayschat.onrender.com";

// مطمئن شوید که تمام عناصر HTML که با getElementById یا querySelector انتخاب می‌کنید، در بالای فایل تعریف شده‌اند.
const loadingScreen = document.getElementById('loading-screen');
const welcomeScreen = document.getElementById('welcome-screen');
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const chatBox = document.getElementById('chat-box');
const settingsToggle = document.getElementById('settings-toggle');
const settingsMenu = document.getElementById('settings-menu');
const closeSettings = document.getElementById('close-settings');
const themeOptions = document.querySelectorAll('.theme-option');
const soundEffectsToggle = document.getElementById('sound-effects');
const smartTypingToggle = document.getElementById('smart-typing');
const animationsToggle = document.getElementById('animations');
const infoButtonHeader = document.getElementById('info-btn'); // For header info button
const infoButtonInput = document.getElementById('info-btn-input'); // For input area info button
const errorScreen = document.getElementById('error-screen');
const retryButton = document.getElementById('retry-btn');
const appHeader = document.querySelector('.app-header'); // برای تابع adjustChatLayout
const inputArea = document.querySelector('.input-area'); // برای تابع adjustChatLayout
const viewPrivacyButton = document.getElementById('view-privacy');

let isOnline = navigator.onLine; // وضعیت اولیه اتصال
let currentTheme = localStorage.getItem('theme') || 'light';
let isSoundEffectsEnabled = localStorage.getItem('soundEffects') === 'true' || true;
let isSmartTypingEnabled = localStorage.getItem('smartTyping') === 'true' || true;
let areAnimationsEnabled = localStorage.getItem('animations') === 'true' || true;

// ** 2. توابع کمکی (Helper Functions) **

// تابع برای پخش افکت صوتی
function playSoundEffect(src) {
    if (isSoundEffectsEnabled) {
        const audio = new Audio(src);
        audio.play().catch(e => console.error("Error playing sound:", e));
    }
}

// تابع برای به‌روزرسانی UI بر اساس وضعیت اتصال
function updateUI() {
    if (isOnline) {
        if (errorScreen) errorScreen.style.display = 'none';
        // اگر صفحه خوش آمدگویی نمایش داده نشده باشد، چت کانتینر را نمایش دهید
        if (welcomeScreen && welcomeScreen.style.display === 'none') {
            if (chatContainer) chatContainer.style.display = 'flex';
        } else if (welcomeScreen) { // اگر صفحه خوش آمدگویی هنوز هست
            if (welcomeScreen) welcomeScreen.style.display = 'flex';
            if (chatContainer) chatContainer.style.display = 'flex';
        }
    } else {
        if (errorScreen) errorScreen.style.display = 'flex';
        if (chatContainer) chatContainer.style.display = 'none';
        if (welcomeScreen) welcomeScreen.style.display = 'none'; // پنهان کردن صفحه خوش آمدگویی
    }
}

// تابع برای بررسی اتصال و فراخوانی updateUI
function checkConnection() {
    isOnline = navigator.onLine;
    updateUI();
}

// تابع برای افزودن پیام به چت‌باکس
function addMessage(sender, message, isTyping = false) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', `${sender}-message`);
    if (isTyping) {
        messageElement.classList.add('typing-indicator');
        messageElement.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
    } else {
        // برای حفظ فرمت کد و لینک‌ها
        const formattedMessage = message.replace(/\n/g, '<br>') // تبدیل newline به <br>
                                        .replace(/```(.*?)```/gs, '<pre><code>$1</code></pre>') // تبدیل بلوک کد
                                        .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>'); // لینک‌ها
        messageElement.innerHTML = formattedMessage;
    }
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
    return messageElement; // اضافه کردن این خط برای برگرداندن المنت نشانگر تایپ
}

// تابع برای ارسال پیام
function sendMessage() {
    const message = userInput.value.trim();
    if (message === '') return;

    if (welcomeScreen && chatContainer) {
        if (welcomeScreen.style.display !== 'none') {
            welcomeScreen.style.display = 'none';
            chatContainer.style.display = 'flex';
            adjustChatLayout();
        }
    }

    addMessage('user', message);
    userInput.value = ''; // پاک کردن ورودی

    const typingIndicator = addMessage('ai', '...', true); // نمایش نشانگر تایپ

    secureFetchGemini(message)
        .then(response => {
            // حذف نشانگر تایپ
            if (typingIndicator && typingIndicator.parentNode) {
                typingIndicator.parentNode.removeChild(typingIndicator);
            }
            addMessage('ai', response);
            playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-positive-notification-alert-sound-2210.mp3');
        })
        .catch(async error => { // **Async را به اینجا اضافه کنید**
            console.error('Error fetching from Gemini API:', error);
            if (typingIndicator && typingIndicator.parentNode) {
                typingIndicator.parentNode.removeChild(typingIndicator);
            }
            let errorMessage = 'متاسفانه خطایی در ارتباط با سرور رخ داد. لطفاً دوباره تلاش کنید.';
            
            try {
                // تلاش برای خواندن پیام خطای دقیق‌تر از پاسخ سرور
                const errorResponseText = error.message.split('message: ')[1];
                if (errorResponseText) {
                    const errorJson = JSON.parse(errorResponseText);
                    if (errorJson.error) {
                        errorMessage = `خطا از سرور: ${errorJson.error}`;
                    } else {
                        errorMessage = `خطا از سرور: ${errorResponseText}`;
                    }
                }
            } catch (parseError) {
                console.error("Could not parse error response from server:", parseError);
                // اگر JSON parse نشد، همان پیام عمومی را نمایش می‌دهیم.
            }

            addMessage('ai', errorMessage);
            playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-wrong-answer-fail-notification-946.mp3');
        });
}

// تابع برای تنظیم ابعاد چت‌باکس
function adjustChatLayout() {
    if (appHeader && inputArea && chatContainer) {
        const headerHeight = appHeader.offsetHeight;
        const inputAreaStyles = getComputedStyle(inputArea);
        const inputAreaHeight = inputArea.offsetHeight + parseFloat(inputAreaStyles.marginTop) + parseFloat(inputAreaStyles.marginBottom); 
        
        chatContainer.style.top = `${headerHeight}px`;
        chatContainer.style.bottom = `${inputAreaHeight}px`;
    }
}

// ** 3. منطق اصلی راه‌اندازی برنامه (پس از بارگذاری صفحه) **

// این بلوک اصلی برای مدیریت صفحه بارگذاری و شروع برنامه است.
// این کد باید جایگزین هر گونه کد setTimeout یا window.onload دیگری شود که قبلاً برای صفحه بارگذاری داشته‌اید.
window.addEventListener('load', () => {
    if (loadingScreen) {
        // 1. شروع انیمیشن محو شدن با تنظیم opacity به 0.
        loadingScreen.style.opacity = '0';

        // 2. پس از گذشت زمان کافی برای اتمام انیمیشن محو شدن (3.5 ثانیه),
        // عنصر loadingScreen را کاملاً از نمایش خارج کنید.
        setTimeout(() => {
            loadingScreen.style.display = 'none';

            // 3. حالا که صفحه بارگذاری پنهان شده است، بقیه توابع اولیه برنامه را اجرا کنید.
            checkConnection(); // بررسی اتصال اینترنت و به‌روزرسانی UI
            if (userInput) {
                userInput.focus(); // فوکوس بر روی ورودی کاربر
            }
            adjustChatLayout(); // تنظیم لی‌آوت چت پس از بارگذاری کامل
            
            // نمایش welcome-screen یا chat-container بسته به وضعیت
            if (isOnline) { // اگر آنلاین هستیم
                if (welcomeScreen && welcomeScreen.style.display !== 'none') {
                    // اگر welcomeScreen قابل مشاهده است، آن را نگه دارید و chatContainer را نمایش دهید
                    chatContainer.style.display = 'flex';
                } else {
                    // اگر welcomeScreen قبلا پنهان شده بود، فقط chatContainer را نمایش دهید
                    chatContainer.style.display = 'flex';
                }
            } else { // اگر آفلاین هستیم، صفحه خطا نمایش داده شده است
                if (chatContainer) chatContainer.style.display = 'none';
                if (welcomeScreen) welcomeScreen.style.display = 'none';
            }
            
        }, 3500); // 3500 میلی‌ثانیه (3.5 ثانیه) - کمی بیشتر از 3 ثانیه transition CSS
    }
});

// ** 4. مدیریت رویدادها (Event Listeners) **

// رویداد ارسال پیام با کلیک روی دکمه
if (sendButton) {
    sendButton.addEventListener('click', sendMessage);
}

// رویداد ارسال پیام با فشردن Enter در ورودی
if (userInput) {
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
}

// رویدادهای مربوط به دکمه‌های تنظیمات
if (settingsToggle) {
    settingsToggle.addEventListener('click', () => {
        if (settingsMenu) settingsMenu.classList.toggle('open');
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-cool-interface-click-1126.mp3');
    });
}

if (closeSettings) {
    closeSettings.addEventListener('click', () => {
        if (settingsMenu) settingsMenu.classList.remove('open');
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-cool-interface-click-1126.mp3');
    });
}

// رویدادهای تغییر تم
themeOptions.forEach(option => {
    option.addEventListener('click', () => {
        themeOptions.forEach(opt => opt.classList.remove('selected'));
        option.classList.add('selected');
        document.body.className = ''; // Remove all existing theme classes
        document.body.classList.add(`${option.dataset.theme}-theme`);
        localStorage.setItem('theme', option.dataset.theme); // Save theme preference
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-unlock-game-notification-253.mp3');
    });
});

// رویدادهای تغییر وضعیت سوئیچ‌ها
if (soundEffectsToggle) {
    soundEffectsToggle.addEventListener('change', () => {
        isSoundEffectsEnabled = soundEffectsToggle.checked;
        localStorage.setItem('soundEffects', isSoundEffectsEnabled);
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-cool-interface-click-1126.mp3');
    });
}

if (smartTypingToggle) {
    smartTypingToggle.addEventListener('change', () => {
        isSmartTypingEnabled = smartTypingToggle.checked;
        localStorage.setItem('smartTyping', isSmartTypingEnabled);
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-cool-interface-click-1126.mp3');
    });
}

if (animationsToggle) {
    animationsToggle.addEventListener('change', () => {
        areAnimationsEnabled = animationsToggle.checked;
        localStorage.setItem('animations', areAnimationsEnabled);
        // اینجا می‌توانید کدی برای فعال/غیرفعال کردن انیمیشن‌های CSS/JS دیگر اضافه کنید
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-cool-interface-click-1126.mp3');
    });
}

// رویدادهای مربوط به دکمه retry در صفحه خطا
if (retryButton) {
    retryButton.addEventListener('click', () => {
        checkConnection();
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-interface-button-click-1129.mp3');
    });
}

// رویدادهای وضعیت شبکه
window.addEventListener('online', () => {
    isOnline = true;
    updateUI();
});

window.addEventListener('offline', () => {
    isOnline = false;
    updateUI();
});

// رویداد برای تغییر اندازه پنجره مرورگر برای تنظیم مجدد لی‌آوت
window.addEventListener('resize', adjustChatLayout);

// رویداد برای نمایش صفحه حریم خصوصی (اگر modal یا صفحه‌ای دارید)
if (viewPrivacyButton) {
    viewPrivacyButton.addEventListener('click', () => {
        // اینجا می‌توانید کد برای نمایش modal حریم خصوصی یا هدایت به صفحه دیگر را اضافه کنید
        console.log("Privacy button clicked. Implement your privacy policy display here.");
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-cool-interface-click-1126.mp3');
    });
}

// رویدادهای مربوط به دکمه‌های اطلاعات
if (infoButtonHeader) {
    infoButtonHeader.addEventListener('click', () => {
        alert('این دکمه اطلاعات برنامه‌نویس یا درباره برنامه را نمایش می‌دهد.');
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-cool-interface-click-1126.mp3');
    });
}

if (infoButtonInput) {
    infoButtonInput.addEventListener('click', () => {
        alert('این دکمه اطلاعات برنامه‌نویس یا درباره برنامه را نمایش می‌دهد.');
        playSoundEffect('https://assets.mixkit.co/sfx/preview/mixkit-cool-interface-click-1126.mp3');
    });
}


// ** 5. بازیابی تنظیمات ذخیره شده و اعمال آن‌ها در شروع **

// بازیابی و اعمال تم ذخیره شده
const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
    document.body.classList.add(`${savedTheme}-theme`);
    themeOptions.forEach(option => {
        if (option.dataset.theme === savedTheme) {
            option.classList.add('selected');
        } else {
            option.classList.remove('selected');
        }
    });
} else {
    // اگر تمی ذخیره نشده، تم light را به عنوان پیش‌فرض اعمال کنید
    document.body.classList.add('light-theme');
    const lightThemeOption = document.querySelector('.theme-option.light-theme');
    if (lightThemeOption) lightThemeOption.classList.add('selected');
}

// بازیابی و اعمال وضعیت سوئیچ‌ها
if (soundEffectsToggle) {
    const savedSoundEffects = localStorage.getItem('soundEffects');
    if (savedSoundEffects !== null) {
        isSoundEffectsEnabled = savedSoundEffects === 'true';
        soundEffectsToggle.checked = isSoundEffectsEnabled;
    }
}

if (smartTypingToggle) {
    const savedSmartTyping = localStorage.getItem('smartTyping');
    if (savedSmartTyping !== null) {
        isSmartTypingEnabled = savedSmartTyping === 'true';
        smartTypingToggle.checked = isSmartTypingEnabled;
    }
}

if (animationsToggle) {
    const savedAnimations = localStorage.getItem('animations');
    if (savedAnimations !== null) {
        areAnimationsEnabled = savedAnimations === 'true';
        animationsToggle.checked = areAnimationsEnabled;
    }
}

// ** 6. تابع secureFetchGemini - به‌روزرسانی شده برای استفاده از آدرس Render **
async function secureFetchGemini(prompt) {
    // استفاده از RENDER_API_BASE_URL برای ساخت URL کامل
    const response = await fetch('https://ayschat.onrender.com/chat/', { 
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'), // اگر از Django CSRF Protection استفاده می‌کنید
        },
        body: JSON.stringify({ prompt: prompt }),
    });

    if (!response.ok) {
        // تغییرات اینجا اعمال می‌شود برای دریافت پیام خطای دقیق‌تر
        const errorText = await response.text();
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
            const errorJson = JSON.parse(errorText);
            if (errorJson.error) {
                errorMessage += `, message: ${errorJson.error}`;
            } else {
                errorMessage += `, raw response: ${errorText}`;
            }
        } catch (e) {
            errorMessage += `, raw response: ${errorText}`;
        }
        throw new Error(errorMessage);
    }

    const data = await response.json();
    return data.response;
}

// تابع کمکی برای دریافت CSRF Token (اگر نیاز دارید)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
