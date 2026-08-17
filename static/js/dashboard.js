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


/* =========================================================
   GLOBAL FLASH / TOAST SYSTEM
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const flashMessages =
        document.querySelectorAll(
            ".flash-message[data-auto-dismiss='true']"
        );


    /* =====================================================
       REMOVE FLASH
    ===================================================== */

    function removeFlash(message) {

        if (!message || message.classList.contains("flash-removing")) {
            return;
        }

        message.classList.add("flash-removing");

        setTimeout(function () {

            if (message && message.parentNode) {
                message.remove();
            }

            cleanupFlashWrapper();

        }, 300);
    }


    /* =====================================================
       REMOVE EMPTY WRAPPER
    ===================================================== */

    function cleanupFlashWrapper() {

        const wrapper =
            document.getElementById("globalFlashWrapper");

        if (!wrapper) {
            return;
        }

        if (!wrapper.querySelector(".flash-message")) {
            wrapper.remove();
        }

    }


    /* =====================================================
       CLOSE BUTTON
    ===================================================== */

    flashMessages.forEach(function (message) {

        const closeButton =
            message.querySelector(".flash-close");


        if (closeButton) {

            closeButton.addEventListener(
                "click",
                function () {

                    removeFlash(message);

                }
            );

        }


        /* =================================================
           AUTO DISMISS
        ================================================= */

        const AUTO_DISMISS_TIME = 5000;


        message._flashTimer =
            setTimeout(function () {

                removeFlash(message);

            }, AUTO_DISMISS_TIME);

    });


    /* =====================================================
       EVENT DELEGATION
       Also handles dynamically inserted flash messages
    ===================================================== */

    document.addEventListener(
        "click",
        function (event) {

            const closeButton =
                event.target.closest(".flash-close");


            if (!closeButton) {
                return;
            }


            const message =
                closeButton.closest(".flash-message");


            if (!message) {
                return;
            }


            if (message._flashTimer) {

                clearTimeout(
                    message._flashTimer
                );

            }


            removeFlash(message);

        }
    );


    /* =====================================================
       PAUSE AUTO DISMISS ON HOVER
    ===================================================== */

    flashMessages.forEach(function (message) {

        message.addEventListener(
            "mouseenter",
            function () {

                if (message._flashTimer) {

                    clearTimeout(
                        message._flashTimer
                    );

                }

                const progress =
                    message.querySelector(
                        ".flash-progress"
                    );

                if (progress) {

                    progress.style.animationPlayState =
                        "paused";

                }

            }
        );


        message.addEventListener(
            "mouseleave",
            function () {

                const progress =
                    message.querySelector(
                        ".flash-progress"
                    );

                if (progress) {

                    progress.style.animationPlayState =
                        "running";

                }


                message._flashTimer =
                    setTimeout(function () {

                        removeFlash(message);

                    }, 2000);

            }
        );

    });

});