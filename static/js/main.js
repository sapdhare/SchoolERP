
"use strict";

/* =========================================================
   SPL SHALASARTHI — LANDING PAGE JAVASCRIPT
   Sections:
   01. Shared helpers
   02. Navbar scroll effect
   03. Mobile navigation drawer
   04. Hero slider
   05. Floating preview interaction
   06. Feature card interaction
   07. ERP preview tabs
   08. Plan billing toggle
   09. Demo modal and success popup
   10. Demo lead form submission
   11. FAQ accordion
========================================================= */


/* =========================================================
   01. SHARED HELPERS
========================================================= */

const $ = (selector, root = document) =>
    root.querySelector(selector);

const $$ = (selector, root = document) =>
    Array.from(root.querySelectorAll(selector));

const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
);


/* =========================================================
   02. NAVBAR SCROLL EFFECT
========================================================= */

(() => {
    const navbar = $("#navbar");

    if (!navbar) return;

    const updateNavbar = () => {
        navbar.classList.toggle(
            "scrolled",
            window.scrollY > 50
        );
    };

    // Set the correct state immediately on page load.
    updateNavbar();

    window.addEventListener("scroll", updateNavbar, {
        passive: true
    });
})();


/* =========================================================
   03. MOBILE NAVIGATION DRAWER
========================================================= */

(() => {
    const menuToggle = $("#menuToggle");
    const closeMenuButton = $("#closeMenu");
    const navLinks = $("#navLinks");
    const overlay = $("#mobileOverlay");

    if (!menuToggle || !navLinks || !overlay) return;

    const isMenuOpen = () =>
        navLinks.classList.contains("active");

    function setMenuState(open) {
        navLinks.classList.toggle("active", open);
        overlay.classList.toggle("active", open);

        menuToggle.setAttribute(
            "aria-expanded",
            String(open)
        );

        navLinks.setAttribute(
            "aria-hidden",
            String(!open)
        );

        overlay.setAttribute(
            "aria-hidden",
            String(!open)
        );

        document.body.classList.toggle(
            "mobile-menu-open",
            open
        );
    }

    function openMenu() {
        setMenuState(true);
    }

    function closeSidebar() {
        setMenuState(false);
    }

    function toggleMenu() {
        setMenuState(!isMenuOpen());
    }

    menuToggle.addEventListener("click", toggleMenu);

    closeMenuButton?.addEventListener(
        "click",
        closeSidebar
    );

    overlay.addEventListener("click", closeSidebar);

    // Close after navigating to a page or section.
    $$(".mobile-nav-links a").forEach(link => {
        link.addEventListener("click", closeSidebar);
    });

    // Close the drawer using Escape.
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && isMenuOpen()) {
            closeSidebar();
        }
    });

    // Close the drawer when returning to desktop layout.
    window.addEventListener("resize", () => {
        if (window.innerWidth > 1024 && isMenuOpen()) {
            closeSidebar();
        }
    });

    // Expose these functions for the existing inline modal buttons.
    window.openMenu = openMenu;
    window.closeSidebar = closeSidebar;

    // Initialize accessibility state.
    setMenuState(false);
})();


/* =========================================================
   04. HERO SLIDER
   Rotates the three .hero-slide elements every 5 seconds.
   This is the ONLY hero slider initializer.
========================================================= */

