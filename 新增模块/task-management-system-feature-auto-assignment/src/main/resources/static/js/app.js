/**
 * 任务管理系统前端演示页（原生 JS）。
 *
 * 前后端分离：本页只通过 /api/tasks 的 REST 接口与后端交互，
 * 后续可以整体替换成 Vue / React 工程，后端接口契约不变。
 */
const API_BASE = '/api/tasks';

const STATUS_OPTIONS = [
    ['TODO', '待办'],
    ['IN_PROGRESS', '进行中'],
    ['DONE', '已完成'],
];

const state = {
    page: 1,
    size: 10,
    total: 0,
    keyword: '',
    status: '',
    priority: '',
    tasks: [],
};

const $ = (id) => document.getElementById(id);

document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadTasks();
});

function bindEvents() {
    $('btn-search').addEventListener('click', () => {
        state.page = 1;
        state.keyword = $('filter-keyword').value.trim();
        state.status = $('filter-status').value;
        state.priority = $('filter-priority').value;
        loadTasks();
    });

    $('filter-keyword').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            $('btn-search').click();
        }
    });

    $('btn-reset').addEventListener('click', () => {
        $('filter-keyword').value = '';
        $('filter-status').value = '';
        $('filter-priority').value = '';
        Object.assign(state, { keyword: '', status: '', priority: '', page: 1 });
        loadTasks();
    });

    $('btn-create').addEventListener('click', () => openDialog());
    $('btn-cancel').addEventListener('click', () => $('task-dialog').close());
    $('task-form').addEventListener('submit', (event) => {
        event.preventDefault();
        saveTask();
    });

    $('btn-prev').addEventListener('click', () => {
        if (state.page > 1) {
            state.page -= 1;
            loadTasks();
        }
    });

    $('btn-next').addEventListener('click', () => {
        const pages = Math.ceil(state.total / state.size) || 0;
        if (state.page < pages) {
            state.page += 1;
            loadTasks();
        }
    });

    // 表格内的编辑 / 删除按钮
    $('task-tbody').addEventListener('click', async (event) => {
        const button = event.target.closest('button[data-action]');
        if (!button) {
            return;
        }
        const id = Number(button.dataset.id);
        if (button.dataset.action === 'edit') {
            const task = state.tasks.find((item) => item.id === id);
            if (task) {
                openDialog(task);
            }
        } else if (button.dataset.action === 'delete') {
            if (window.confirm(`确定删除任务「${button.dataset.title}」吗？`)) {
                await removeTask(id);
            }
        }
    });

    // 表格内的状态下拉框：直接调 PATCH 接口
    $('task-tbody').addEventListener('change', async (event) => {
        const select = event.target.closest('select[data-action="status"]');
        if (!select) {
            return;
        }
        try {
            await request(`/${select.dataset.id}/status?status=${encodeURIComponent(select.value)}`, {
                method: 'PATCH',
            });
            showToast('状态已更新');
        } catch (error) {
            showToast(error.message, true);
        }
        loadTasks();
    });
}

/**
 * 统一请求封装：解析 { code, message, data }，code !== 0 视为失败。
 */
async function request(path, options = {}) {
    const response = await fetch(API_BASE + path, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });

    let payload = null;
    try {
        payload = await response.json();
    } catch (ignored) {
        // 没有响应体时忽略
    }

    if (!response.ok || (payload && payload.code !== 0)) {
        throw new Error((payload && payload.message) || `请求失败（HTTP ${response.status}）`);
    }
    return payload ? payload.data : null;
}

async function loadTasks() {
    const params = new URLSearchParams({ page: state.page, size: state.size });
    if (state.keyword) {
        params.append('keyword', state.keyword);
    }
    if (state.status) {
        params.append('status', state.status);
    }
    if (state.priority) {
        params.append('priority', state.priority);
    }

    try {
        const data = await request(`?${params.toString()}`);
        state.tasks = (data && data.records) || [];
        state.total = (data && data.total) || 0;
        renderTable();
        renderPager();
    } catch (error) {
        showToast(error.message, true);
    }
}

