/* =========================================
   SIDEBAR TOGGLE
========================================= */

function toggleSidebar() {

    const sidebar =
        document.getElementById("sidebar");

    const overlay =
        document.getElementById("sidebarOverlay");

    const toggle =
        document.getElementById("mobileSidebarToggle");

    if (!sidebar || !overlay) {
        return;
    }

    const isOpen =
        sidebar.classList.toggle("active");

    overlay.classList.toggle(
        "active",
        isOpen
    );

    document.body.classList.toggle(
        "sidebar-open",
        isOpen
    );

    if (toggle) {

        toggle.setAttribute(
            "aria-expanded",
            String(isOpen)
        );

        toggle.setAttribute(
            "aria-label",
            isOpen
                ? "Close navigation"
                : "Open navigation"
        );

        toggle.innerHTML = isOpen
            ? '<i class="fa-solid fa-xmark"></i>'
            : '<i class="fa-solid fa-bars"></i>';
    }
}


/* =========================================
   CLOSE SIDEBAR
========================================= */

function closeSidebar() {

    const sidebar =
        document.getElementById("sidebar");

    const overlay =
        document.getElementById("sidebarOverlay");

    const toggle =
        document.getElementById("mobileSidebarToggle");

    if (sidebar) {
        sidebar.classList.remove("active");
    }

    if (overlay) {
        overlay.classList.remove("active");
    }

    document.body.classList.remove(
        "sidebar-open"
    );

    if (toggle) {

        toggle.setAttribute(
            "aria-expanded",
            "false"
        );

        toggle.setAttribute(
            "aria-label",
            "Open navigation"
        );

        toggle.innerHTML =
            '<i class="fa-solid fa-bars"></i>';
    }
}



/* =========================================
   MOBILE MENU LINK CLICK
========================================= */

document.addEventListener(
    "click",
    function (event) {

        const link =
            event.target.closest(
                ".menu-link"
            );

        if (!link) {
            return;
        }

        if (window.innerWidth <= 768) {

            closeSidebar();
        }
    }
);

/* =========================================
   ESCAPE KEY
========================================= */

document.addEventListener(
    "keydown",
    function (event) {

        if (event.key === "Escape") {

            closeSidebar();
        }
    }
);


/* =========================================
   RESIZE
========================================= */

let sidebarResizeTimer;

window.addEventListener(
    "resize",
    function () {

        clearTimeout(
            sidebarResizeTimer
        );

        sidebarResizeTimer =
            setTimeout(function () {

                if (
                    window.innerWidth > 768
                ) {

                    closeSidebar();
                }

            }, 100);
    }
);

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



/* =========================================================
   CLERK ERP HELP & GUIDE MODAL
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const helpModal =
        document.getElementById("erpHelpModal");

    const openHelpBtn =
        document.getElementById("openErpHelpBtn");

    const closeHelpBtn =
        document.getElementById("closeErpHelpBtn");

    const doneHelpBtn =
        document.getElementById("erpHelpDoneBtn");


    /* -----------------------------------------------------
       OPEN
    ----------------------------------------------------- */

    function openErpHelp() {

        if (!helpModal) {
            return;
        }

        helpModal.classList.add("open");

        helpModal.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.classList.add(
            "erp-help-open"
        );
    }


    /* -----------------------------------------------------
       CLOSE
    ----------------------------------------------------- */

    function closeErpHelp() {

        if (!helpModal) {
            return;
        }

        helpModal.classList.remove("open");

        helpModal.setAttribute(
            "aria-hidden",
            "true"
        );

        document.body.classList.remove(
            "erp-help-open"
        );
    }


    /* -----------------------------------------------------
       OPEN BUTTON
    ----------------------------------------------------- */

    if (openHelpBtn) {

        openHelpBtn.addEventListener(
            "click",
            openErpHelp
        );

    }


    /* -----------------------------------------------------
       CLOSE BUTTON
    ----------------------------------------------------- */

    if (closeHelpBtn) {

        closeHelpBtn.addEventListener(
            "click",
            closeErpHelp
        );

    }


    /* -----------------------------------------------------
       DONE BUTTON
    ----------------------------------------------------- */

    if (doneHelpBtn) {

        doneHelpBtn.addEventListener(
            "click",
            closeErpHelp
        );

    }


    /* -----------------------------------------------------
       CLICK OUTSIDE MODAL
    ----------------------------------------------------- */

    if (helpModal) {

        helpModal.addEventListener(
            "click",
            function (event) {

                if (
                    event.target === helpModal
                ) {
                    closeErpHelp();
                }

            }
        );

    }


    /* -----------------------------------------------------
       ESCAPE
    ----------------------------------------------------- */

    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape" &&
                helpModal &&
                helpModal.classList.contains("open")
            ) {

                closeErpHelp();

            }

        }
    );

});