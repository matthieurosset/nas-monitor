const CHART_COLORS = [
    '#58a6ff', '#3fb950', '#d29922', '#f85149', '#bc8cff',
    '#79c0ff', '#56d364', '#e3b341', '#ff7b72', '#d2a8ff',
    '#39d353', '#db6d28', '#f778ba', '#a5d6ff', '#7ee787',
];

const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: {
            position: 'top',
            labels: {
                color: '#8b949e',
                boxWidth: 12,
                padding: 12,
                font: { size: 11 },
            },
        },
        tooltip: {
            backgroundColor: '#1c2128',
            titleColor: '#c9d1d9',
            bodyColor: '#8b949e',
            borderColor: '#30363d',
            borderWidth: 1,
            padding: 10,
            bodyFont: { size: 12 },
        },
    },
    scales: {
        x: {
            type: 'time',
            grid: {
                color: 'rgba(48, 54, 61, 0.5)',
                drawBorder: false,
            },
            ticks: { color: '#6e7681', font: { size: 10 } },
        },
        y: {
            grid: {
                color: 'rgba(48, 54, 61, 0.5)',
                drawBorder: false,
            },
            ticks: { color: '#6e7681', font: { size: 10 } },
            beginAtZero: true,
        },
    },
};

let cpuChart, memoryChart, networkChart;
let currentPeriod = '1h';
let currentContainer = '';

function initCharts() {
    const cpuCtx = document.getElementById('cpu-chart');
    const memCtx = document.getElementById('memory-chart');
    const netCtx = document.getElementById('network-chart');

    if (!cpuCtx) return;

    cpuChart = new Chart(cpuCtx, {
        type: 'line',
        data: { datasets: [] },
        options: {
            ...CHART_DEFAULTS,
            scales: {
                ...CHART_DEFAULTS.scales,
                y: { ...CHART_DEFAULTS.scales.y, max: 100 },
            },
        },
    });

    memoryChart = new Chart(memCtx, {
        type: 'line',
        data: { datasets: [] },
        options: {
            ...CHART_DEFAULTS,
            scales: {
                ...CHART_DEFAULTS.scales,
                y: { ...CHART_DEFAULTS.scales.y, max: 100 },
            },
        },
    });

    networkChart = new Chart(netCtx, {
        type: 'line',
        data: { datasets: [] },
        options: CHART_DEFAULTS,
    });

    loadContainerList();
    loadData();
}

function loadContainerList() {
    fetch('/history/containers')
        .then(r => r.json())
        .then(names => {
            const select = document.getElementById('container-select');
            if (!select) return;
            names.forEach(name => {
                const opt = document.createElement('option');
                opt.value = name;
                opt.textContent = name;
                select.appendChild(opt);
            });
        });
}

function loadData() {
    let url = `/history/data?period=${currentPeriod}`;
    if (currentContainer) {
        url += `&container=${encodeURIComponent(currentContainer)}`;
    }

    fetch(url)
        .then(r => r.json())
        .then(data => {
            updateCharts(data);
        });
}

function updateCharts(data) {
    const containers = Object.keys(data);

    const cpuDatasets = [];
    const memDatasets = [];
    const netDatasets = [];

    containers.forEach((name, i) => {
        const color = CHART_COLORS[i % CHART_COLORS.length];
        const d = data[name];
        const points = d.timestamps.map((t, j) => ({ x: new Date(t), y: d.cpu[j] }));
        const memPoints = d.timestamps.map((t, j) => ({ x: new Date(t), y: d.memory[j] }));
        const netPoints = d.timestamps.map((t, j) => ({
            x: new Date(t),
            y: Math.round(d.net_rx[j] / 1048576),
        }));

        const base = {
            label: name,
            borderColor: color,
            backgroundColor: color + '20',
            borderWidth: 1.5,
            pointRadius: 0,
            pointHitRadius: 8,
            tension: 0.3,
            fill: false,
        };

        cpuDatasets.push({ ...base, data: points });
        memDatasets.push({ ...base, data: memPoints });
        netDatasets.push({ ...base, data: netPoints });
    });

    cpuChart.data.datasets = cpuDatasets;
    memoryChart.data.datasets = memDatasets;
    networkChart.data.datasets = netDatasets;

    cpuChart.update();
    memoryChart.update();
    networkChart.update();
}

// Period selector
document.addEventListener('DOMContentLoaded', () => {
    initCharts();

    document.querySelectorAll('.period-selector .btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelector('.period-selector .btn.active')?.classList.remove('active');
            btn.classList.add('active');
            currentPeriod = btn.dataset.period;
            loadData();
        });
    });

    const select = document.getElementById('container-select');
    if (select) {
        select.addEventListener('change', () => {
            currentContainer = select.value;
            loadData();
        });
    }
});