function renderTable() {
    const tbody = $('task-tbody');
    tbody.innerHTML = '';
    $('empty-tip').hidden = state.tasks.length > 0;

    state.tasks.forEach((task) => {
        const row = document.createElement('tr');
        const statusOptions = STATUS_OPTIONS
            .map(([value, label]) => `<option value="${value}" ${value === task.status ? 'selected' : ''}>${label}</option>`)
            .join('');

        row.innerHTML = `
            <td>${task.id}</td>
            <td class="title-cell">${escapeHtml(task.title)}</td>
            <td class="desc-cell" title="${escapeHtml(task.description || '')}">${escapeHtml(task.description || '-')}</td>
            <td>
                <select class="status-select" data-action="status" data-id="${task.id}" data-status="${task.status}">
                    ${statusOptions}
                </select>
            </td>
            <td><span class="priority priority-${task.priority}">${escapeHtml(task.priorityLabel || task.priority)}</span></td>
            <td>${formatDateTime(task.dueDate)}</td>
            <td class="actions">
                <button type="button" class="btn btn-sm" data-action="edit" data-id="${task.id}">编辑</button>
                <button type="button" class="btn btn-sm btn-danger" data-action="delete"
                        data-id="${task.id}" data-title="${escapeHtml(task.title)}">删除</button>
            </td>`;
        tbody.appendChild(row);
    });
}

function renderPager() {
    const pages = Math.ceil(state.total / state.size) || 0;
    const current = pages === 0 ? 0 : state.page;
    $('page-info').textContent = `共 ${state.total} 条，第 ${current} / ${pages} 页`;
    $('btn-prev').disabled = state.page <= 1;
    $('btn-next').disabled = state.page >= pages;
}

function openDialog(task) {
    $('form-error').hidden = true;
    $('dialog-title').textContent = task ? '编辑任务' : '新建任务';
    $('task-id').value = task ? task.id : '';
    $('task-title').value = task ? task.title : '';
    $('task-description').value = task && task.description ? task.description : '';
    $('task-status').value = task ? task.status : 'TODO';
    $('task-priority').value = task ? task.priority : 'MEDIUM';
    $('task-due-date').value = task && task.dueDate ? task.dueDate.slice(0, 16) : '';
    $('task-dialog').showModal();
    $('task-title').focus();
}

async function saveTask() {
    const id = $('task-id').value;
    const dueDate = $('task-due-date').value;
    const payload = {
        title: $('task-title').value.trim(),
        description: $('task-description').value.trim() || null,
        priority: $('task-priority').value,
        dueDate: dueDate ? `${dueDate}:00` : null,
    };

    if (!payload.title) {
        $('form-error').textContent = '任务标题不能为空';
        $('form-error').hidden = false;
        return;
    }

    try {
        if (id) {
            payload.status = $('task-status').value;
            await request(`/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
            showToast('任务已更新');
        } else {
            await request('', { method: 'POST', body: JSON.stringify(payload) });
            showToast('任务已创建');
            state.page = 1;
        }
        $('task-dialog').close();
        loadTasks();
    } catch (error) {
        $('form-error').textContent = error.message;
        $('form-error').hidden = false;
    }
}

async function removeTask(id) {
    try {
        await request(`/${id}`, { method: 'DELETE' });
        showToast('任务已删除');
        if (state.tasks.length === 1 && state.page > 1) {
            state.page -= 1;
        }
        loadTasks();
    } catch (error) {
        showToast(error.message, true);
    }
}

function formatDateTime(value) {
    if (!value) {
        return '-';
    }
    return String(value).replace('T', ' ').slice(0, 16);
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    }[ch]));
}

let toastTimer = null;

function showToast(message, isError = false) {
    const toast = $('toast');
    toast.textContent = message;
    toast.classList.toggle('toast-error', isError);
    toast.hidden = false;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
        toast.hidden = true;
    }, 2600);
}