(() => {
    const slider = $(".hero-slider");

    if (!slider) return;

    const slides = $$(".hero-slide", slider);

    if (slides.length === 0) return;

    // Avoid duplicate initialization.
    if (slider.dataset.initialized === "true") return;
    slider.dataset.initialized = "true";

    let currentIndex = slides.findIndex(slide =>
        slide.classList.contains("active")
    );

    if (currentIndex < 0) currentIndex = 0;

    let timerId = null;

    // Make sure exactly one slide is active.
    function showSlide(index) {
        slides.forEach((slide, slideIndex) => {
            const active = slideIndex === index;

            slide.classList.toggle("active", active);
            slide.setAttribute(
                "aria-hidden",
                String(!active)
            );
        });

        currentIndex = index;
    }

    function stopSlider() {
        if (timerId !== null) {
            window.clearInterval(timerId);
            timerId = null;
        }
    }

    function startSlider() {
        stopSlider();

        // Don't auto-rotate when reduced motion is requested.
        if (prefersReducedMotion.matches) return;

        // Don't rotate while the page is hidden.
        if (document.hidden) return;

        if (slides.length < 2) return;

        timerId = window.setInterval(() => {
            const nextIndex = (currentIndex + 1) % slides.length;
            showSlide(nextIndex);
        }, 5000);
    }

    // Normalize the initial slide state.
    showSlide(currentIndex);
    startSlider();

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopSlider();
        } else {
            startSlider();
        }
    });

    // Respond if the visitor changes motion preferences.
    if (typeof prefersReducedMotion.addEventListener === "function") {
        prefersReducedMotion.addEventListener("change", startSlider);
    } else if (typeof prefersReducedMotion.addListener === "function") {
        // Older browser compatibility.
        prefersReducedMotion.addListener(startSlider);
    }
})();


/* =========================================================
   05. FLOATING PREVIEW INTERACTION
   Only runs if .hero-right and .floating-msg exist.
========================================================= */

(() => {
    const heroPreview = $(".hero-right");
    const floatingCard = $(".floating-msg");

    if (!heroPreview || !floatingCard) return;
    if (prefersReducedMotion.matches) return;

    // Pointer tilt is only useful on devices with a fine pointer.
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
        return;
    }

    heroPreview.addEventListener("mousemove", event => {
        const rect = heroPreview.getBoundingClientRect();

        const relativeX =
            (event.clientX - rect.left) / rect.width;

        const relativeY =
            (event.clientY - rect.top) / rect.height;

        const rotateY = (0.5 - relativeX) * 8;
        const rotateX = (relativeY - 0.5) * 6;

        floatingCard.style.transform =
            `perspective(900px) rotateY(${rotateY}deg) rotateX(${rotateX}deg)`;
    });

    heroPreview.addEventListener("mouseleave", () => {
        floatingCard.style.transform = "";
    });
})();


/* =========================================================
   06. FEATURE CARD INTERACTION
========================================================= */

(() => {
    const featureCards = $$(".feature-card");

    if (featureCards.length === 0) return;
    if (prefersReducedMotion.matches) return;

    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
        return;
    }

    featureCards.forEach(card => {
        card.addEventListener("mousemove", event => {
            const rect = card.getBoundingClientRect();

            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;

            const rotateX = -((y - rect.height / 2) / 18);
            const rotateY = (x - rect.width / 2) / 18;

            card.style.transform =
                `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.015)`;
        });

        card.addEventListener("mouseleave", () => {
            card.style.transform = "";
        });
    });
})();


/* =========================================================
   07. ERP PREVIEW TABS
========================================================= */

