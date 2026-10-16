const tg = window.Telegram?.WebApp;

// App State
let currentUser = {
    id: 8422157752, // Default admin/test ID fallback
    first_name: "Foydalanuvchi",
    username: "pixora_user",
    balance: 0
};

let allServices = [];
let filteredServices = [];
let currentCategory = 'all';
let selectedServiceForModal = null;
let activeNumbers = [];
let numberPollInterval = null;

// Initialize on Load
document.addEventListener("DOMContentLoaded", async () => {
    if (tg) {
        tg.ready();
        tg.expand();
        tg.enableClosingConfirmation();

        if (tg.initDataUnsafe?.user) {
            const u = tg.initDataUnsafe.user;
            currentUser.id = u.id;
            currentUser.first_name = u.first_name || "Foydalanuvchi";
            currentUser.username = u.username || "";
        }
    }

    // Update UI profile
    document.getElementById("userName").textContent = currentUser.first_name;
    document.getElementById("userTag").textContent = currentUser.username ? `@${currentUser.username}` : `ID: ${currentUser.id}`;
    document.getElementById("referralLinkInput").value = `https://t.me/PixoraSmmUzBot?start=ref_${currentUser.id}`;

    // Load initial data
    await loadUserData();
    await loadServices();
    await loadUserOrders();
    await loadActiveNumbers();

    // Start background status poll for virtual numbers
    startNumberPolling();
});

// Toast notification helper
function showToast(message) {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = message;
    container.appendChild(toast);

    if (tg?.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred("success");
    }

    setTimeout(() => {
        toast.remove();
    }, 3200);
}

// User Data
async function loadUserData() {
    try {
        const res = await fetch(`/api/user?user_id=${currentUser.id}&username=${encodeURIComponent(currentUser.username)}&first_name=${encodeURIComponent(currentUser.first_name)}`);
        if (res.ok) {
            const data = await res.json();
            currentUser.balance = data.balance || 0;
            document.getElementById("userBalance").textContent = `${formatNumber(currentUser.balance)} UZS`;
            document.getElementById("refCount").textContent = data.referrals_count || 0;
            document.getElementById("refEarned").textContent = `${formatNumber(data.referral_earned || 0)} UZS`;
            
            if (data.card_number) {
                document.getElementById("depositCardNum").textContent = data.card_number;
            }
            if (data.card_holder) {
                document.getElementById("depositCardName").textContent = data.card_holder;
            }
        }
    } catch (e) {
        console.error("User data fetch error:", e);
    }
}

