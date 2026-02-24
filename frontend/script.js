// Postavi URL servera. Ako pokreces sa istog racunara, localhost je u redu.
const API_BASE_URL = 'http://127.0.0.1:5000';

// Elementi iz DOM-a
const elPeopleCount = document.getElementById('status-people');
const elAlarmStatus = document.getElementById('status-alarm');
const elTimerVal = document.getElementById('timer-val');
const elAlarmText = document.getElementById('alarm-text');
const elSecurityMsg = document.getElementById('security-message');

// Periodicno preuzimanje stanja sa servera
async function fetchStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/status`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        // Azuriranje broja ljudi
        elPeopleCount.innerText = `Ljudi u kuci: ${data.people_count}`;

        // Azuriranje alarma
        if (data.alarm_active) {
            elAlarmStatus.innerText = "ALARM AKTIVAN";
            elAlarmStatus.className = "status-danger";
            elAlarmStatus.style.backgroundColor = "";
            elAlarmText.innerText = "Sistem detektuje uzbunu!";
            elAlarmText.style.color = "#ef5350";
        } else if (data.security_armed) {
            elAlarmStatus.innerText = "Sistem Naoruzan";
            elAlarmStatus.className = "status-safe";
            elAlarmStatus.style.backgroundColor = "#1976d2";
            elAlarmText.innerText = "Sistem je obezbedjen.";
            elAlarmText.style.color = "#90caf9";
        } else {
            elAlarmStatus.innerText = "Sistem Deaktiviran";
            elAlarmStatus.className = "status-safe";
            elAlarmStatus.style.backgroundColor = "#424242";
            elAlarmText.innerText = "Bezbednosne funkcije su iskljucene.";
            elAlarmText.style.color = "#ffffff";
        }

        // Azuriranje stoperice (konverzija iz sekundi u MM:SS formulu)
        const mins = Math.floor(data.stopwatch_time / 60);
        const secs = data.stopwatch_time % 60;
        elTimerVal.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

    } catch (error) {
        console.error('Greska pri dohvatanju statusa:', error);
    }
}

// Komanda: Deaktivacija alarma
async function deactivateAlarm() {
    const pin = document.getElementById('pin-input').value;
    if (!pin) {
        elSecurityMsg.innerText = "Molimo unesite PIN.";
        elSecurityMsg.style.color = "red";
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/alarm/deactivate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin: pin })
        });
        
        const result = await response.json();
        if (result.status === "success") {
            elSecurityMsg.innerText = "Uspesna deaktivacija.";
            elSecurityMsg.style.color = "green";
            document.getElementById('pin-input').value = ""; // Ocisti polje
            fetchStatus(); // Osvezi odmah
            
            // NOVO: Obrisi poruku o uspehu nakon 3 sekunde
            setTimeout(() => {
                if (elSecurityMsg.innerText === "Uspesna deaktivacija.") {
                    elSecurityMsg.innerText = "";
                }
            }, 3000);

        } else {
            elSecurityMsg.innerText = "Pogresan PIN.";
            elSecurityMsg.style.color = "red";
            
            // NOVO: Obrisi i poruku za gresku nakon 3 sekunde
            setTimeout(() => {
                if (elSecurityMsg.innerText === "Pogresan PIN.") {
                    elSecurityMsg.innerText = "";
                }
            }, 3000);
        }
    } catch (error) {
        console.error('Greska pri slanju PIN-a:', error);
    }
}

// Komanda: Promena RGB boje
async function setRGB(color) {
    try {
        await fetch(`${API_BASE_URL}/api/rgb`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ color: color })
        });
    } catch (error) {
        console.error('Greska pri promeni boje:', error);
    }
}

// Komanda: Postavljanje vremena stoperice
async function setStopwatchTime() {
    const timeVal = document.getElementById('timer-input').value;
    if (!timeVal || timeVal <= 0) return;

    try {
        await fetch(`${API_BASE_URL}/api/stopwatch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: "set_time", time: timeVal })
        });
        document.getElementById('timer-input').value = "";
        fetchStatus();
    } catch (error) {
        console.error('Greska pri postavljanju vremena:', error);
    }
}

// Komanda: Postavljanje N sekundi za dodavanje na dugme
async function setStopwatchN() {
    const nVal = document.getElementById('n-input').value;
    if (!nVal || nVal <= 0) return;

    try {
        await fetch(`${API_BASE_URL}/api/stopwatch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: "set_n", n: nVal })
        });
        document.getElementById('n-input').value = "";
        alert(`Broj sekundi po pritisku (N) je azuriran na: ${nVal}`);
    } catch (error) {
        console.error('Greska pri postavljanju N vrednosti:', error);
    }
}

// Pokreni osvezavanje stanja na svake 2 sekunde
setInterval(fetchStatus, 2000);
fetchStatus(); // Prvo inicijalno povlacenje podataka