(() => {
    const previewData = {
        dashboard: {
            image: "/static/images/dashboard_preview.png",
            badge1: "📊 Live Dashboard",
            badge2: "☁ Cloud Based",
            badge3: "⚡ Real Time Data"
        },

        students: {
            image: "/static/images/student_preview.png",
            badge1: "👨‍🎓 Student Records",
            badge2: "📋 Admission Tracking",
            badge3: "🔍 Instant Search"
        },

        fees: {
            image: "/static/images/fees_preview.png",
            badge1: "💰 Fee Collection",
            badge2: "📈 Payment Reports",
            badge3: "🧾 Receipt Generation"
        },

        certificates: {
            image: "/static/images/certificate_preview.png",
            badge1: "📜 Bonafide",
            badge2: "🎓 TC Generation",
            badge3: "⚡ One Click Download"
        },

        reports: {
            image: "/static/images/report_preview.png",
            badge1: "📊 Analytics",
            badge2: "📈 Smart Reports",
            badge3: "🎯 Decision Insights"
        },

        staff: {
            image: "/static/images/staff_preview.png",
            badge1: "👩‍🏫 Staff Management",
            badge2: "📝 Attendance",
            badge3: "📋 Teacher Records"
        }
    };

    const tabs = $$(".preview-tab");

    if (tabs.length === 0) return;

    const previewImage = $("#previewImage");
    const badge1 = $("#badge1");
    const badge2 = $("#badge2");
    const badge3 = $("#badge3");

    function activatePreview(tab) {
        const key = tab.dataset.tab;
        const data = previewData[key];

        // Ignore unknown tabs instead of throwing an error.
        if (!data) return;

        tabs.forEach(item => {
            const active = item === tab;

            item.classList.toggle("active", active);

            if (item.hasAttribute("aria-selected")) {
                item.setAttribute(
                    "aria-selected",
                    String(active)
                );
            }
        });

        if (previewImage) {
            previewImage.src = data.image;
            previewImage.alt = `${key} ERP preview`;
        }

        if (badge1) badge1.textContent = data.badge1;
        if (badge2) badge2.textContent = data.badge2;
        if (badge3) badge3.textContent = data.badge3;
    }

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            activatePreview(tab);
        });
    });
})();


/* =========================================================
   08. PLAN BILLING TOGGLE
   Supports existing inline onclick="toggleBilling(...)"
========================================================= */

window.toggleBilling = function (type, button) {
    if (type !== "monthly" && type !== "yearly") return;

    const billingButtons = $$(".billing-btn");

    billingButtons.forEach(item => {
        const active = item === button;

        item.classList.toggle("active", active);

        if (item.hasAttribute("aria-pressed")) {
            item.setAttribute("aria-pressed", String(active));
        }
    });

    // Update prices using the existing data-month/data-year values.
    $$(".amount").forEach(price => {
        const rawValue = type === "monthly"
            ? price.dataset.month
            : price.dataset.year;

        if (rawValue === undefined || rawValue === "") return;

        const amount = Number(rawValue);

        if (!Number.isFinite(amount)) return;

        price.textContent =
            "₹" + amount.toLocaleString("en-IN");
    });

    $$(".duration").forEach(duration => {
        duration.textContent =
            type === "monthly" ? "/month" : "/year";
    });
};


/* =========================================================
   SHALASARTHI — DEMO MODAL + LEAD SUBMISSION
   Modal:       #planModal
   Form:        #demoForm
   Endpoint:    POST /submit-lead
   Success UI:  #successPopup
========================================================= */