// Switch Tabs
function switchTab(tabId) {
    document.querySelectorAll(".nav-tabs .tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

    const tabBtn = event?.currentTarget;
    if (tabBtn) tabBtn.classList.add("active");

    const content = document.getElementById(`tab-${tabId}`);
    if (content) content.classList.add("active");

    if (tg?.HapticFeedback) {
        tg.HapticFeedback.selectionChanged();
    }

    if (tabId === 'orders') {
        loadUserOrders();
    } else if (tabId === 'numbers') {
        loadActiveNumbers();
    }
}

// SMM Services Logic
async function loadServices() {
    const grid = document.getElementById("servicesGrid");
    try {
        const res = await fetch(`/api/services`);
        if (res.ok) {
            allServices = await res.json();
            renderServices(allServices);
        } else {
            grid.innerHTML = `<div class="empty-state">Xizmatlarni yuklab bo'lmadi.</div>`;
        }
    } catch (e) {
        grid.innerHTML = `<div class="empty-state">Tarmoq xatosi: ${e.message}</div>`;
    }
}

function filterCategory(cat, btn) {
    currentCategory = cat;
    document.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
    if (btn) btn.classList.add("active");

    applyFilters();
}

function handleSearch(query) {
    applyFilters();
}

function applyFilters() {
    const query = document.getElementById("searchInput").value.toLowerCase().trim();
    
    filteredServices = allServices.filter(s => {
        const matchCat = currentCategory === 'all' || s.category.toLowerCase().includes(currentCategory);
        const matchQuery = !query || s.name.toLowerCase().includes(query) || s.category.toLowerCase().includes(query);
        return matchCat && matchQuery;
    });

    renderServices(filteredServices);
}

function renderServices(services) {
    const grid = document.getElementById("servicesGrid");
    if (!services || services.length === 0) {
        grid.innerHTML = `<div class="empty-state">Mos keluvchi xizmat topilmadi.</div>`;
        return;
    }

    grid.innerHTML = services.map(s => `
        <div class="service-card">
            <div class="service-header">
                <div class="service-title">${escapeHtml(s.name)}</div>
                <div class="service-rate-badge">${formatNumber(s.rate)} UZS / 1k</div>
            </div>
            <div class="service-desc">${escapeHtml(s.description || 'Tezkor va sifatli xizmat.')}</div>
            <div class="service-footer">
                <div class="service-limits">Min: ${formatNumber(s.min)} | Max: ${formatNumber(s.max)}</div>
                <button class="order-btn" onclick="openOrderModal(${s.service_id})">
                    <i class="fa-solid fa-cart-shopping"></i> Buyurtma
                </button>
            </div>
        </div>
    `).join("");
}

// Modal Order Logic
function openOrderModal(serviceId) {
    selectedServiceForModal = allServices.find(s => s.service_id === serviceId);
    if (!selectedServiceForModal) return;

    document.getElementById("modalServiceTitle").textContent = selectedServiceForModal.name;
    document.getElementById("modalServiceDesc").textContent = selectedServiceForModal.description || "Kafolatlangan xizmat.";
    document.getElementById("modalMinMax").textContent = `Min: ${formatNumber(selectedServiceForModal.min)} | Max: ${formatNumber(selectedServiceForModal.max)}`;
    document.getElementById("modalRate").textContent = `1000 ta: ${formatNumber(selectedServiceForModal.rate)} UZS`;

    document.getElementById("orderLink").value = "";
    document.getElementById("orderQuantity").value = selectedServiceForModal.min;
    calculateModalPrice();

    document.getElementById("orderModal").classList.add("active");

    if (tg?.HapticFeedback) {
        tg.HapticFeedback.impactOccurred("medium");
    }
}

function closeOrderModal() {
    document.getElementById("orderModal").classList.remove("active");
    selectedServiceForModal = null;
}

function calculateModalPrice() {
    if (!selectedServiceForModal) return;
    const qty = parseInt(document.getElementById("orderQuantity").value) || 0;
    const total = (qty / 1000) * selectedServiceForModal.rate;
    document.getElementById("modalTotalPrice").textContent = `${formatNumber(Math.round(total))} UZS`;
}

async function submitModalOrder() {
    if (!selectedServiceForModal) return;

    const link = document.getElementById("orderLink").value.trim();
    const qty = parseInt(document.getElementById("orderQuantity").value) || 0;

    if (!link) {
        alert("Iltimos, havolani kiriting!");
        return;
    }

    if (qty < selectedServiceForModal.min || qty > selectedServiceForModal.max) {
        alert(`Miqdor ${selectedServiceForModal.min} va ${selectedServiceForModal.max} orasida bo'lishi kerak!`);
        return;
    }

    const total = (qty / 1000) * selectedServiceForModal.rate;
    if (currentUser.balance < total) {
        alert(`Mablag' yetarli emas! Sizning balansingiz: ${formatNumber(currentUser.balance)} UZS. Talab qilinadi: ${formatNumber(total)} UZS.`);
        openDepositModal();
        return;
    }

    const btn = document.getElementById("submitOrderBtn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Yuborilmoqda...`;

    try {
        const res = await fetch("/api/order", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: currentUser.id,
                service_id: selectedServiceForModal.service_id,
                link: link,
                quantity: qty
            })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            showToast("🎉 Buyurtmangiz qabul qilindi va ishga tushirildi!");
            closeOrderModal();
            await loadUserData();
            await loadUserOrders();
        } else {
            const err = data.error || "Buyurtma berilmadi";
            alert(err.startsWith("🛠") ? err : `Xatolik: ${err}`);
        }
    } catch (e) {
        alert(`Tarmoq xatosi: ${e.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-check"></i> Buyurtmani tasdiqlash`;
    }
}

// Virtual Numbers Logic
function updateNumberPrice() {
    const sel = document.getElementById("numberCountrySelect");
    const opt = sel.options[sel.selectedIndex];
    const price = opt?.getAttribute("data-price") || "8500";
    document.getElementById("numberSelectedPrice").textContent = `${formatNumber(price)} UZS`;
}

async function loadCountriesForService() {
    const service = document.getElementById("numberServiceSelect").value;
    try {
        const res = await fetch(`/api/numbers/countries?service=${service}`);
        if (res.ok) {
            const list = await res.json();
            const sel = document.getElementById("numberCountrySelect");
            sel.innerHTML = list.map(c => `
                <option value="${c.country || c.id}" data-price="${c.price || 8500}">
                    ${escapeHtml(c.name)} — ${formatNumber(c.price || 8500)} UZS
                </option>
            `).join("");
            updateNumberPrice();
        }
    } catch (e) {
        console.error("Load countries error:", e);
    }
}

async function buyVirtualNumber() {
    const serviceCode = document.getElementById("numberServiceSelect").value;
    const countrySel = document.getElementById("numberCountrySelect");
    const countryCode = countrySel.value;
    const price = parseFloat(countrySel.options[countrySel.selectedIndex]?.getAttribute("data-price") || 8500);

    if (currentUser.balance < price) {
        alert(`Mablag' yetarli emas! Raqam narxi: ${formatNumber(price)} UZS. Balansingiz: ${formatNumber(currentUser.balance)} UZS.`);
        openDepositModal();
        return;
    }

    try {
        const res = await fetch("/api/numbers/buy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: currentUser.id,
                service: serviceCode,
                country: countryCode,
                price: price
            })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            showToast(`📲 Raqam xarid qilindi: ${data.phone}`);
            await loadUserData();
            await loadActiveNumbers();
        } else {
            const err = data.error || "Raqam berilmadi";
            alert(err.startsWith("🛠") ? err : `Xatolik: ${err}`);
        }
    } catch (e) {
        alert(`Tarmoq xatosi: ${e.message}`);
    }
}

