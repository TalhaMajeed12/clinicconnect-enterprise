(() => {
    'use strict';

    const toggle = document.getElementById('clinical-chat-toggle');
    const panel = document.getElementById('clinical-chat-panel');
    const close = document.getElementById('clinical-chat-close');
    const form = document.getElementById('clinical-chat-form');
    const input = document.getElementById('clinical-chat-input');
    const messages = document.getElementById('clinical-chat-messages');
    if (!toggle || !panel || !form || !input || !messages) return;

    const addMessage = (text, kind, emergency = false) => {
        const item = document.createElement('div');
        item.className = `clinical-chat-message ${kind}${emergency ? ' emergency' : ''}`;
        item.textContent = text;
        messages.appendChild(item);
        messages.scrollTop = messages.scrollHeight;
    };

    const openPanel = () => {
        panel.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
        input.focus();
        if (!messages.children.length) {
            addMessage(panel.dataset.welcome, 'assistant');
        }
    };

    const closePanel = () => {
        panel.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
    };

    const sendMessage = async (question) => {
        const message = question.trim();
        if (!message) return;
        addMessage(message, 'user');
        input.value = '';
        input.disabled = true;

        try {
            const response = await fetch('/chatbot/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify({message}),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Request failed');
            addMessage(`${data.message}\n\n${data.disclaimer}`, 'assistant', data.emergency);
            if (data.action === 'guided_booking' && bookingToggle) openGuidedBooking();
        } catch (error) {
            addMessage(panel.dataset.error, 'assistant', true);
        } finally {
            input.disabled = false;
            input.focus();
        }
    };

    toggle.addEventListener('click', openPanel);
    close.addEventListener('click', closePanel);
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        sendMessage(input.value);
    });
    document.querySelectorAll('[data-chat-question]').forEach((button) => {
        button.addEventListener('click', () => sendMessage(button.dataset.chatQuestion));
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !panel.hidden) closePanel();
    });

    const bookingToggle = document.getElementById('guided-booking-toggle');
    const bookingForm = document.getElementById('guided-booking-form');
    if (!bookingToggle) return;
    const bookingSection = document.getElementById('appointment-request');
    const openGuidedBooking = () => {
        if (!bookingForm || !bookingSection) {
            window.location.href = bookingToggle.dataset.bookingUrl;
            return;
        }
        closePanel();
        bookingSection.scrollIntoView({behavior: 'smooth', block: 'start'});
        window.setTimeout(() => bookingSection.focus({preventScroll: true}), 450);
    };
    bookingToggle.addEventListener('click', openGuidedBooking);
    if (!bookingForm) return;
    const specialty = document.getElementById('guided-specialty');
    const appointmentType = document.getElementById('guided-type');
    const date = document.getElementById('guided-date');
    const doctor = document.getElementById('guided-doctor');
    const slot = document.getElementById('guided-slot');
    const bookingStatus = document.getElementById('guided-booking-status');
    let doctors = [];
    const today = new Date();
    const localDate = value => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
    date.min = localDate(today);
    date.value = localDate(today);

    const resetSelect = (control, label, disabled = true) => {
        const option = new Option(label, '', true, true);
        option.disabled = true;
        control.replaceChildren(option);
        control.disabled = disabled;
    };

    const populateSlots = selectedDoctor => {
        resetSelect(
            slot,
            selectedDoctor ? 'Choose an available time' : 'Select a doctor to view times',
            !selectedDoctor
        );
        (selectedDoctor?.slots || []).forEach(item => slot.add(new Option(item.label, item.value)));
    };

    const loadDiscovery = async () => {
        bookingStatus.textContent = 'Checking clinician availability…';
        const query = new URLSearchParams({date: date.value});
        if (specialty.value) query.set('specialty', specialty.value);
        try {
            const response = await fetch(`/appointments/discovery?${query}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Unable to check availability');
            if (!specialty.options.length || specialty.options.length === 1) {
                data.specialties.forEach(value => specialty.add(new Option(value, value)));
            }
            doctors = data.doctors;
            resetSelect(doctor, doctors.length ? 'Choose a doctor' : 'No doctors available', !doctors.length);
            doctors.forEach(item => {
                const reviews = item.review_count
                    ? `${Number(item.rating).toFixed(1)}★ (${item.review_count} review${item.review_count === 1 ? '' : 's'})`
                    : 'New · no reviews yet';
                doctor.add(new Option(`Dr. ${item.name} — ${item.specialty} — ${reviews}`, item.id));
            });
            if (doctors.length) {
                doctor.value = String(doctors[0].id);
                populateSlots(doctors[0]);
            } else {
                populateSlots(null);
            }
            bookingStatus.textContent = doctors.length
                ? 'The best-rated available doctor is selected first. You can choose another doctor or time.'
                : 'No matching doctor is available from this date. Try another specialty or date.';
        } catch (error) { bookingStatus.textContent = error.message; }
    };

    specialty.addEventListener('change', loadDiscovery);
    date.addEventListener('change', loadDiscovery);
    doctor.addEventListener('change', () => {
        const selectedDoctor = doctors.find(item => String(item.id) === doctor.value);
        populateSlots(selectedDoctor);
    });
    bookingForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        bookingStatus.textContent = 'Sending your protected request…';
        try {
            const response = await fetch('/appointments/request', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
                body: JSON.stringify({
                    specialty: specialty.value, clinician_id: doctor.value,
                    appointment_type: appointmentType.value,
                    preferred_at: slot.value,
                    full_name: document.getElementById('guided-name').value,
                    date_of_birth: document.getElementById('guided-dob').value,
                    phone: document.getElementById('guided-phone').value,
                    email: document.getElementById('guided-email').value,
                    reason: document.getElementById('guided-reason').value,
                }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Unable to submit request');
            bookingStatus.textContent = `${data.message} Clinic phone: ${data.clinic_phone}`;
            addMessage(`${data.message}\nClinic phone: ${data.clinic_phone}`, 'assistant');
            bookingForm.querySelectorAll('input, select, textarea, button').forEach(control => control.disabled = true);
        } catch (error) { bookingStatus.textContent = error.message; }
    });
    loadDiscovery();
    if (window.location.hash === '#appointment-request') {
        window.setTimeout(() => bookingSection.scrollIntoView({behavior: 'smooth'}), 150);
    }
})();
