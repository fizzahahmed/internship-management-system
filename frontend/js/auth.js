const API = 'http://127.0.0.1:5000/api'

function showError(msg) {
    const el = document.getElementById('error-msg')
    el.textContent = msg
    el.style.display = 'block'
    document.getElementById('success-msg').style.display = 'none'
}

function showSuccess(msg) {
    const el = document.getElementById('success-msg')
    el.textContent = msg
    el.style.display = 'block'
    document.getElementById('error-msg').style.display = 'none'
}

async function login() {
    const email    = document.getElementById('email').value
    const password = document.getElementById('password').value

    if (!email || !password) {
        showError('Please fill in all fields')
        return
    }

    try {
        const res  = await fetch(`${API}/auth/login`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ email, password })
        })
        const data = await res.json()

        if (!res.ok) {
            showError(data.error || 'Login failed')
            return
        }

        localStorage.setItem('token',        data.token)
        localStorage.setItem('role',         data.role)
        localStorage.setItem('name',         data.name)
        localStorage.setItem('id',           data.id)
        localStorage.setItem('profile_id',   data.profile_id)
        // Store department for both students and coordinators
        localStorage.setItem('department',   data.department   || '')
        // Store company name for employers
        localStorage.setItem('company_name', data.company_name || '')

        if (data.role === 'student') {
            window.location.href = 'student-dashboard.html'
        } else if (data.role === 'employer') {
            window.location.href = 'employer-dashboard.html'
        } else if (data.role === 'coordinator') {
            window.location.href = 'coordinator-dashboard.html'
        }

    } catch (err) {
        showError('Cannot connect to server. Make sure Flask is running.')
    }
}

function logout() {
    localStorage.clear()
    window.location.href = 'login.html'
}