async function loadActiveNumbers() {
    const container = document.getElementById("activeNumbersList");
    try {
        const res = await fetch(`/api/numbers/active?user_id=${currentUser.id}`);
        if (res.ok) {
            activeNumbers = await res.json();
            if (activeNumbers.length === 0) {
                container.innerHTML = `<div class="empty-state">Hozirda faol raqamingiz yo'q.</div>`;
                return;
            }

            container.innerHTML = activeNumbers.map(n => `
                <div class="number-card">
                    <div class="number-info">
                        <strong>${escapeHtml(n.phone)}</strong>
                        <span>${escapeHtml(n.service_title)} (${escapeHtml(n.country_title)})</span>
                    </div>
                    <div class="number-sms-box">
                        ${n.sms_code ? 
                            `<span class="sms-code">${escapeHtml(n.sms_code)}</span>` : 
                            `<span class="sms-waiting"><i class="fa-solid fa-spinner fa-spin"></i> Kod kutilmoqda...</span>`
                        }
                    </div>
                </div>
            `).join("");
        }
    } catch (e) {
        console.error("Error loading active numbers:", e);
    }
}

function startNumberPolling() {
    if (numberPollInterval) clearInterval(numberPollInterval);
    numberPollInterval = setInterval(async () => {
        // Poll every 4 seconds if there are numbers waiting for code
        const waiting = activeNumbers.filter(n => !n.sms_code && n.status === 'WAIT_CODE');
        if (waiting.length > 0) {
            await loadActiveNumbers();
        }
    }, 4000);
}

