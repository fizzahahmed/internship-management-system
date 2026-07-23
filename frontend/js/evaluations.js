const API = 'http://127.0.0.1:5000/api'

function getToken() {
    return localStorage.getItem('token')
}

function logout() {
    localStorage.clear()
    window.location.href = 'login.html'
}

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const name = localStorage.getItem('name')
    if (!getToken()) {
        window.location.href = 'login.html'
        return
    }
    const welcomeEl = document.getElementById('welcome-msg')
    if (welcomeEl) welcomeEl.textContent = `Welcome, ${name}`

    loadEmployerDashboard()
})

async function loadEmployerDashboard() {
    try {
        const [internsRes, evalsRes] = await Promise.all([
            fetch(`${API}/internships/`, { headers: authHeaders() }),
            fetch(`${API}/evaluations/`, { headers: authHeaders() })
        ])

        const internships = await internsRes.json()
        const evaluations = await evalsRes.json()

        document.getElementById('stat-interns').textContent = internships.length
        document.getElementById('stat-evaluations').textContent = evaluations.length

        const table = document.getElementById('interns-table')
        if (internships.length === 0) {
            table.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#888">No interns yet</td></tr>'
        } else {
            table.innerHTML = internships.map(i => `
                <tr>
                    <td>${i.students?.user_id || 'N/A'}</td>
                    <td>N/A</td>
                    <td>${i.start_date || 'N/A'}</td>
                    <td><span class="badge badge-success">${i.status}</span></td>
                    <td><button class="btn btn-warning" style="padding:5px 12px; font-size:12px"
                        onclick="selectInternship(${i.id})">Evaluate</button></td>
                </tr>
            `).join('')
        }

        const select = document.getElementById('internship-select')
        internships.forEach(i => {
            const opt = document.createElement('option')
            opt.value = i.id
            opt.textContent = `Internship #${i.id} — ${i.employers?.company_name || 'Company'}`
            select.appendChild(opt)
        })

    } catch (err) {
        console.error('Error loading employer dashboard:', err)
    }
}

function selectInternship(id) {
    document.getElementById('internship-select').value = id
    document.getElementById('score').focus()
}

async function submitEvaluation() {
    const internshipId = document.getElementById('internship-select').value
    const score = document.getElementById('score').value
    const comments = document.getElementById('comments').value

    if (!internshipId || !score) {
        document.getElementById('error-msg').textContent = 'Please select an internship and enter a score'
        document.getElementById('error-msg').style.display = 'block'
        return
    }

    try {
        const res = await fetch(`${API}/evaluations/`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ internship_id: internshipId, score, comments })
        })

        const data = await res.json()
        if (!res.ok) {
            document.getElementById('error-msg').textContent = data.error || 'Failed to submit'
            document.getElementById('error-msg').style.display = 'block'
            return
        }

        document.getElementById('success-msg').textContent = 'Evaluation submitted successfully!'
        document.getElementById('success-msg').style.display = 'block'
        document.getElementById('error-msg').style.display = 'none'
        document.getElementById('score').value = ''
        document.getElementById('comments').value = ''

    } catch (err) {
        console.error(err)
    }
}