(() => {
    "use strict";

    function initializeDemoModal() {
        const modal = document.getElementById("planModal");
        const form = document.getElementById("demoForm");
        const successPopup = document.getElementById("successPopup");

        // main.js may also load on pages without the demo modal.
        if (!modal || !form) {
            return;
        }

        // Prevent duplicate event handlers.
        if (form.dataset.demoInitialized === "true") {
            return;
        }

        form.dataset.demoInitialized = "true";

        const modalBox = modal.querySelector(".modal-box");
        const submitButton = form.querySelector('[type="submit"]');

        const formMessage = form.querySelector("#demoFormMessage");
        const messageInput = form.querySelector("#message");
        const messageCount = form.querySelector("#demoMessageCount");

        const selectedPlanInput =
            form.querySelector('[name="selected_plan"]');

        const selectedPlanDisplay =
            form.querySelector('[name="selected_plan_display"]');

        let isSubmitting = false;
        let previousFocus = null;

        const reduceMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;

        /* -----------------------------------------------------
           FIELD HELPERS
        ----------------------------------------------------- */

        function getField(name) {
            return form.elements.namedItem(name);
        }

        function getValue(name) {
            const field = getField(name);
            return field ? String(field.value || "").trim() : "";
        }

        /* -----------------------------------------------------
           STATUS MESSAGE
        ----------------------------------------------------- */

        function showFormMessage(message, type = "error") {
            if (!formMessage) {
                console[type === "error" ? "error" : "log"](message);
                return;
            }

            formMessage.textContent = message;
            formMessage.hidden = false;
            formMessage.dataset.type = type;

            formMessage.classList.toggle(
                "is-success",
                type === "success"
            );

            formMessage.classList.toggle(
                "is-error",
                type === "error"
            );

            formMessage.setAttribute(
                "role",
                type === "error" ? "alert" : "status"
            );

            formMessage.scrollIntoView({
                behavior: reduceMotion ? "auto" : "smooth",
                block: "nearest"
            });
        }

        function clearFormMessage() {
            if (!formMessage) return;

            formMessage.hidden = true;
            formMessage.textContent = "";

            delete formMessage.dataset.type;

            formMessage.classList.remove(
                "is-success",
                "is-error"
            );
        }

        /* -----------------------------------------------------
           SUBMIT BUTTON STATE
        ----------------------------------------------------- */

        function setSubmitting(submitting) {
            isSubmitting = submitting;

            if (!submitButton) return;

            submitButton.disabled = submitting;

            submitButton.setAttribute(
                "aria-busy",
                String(submitting)
            );

            submitButton.classList.toggle(
                "is-loading",
                submitting
            );

            const normalContent = submitButton.querySelector(
                ".demo-submit-content"
            );

            const loadingContent = submitButton.querySelector(
                ".demo-submit-loading"
            );

            if (normalContent && loadingContent) {
                normalContent.hidden = submitting;
                loadingContent.hidden = !submitting;
            } else {
                submitButton.textContent = submitting
                    ? "Submitting your request..."
                    : "Request My Free Demo";
            }
        }

        /* -----------------------------------------------------
           MODAL OPEN
        ----------------------------------------------------- */

        window.openPlanModal = function (plan = "Free Demo") {
            previousFocus = document.activeElement;

            const chosenPlan = String(plan || "Free Demo").trim();

            const displayPlan = chosenPlan.toLowerCase().includes("plan")
                ? chosenPlan
                : `${chosenPlan} Plan`;

            if (selectedPlanInput) {
                selectedPlanInput.value = displayPlan;
            }

            if (selectedPlanDisplay) {
                selectedPlanDisplay.value = displayPlan;
            }

            clearFormMessage();

            modal.style.display = "flex";
            modal.classList.add("active");
            modal.setAttribute("aria-hidden", "false");

            document.body.classList.add("modal-open");

            if (typeof window.closeSidebar === "function") {
                window.closeSidebar();
            }

            window.requestAnimationFrame(() => {
                const firstInput = form.querySelector(
                    'input:not([type="hidden"]):not([readonly]), textarea'
                );

                if (firstInput) {
                    firstInput.focus();
                }
            });
        };

        /* -----------------------------------------------------
           MODAL CLOSE
        ----------------------------------------------------- */

        window.closePlanModal = function () {
            // Do not close while the server is processing the request.
            if (isSubmitting) return;

            modal.classList.remove("active");
            modal.style.display = "none";
            modal.setAttribute("aria-hidden", "true");

            document.body.classList.remove("modal-open");

            if (
                previousFocus &&
                document.contains(previousFocus) &&
                typeof previousFocus.focus === "function"
            ) {
                previousFocus.focus();
            }
        };

        /* -----------------------------------------------------
           SUCCESS POPUP
        ----------------------------------------------------- */

        window.closeSuccessPopup = function () {
            if (!successPopup) return;

            successPopup.classList.remove("active");
            successPopup.style.display = "none";
            successPopup.setAttribute("aria-hidden", "true");

            document.body.classList.remove("modal-open");

            if (
                previousFocus &&
                document.contains(previousFocus) &&
                typeof previousFocus.focus === "function"
            ) {
                previousFocus.focus();
            }
        };

        function openSuccessPopup(message) {
            if (!successPopup) {
                // Fallback if the popup HTML has not been added.
                window.alert(message);
                return;
            }

            const messageElement = successPopup.querySelector(
                "#successPopupMessage"
            );

            if (messageElement) {
                messageElement.textContent = message;
            }

            successPopup.style.display = "flex";
            successPopup.classList.add("active");

            successPopup.setAttribute("aria-hidden", "false");

            document.body.classList.add("modal-open");

            const doneButton = successPopup.querySelector(
                ".demo-success-button"
            );

            if (doneButton) {
                doneButton.focus();
            }
        }

        /* -----------------------------------------------------
           CLOSE ON BACKDROP CLICK
        ----------------------------------------------------- */

        modal.addEventListener("click", event => {
            if (event.target === modal) {
                window.closePlanModal();
            }
        });

        if (successPopup) {
            successPopup.addEventListener("click", event => {
                if (event.target === successPopup) {
                    window.closeSuccessPopup();
                }
            });
        }

        /* -----------------------------------------------------
           ESCAPE KEY
        ----------------------------------------------------- */

        document.addEventListener("keydown", event => {
            if (event.key !== "Escape") return;

            if (
                modal.getAttribute("aria-hidden") === "false"
            ) {
                window.closePlanModal();
            } else if (
                successPopup &&
                successPopup.getAttribute("aria-hidden") === "false"
            ) {
                window.closeSuccessPopup();
            }
        });

        /* -----------------------------------------------------
           MESSAGE CHARACTER COUNTER
        ----------------------------------------------------- */

        function updateMessageCount() {
            if (!messageInput || !messageCount) return;

            messageCount.textContent =
                `${messageInput.value.length} / 1500`;
        }

        if (messageInput) {
            messageInput.addEventListener(
                "input",
                updateMessageCount
            );
        }

        updateMessageCount();

        /* -----------------------------------------------------
           RESET FORM AFTER SUCCESS
        ----------------------------------------------------- */

        function resetForm() {
            form.reset();

            // Restore the plan's default values after resetting.
            if (selectedPlanInput) {
                selectedPlanInput.value = "Free Demo Plan";
            }

            if (selectedPlanDisplay) {
                selectedPlanDisplay.value = "Free Demo Plan";
            }

            updateMessageCount();
            clearFormMessage();
        }

        /* -----------------------------------------------------
           SUBMIT DEMO REQUEST
        ----------------------------------------------------- */

        form.addEventListener("submit", async event => {
            // Always prevent a normal browser form navigation.
            event.preventDefault();

            if (isSubmitting) return;

            clearFormMessage();

            // Validate required fields.
            const school = getValue("school_name");
            const person = getValue("contact_person");
            const mobile = getValue("mobile");
            const email = getValue("email");
            const students = getValue("students");
            const selectedPlan =
                getValue("selected_plan") || "Free Demo Plan";
            const message = getValue("message");

            const schoolField = getField("school_name");
            const personField = getField("contact_person");
            const mobileField = getField("mobile");
            const emailField = getField("email");
            const studentsField = getField("students");

            if (!school || !person || !mobile) {
                showFormMessage(
                    "Please enter your school name, contact person and mobile number.",
                    "error"
                );

                if (!school && schoolField) {
                    schoolField.focus();
                } else if (!person && personField) {
                    personField.focus();
                } else if (!mobile && mobileField) {
                    mobileField.focus();
                }

                return;
            }

            if (!/^[6-9]\d{9}$/.test(mobile)) {
                showFormMessage(
                    "Please enter a valid 10-digit Indian mobile number.",
                    "error"
                );

                mobileField?.focus();
                return;
            }

            if (email && emailField && !emailField.validity.valid) {
                showFormMessage(
                    "Please enter a valid email address.",
                    "error"
                );

                emailField.focus();
                return;
            }

            let studentCount = null;

            if (students !== "") {
                studentCount = Number(students);

                if (
                    !Number.isSafeInteger(studentCount) ||
                    studentCount < 1 ||
                    studentCount > 1000000
                ) {
                    showFormMessage(
                        "Enter a whole student count between 1 and 1,000,000.",
                        "error"
                    );

                    studentsField?.focus();
                    return;
                }
            }

            const payload = {
                lead_source: "Landing Page Demo Modal",
                school_name: school,
                contact_person: person,
                mobile: mobile,
                email: email,
                student_strength: studentCount,
                selected_plan: selectedPlan,
                message: message
            };

            setSubmitting(true);

            try {
                const headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                };

                // Send the CSRF token if Flask-WTF provides one.
                const csrfField = form.querySelector(
                    'input[name="csrf_token"]'
                );

                if (csrfField?.value) {
                    headers["X-CSRFToken"] = csrfField.value;
                }

                const response = await fetch(form.action, {
                    method: "POST",
                    headers: headers,
                    credentials: "same-origin",
                    body: JSON.stringify(payload)
                });

                const contentType =
                    response.headers.get("content-type") || "";

                // A redirect/HTML response is not a confirmed JSON success.
                if (!contentType.includes("application/json")) {
                    throw new Error(
                        "The server did not return a JSON response. Check the Flask /submit-lead route and CSRF configuration."
                    );
                }

                const result = await response.json();

                if (!response.ok || result.success !== true) {
                    throw new Error(
                        result.message ||
                        "Your demo request could not be submitted. Please try again."
                    );
                }

                // Only show success after the server confirms it.
                const successMessage =
                    result.message ||
                    "Your demo request has been received. Our team will contact you shortly.";

                // Close the form and display confirmation.
                modal.classList.remove("active");
                modal.style.display = "none";
                modal.setAttribute("aria-hidden", "true");

                resetForm();

                openSuccessPopup(successMessage);

            } catch (error) {
                console.error(
                    "Demo lead submission failed:",
                    error
                );

                showFormMessage(
                    error.message ||
                    "Something went wrong. Please try again.",
                    "error"
                );

            } finally {
                setSubmitting(false);
            }
        });
    }

    // Initialize safely whether the script loads before or after the HTML.
    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initializeDemoModal,
            { once: true }
        );
    } else {
        initializeDemoModal();
    }
})();