// User Orders History
async function loadUserOrders() {
    const container = document.getElementById("ordersList");
    try {
        const res = await fetch(`/api/user/orders?user_id=${currentUser.id}`);
        if (res.ok) {
            const orders = await res.json();
            if (orders.length === 0) {
                container.innerHTML = `<div class="empty-state">Sizda hali buyurtmalar mavjud emas.</div>`;
                return;
            }

            container.innerHTML = orders.map(o => `
                <div class="order-history-card">
                    <div class="order-history-header">
                        <span>#${o.id} • ${escapeHtml(o.category)}</span>
                        <span class="status-badge status-${(o.status || 'pending').toLowerCase()}">${escapeHtml(o.status)}</span>
                    </div>
                    <div style="font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 4px;">
                        ${escapeHtml(o.service_name)}
                    </div>
                    <div style="font-size: 11px; color: #94a3b8; display: flex; justify-content: space-between;">
                        <span>Soni: ${formatNumber(o.quantity)} dona</span>
                        <span style="color: #00e676; font-weight: 700;">${formatNumber(o.price)} UZS</span>
                    </div>
                </div>
            `).join("");
        }
    } catch (e) {
        container.innerHTML = `<div class="empty-state">Buyurtmalarni yuklab bo'lmadi.</div>`;
    }
}

// Deposit Modal
function openDepositModal() {
    document.getElementById("depositModal").classList.add("active");
}

function closeDepositModal() {
    document.getElementById("depositModal").classList.remove("active");
}

// Copy Referral Link
function copyRefLink() {
    const input = document.getElementById("referralLinkInput");
    input.select();
    input.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(input.value);
    showToast("📋 Referal havolangiz nusxalandi!");
}

// Helpers
function formatNumber(num) {
    return Number(num).toLocaleString('uz-UZ');
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[m]);
}

// Free Services Logic
let selectedFreeType = null;
const freeServicesConfig = {
    'tg_sub': { title: "✈️ Bepul Telegram Obunachi", qty: "20 ta", desc: "Telegram kanal yoki guruh havolasini kiriting", placeholder: "https://t.me/kanal_nomi" },
    'tg_view': { title: "✈️ Bepul Telegram Ko'rish", qty: "100 ta", desc: "Telegram post havolasini kiriting", placeholder: "https://t.me/kanal/123" },
    'tg_react': { title: "✈️ Bepul Telegram Reaksiya", qty: "30 ta", desc: "Telegram post havolasini kiriting", placeholder: "https://t.me/kanal/123" },
    'ig_view': { title: "📸 Bepul Instagram Ko'rish", qty: "100 ta", desc: "Instagram video yoki Reels havolasini kiriting", placeholder: "https://instagram.com/reel/..." }
};

function openFreeOrderModal(type) {
    selectedFreeType = type;
    const cfg = freeServicesConfig[type];
    if (!cfg) return;

    document.getElementById("freeModalTitle").textContent = cfg.title;
    document.getElementById("freeModalQty").textContent = `Miqdor: ${cfg.qty}`;
    document.getElementById("freeModalDesc").textContent = cfg.desc;
    document.getElementById("freeOrderLink").placeholder = cfg.placeholder;
    document.getElementById("freeOrderLink").value = "";

    document.getElementById("freeOrderModal").classList.add("active");
    if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred("medium");
}

function closeFreeOrderModal() {
    document.getElementById("freeOrderModal").classList.remove("active");
    selectedFreeType = null;
}

async function submitFreeOrder() {
    if (!selectedFreeType) return;
    const link = document.getElementById("freeOrderLink").value.trim();
    if (!link) {
        alert("Iltimos, havolani kiriting!");
        return;
    }

    const btn = document.getElementById("submitFreeBtn");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Yuborilmoqda...`;

    try {
        const res = await fetch("/api/free/order", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: currentUser.id,
                service_type: selectedFreeType,
                link: link
            })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            showToast(`🎉 Bepul xizmatingiz qabul qilindi! (#${data.order_id})`);
            closeFreeOrderModal();
            await loadUserOrders();
        } else {
            const err = data.error || "Bepul buyurtma berilmadi";
            alert(err.startsWith("🛠") ? err : `Xatolik: ${err}`);
        }
    } catch (e) {
        alert(`Tarmoq xatosi: ${e.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-gift"></i> Bepul buyurtmani olish`;
    }
}
