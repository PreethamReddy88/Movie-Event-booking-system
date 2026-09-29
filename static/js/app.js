/**
 * CinePrime — Cinema Ticket Booking System
 * Complete Vanilla JS Client Application
 */

const API_BASE = '/api';

// ── Application State ──
const state = {
  token: localStorage.getItem('cineprime_token') || '',
  user: null,
  movies: [],
  selectedMovie: null,
  shows: [],
  selectedShow: null,
  seats: [],
  selectedSeatIds: new Set(),
  activeBooking: null,
  isAuthSignUp: false,
};

// ── Utility: Toast Notifications ──
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ── Utility: Architecture & Concurrency Logger ──
function logInspector(category, message, level = '') {
  const logsContainer = document.getElementById('inspectorLogs');
  const entry = document.createElement('div');
  entry.className = `log-entry ${level}`;
  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');
  entry.innerHTML = `<span class="log-time">[${timeStr}] [${category}]</span> <span>${message}</span>`;
  logsContainer.appendChild(entry);
  logsContainer.scrollTop = logsContainer.scrollHeight;
}

// ── Drawer Toggle ──
function toggleInspector() {
  const drawer = document.getElementById('inspectorDrawer');
  const icon = document.getElementById('inspectorToggleIcon');
  drawer.classList.toggle('collapsed');
  icon.textContent = drawer.classList.contains('collapsed') ? '▲' : '▼';
}

// ── Tab Navigation ──
function switchTab(tabId) {
  document.getElementById('moviesSection').style.display = tabId === 'moviesSection' ? 'block' : 'none';
  document.getElementById('myBookingsSection').style.display = tabId === 'myBookingsSection' ? 'block' : 'none';
  
  document.querySelectorAll('.nav-item').forEach(el => {
    if (el.textContent.includes('Movies') && tabId === 'moviesSection') el.classList.add('active');
    else if (el.textContent.includes('Bookings') && tabId === 'myBookingsSection') el.classList.add('active');
    else el.classList.remove('active');
  });

  if (tabId === 'myBookingsSection') {
    loadMyBookings();
  }
}

function scrollToMovies() {
  document.getElementById('moviesSection').scrollIntoView({ behavior: 'smooth' });
}

// ── API Helper ──
async function apiCall(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(state.token ? { 'Authorization': `Bearer ${state.token}` } : {}),
    ...options.headers,
  };

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });
    
    if (res.status === 401 && state.token) {
      logInspector('Auth', 'JWT token expired or invalid', 'redis');
      logout();
      showToast('Session expired. Please sign in again.', 'error');
      throw new Error('Unauthorized');
    }

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'API request failed');
    }
    return data;
  } catch (err) {
    throw err;
  }
}

// ── Auth Management ──
async function checkAuth() {
  if (!state.token) {
    renderUserArea();
    return;
  }
  try {
    const user = await apiCall('/auth/me');
    state.user = user;
    renderUserArea();
    logInspector('Auth', `Logged in as ${user.name} (${user.role})`, 'success');
  } catch (e) {
    state.token = '';
    localStorage.removeItem('cineprime_token');
    renderUserArea();
  }
}

function renderUserArea() {
  const area = document.getElementById('userArea');
  if (state.user) {
    area.innerHTML = `
      <div class="user-pill">
        <div class="user-avatar">${state.user.name.charAt(0).toUpperCase()}</div>
        <div class="user-info-text">${state.user.name}</div>
        <span class="user-role-badge">${state.user.role}</span>
        <button onclick="logout()" style="background:none; color:var(--text-dim); margin-left:4px;" title="Logout">✕</button>
      </div>
    `;
  } else {
    area.innerHTML = `
      <button class="btn-primary" onclick="openAuthModal()">Sign In</button>
    `;
  }
}

function openAuthModal() {
  document.getElementById('authModal').classList.add('active');
}

