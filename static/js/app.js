// ===== Utils =====

const API_URL = '/api';

async function apiCall(endpoint, options = {}) {
    const response = await fetch(API_URL + endpoint, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        credentials: 'include' // Cookies yuborish
    });
    
    if (response.status === 401) {
        // Login sahifasiga qaytarish
        window.location.href = '/';
        return null;
    }
    
    if (!response.ok) {
        const error = await response.json();
        alert('Xato: ' + (error.detail || 'Noma\'lum xato'));
        return null;
    }
    
    return await response.json();
}

// ===== Announcements =====

async function loadAnnouncements() {
    const fromCity = document.getElementById('filter-from')?.value;
    const toCity = document.getElementById('filter-to')?.value;
    
    const listEl = document.getElementById('announcements-list');
    listEl.innerHTML = '<p class="loading">Yuklanmoqda...</p>';
    
    const params = new URLSearchParams();
    if (fromCity) params.append('from_city', fromCity);
    if (toCity) params.append('to_city', toCity);
    
    const anns = await apiCall('/announcements?' + params.toString());
    if (!anns) return;
    
    if (anns.length === 0) {
        listEl.innerHTML = '<p class="loading">E\'lonlar topilmadi</p>';
        return;
    }
    
    listEl.innerHTML = anns.map(ann => `
        <div class="announcement-card">
            <h3>${ann.car_type}</h3>
            <div class="route-info">📍 ${ann.from_city} → ${ann.to_city}</div>
            
            <div class="card-detail">
                <span>🗓 ${ann.trip_date}</span>
                <span>💺 ${ann.available_seats}/${ann.total_seats} joy</span>
            </div>
            
            ${ann.driver ? `
                <div class="driver-info">
                    <strong>👤 ${ann.driver.full_name}</strong>
                    📞 ${ann.driver.phone}<br>
                    ${ann.driver.username ? `🔗 @${ann.driver.username}` : ''}<br>
                    ${ann.driver.plate_number ? `🔢 ${ann.driver.plate_number}` : ''}<br>
                    🧳 ${ann.driver.has_luggage ? 'Bagaj bor' : 'Bagaj yo\'q'}<br>
                    📦 ${ann.driver.takes_parcel ? 'Pochta qabul' : 'Pochta yo\'q'}
                </div>
            ` : ''}
            
            <button class="btn-primary booking-button" 
                    onclick="openBookingModal(${ann.id}, ${ann.available_seats})">
                🎫 Joy band qilish
            </button>
        </div>
    `).join('');
}

function openBookingModal(annId, availableSeats) {
    const modal = document.getElementById('booking-modal');
    const seatsSelect = document.getElementById('booking-seats');
    
    // Max seats selectini cheklash
    seatsSelect.innerHTML = '';
    for (let i = 1; i <= Math.min(availableSeats, 4); i++) {
        seatsSelect.innerHTML += `<option value="${i}">${i} joy</option>`;
    }
    
    document.getElementById('booking-ann-id').value = annId;
    modal.classList.remove('hidden');
}

function closeBookingModal() {
    document.getElementById('booking-modal').classList.add('hidden');
}

document.getElementById('booking-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const annId = parseInt(document.getElementById('booking-ann-id').value);
    const seats = parseInt(document.getElementById('booking-seats').value);
    
    const result = await apiCall('/bookings/create', {
        method: 'POST',
        body: JSON.stringify({ announcement_id: annId, seats })
    });
    
    if (result) {
        alert('✅ Joy band qilindi! To\'lov sahifasiga o\'tishdalaringiz kerak.');
        closeBookingModal();
        await loadMyBookings();
    }
});

// ===== My Bookings =====

async function loadMyBookings() {
    const listEl = document.getElementById('bookings-list');
    if (!listEl) return;
    
    listEl.innerHTML = '<p class="loading">Yuklanmoqda...</p>';
    
    const bookings = await apiCall('/bookings/my');
    if (!bookings) return;
    
    if (bookings.length === 0) {
        listEl.innerHTML = '<p class="loading">Buyurtmalaringiz yo\'q</p>';
        return;
    }
    
    const statusMap = {
        'pending_payment': 'To\'lov kutilmoqda',
        'waiting_driver': 'Haydovchi javobini kutmoqda',
        'confirmed': 'Tasdiqlangan',
        'rejected': 'Rad etilgan',
        'cancelled': 'Bekor qilingan'
    };
    
    listEl.innerHTML = bookings.map(b => `
        <div class="booking-item">
            <div class="booking-details">
                <h4>#${b.id} - ${b.announcement.from_city} → ${b.announcement.to_city}</h4>
                <p>💺 ${b.seats} joy | 🗓 ${b.announcement.trip_date}</p>
            </div>
            <span class="booking-status status-${b.status}">
                ${statusMap[b.status] || b.status}
            </span>
        </div>
    `).join('');
}

// ===== Profile =====

async function loadProfile() {
    const profileEl = document.getElementById('profile-info');
    if (!profileEl) return;
    
    profileEl.innerHTML = '<p class="loading">Yuklanmoqda...</p>';
    
    const user = await apiCall('/user/me');
    if (!user) return;
    
    profileEl.innerHTML = `
        <div class="profile-field">
            <strong>Nomi:</strong>
            <span>${user.full_name || '-'}</span>
        </div>
        <div class="profile-field">
            <strong>Telegram:</strong>
            <span>${user.username ? '@' + user.username : 'yo\'q'}</span>
        </div>
        <div class="profile-field">
            <strong>Telefon:</strong>
            <span>${user.phone || '-'}</span>
        </div>
        <div class="profile-field">
            <strong>Rol:</strong>
            <span>${user.role === 'driver' ? '🚖 Taksichi' : '🧍 Yo\'lovchi'}</span>
        </div>
        ${user.car_brand ? `
            <div class="profile-field">
                <strong>Mashina:</strong>
                <span>${user.car_brand}${user.plate_number ? ' (' + user.plate_number + ')' : ''}</span>
            </div>
        ` : ''}
    `;
}

// ===== Logout =====

function logout() {
    if (confirm('Chiqmoqchi musiz?')) {
        // Cookie'ni o'chirish (simple yechim)
        document.cookie = 'session_tg_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
        window.location.href = '/';
    }
}

// ===== Initial Load =====

document.addEventListener('DOMContentLoaded', () => {
    // Agar dashboard'da bo'lsa ma'lumotlarni yuklash
    if (window.location.pathname === '/dashboard') {
        loadAnnouncements();
        loadMyBookings();
        loadProfile();
        
        // Har 10 sekundda yangilash
        setInterval(loadAnnouncements, 10000);
        setInterval(loadMyBookings, 10000);
    }
});

// Filter o'zgarganida
document.getElementById('filter-from')?.addEventListener('change', () => loadAnnouncements());
document.getElementById('filter-to')?.addEventListener('change', () => loadAnnouncements());
