// TOGGLE SIDEBAR
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("active");
}

// CLOSE SIDEBAR WHEN CLICK OUTSIDE (MOBILE UX 🔥)
document.addEventListener("click", function (e) {
    const sidebar = document.getElementById("sidebar");
    const toggle = document.querySelector(".menu-toggle");

    if (
        sidebar &&
        !sidebar.contains(e.target) &&
        !toggle.contains(e.target)
    ) {
        sidebar.classList.remove("active");
    }
});

// LOGOUT BUTTON
document.querySelector(".logout-btn").addEventListener("click", function () {
    window.location.href = "/login";
});

// STATS SECTION JS
function goTo(section) {
    console.log("Navigate to:", section);

    // future routes
    // window.location.href = "/" + section;
}

// ===== CHART (DYNAMIC) =====
document.addEventListener("DOMContentLoaded", function () {

    const ctx = document.getElementById('overviewChart');

    if (ctx && typeof chartData !== "undefined") {

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartData.labels,

                datasets: [{
                    label: 'Students Growth',

                    data: chartData.students,

                    borderColor: '#0EA5A4',
                    backgroundColor: 'rgba(14,165,164,0.1)',

                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#0EA5A4'
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: { display: false }
                },

                scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: 'rgba(0,0,0,0.05)' } }
                },

                animation: {
                    duration: 1500,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }
});