function closeAuthModal() {
  document.getElementById('authModal').classList.remove('active');
}

function toggleAuthMode() {
  state.isAuthSignUp = !state.isAuthSignUp;
  document.getElementById('nameGroup').style.display = state.isAuthSignUp ? 'block' : 'none';
  document.getElementById('authModalTitle').textContent = state.isAuthSignUp ? 'Create CinePrime Account' : 'Sign In to CinePrime';
  document.getElementById('authSubmitBtn').textContent = state.isAuthSignUp ? 'Sign Up' : 'Sign In';
  document.getElementById('authToggleText').textContent = state.isAuthSignUp ? 'Already have an account?' : "Don't have an account?";
  document.getElementById('authToggleLink').textContent = state.isAuthSignUp ? 'Sign In' : 'Sign Up';
}

function quickFillLogin(email, pass) {
  document.getElementById('authEmail').value = email;
  document.getElementById('authPassword').value = pass;
  if (state.isAuthSignUp) toggleAuthMode();
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const email = document.getElementById('authEmail').value;
  const password = document.getElementById('authPassword').value;

  try {
    if (state.isAuthSignUp) {
      const name = document.getElementById('authName').value || 'User';
      await apiCall('/auth/signup', {
        method: 'POST',
        body: JSON.stringify({ name, email, password }),
      });
      showToast('Account created! Logging you in...', 'success');
    }

    const tokenRes = await apiCall('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    state.token = tokenRes.access_token;
    localStorage.setItem('cineprime_token', state.token);
    await checkAuth();
    closeAuthModal();
    showToast(`Welcome back, ${state.user.name}!`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function logout() {
  state.token = '';
  state.user = null;
  localStorage.removeItem('cineprime_token');
  renderUserArea();
  showToast('Logged out successfully', 'info');
}

// ── Movies Catalog ──
async function loadMovies() {
  try {
    const movies = await apiCall('/movies');
    state.movies = movies;
    document.getElementById('movieCountBadge').textContent = `${movies.length} Movies`;
    renderMoviesGrid();

    // Set Hero movie
    if (movies.length > 0) {
      const hero = movies[0];
      document.getElementById('heroTitle').textContent = hero.title;
      document.getElementById('heroGenre').textContent = hero.genre;
      document.getElementById('heroDuration').textContent = `⏱️ ${hero.duration_minutes} mins`;
      document.getElementById('heroLang').textContent = `🌐 ${hero.language}`;
    }
  } catch (err) {
    showToast('Failed to load movies: ' + err.message, 'error');
  }
}

function renderMoviesGrid() {
  const grid = document.getElementById('moviesGrid');
  grid.innerHTML = '';

  state.movies.forEach(movie => {
    let artClass = 'poster-art-dune';
    let icon = '🏜️';
    if (movie.title.toLowerCase().includes('oppenheimer')) {
      artClass = 'poster-art-oppenheimer';
      icon = '💥';
    } else if (movie.title.toLowerCase().includes('interstellar')) {
      artClass = 'poster-art-interstellar';
      icon = '🌌';
    }

    const card = document.createElement('div');
    card.className = 'movie-card';
    card.innerHTML = `
      <div class="movie-poster-box">
        <div class="${artClass}">
          <div class="poster-icon">${icon}</div>
          <div class="poster-title-text">${movie.title}</div>
        </div>
        <div class="movie-format-badge">IMAX 4K</div>
      </div>
      <div class="movie-card-body">
        <div class="movie-card-title">${movie.title}</div>
        <div class="movie-card-genre">${movie.genre} • ${movie.language}</div>
        <div class="movie-card-footer">
          <span>⏱️ ${movie.duration_minutes}m</span>
          <button class="btn-primary" style="padding: 0.35rem 0.8rem; font-size: 0.8rem;" onclick="selectMovie(${movie.id}); event.stopPropagation();">
            Book Seats
          </button>
        </div>
      </div>
    `;
    card.onclick = () => selectMovie(movie.id);
    grid.appendChild(card);
  });
}

function quickBookFeatured() {
  if (state.movies.length > 0) {
    selectMovie(state.movies[0].id);
  }
}

// ── Showtime Selection ──
async function selectMovie(movieId) {
  const movie = state.movies.find(m => m.id === movieId);
  if (!movie) return;
  state.selectedMovie = movie;

  document.getElementById('wsThumb').textContent = movie.title.includes('Dune') ? '🏜️' : movie.title.includes('Oppenheimer') ? '💥' : '🌌';
  document.getElementById('wsMovieTitle').textContent = movie.title;
  document.getElementById('wsMovieMeta').textContent = `${movie.duration_minutes} mins • ${movie.genre} • ${movie.language}`;

  const ws = document.getElementById('bookingWorkspace');
  ws.style.display = 'block';
  ws.scrollIntoView({ behavior: 'smooth' });

  // Reset seats
  document.getElementById('cinemaHall').style.display = 'none';
  state.selectedSeatIds.clear();
  updateSummaryBar();

  // Load shows
  try {
    const shows = await apiCall(`/shows/movie/${movieId}`);
    state.shows = shows;
    renderShowtimes();
    logInspector('Catalog', `Loaded ${shows.length} shows for movie: "${movie.title}"`);
  } catch (err) {
    showToast('Failed to load shows: ' + err.message, 'error');
  }
}

function closeWorkspace() {
  document.getElementById('bookingWorkspace').style.display = 'none';
  state.selectedMovie = null;
  state.selectedShow = null;
  state.selectedSeatIds.clear();
}

function renderShowtimes() {
  const container = document.getElementById('showtimesContainer');
  if (state.shows.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
        No active shows scheduled for this movie yet.
      </div>
    `;
    return;
  }

  // Group shows by theatre
  const grouped = {};
  state.shows.forEach(s => {
    const tName = s.theatre ? `${s.theatre.name} (${s.theatre.city})` : `Theatre #${s.theatre_id}`;
    if (!grouped[tName]) grouped[tName] = [];
    grouped[tName].push(s);
  });

  let html = `<div style="font-size: 1rem; font-weight: 700; margin-bottom: 1rem;">Select a Theatre & Showtime:</div>`;

  for (const [theatreName, showList] of Object.entries(grouped)) {
    html += `
      <div class="theatre-row">
        <div class="theatre-name">🏛️ ${theatreName}</div>
        <div class="shows-list">
          ${showList.map(s => {
            const dt = new Date(s.show_time);
            const timeStr = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const dateStr = dt.toLocaleDateString([], { month: 'short', day: 'numeric' });
            return `
              <div class="show-chip ${state.selectedShow?.id === s.id ? 'active' : ''}" onclick="selectShow(${s.id})">
                <div class="show-time">${dateStr} • ${timeStr}</div>
                <div class="show-price">₹${s.price} (IMAX)</div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
}

// ── Seat Layout & Interactive Hall ──
async function selectShow(showId) {
  const show = state.shows.find(s => s.id === showId);
  if (!show) return;
  state.selectedShow = show;
  renderShowtimes(); // refresh active chip styling

  state.selectedSeatIds.clear();
  updateSummaryBar();

  logInspector('Catalog', `Selected show #${show.id} at ₹${show.price}. Fetching real-time seat status...`);

  try {
    const seats = await apiCall(`/shows/${showId}/seats`);
    state.seats = seats;
    renderSeatMatrix();
    document.getElementById('cinemaHall').style.display = 'flex';
    document.getElementById('cinemaHall').scrollIntoView({ behavior: 'smooth' });
    logInspector('DB', `Fetched ${seats.length} seats. ${seats.filter(s => !s.is_booked).length} available.`);
  } catch (err) {
    showToast('Failed to load seats: ' + err.message, 'error');
  }
}

function renderSeatMatrix() {
  const matrix = document.getElementById('seatMatrix');
  matrix.innerHTML = '';

  // Group seats by row letter (e.g. A, B, C)
  const rows = {};
  state.seats.forEach(s => {
    const rowLetter = s.seat_number.charAt(0);
    if (!rows[rowLetter]) rows[rowLetter] = [];
    rows[rowLetter].push(s);
  });

  // Sort rows alphabetically
  const sortedRowKeys = Object.keys(rows).sort();

  sortedRowKeys.forEach(rowKey => {
    const rowEl = document.createElement('div');
    rowEl.className = 'seat-row';

    const label = document.createElement('div');
    label.className = 'row-label';
    label.textContent = rowKey;
    rowEl.appendChild(label);

    const itemsContainer = document.createElement('div');
    itemsContainer.className = 'seat-row-items';

    // Sort seats in row by number
    rows[rowKey].sort((a, b) => {
      const numA = parseInt(a.seat_number.slice(1)) || 0;
      const numB = parseInt(b.seat_number.slice(1)) || 0;
      return numA - numB;
    });

    rows[rowKey].forEach(seat => {
      const seatEl = document.createElement('div');
      const isSelected = state.selectedSeatIds.has(seat.id);
      const isBooked = seat.is_booked;
      const isPremium = seat.seat_type === 'premium';

      seatEl.className = `seat-unit ${isPremium ? 'premium' : ''} ${isSelected ? 'selected' : ''} ${isBooked ? 'booked' : ''}`;
      seatEl.textContent = seat.seat_number;
      seatEl.title = `Seat ${seat.seat_number} (${seat.seat_type.toUpperCase()}) - ${isBooked ? 'Already Booked' : 'Available'}`;

      if (!isBooked) {
        seatEl.onclick = () => toggleSeat(seat.id);
      }

      itemsContainer.appendChild(seatEl);
    });

    rowEl.appendChild(itemsContainer);
    matrix.appendChild(rowEl);
  });
}

function toggleSeat(seatId) {
  if (state.selectedSeatIds.has(seatId)) {
    state.selectedSeatIds.delete(seatId);
  } else {
    // Max 6 seats per transaction
    if (state.selectedSeatIds.size >= 6) {
      showToast('Maximum 6 seats per transaction', 'info');
      return;
    }
    state.selectedSeatIds.add(seatId);
  }
  renderSeatMatrix();
  updateSummaryBar();
}

function updateSummaryBar() {
  const count = state.selectedSeatIds.size;
  document.getElementById('selectedCount').textContent = count;

  const badges = document.getElementById('selectedBadges');
  if (count === 0) {
    badges.innerHTML = `<span style="color: var(--text-dim); font-size: 0.85rem;">Click seats in the hall to select</span>`;
    document.getElementById('totalPrice').textContent = '₹0';
    document.getElementById('btnProceedBooking').disabled = true;
    return;
  }

  const selectedSeats = state.seats.filter(s => state.selectedSeatIds.has(s.id));
  badges.innerHTML = selectedSeats.map(s => `<span class="seat-badge">${s.seat_number}</span>`).join('');

  const total = (state.selectedShow?.price || 0) * count;
  document.getElementById('totalPrice').textContent = `₹${total}`;
  document.getElementById('btnProceedBooking').disabled = false;
}

// ── Booking Flow & Distributed Lock Acquisition ──
async function handleProceedBooking() {
  if (!state.token) {
    showToast('Please sign in to proceed with booking', 'info');
    openAuthModal();
    return;
  }

  if (state.selectedSeatIds.size === 0 || !state.selectedShow) {
    showToast('Please select at least one seat', 'info');
    return;
  }

  const seatIds = Array.from(state.selectedSeatIds);
  const selectedSeatObjs = state.seats.filter(s => state.selectedSeatIds.has(s.id));
  const seatNumbers = selectedSeatObjs.map(s => s.seat_number).join(', ');
  const idempotencyKey = 'web-' + crypto.randomUUID();

  logInspector('Lock', `[Layer 1] Attempting Redis lock SET NX EX 300 for seats: ${seatNumbers}...`, 'redis');
  logInspector('DB', `[Layer 2] Opening ACID transaction; checking SELECT ... FOR UPDATE...`, 'db');

  const btn = document.getElementById('btnProceedBooking');
  btn.disabled = true;
  btn.textContent = 'Reserving Seats...';

  try {
    const booking = await apiCall('/bookings', {
      method: 'POST',
      body: JSON.stringify({
        show_id: state.selectedShow.id,
        seat_ids: seatIds,
        idempotency_key: idempotencyKey,
      }),
    });

    state.activeBooking = booking;
    logInspector('Booking', `✓ Created PENDING booking #${booking.id}. Status: PENDING. Seats held!`, 'success');
    showToast('Seats temporarily held! Please complete payment within 5 mins.', 'success');

    // Open Payment Modal
    openPaymentModal(booking, seatNumbers);
  } catch (err) {
    logInspector('Lock', `❌ Booking rejected: ${err.message}`, 'redis');
    showToast(err.message, 'error');
    // Refresh seat map to show updated reality
    selectShow(state.selectedShow.id);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Proceed to Reserve ➜';
  }
}

// ── Payment Modal & Gateway Simulation ──
function openPaymentModal(booking, seatNumbers) {
  document.getElementById('payBookingId').textContent = `#${booking.id}`;
  document.getElementById('paySeatsText').textContent = seatNumbers;
  const total = (state.selectedShow?.price || 0) * booking.seats.length;
  document.getElementById('payAmountText').textContent = `₹${total}`;
  document.getElementById('paymentModal').classList.add('active');
}

function closePaymentModal() {
  document.getElementById('paymentModal').classList.remove('active');
}

async function submitPayment(simulateFailure = false) {
  if (!state.activeBooking) return;
  const bookingId = state.activeBooking.id;

  if (simulateFailure) {
    logInspector('Payment', `Simulating payment failure on booking #${bookingId}...`, 'redis');
  } else {
    logInspector('Payment', `Charging payment for booking #${bookingId}...`, 'success');
  }

  try {
    const payment = await apiCall('/payments', {
      method: 'POST',
      body: JSON.stringify({
        booking_id: bookingId,
        simulate_failure: simulateFailure,
      }),
    });

    closePaymentModal();

    if (payment.status.toLowerCase() === 'success') {
      logInspector('Payment', `✓ Payment #${payment.id} SUCCESS. Booking confirmed!`, 'success');
      logInspector('Redis', `✓ Redis locks released (seats are now permanently committed in DB)`, 'success');
      showToast('Booking Confirmed! Enjoy your movie 🍿', 'success');

      // Open Ticket Modal
      openTicketModal(state.activeBooking);
    } else {
      logInspector('Payment', `❌ Payment FAILED. Booking marked FAILED.`, 'redis');
      logInspector('Redis', `✓ Redis seat locks auto-released back to the hall pool.`, 'redis');
      showToast('Payment failed. Seats have been released back for other users.', 'error');
    }

    // Refresh seat matrix
    selectShow(state.selectedShow.id);
  } catch (err) {
    showToast('Payment error: ' + err.message, 'error');
  }
}

// ── Confirmed Ticket Modal ──
function openTicketModal(booking) {
  document.getElementById('ticketMovieTitle').textContent = state.selectedMovie?.title || 'Movie';
  document.getElementById('ticketTheatre').textContent = state.selectedShow?.theatre?.name || 'CinePrime IMAX';
  
  const dt = new Date(state.selectedShow?.show_time);
  document.getElementById('ticketShowtime').textContent = dt.toLocaleString([], {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });

  document.getElementById('ticketSeats').textContent = booking.seats.join(', ');
  document.getElementById('ticketBookingId').textContent = `#${booking.id}`;
  document.getElementById('ticketIdemKey').textContent = booking.idempotency_key;

  document.getElementById('ticketModal').classList.add('active');
}

function closeTicketModal() {
  document.getElementById('ticketModal').classList.remove('active');
}

// ── My Bookings Tab ──
async function loadMyBookings() {
  if (!state.token) {
    document.getElementById('bookingsList').innerHTML = `
      <div class="glass-panel" style="text-align: center; padding: 2.5rem;">
        <p style="color: var(--text-muted); margin-bottom: 1rem;">Please sign in to view your booked tickets.</p>
        <button class="btn-primary" onclick="openAuthModal()">Sign In</button>
      </div>
    `;
    return;
  }

  try {
    const bookings = await apiCall('/bookings');
    renderBookingsList(bookings);
  } catch (err) {
    showToast('Failed to load bookings: ' + err.message, 'error');
  }
}

function renderBookingsList(bookings) {
  const container = document.getElementById('bookingsList');
  if (bookings.length === 0) {
    container.innerHTML = `
      <div class="glass-panel" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
        You haven't made any bookings yet. Browse our movies and pick a show!
      </div>
    `;
    return;
  }

  container.innerHTML = bookings.map(b => {
    const isConfirmed = b.status.toLowerCase() === 'confirmed';
    const isPending = b.status.toLowerCase() === 'pending';
    const dt = new Date(b.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

    return `
      <div class="booking-card">
        <div>
          <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.4rem;">
            <strong style="font-size: 1.15rem; color: #fff;">Booking #${b.id}</strong>
            <span class="user-role-badge" style="${isConfirmed ? 'background:rgba(16,185,129,0.15); color:#34d399;' : isPending ? 'background:rgba(245,158,11,0.15); color:#fbbf24;' : 'background:rgba(239,68,68,0.15); color:#f87171;'}">
              ${b.status.toUpperCase()}
            </span>
          </div>
          <div style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.3rem;">
            Seats: <strong style="color: var(--accent-gold-light);">${b.seats.join(', ') || 'N/A'}</strong> • Show ID: #${b.show_id}
          </div>
          <div style="font-size: 0.75rem; color: var(--text-dim);" class="mono">
            Booked on ${dt} • Key: ${b.idempotency_key}
          </div>
        </div>

        <div style="display: flex; gap: 0.75rem;">
          ${isConfirmed ? `
            <button class="btn-secondary" style="color: #f87171; border-color: rgba(239,68,68,0.3);" onclick="cancelBooking(${b.id})">
              Cancel Seats
            </button>
          ` : isPending ? `
            <button class="btn-primary" onclick="resumePayment(${b.id}, '${b.seats.join(', ')}')">
              Complete Payment
            </button>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

async function cancelBooking(bookingId) {
  if (!confirm(`Are you sure you want to cancel booking #${bookingId}? Seats will be released back to the theatre.`)) {
    return;
  }

  logInspector('Booking', `Cancelling booking #${bookingId}... Releasing DB seats and locks.`, 'redis');

  try {
    await apiCall(`/bookings/${bookingId}/cancel`, { method: 'POST' });
    showToast(`Booking #${bookingId} cancelled successfully.`, 'info');
    loadMyBookings();
    if (state.selectedShow) {
      selectShow(state.selectedShow.id);
    }
  } catch (err) {
    showToast('Failed to cancel: ' + err.message, 'error');
  }
}

function resumePayment(bookingId, seatNumbers) {
  state.activeBooking = { id: bookingId, seats: seatNumbers.split(', ') };
  openPaymentModal(state.activeBooking, seatNumbers);
}

// ── Application Initialization ──
document.addEventListener('DOMContentLoaded', async () => {
  logInspector('App', 'CinePrime Frontend loaded successfully.');
  await checkAuth();
  await loadMovies();
});
