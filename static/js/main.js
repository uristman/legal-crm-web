// Legal CRM Web - Основной JavaScript файл

// Глобальные переменные
let clientsDataTable, casesDataTable, servicesDataTable, paymentsDataTable, eventsDataTable;
let currentEditingId = null;

// Инициализация при загрузке страницы
$(document).ready(function() {
    console.log('🚀 Legal CRM Web инициализация...');
    
    // Инициализация компонентов
    initializeComponents();
    
    // Загрузка данных
    loadAllData();
    
    // Обновление статистики
    updateStatistics();
    
    // Инициализация поиска
    initializeSearch();
    
    console.log('✅ Legal CRM Web готов к работе!');
});

// Инициализация компонентов
function initializeComponents() {
    // Инициализация DateTime picker
    flatpickr("input[type='date']", {
        locale: "ru",
        dateFormat: "Y-m-d",
        allowInput: true
    });
    
    flatpickr("input[type='time']", {
        locale: "ru",
        enableTime: true,
        noCalendar: true,
        dateFormat: "H:i",
        allowInput: true
    });
    
    // Инициализация Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Загрузка всех данных
function loadAllData() {
    loadClients();
    loadCases();
    loadServices();
    loadPayments();
    loadEvents();
}

// Загрузка клиентов
function loadClients() {
    $.ajax({
        url: '/api/clients',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                displayClients(response.data);
            } else {
                showNotification('Ошибка загрузки клиентов: ' + response.error, 'error');
            }
        },
        error: function(xhr, status, error) {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// Отображение клиентов
function displayClients(clients) {
    if (clientsDataTable) {
        clientsDataTable.destroy();
    }
    
    const tbody = $('#clients-table tbody');
    tbody.empty();
    
    clients.forEach(function(client) {
        const row = `
            <tr>
                <td>${client.id}</td>
                <td>${client.full_name}</td>
                <td>${client.phone || '-'}</td>
                <td>${client.email || '-'}</td>
                <td><span class="badge bg-${client.status === 'Активный' ? 'success' : 'secondary'}">${client.status}</span></td>
                <td>${formatDate(client.created_date)}</td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" onclick="editClient(${client.id})" title="Редактировать">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteClient(${client.id})" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
    
    // Инициализация DataTable
    clientsDataTable = $('#clients-table').DataTable({
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/Russian.json'
        },
        pageLength: 25,
        responsive: true
    });
}

// Загрузка дел
function loadCases() {
    $.ajax({
        url: '/api/cases',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                displayCases(response.data);
            } else {
                showNotification('Ошибка загрузки дел: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// Отображение дел
function displayCases(cases) {
    if (casesDataTable) {
        casesDataTable.destroy();
    }
    
    const tbody = $('#cases-table tbody');
    tbody.empty();
    
    cases.forEach(function(case_item) {
        const row = `
            <tr>
                <td>${case_item.case_number}</td>
                <td>${case_item.client_name}</td>
                <td>${case_item.court_name || '-'}</td>
                <td>${case_item.case_type || '-'}</td>
                <td>${case_item.case_stage || '-'}</td>
                <td>${formatDate(case_item.start_date)}</td>
                <td><span class="badge bg-${case_item.status === 'Активное' ? 'success' : 'secondary'}">${case_item.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" onclick="editCase(${case_item.id})" title="Редактировать">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteCase(${case_item.id})" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
    
    casesDataTable = $('#cases-table').DataTable({
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/Russian.json'
        },
        pageLength: 25,
        responsive: true
    });
}

// Загрузка услуг
function loadServices() {
    $.ajax({
        url: '/api/services',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                displayServices(response.data);
            } else {
                showNotification('Ошибка загрузки услуг: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// Отображение услуг
function displayServices(services) {
    if (servicesDataTable) {
        servicesDataTable.destroy();
    }
    
    const tbody = $('#services-table tbody');
    tbody.empty();
    
    services.forEach(function(service) {
        const row = `
            <tr>
                <td>${service.service_type}</td>
                <td>${service.client_name}</td>
                <td>${service.case_number || '-'}</td>
                <td>${formatDate(service.service_date)}</td>
                <td>${service.hours || 0}</td>
                <td>${formatCurrency(service.cost)}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteService(${service.id})" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
    
    servicesDataTable = $('#services-table').DataTable({
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/Russian.json'
        },
        pageLength: 25,
        responsive: true
    });
}

// Загрузка платежей
function loadPayments() {
    $.ajax({
        url: '/api/payments',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                displayPayments(response.data);
            } else {
                showNotification('Ошибка загрузки платежей: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// Отображение платежей
function displayPayments(payments) {
    if (paymentsDataTable) {
        paymentsDataTable.destroy();
    }
    
    const tbody = $('#payments-table tbody');
    tbody.empty();
    
    payments.forEach(function(payment) {
        const row = `
            <tr>
                <td>${payment.client_name}</td>
                <td>${payment.case_number || '-'}</td>
                <td><strong>${formatCurrency(payment.amount)}</strong></td>
                <td>${payment.payment_type || '-'}</td>
                <td>${formatDate(payment.payment_date)}</td>
                <td>${payment.payment_method || '-'}</td>
                <td><span class="badge bg-${payment.status === 'Оплачено' ? 'success' : 'warning'}">${payment.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deletePayment(${payment.id})" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
    
    paymentsDataTable = $('#payments-table').DataTable({
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/Russian.json'
        },
        pageLength: 25,
        responsive: true
    });
}

// Загрузка событий
function loadEvents() {
    $.ajax({
        url: '/api/events',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                displayEvents(response.data);
            } else {
                showNotification('Ошибка загрузки событий: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// Отображение событий
function displayEvents(events) {
    if (eventsDataTable) {
        eventsDataTable.destroy();
    }
    
    const tbody = $('#events-table tbody');
    tbody.empty();
    
    events.forEach(function(event) {
        const row = `
            <tr>
                <td>${event.title}</td>
                <td>${event.event_type}</td>
                <td>${formatDate(event.event_date)}</td>
                <td>${event.event_time || '-'}</td>
                <td>${event.client_name || '-'}</td>
                <td>${event.case_number || '-'}</td>
                <td><span class="badge bg-${getEventStatusColor(event.status)}">${event.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="deleteEvent(${event.id})" title="Удалить">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });
    
    eventsDataTable = $('#events-table').DataTable({
        language: {
            url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/Russian.json'
        },
        pageLength: 25,
        responsive: true
    });
}

// Обновление статистики
function updateStatistics() {
    $.ajax({
        url: '/api/statistics',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const stats = response.data;
                
                $('#stats-clients').text(stats.active_clients);
                $('#stats-cases').text(stats.active_cases);
                $('#stats-events').text(stats.today_events);
                $('#stats-income').text(formatCurrency(stats.month_payments));
                
                $('#total-clients').text(stats.active_clients);
                $('#total-cases').text(stats.active_cases);
                $('#total-income').text(formatCurrency(stats.month_payments));
            }
        },
        error: function() {
            console.error('Ошибка загрузки статистики');
        }
    });
}

// ==================== ФУНКЦИИ КЛИЕНТОВ ====================

// Открытие модального окна клиента
function openClientModal(clientId = null) {
    currentEditingId = clientId;
    
    if (clientId) {
        $('#clientModalTitle').html('<i class="fas fa-user-edit me-2"></i>Редактировать клиента');
        
        // Загружаем данные клиента
        $.ajax({
            url: `/api/clients/${clientId}`,
            method: 'GET',
            success: function(response) {
                if (response.success) {
                    const client = response.data;
                    $('#clientId').val(client.id);
                    $('#clientFullName').val(client.full_name);
                    $('#clientPhone').val(client.phone || '');
                    $('#clientEmail').val(client.email || '');
                    $('#clientAddress').val(client.address || '');
                    $('#clientPassport').val(client.passport_data || '');
                    $('#clientInn').val(client.inn || '');
                    $('#clientStatus').val(client.status);
                    $('#clientNotes').val(client.notes || '');
                }
            }
        });
    } else {
        $('#clientModalTitle').html('<i class="fas fa-user-plus me-2"></i>Добавить клиента');
        $('#clientForm')[0].reset();
        $('#clientId').val('');
    }
    
    $('#clientModal').modal('show');
}

// Сохранение клиента
function saveClient() {
    const formData = {
        full_name: $('#clientFullName').val().trim(),
        phone: $('#clientPhone').val().trim(),
        email: $('#clientEmail').val().trim(),
        address: $('#clientAddress').val().trim(),
        passport_data: $('#clientPassport').val().trim(),
        inn: $('#clientInn').val().trim(),
        status: $('#clientStatus').val(),
        notes: $('#clientNotes').val().trim()
    };
    
    if (!formData.full_name) {
        showNotification('Пожалуйста, введите ФИО клиента', 'error');
        return;
    }
    
    const method = currentEditingId ? 'PUT' : 'POST';
    const url = currentEditingId ? `/api/clients/${currentEditingId}` : '/api/clients';
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                showNotification(currentEditingId ? 'Клиент обновлен!' : 'Клиент добавлен!', 'success');
                $('#clientModal').modal('hide');
                loadClients();
                updateStatistics();
            } else {
                showNotification('Ошибка: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// Редактирование клиента
function editClient(clientId) {
    openClientModal(clientId);
}

// Удаление клиента
function deleteClient(clientId) {
    if (confirm('Вы уверены, что хотите удалить этого клиента? Все связанные данные также будут удалены.')) {
        $.ajax({
            url: `/api/clients/${clientId}`,
            method: 'DELETE',
            success: function(response) {
                if (response.success) {
                    showNotification('Клиент удален!', 'success');
                    loadClients();
                    updateStatistics();
                } else {
                    showNotification('Ошибка: ' + response.error, 'error');
                }
            },
            error: function() {
                showNotification('Ошибка соединения с сервером', 'error');
            }
        });
    }
}

// ==================== ФУНКЦИИ ДЕЛ ====================

// Открытие модального окна дела
function openCaseModal(caseId = null) {
    currentEditingId = caseId;
    
    if (caseId) {
        $('#caseModalTitle').html('<i class="fas fa-gavel me-2"></i>Редактировать дело');
        // Здесь нужно загрузить данные дела и заполнить форму
    } else {
        $('#caseModalTitle').html('<i class="fas fa-plus me-2"></i>Добавить дело');
        $('#caseForm')[0].reset();
        $('#caseId').val('');
    }
    
    // Загружаем список клиентов для выпадающего списка
    loadClientsForSelect('#caseClientId');
    
    $('#caseModal').modal('show');
}

// Сохранение дела
function saveCase() {
    const formData = {
        client_id: parseInt($('#caseClientId').val()),
        case_number: $('#caseNumber').val().trim(),
        court_name: $('#caseCourt').val().trim(),
        case_type: $('#caseType').val().trim(),
        plaintiff: $('#casePlaintiff').val().trim(),
        defendant: $('#caseDefendant').val().trim(),
        claim_amount: parseFloat($('#caseClaimAmount').val()) || 0,
        case_stage: $('#caseStage').val().trim(),
        notes: $('#caseNotes').val().trim()
    };
    
    if (!formData.client_id || !formData.case_number) {
        showNotification('Пожалуйста, заполните обязательные поля', 'error');
        return;
    }
    
    const method = currentEditingId ? 'PUT' : 'POST';
    const url = currentEditingId ? `/api/cases/${currentEditingId}` : '/api/cases';
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                showNotification(currentEditingId ? 'Дело обновлено!' : 'Дело добавлено!', 'success');
                $('#caseModal').modal('hide');
                loadCases();
                updateStatistics();
            } else {
                showNotification('Ошибка: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// ==================== ФУНКЦИИ УСЛУГ ====================

// Открытие модального окна услуги
function openServiceModal(serviceId = null) {
    currentEditingId = serviceId;
    
    if (serviceId) {
        $('#serviceModalTitle').html('<i class="fas fa-briefcase me-2"></i>Редактировать услугу');
    } else {
        $('#serviceModalTitle').html('<i class="fas fa-plus me-2"></i>Добавить услугу');
        $('#serviceForm')[0].reset();
        $('#serviceId').val('');
    }
    
    // Загружаем список клиентов для выпадающего списка
    loadClientsForSelect('#serviceClientId');
    
    // Устанавливаем текущую дату
    if (!serviceId) {
        $('#serviceDate').val(new Date().toISOString().split('T')[0]);
    }
    
    $('#serviceModal').modal('show');
}

// Сохранение услуги
function saveService() {
    const formData = {
        client_id: parseInt($('#serviceClientId').val()),
        service_type: $('#serviceType').val().trim(),
        description: $('#serviceDescription').val().trim(),
        service_date: $('#serviceDate').val(),
        hours: parseFloat($('#serviceHours').val()) || 0,
        cost: parseFloat($('#serviceCost').val()) || 0,
        notes: $('#serviceNotes').val().trim()
    };
    
    if (!formData.client_id || !formData.service_type) {
        showNotification('Пожалуйста, заполните обязательные поля', 'error');
        return;
    }
    
    const method = currentEditingId ? 'PUT' : 'POST';
    const url = currentEditingId ? `/api/services/${currentEditingId}` : '/api/services';
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                showNotification(currentEditingId ? 'Услуга обновлена!' : 'Услуга добавлена!', 'success');
                $('#serviceModal').modal('hide');
                loadServices();
                updateStatistics();
            } else {
                showNotification('Ошибка: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// ==================== ФУНКЦИИ ПЛАТЕЖЕЙ ====================

// Открытие модального окна платежа
function openPaymentModal(paymentId = null) {
    currentEditingId = paymentId;
    
    if (paymentId) {
        $('#paymentModalTitle').html('<i class="fas fa-money-bill me-2"></i>Редактировать платеж');
    } else {
        $('#paymentModalTitle').html('<i class="fas fa-plus me-2"></i>Добавить платеж');
        $('#paymentForm')[0].reset();
        $('#paymentId').val('');
    }
    
    // Загружаем список клиентов для выпадающего списка
    loadClientsForSelect('#paymentClientId');
    
    // Устанавливаем текущую дату
    if (!paymentId) {
        $('#paymentDate').val(new Date().toISOString().split('T')[0]);
    }
    
    $('#paymentModal').modal('show');
}

// Сохранение платежа
function savePayment() {
    const formData = {
        client_id: parseInt($('#paymentClientId').val()),
        amount: parseFloat($('#paymentAmount').val()),
        payment_type: $('#paymentType').val(),
        payment_date: $('#paymentDate').val(),
        payment_method: $('#paymentMethod').val(),
        invoice_number: $('#paymentInvoice').val().trim(),
        notes: $('#paymentNotes').val().trim()
    };
    
    if (!formData.client_id || !formData.amount) {
        showNotification('Пожалуйста, заполните обязательные поля', 'error');
        return;
    }
    
    const method = currentEditingId ? 'PUT' : 'POST';
    const url = currentEditingId ? `/api/payments/${currentEditingId}` : '/api/payments';
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                showNotification(currentEditingId ? 'Платеж обновлен!' : 'Платеж добавлен!', 'success');
                $('#paymentModal').modal('hide');
                loadPayments();
                updateStatistics();
            } else {
                showNotification('Ошибка: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// ==================== ФУНКЦИИ СОБЫТИЙ ====================

// Открытие модального окна события
function openEventModal(eventId = null) {
    currentEditingId = eventId;
    
    if (eventId) {
        $('#eventModalTitle').html('<i class="fas fa-calendar me-2"></i>Редактировать событие');
    } else {
        $('#eventModalTitle').html('<i class="fas fa-plus me-2"></i>Добавить событие');
        $('#eventForm')[0].reset();
        $('#eventId').val('');
    }
    
    // Устанавливаем завтрашнюю дату по умолчанию
    if (!eventId) {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        $('#eventDate').val(tomorrow.toISOString().split('T')[0]);
    }
    
    $('#eventModal').modal('show');
}

// Сохранение события
function saveEvent() {
    const formData = {
        title: $('#eventTitle').val().trim(),
        event_type: $('#eventType').val(),
        event_date: $('#eventDate').val(),
        event_time: $('#eventTime').val(),
        location: $('#eventLocation').val().trim(),
        description: $('#eventDescription').val().trim()
    };
    
    if (!formData.title || !formData.event_type || !formData.event_date) {
        showNotification('Пожалуйста, заполните обязательные поля', 'error');
        return;
    }
    
    const method = currentEditingId ? 'PUT' : 'POST';
    const url = currentEditingId ? `/api/events/${currentEditingId}` : '/api/events';
    
    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                showNotification(currentEditingId ? 'Событие обновлено!' : 'Событие добавлено!', 'success');
                $('#eventModal').modal('hide');
                loadEvents();
                updateStatistics();
            } else {
                showNotification('Ошибка: ' + response.error, 'error');
            }
        },
        error: function() {
            showNotification('Ошибка соединения с сервером', 'error');
        }
    });
}

// ==================== УТИЛИТЫ ====================

// Загрузка клиентов в выпадающий список
function loadClientsForSelect(selectId) {
    $.ajax({
        url: '/api/clients',
        method: 'GET',
        success: function(response) {
            if (response.success) {
                const select = $(selectId);
                select.empty();
                select.append('<option value="">Выберите клиента</option>');
                
                response.data.forEach(function(client) {
                    select.append(`<option value="${client.id}">${client.full_name}</option>`);
                });
            }
        }
    });
}

// Инициализация поиска
function initializeSearch() {
    $('#clients-search').on('keyup', function() {
        if (clientsDataTable) {
            clientsDataTable.search($(this).val()).draw();
        }
    });
}

// Показ уведомлений
function showNotification(message, type = 'info') {
    const toast = $('#notificationToast');
    const toastMessage = $('#toastMessage');
    
    // Устанавливаем сообщение
    toastMessage.text(message);
    
    // Устанавливаем цвет в зависимости от типа
    const header = toast.find('.toast-header');
    header.removeClass('bg-success bg-warning bg-danger bg-info');
    
    switch(type) {
        case 'success':
            header.addClass('bg-success');
            break;
        case 'error':
            header.addClass('bg-danger');
            break;
        case 'warning':
            header.addClass('bg-warning');
            break;
        default:
            header.addClass('bg-info');
    }
    
    // Показываем toast
    const bsToast = new bootstrap.Toast(toast[0]);
    bsToast.show();
}

// Форматирование даты
function formatDate(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    
    return date.toLocaleDateString('ru-RU');
}

// Форматирование валюты
function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '0 ₽';
    
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    }).format(amount);
}

// Получение цвета для статуса события
function getEventStatusColor(status) {
    switch(status) {
        case 'Запланировано':
            return 'primary';
        case 'Завершено':
            return 'success';
        case 'Отменено':
            return 'danger';
        default:
            return 'secondary';
    }
}

// ==================== DELETE FUNCTIONS ====================

function deleteCase(caseId) {
    if (confirm('Вы уверены, что хотите удалить это дело?')) {
        $.ajax({
            url: `/api/cases/${caseId}`,
            method: 'DELETE',
            success: function(response) {
                if (response.success) {
                    showNotification('Дело удалено!', 'success');
                    loadCases();
                    updateStatistics();
                } else {
                    showNotification('Ошибка: ' + response.error, 'error');
                }
            },
            error: function() {
                showNotification('Ошибка соединения с сервером', 'error');
            }
        });
    }
}

function deleteService(serviceId) {
    if (confirm('Вы уверены, что хотите удалить эту услугу?')) {
        $.ajax({
            url: `/api/services/${serviceId}`,
            method: 'DELETE',
            success: function(response) {
                if (response.success) {
                    showNotification('Услуга удалена!', 'success');
                    loadServices();
                    updateStatistics();
                } else {
                    showNotification('Ошибка: ' + response.error, 'error');
                }
            },
            error: function() {
                showNotification('Ошибка соединения с сервером', 'error');
            }
        });
    }
}

function deletePayment(paymentId) {
    if (confirm('Вы уверены, что хотите удалить этот платеж?')) {
        $.ajax({
            url: `/api/payments/${paymentId}`,
            method: 'DELETE',
            success: function(response) {
                if (response.success) {
                    showNotification('Платеж удален!', 'success');
                    loadPayments();
                    updateStatistics();
                } else {
                    showNotification('Ошибка: ' + response.error, 'error');
                }
            },
            error: function() {
                showNotification('Ошибка соединения с сервером', 'error');
            }
        });
    }
}

function deleteEvent(eventId) {
    if (confirm('Вы уверены, что хотите удалить это событие?')) {
        $.ajax({
            url: `/api/events/${eventId}`,
            method: 'DELETE',
            success: function(response) {
                if (response.success) {
                    showNotification('Событие удалено!', 'success');
                    loadEvents();
                    updateStatistics();
                } else {
                    showNotification('Ошибка: ' + response.error, 'error');
                }
            },
            error: function() {
                showNotification('Ошибка соединения с сервером', 'error');
            }
        });
    }
}