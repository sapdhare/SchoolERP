/* =========================================
   SIDEBAR TOGGLE
========================================= */

function toggleSidebar() {

    const sidebar =
        document.getElementById("sidebar");

    const overlay =
        document.getElementById("sidebarOverlay");

    sidebar.classList.toggle("active");

    overlay.classList.toggle("active");
}


/* =========================================
   CLOSE SIDEBAR
========================================= */

function closeSidebar() {

    document.getElementById(
        "sidebar"
    ).classList.remove("active");

    document.getElementById(
        "sidebarOverlay"
    ).classList.remove("active");
}


/* =========================================
   AUTO CLOSE MOBILE SIDEBAR
========================================= */

document.querySelectorAll(".menu-link")
.forEach(link => {

    link.addEventListener("click", () => {

        if (window.innerWidth <= 768) {

            closeSidebar();
        }
    });

});


/* =========================================
   CLOSE SIDEBAR ON RESIZE
========================================= */

window.addEventListener("resize", () => {

    if (window.innerWidth > 768) {

        closeSidebar();
    }
});


/* =========================================
   FUTURE NAVIGATION
========================================= */

function goTo(section) {

    console.log(
        "Navigate to:",
        section
    );
}


/* =========================================
   CHART JS
========================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const ctx =
            document.getElementById(
                "overviewChart"
            );

        if (
            ctx &&
            typeof chartData !== "undefined"
        ) {

            new Chart(ctx, {

                type: "line",

                data: {

                    labels:
                        chartData.labels,

                    datasets: [{

                        label:
                            "Students Growth",

                        data:
                            chartData.students,

                        borderColor:
                            "#0EA5A4",

                        backgroundColor:
                            "rgba(14,165,164,0.1)",

                        fill: true,

                        tension: 0.4,

                        pointRadius: 4,

                        pointBackgroundColor:
                            "#0EA5A4"
                    }]
                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {

                        legend: {
                            display: false
                        }
                    },

                    scales: {

                        x: {
                            grid: {
                                display: false
                            }
                        },

                        y: {
                            grid: {
                                color:
                                "rgba(0,0,0,0.05)"
                            }
                        }
                    },

                    animation: {

                        duration: 1500,

                        easing:
                            "easeInOutQuart"
                    }
                }
            });
        }
    }
);