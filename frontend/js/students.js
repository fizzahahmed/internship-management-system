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
    const role = localStorage.getItem('role')

    if (!getToken()) {
        window.location.href = 'login.html'
        return
    }

    const welcomeEl = document.getElementById('welcome-msg')
    if (welcomeEl) welcomeEl.textContent = `Welcome, ${name}`

    if (role === 'student') loadStudentDashboard()
    if (role === 'coordinator') loadCoordinatorDashboard()
})

async function loadStudentDashboard() {
    const studentId = localStorage.getItem('id')

    try {
        const [internsRes, evalsRes, vivaRes] = await Promise.all([
            fetch(`${API}/internships/`, { headers: authHeaders() }),
            fetch(`${API}/evaluations/`, { headers: authHeaders() }),
            fetch(`${API}/viva/`, { headers: authHeaders() })
        ])

        const internships = await internsRes.json()
        const evaluations = await evalsRes.json()
        const vivas = await vivaRes.json()

        document.getElementById('stat-internships').textContent = internships.length
        document.getElementById('stat-evaluations').textContent = evaluations.length
        document.getElementById('stat-viva').textContent = vivas.length

        const internTable = document.getElementById('internships-table')
        if (internships.length === 0) {
            internTable.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#888">No internships found</td></tr>'
        } else {
            internTable.innerHTML = internships.map(i => `
                <tr>
                    <td>${i.employers?.company_name || 'N/A'}</td>
                    <td>${i.start_date || 'N/A'}</td>
                    <td>${i.end_date || 'N/A'}</td>
                    <td><span class="badge badge-${i.status === 'ongoing' ? 'success' : 'info'}">${i.status}</span></td>
                </tr>
            `).join('')
        }

        const evalTable = document.getElementById('evaluations-table')
        if (evaluations.length === 0) {
            evalTable.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#888">No evaluations yet</td></tr>'
        } else {
            evalTable.innerHTML = evaluations.map(e => `
                <tr>
                    <td>${e.score}/100</td>
                    <td>${e.comments || 'N/A'}</td>
                    <td>${e.created_at ? e.created_at.split('T')[0] : 'N/A'}</td>
                </tr>
            `).join('')
        }

        const vivaTable = document.getElementById('viva-table')
        if (vivas.length === 0) {
            vivaTable.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#888">No viva scheduled yet</td></tr>'
        } else {
            vivaTable.innerHTML = vivas.map(v => `
                <tr>
                    <td>${v.date || 'N/A'}</td>
                    <td>${v.marks}/100</td>
                    <td>${v.remarks || 'N/A'}</td>
                </tr>
            `).join('')
        }

    } catch (err) {
        console.error('Error loading dashboard:', err)
    }
}

async function loadCoordinatorDashboard() {
    try {
        const [studentsRes, employersRes, internsRes, vivaRes] = await Promise.all([
            fetch(`${API}/students/`, { headers: authHeaders() }),
            fetch(`${API}/employers/`, { headers: authHeaders() }),
            fetch(`${API}/internships/`, { headers: authHeaders() }),
            fetch(`${API}/viva/`, { headers: authHeaders() })
        ])

        const students = await studentsRes.json()
        const employers = await employersRes.json()
        const internships = await internsRes.json()
        const vivas = await vivaRes.json()

        document.getElementById('stat-students').textContent = students.length
        document.getElementById('stat-employers').textContent = employers.length
        document.getElementById('stat-internships').textContent = internships.length
        document.getElementById('stat-viva').textContent = vivas.length

        const studTable = document.getElementById('students-table')
        if (students.length === 0) {
            studTable.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#888">No students found</td></tr>'
        } else {
            studTable.innerHTML = students.map(s => `
                <tr>
                    <td>${s.users?.name || 'N/A'}</td>
                    <td>${s.users?.email || 'N/A'}</td>
                    <td>${s.department || 'N/A'}</td>
                    <td>${s.credit_hours || 'N/A'}</td>
                    <td><span class="badge badge-success">${s.status}</span></td>
                </tr>
            `).join('')
        }

        const internTable = document.getElementById('internships-table')
        if (internships.length === 0) {
            internTable.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#888">No internships found</td></tr>'
        } else {
            internTable.innerHTML = internships.map(i => `
                <tr>
                    <td>${i.employers?.company_name || 'N/A'}</td>
                    <td>${i.start_date || 'N/A'}</td>
                    <td>${i.end_date || 'N/A'}</td>
                    <td><span class="badge badge-${i.status === 'ongoing' ? 'success' : 'info'}">${i.status}</span></td>
                </tr>
            `).join('')
        }

        loadStudentDropdown(students)

    } catch (err) {
        console.error('Error loading coordinator dashboard:', err)
    }
}

function loadStudentDropdown(students) {
    const select = document.getElementById('student-select')
    if (!select) return
    students.forEach(s => {
        const opt = document.createElement('option')
        opt.value = s.id
        opt.textContent = s.users?.name || 'Student ' + s.id
        select.appendChild(opt)
    })
}

async function scheduleViva() {
    const studentId = document.getElementById('student-select').value
    const date = document.getElementById('viva-date').value
    const marks = document.getElementById('viva-marks').value
    const remarks = document.getElementById('viva-remarks').value

    if (!studentId || !date || !marks) {
        document.getElementById('error-msg').textContent = 'Please fill all required fields'
        document.getElementById('error-msg').style.display = 'block'
        return
    }

    try {
        const res = await fetch(`${API}/viva/`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ student_id: studentId, date, marks, remarks })
        })

        const data = await res.json()
        if (!res.ok) {
            document.getElementById('error-msg').textContent = data.error || 'Failed'
            document.getElementById('error-msg').style.display = 'block'
            return
        }

        document.getElementById('success-msg').textContent = 'Viva scheduled successfully!'
        document.getElementById('success-msg').style.display = 'block'
        document.getElementById('error-msg').style.display = 'none'

    } catch (err) {
        console.error(err)
    }
}