/* =========================================================
   11. FAQ ACCORDION
   - Only one answer open at a time
   - Updates + / − indicators
   - Updates aria-expanded
   - Uses inert to prevent interaction with closed answers
   - Supports keyboard interaction through native buttons
========================================================= */

(() => {
    "use strict";

    const faqSection = document.querySelector("#faq");

    if (!faqSection) return;

    const faqItems = Array.from(
        faqSection.querySelectorAll(".faq-item")
    );

    if (faqItems.length === 0) return;

    function setFaqState(item, isOpen) {
        const button = item.querySelector(".faq-question");
        const answer = item.querySelector(".faq-answer");
        const icon = item.querySelector(".faq-icon");

        if (!button || !answer) return;

        item.classList.toggle("active", isOpen);

        button.setAttribute(
            "aria-expanded",
            String(isOpen)
        );

        if (icon) {
            icon.textContent = isOpen ? "−" : "+";
        }

        // Closed answers must not be keyboard-focusable.
        answer.inert = !isOpen;
    }

    // Normalize initial state from the existing .active class.
    // If several items are marked active in HTML, keep only the first.
    let initialOpenItem = null;

    faqItems.forEach((item) => {
        if (item.classList.contains("active") && !initialOpenItem) {
            initialOpenItem = item;
        }
    });

    faqItems.forEach((item) => {
        setFaqState(item, item === initialOpenItem);
    });

    // Handle FAQ clicks using event delegation.
    faqSection.addEventListener("click", (event) => {
        const button = event.target.closest(".faq-question");

        if (!button || !faqSection.contains(button)) {
            return;
        }

        const currentItem = button.closest(".faq-item");

        if (!currentItem) return;

        const shouldOpen =
            !currentItem.classList.contains("active");

        // Close every FAQ item first.
        faqItems.forEach((item) => {
            setFaqState(item, false);
        });

        // Open the selected item if it was previously closed.
        // Clicking an open item therefore closes it.
        if (shouldOpen) {
            setFaqState(currentItem, true);
        }
    });
})();
