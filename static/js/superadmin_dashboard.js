/* =========================================================
   SUPERADMIN NAVBAR INTERACTIONS
========================================================= */

(() => {
    "use strict";

    function initSuperadminNavbar() {
        const navbar = document.getElementById("superadminNavbar");

        if (!navbar || navbar.dataset.initialized === "true") {
            return;
        }

        navbar.dataset.initialized = "true";


        const profileButton = document.getElementById(
            "superadminProfileButton"
        );

        const profileDropdown = document.getElementById(
            "superadminProfileDropdown"
        );

        const profileWrapper = document.getElementById(
            "superadminProfileWrapper"
        );

        const menuToggle = document.getElementById(
            "superadminMenuToggle"
        );


        /* -----------------------------------------------
           ACCESSIBLE DROPDOWN HELPER
        ------------------------------------------------ */

        function setDropdown(button, panel, isOpen) {
            if (!button || !panel) {
                return;
            }

            button.classList.toggle("is-open", isOpen);
            panel.classList.toggle("is-open", isOpen);

            button.setAttribute("aria-expanded", String(isOpen));
            panel.setAttribute("aria-hidden", String(!isOpen));

            panel.inert = !isOpen;
        }


        function closeAllDropdowns() {
            setDropdown(
                profileButton,
                profileDropdown,
                false
            );
        }

        /* ----------------------------------------------
           PROFILE
        ------------------------------------------------ */

        if (profileButton && profileDropdown) {
            profileButton.addEventListener("click", (event) => {
                event.stopPropagation();

                const shouldOpen =
                    !profileDropdown.classList.contains("is-open");

                closeAllDropdowns();

                setDropdown(
                    profileButton,
                    profileDropdown,
                    shouldOpen
                );
            });
        }


        /* -----------------------------------------------
           CLOSE ON OUTSIDE CLICK
        ------------------------------------------------ */

        document.addEventListener("click", (event) => {

            const clickedInsideProfile =
                profileWrapper &&
                profileWrapper.contains(event.target);

            if (
                !clickedInsideProfile
            ) {
                closeAllDropdowns();
            }
        });


        /* -----------------------------------------------
           CLOSE ON ESCAPE
        ------------------------------------------------ */

        document.addEventListener("keydown", (event) => {
            if (event.key !== "Escape") {
                return;
            }


            const profileWasOpen =
                profileDropdown &&
                profileDropdown.classList.contains("is-open");

            closeAllDropdowns();

            if (profileWasOpen && profileButton) {
                profileButton.focus();
            }
        });


        /* -----------------------------------------------
           SIDEBAR TOGGLE
           
           Supports common existing sidebar patterns.
           Add your actual sidebar selector here if needed.
        ------------------------------------------------ */

        if (menuToggle) {
            menuToggle.addEventListener("click", () => {
                const sidebar = document.querySelector(
                    "#sidebar, .sidebar, .dashboard-sidebar, " +
                    ".sidebar-wrapper, aside"
                );

                const mainContent = document.querySelector(
                    "#mainContent, .main-content, " +
                    ".dashboard-main, .content-wrapper"
                );

                if (!sidebar) {
                    console.warn(
                        "Superadmin navbar: sidebar not found. " +
                        "Update the selector in superadmin-navbar.js."
                    );
                    return;
                }

                const isMobile = window.matchMedia(
                    "(max-width: 768px)"
                ).matches;

                if (isMobile) {
                    sidebar.classList.toggle("is-open");

                    const isOpen =
                        sidebar.classList.contains("is-open");

                    menuToggle.setAttribute(
                        "aria-expanded",
                        String(isOpen)
                    );

                    document.body.classList.toggle(
                        "superadmin-sidebar-open",
                        isOpen
                    );
                } else {
                    sidebar.classList.toggle("is-collapsed");

                    const isCollapsed =
                        sidebar.classList.contains("is-collapsed");

                    menuToggle.setAttribute(
                        "aria-expanded",
                        String(!isCollapsed)
                    );

                    if (mainContent) {
                        mainContent.classList.toggle(
                            "sidebar-collapsed",
                            isCollapsed
                        );
                    }
                }
            });
        }


        /* -----------------------------------------------
           FLASH MESSAGE DISMISSAL
        ------------------------------------------------ */

        document
            .querySelectorAll(".superadmin-flash-close")
            .forEach((button) => {
                button.addEventListener("click", () => {
                    const flash = button.closest(
                        ".superadmin-flash"
                    );

                    if (flash) {
                        flash.remove();
                    }
                });
            });

    }


    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initSuperadminNavbar
        );
    } else {
        initSuperadminNavbar();
    }

})();



/* =========================================================
   SUPERADMIN NOTIFICATIONS
   - Load unread count on page load
   - Poll for new notifications
   - Animate unread notifications
   - Mark an individual notification as read on click
========================================================= */


(() => {
    "use strict";

    // Prevent this script from initializing twice.
    if (window.__superadminNotificationsInitialized) return;
    window.__superadminNotificationsInitialized = true;

    const wrapper = document.getElementById(
        "superadminNotificationWrapper"
    );

    const button = document.getElementById(
        "superadminNotificationButton"
    );

    const badge = document.getElementById(
        "superadminNotificationBadge"
    );

    const panel = document.getElementById(
        "superadminNotificationPanel"
    );

    const list = document.getElementById(
        "superadminNotificationList"
    );

    const summary = document.getElementById(
        "superadminNotificationSummary"
    );

    const footer = document.getElementById(
        "superadminNotificationFooter"
    );

    const loadMoreButton = document.getElementById(
        "superadminNotificationLoadMore"
    );

    if (
        !wrapper ||
        !button ||
        !badge ||
        !panel ||
        !list ||
        !summary ||
        !footer ||
        !loadMoreButton
    ) {
        console.error(
            "Super Admin notifications: required HTML elements are missing."
        );

        return;
    }

    // ---------------------------------------------------------
    // CONFIGURATION
    // ---------------------------------------------------------

    const API_URL = "/superadmin/api/notifications";

    const PAGE_SIZE = 6;

    const REFRESH_INTERVAL = 30 * 1000;

    const ALLOWED_TARGETS = new Set([
        "/superadmin/leads",
        "/superadmin/schools",
        "/superadmin/subscriptions",
        "/superadmin/payments"
    ]);

    // Stores notifications already loaded into the current panel.
    const notificationMap = new Map();

    let loadedCount = 0;
    let unreadCount = 0;

    let isOpen = false;
    let isLoading = false;
    let isLoadingMore = false;

    let refreshTimer = null;
    let refreshRequest = null;

    let csrfToken = "";

    const readInFlight = new Set();
    const pendingReadIds = new Set();

    let hasMoreNotifications = false;
    let nextCursor = null;

    // ---------------------------------------------------------
    // CSRF TOKEN
    // ---------------------------------------------------------

    function getCsrfToken() {
        if (csrfToken) return csrfToken;

        const meta = document.querySelector(
            'meta[name="csrf-token"]'
        );

        if (meta) {
            csrfToken = meta.content || "";
        }

        if (!csrfToken) {
            const input = document.querySelector(
                'input[name="csrf_token"]'
            );

            if (input) {
                csrfToken = input.value || "";
            }
        }

        return csrfToken;
    }

    // ---------------------------------------------------------
    // HTML ESCAPING
    // ---------------------------------------------------------

    function escapeHTML(value) {
        return String(value ?? "").replace(
            /[&<>"']/g,
            character => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            })[character]
        );
    }

    // ---------------------------------------------------------
    // DATE FORMATTING
    // ---------------------------------------------------------

    function formatDate(value) {
        if (!value) return "";

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return "";
        }

        return new Intl.DateTimeFormat("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            hour12: true
        }).format(date);
    }

    // ---------------------------------------------------------
    // NOTIFICATION ICONS
    // ---------------------------------------------------------

    function getIcon(type) {
        const icons = {
            lead: `
                <svg viewBox="0 0 24 24"
                    width="19" height="19"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
                    <circle cx="9" cy="7" r="4"></circle>
                    <path d="M19 8v6"></path>
                    <path d="M22 11h-6"></path>
                </svg>
            `,

            school: `
                <svg viewBox="0 0 24 24"
                    width="19" height="19"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <path d="M3 21V8l9-5 9 5v13"></path>
                    <path d="M9 21v-7h6v7"></path>
                    <path d="M7 10h2"></path>
                    <path d="M15 10h2"></path>
                </svg>
            `,

            payment: `
                <svg viewBox="0 0 24 24"
                    width="19" height="19"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <rect x="3" y="5" width="18" height="14" rx="2"></rect>
                    <path d="M3 10h18"></path>
                    <path d="M7 15h3"></path>
                </svg>
            `,

            renewal: `
                <svg viewBox="0 0 24 24"
                    width="19" height="19"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <path d="M20 7v5h-5"></path>
                    <path d="M4 17v-5h5"></path>
                    <path d="M5.6 9A7 7 0 0 1 18 6l2 6"></path>
                    <path d="M18.4 15A7 7 0 0 1 6 18l-2-6"></path>
                </svg>
            `,

            subscription: `
                <svg viewBox="0 0 24 24"
                    width="19" height="19"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <rect x="3" y="5" width="18" height="14" rx="2"></rect>
                    <path d="M3 10h18"></path>
                    <path d="M7 15h4"></path>
                </svg>
            `
        };

        return icons[type] || icons.subscription;
    }

    // ---------------------------------------------------------
    // BADGE
    // ---------------------------------------------------------

    function updateBadge(count) {
        unreadCount = Math.max(
            0,
            Number.parseInt(count, 10) || 0
        );

        badge.textContent = unreadCount > 99
            ? "99+"
            : String(unreadCount);

        badge.hidden = unreadCount === 0;

        button.setAttribute(
            "aria-label",
            unreadCount > 0
                ? `Notifications, ${unreadCount} unread`
                : "Notifications"
        );

        summary.textContent = unreadCount === 1
            ? "1 unread update"
            : `${unreadCount} unread updates`;
    }

    // ---------------------------------------------------------
    // PANEL OPEN / CLOSE
    // ---------------------------------------------------------

    function openPanel() {
        isOpen = true;

        panel.setAttribute("aria-hidden", "false");
        panel.removeAttribute("inert");

        panel.classList.add("is-open");

        button.classList.add("is-open");
        button.setAttribute("aria-expanded", "true");

        // Refresh immediately when opening.
        refreshNotifications();
    }

    function closePanel() {
        isOpen = false;

        panel.setAttribute("aria-hidden", "true");
        panel.setAttribute("inert", "");

        panel.classList.remove("is-open");

        button.classList.remove("is-open");
        button.setAttribute("aria-expanded", "false");
    }

    button.addEventListener("click", event => {
        event.preventDefault();

        if (isOpen) {
            closePanel();
        } else {
            openPanel();
        }
    });

    document.addEventListener("click", event => {
        if (
            isOpen &&
            !wrapper.contains(event.target)
        ) {
            closePanel();
        }
    });

    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && isOpen) {
            closePanel();
            button.focus();
        }
    });

    // ---------------------------------------------------------
    // TARGET URL VALIDATION
    // ---------------------------------------------------------

    function getSafeTarget(url) {
        if (typeof url !== "string") {
            return null;
        }

        if (!ALLOWED_TARGETS.has(url)) {
            return null;
        }

        return url;
    }

    // ---------------------------------------------------------
    // RENDER ONE NOTIFICATION
    // ---------------------------------------------------------

    function renderNotification(notification) {
        const id = Number(notification.id);

        if (!Number.isSafeInteger(id) || id <= 0) {
            return null;
        }

        const target = getSafeTarget(notification.url);

        if (!target) {
            console.warn(
                "Notification has an unsupported destination:",
                id
            );

            return null;
        }

        const type = String(notification.type || "subscription");

        const item = document.createElement("a");

        item.className = "superadmin-notification-item";

        item.href = target;

        item.dataset.notificationId = String(id);

        item.innerHTML = `
            <span class="superadmin-notification-item-icon is-${escapeHTML(type)}">
                ${getIcon(type)}
            </span>

            <span class="superadmin-notification-item-content">
                <strong>${escapeHTML(notification.title)}</strong>

                <span>${escapeHTML(notification.message)}</span>

                <time datetime="${escapeHTML(notification.created_at || "")}">
                    ${escapeHTML(formatDate(notification.created_at))}
                </time>
            </span>

            <span class="superadmin-notification-item-arrow"
                aria-hidden="true">→</span>
        `;

        if (notification.read_at) {
            item.classList.add("is-read");
        } else {
            item.classList.add("is-unread");
        }

        item.addEventListener("click", event => {
            // Do not intercept Ctrl+Click, Cmd+Click,
            // middle-click, or other modified navigation.
            if (
                event.ctrlKey ||
                event.metaKey ||
                event.shiftKey ||
                event.altKey ||
                event.button !== 0
            ) {
                return;
            }

            event.preventDefault();

            markAsRead(id).finally(() => {
                window.location.assign(target);
            });
        });

        return item;
    }

    // ---------------------------------------------------------
    // EMPTY / ERROR / LOADING STATES
    // ---------------------------------------------------------

    function showMessage(title, message) {
        list.innerHTML = `
            <div class="superadmin-notification-empty">
                <strong>${escapeHTML(title)}</strong>
                <p>${escapeHTML(message)}</p>
            </div>
        `;
    }

    function showLoading() {
        list.setAttribute("aria-busy", "true");

        if (notificationMap.size === 0) {
            list.innerHTML = `
                <div class="superadmin-notification-loading">
                    Loading notifications...
                </div>
            `;
        }
    }

    function finishLoading() {
        list.setAttribute("aria-busy", "false");
    }

      // ---------------------------------------------------------
    // LOAD MORE & VIEW ALL — BACKEND PAGINATION WORKFLOW
    // ---------------------------------------------------------

    function updateLoadMoreButton(hasMore) {
        const loadMoreWrapper = document.getElementById("superadminLoadMoreWrapper");
        if (!loadMoreWrapper || !loadMoreButton) return;

        // Toggle the entire container wrapper block visibility based on backend state
        if (hasMore === true) {
            loadMoreWrapper.style.display = "block";
            loadMoreButton.style.display = "inline-flex";
        } else {
            loadMoreWrapper.style.display = "none";
            loadMoreButton.style.display = "none";
        }

        loadMoreButton.disabled = isLoadingMore;

        const label = loadMoreButton.querySelector(".superadmin-load-more-label");
        if (label) {
            label.textContent = isLoadingMore
                ? "Loading older updates..."
                : "Load more notifications";
        }
    }

    function renderLoadedNotifications() {
        const notifications = Array.from(notificationMap.values());
        list.innerHTML = "";

        if (notifications.length === 0) {
            showMessage(
                "You're all caught up",
                "There are no unread notifications right now."
            );
        } else {
            const fragment = document.createDocumentFragment();
            notifications.forEach(notification => {
                const item = renderNotification(notification);
                if (item) {
                    fragment.appendChild(item);
                }
            });
            list.appendChild(fragment);
        }

        finishLoading();

        // Control the visibility of the "Load More" row using the tracking state from the API
        updateLoadMoreButton(hasMoreNotifications);
    }

    // LOAD MORE ACTION: Incremental backend fetch by 5 items
    loadMoreButton.addEventListener("click", async (e) => {
        e.preventDefault();
        if (isLoadingMore || !hasMoreNotifications) return;

        isLoadingMore = true;
        updateLoadMoreButton(true);

        try {
            // Append parameters to fetch older rows starting from nextCursor
            const url = new URL(API_URL, window.location.origin);
            url.searchParams.append("limit", "5");
            if (nextCursor) {
                url.searchParams.append("cursor", nextCursor);
            }

            const data = await fetchNotificationsFromEndpoint(url.toString());
            
            // Append newly fetched rows to the cache layout
            if (data && Array.isArray(data.notifications)) {
                data.notifications.forEach(n => notificationMap.set(n.id, n));
            }

            hasMoreNotifications = data.has_more === true;
            nextCursor = data.next_cursor ?? null;
            
        } catch (error) {
            console.error("Failed to load older notifications:", error);
        } finally {
            isLoadingMore = false;
            renderLoadedNotifications();
        }
    });

    // VIEW ALL ACTION: Loads all items instantly into the workspace frame panel
    footer.addEventListener("click", async (e) => {
        e.preventDefault();
        if (isLoading) return;

        isLoading = true;
        list.setAttribute("aria-busy", "true");
        footer.disabled = true;
        footer.textContent = "Loading all updates...";

        try {
            // Fetch everything at once by lifting the threshold boundary limit (e.g., 50)
            const url = new URL(API_URL, window.location.origin);
            url.searchParams.append("limit", "50");

            const data = await fetchNotificationsFromEndpoint(url.toString());
            
            // Clean out current data mapping arrays to handle full structural refresh
            notificationMap.clear();
            if (data && Array.isArray(data.notifications)) {
                data.notifications.forEach(n => notificationMap.set(n.id, n));
            }

            // Since we fetched everything, collapse the incremental button state
            hasMoreNotifications = false;
            nextCursor = null;

        } catch (error) {
            console.error("Failed to load all notifications:", error);
        } finally {
            isLoading = false;
            footer.disabled = false;
            footer.innerHTML = `<span>View all notifications</span><span aria-hidden="true">→</span>`;
            list.setAttribute("aria-busy", "false");
            renderLoadedNotifications();
        }
    });

    // ---------------------------------------------------------
    // CLEAN API REQUEST ABSTRACTION
    // ---------------------------------------------------------

    async function fetchNotificationsFromEndpoint(url) {
        const response = await fetch(url, {
            method: "GET",
            credentials: "same-origin",
            cache: "no-store",
            headers: {
                "Accept": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`Notification request failed (${response.status}).`);
        }

        const data = await response.json();

        if (!data || data.success !== true) {
            throw new Error(data?.message || "Unable to load notifications.");
        }

        if (!Array.isArray(data.notifications) || !Number.isFinite(Number(data.unread_count))) {
            throw new Error("The notification API returned an invalid response.");
        }

        updateBadge(data.unread_count);
        return data;
    }

    // Keep your original entry endpoint signature completely valid for standard polling
    async function fetchNotifications() {
        // Default entry parameters: loads the standard initial view segment batch (e.g., 5 items)
        const url = new URL(API_URL, window.location.origin);
        url.searchParams.append("limit", "5");
        
        const data = await fetchNotificationsFromEndpoint(url.toString());
        
        hasMoreNotifications = data.has_more === true;
        nextCursor = data.next_cursor ?? null;
        
        return data;
    }

    // ---------------------------------------------------------
    // REFRESH WITHOUT DUPLICATES
    // ---------------------------------------------------------

    async function refreshNotifications() {
        if (refreshRequest) {
            return refreshRequest;
        }

        refreshRequest = (async () => {
            if (notificationMap.size === 0) {
                showLoading();
            }

            try {
                const data = await fetchNotifications();

                updateBadge(data.unread_count);

                const incoming = data.notifications;

                // Remember IDs already displayed so repeated polling
                // does not create duplicate notification cards.
                incoming.forEach(notification => {
                    const id = Number(notification.id);

                    if (
                        Number.isSafeInteger(id) &&
                        id > 0 &&
                        !notificationMap.has(id)
                    ) {
                        notificationMap.set(id, notification);
                    } else if (
                        Number.isSafeInteger(id) &&
                        notificationMap.has(id)
                    ) {
                        // Update the existing notification data.
                        notificationMap.set(id, {
                            ...notificationMap.get(id),
                            ...notification
                        });
                    }
                });

                // Keep the newest notifications first.
                const sorted = Array.from(
                    notificationMap.entries()
                ).sort((a, b) => {
                    const dateA = Date.parse(
                        a[1].created_at || ""
                    ) || 0;

                    const dateB = Date.parse(
                        b[1].created_at || ""
                    ) || 0;

                    return dateB - dateA || b[0] - a[0];
                });

                notificationMap.clear();

                sorted.forEach(([id, notification]) => {
                    notificationMap.set(id, notification);
                });

                // Keep a small local buffer so Load More can show
                // additional notifications returned by the server.
                const MAX_BUFFER = 100;

                while (notificationMap.size > MAX_BUFFER) {
                    const oldestId = Array.from(
                        notificationMap.keys()
                    ).pop();

                    notificationMap.delete(oldestId);
                }

                // Initial display is the latest five. During polling,
                // retain the user's current loaded count.
                if (loadedCount === 0) {
                    loadedCount = Math.min(
                        PAGE_SIZE,
                        notificationMap.size
                    );
                }

                renderLoadedNotifications();

            } catch (error) {
                console.error(
                    "Unable to refresh Super Admin notifications:",
                    error
                );

                if (notificationMap.size === 0) {
                    showMessage(
                        "Unable to load notifications",
                        "Please try again shortly."
                    );

                    finishLoading();
                }

            } finally {
                refreshRequest = null;
            }
        })();

        return refreshRequest;
    }

    // ---------------------------------------------------------
    // MARK AS READ
    // ---------------------------------------------------------

    async function markAsRead(notificationId) {
        if (
            readInFlight.has(notificationId) ||
            pendingReadIds.has(notificationId)
        ) {
            return;
        }

        readInFlight.add(notificationId);

        try {
            const headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            };

            const token = getCsrfToken();

            if (token) {
                headers["X-CSRFToken"] = token;
            }

            const response = await fetch(
                `${API_URL}/${notificationId}/read`,
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers,
                    body: "{}"
                }
            );

            const data = await response.json();

            if (!response.ok || data.success !== true) {
                throw new Error(
                    data?.message || "Unable to mark notification as read."
                );
            }

            pendingReadIds.add(notificationId);

            const notification = notificationMap.get(notificationId);

            if (notification) {
                notification.read_at =
                    notification.read_at || new Date().toISOString();

                notificationMap.set(
                    notificationId,
                    notification
                );
            }

            // The API should return the authoritative unread count
            // when available. Otherwise, refresh it from the server.
            if (Number.isFinite(Number(data.unread_count))) {
                updateBadge(data.unread_count);
            } else {
                await refreshNotifications();
            }

            const item = list.querySelector(
                `[data-notification-id="${notificationId}"]`
            );

            if (item) {
                item.classList.remove("is-unread");
                item.classList.add("is-read");
            }

        } catch (error) {
            console.error(
                "Unable to mark notification as read:",
                error
            );

            // Do not silently pretend that the server saved the read
            // state. The destination still opens when the click handler
            // finishes, but the next server refresh can restore the
            // correct unread count.

        } finally {
            readInFlight.delete(notificationId);
        }
    }

    // ---------------------------------------------------------
    // INITIAL LOAD
    // ---------------------------------------------------------

    async function initializeNotifications() {
        await refreshNotifications();

        // Poll every 30 seconds. The server remains the source of truth.
        refreshTimer = window.setInterval(() => {
            if (!document.hidden) {
                refreshNotifications();
            }
        }, REFRESH_INTERVAL);
    }

    // Refresh when the user returns to the browser tab.
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            refreshNotifications();
        }
    });

    initializeNotifications();

    // Optional cleanup if the page is being torn down.
    window.addEventListener("pagehide", () => {
        if (refreshTimer !== null) {
            window.clearInterval(refreshTimer);
        }
    });

})();

/* =========================================================
   SUPERADMIN BUSINESS ANALYTICS
   Revenue Chart + Subscription Doughnut
   Source: /superadmin/dashboard/analytics

   Features:
   - Database-driven chart data
   - Smooth revenue gradient
   - INR currency formatting
   - Active / Renewals Due / Expired
   - Automatic refresh every 60 seconds
   - Safe error handling
========================================================= */

(() => {
    "use strict";

    const REFRESH_INTERVAL = 60_000;

    let revenueChart = null;
    let subscriptionChart = null;
    let refreshTimer = null;
    let isRefreshing = false;
    let activeController = null;

    const currencyFormatter = new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2
    });

    const numberFormatter = new Intl.NumberFormat("en-IN");

    function formatCurrency(value) {
        const amount = Number(value);

        return currencyFormatter.format(
            Number.isFinite(amount) ? amount : 0
        );
    }

    function formatNumber(value) {
        const amount = Number(value);

        return numberFormatter.format(
            Number.isFinite(amount) ? amount : 0
        );
    }

    function getElement(id) {
        return document.getElementById(id);
    }

    function setText(id, value) {
        const element = getElement(id);

        if (element) {
            element.textContent = value;
        }
    }

    function showMessage(id, message) {
        const element = getElement(id);

        if (!element) {
            return;
        }

        element.textContent = message;
        element.hidden = !message;
    }

    function formatUpdatedAt(value) {
        if (!value) {
            return "Update time unavailable";
        }

        return `Updated ${value}`;
    }


    /* =====================================================
       REVENUE CHART
    ====================================================== */

    function createRevenueChart(labels, values) {
        const canvas = getElement("revenueChart");

        if (!canvas || typeof Chart === "undefined") {
            return;
        }

        const context = canvas.getContext("2d");

        if (revenueChart) {
            revenueChart.destroy();
            revenueChart = null;
        }

        function getGradient(chartContext) {
            const chartArea = chartContext.chart.chartArea;

            if (!chartArea) {
                return "rgba(13, 148, 136, 0.10)";
            }

            const gradient = chartContext.chart.ctx.createLinearGradient(
                0,
                chartArea.top,
                0,
                chartArea.bottom
            );

            gradient.addColorStop(
                0,
                "rgba(13, 148, 136, 0.24)"
            );

            gradient.addColorStop(
                0.65,
                "rgba(45, 212, 191, 0.09)"
            );

            gradient.addColorStop(
                1,
                "rgba(45, 212, 191, 0.015)"
            );

            return gradient;
        }

        revenueChart = new Chart(context, {
            type: "line",

            data: {
                labels: labels,

                datasets: [{
                    label: "Revenue",

                    data: values,

                    borderColor: "#0d9488",

                    backgroundColor: getGradient,

                    borderWidth: 3,

                    fill: true,

                    tension: 0.38,

                    cubicInterpolationMode: "monotone",

                    pointRadius: 4,

                    pointHoverRadius: 7,

                    pointBackgroundColor: "#ffffff",

                    pointBorderColor: "#0d9488",

                    pointBorderWidth: 2.5,

                    pointHoverBackgroundColor: "#0d9488",

                    pointHoverBorderColor: "#ffffff",

                    pointHoverBorderWidth: 3,

                    spanGaps: false
                }]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                interaction: {
                    mode: "index",
                    intersect: false
                },

                animation: {
                    duration: 450,
                    easing: "easeOutQuart"
                },

                layout: {
                    padding: {
                        top: 8,
                        right: 8,
                        bottom: 0,
                        left: 0
                    }
                },

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        enabled: true,

                        backgroundColor: "#17243b",

                        titleColor: "#ffffff",

                        bodyColor: "#e2e8f0",

                        padding: 12,

                        cornerRadius: 10,

                        displayColors: false,

                        callbacks: {
                            label(context) {
                                return `Revenue: ${formatCurrency(
                                    context.parsed.y
                                )}`;
                            }
                        }
                    }
                },

                scales: {
                    x: {
                        border: {
                            display: false
                        },

                        grid: {
                            display: false,
                            drawTicks: false
                        },

                        ticks: {
                            color: "#8290a5",
                            maxRotation: 0,
                            autoSkip: false,
                            padding: 10,
                            font: {
                                size: 10,
                                weight: "600"
                            }
                        }
                    },

                    y: {
                        beginAtZero: true,

                        border: {
                            display: false
                        },

                        grid: {
                            color: "rgba(148, 163, 184, 0.15)",
                            drawTicks: false
                        },

                        ticks: {
                            color: "#8290a5",
                            padding: 10,
                            maxTicksLimit: 6,

                            callback(value) {
                                return new Intl.NumberFormat(
                                    "en-IN",
                                    {
                                        notation: "compact",
                                        maximumFractionDigits: 1
                                    }
                                ).format(value);
                            },

                            font: {
                                size: 10
                            }
                        }
                    }
                }
            }
        });
    }


    /* =====================================================
       SUBSCRIPTION DOUGHNUT
    ====================================================== */

    function createSubscriptionChart(labels, values) {
        const canvas = getElement("subscriptionChart");

        if (!canvas || typeof Chart === "undefined") {
            return;
        }

        if (subscriptionChart) {
            subscriptionChart.destroy();
            subscriptionChart = null;
        }

        const context = canvas.getContext("2d");

        subscriptionChart = new Chart(context, {
            type: "doughnut",

            data: {
                labels: labels,

                datasets: [{
                    data: values,

                    backgroundColor: [
                        "#10b981",
                        "#f59e0b",
                        "#ef4444"
                    ],

                    hoverBackgroundColor: [
                        "#059669",
                        "#d97706",
                        "#dc2626"
                    ],

                    borderColor: "#ffffff",

                    borderWidth: 4,

                    hoverBorderWidth: 4,

                    hoverOffset: 7,

                    spacing: 3
                }]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                cutout: "72%",

                animation: {
                    duration: 450,
                    easing: "easeOutQuart"
                },

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        enabled: true,

                        backgroundColor: "#17243b",

                        titleColor: "#ffffff",

                        bodyColor: "#e2e8f0",

                        padding: 12,

                        cornerRadius: 10,

                        callbacks: {
                            label(context) {
                                return (
                                    ` ${context.label}: ` +
                                    formatNumber(context.parsed)
                                );
                            }
                        }
                    }
                }
            }
        });
    }


    /* =====================================================
       UPDATE SUBSCRIPTION SUMMARY
    ====================================================== */

    function updateSubscriptionSummary(values) {
        const active = Number(values[0]) || 0;
        const renewals = Number(values[1]) || 0;
        const expired = Number(values[2]) || 0;

        setText("saActiveSubscriptions", formatNumber(active));

        setText(
            "saRenewalSubscriptions",
            formatNumber(renewals)
        );

        setText("saExpiredSubscriptions", formatNumber(expired));

        setText(
            "saTotalSubscriptions",
            formatNumber(active + renewals + expired)
        );
    }


    /* =====================================================
       REFRESH ANALYTICS FROM THE SERVER
    ====================================================== */

    async function refreshAnalytics() {
        const wrapper = getElement("superadminBusinessAnalytics");

        if (!wrapper || isRefreshing) {
            return;
        }

        const endpoint = wrapper.dataset.refreshUrl;

        if (!endpoint) {
            console.error(
                "Superadmin analytics: refresh URL is missing."
            );

            return;
        }

        if (typeof Chart === "undefined") {
            showMessage(
                "saRevenueChartMessage",
                "Chart.js could not be loaded. Check the script include."
            );

            showMessage(
                "saSubscriptionChartMessage",
                "Chart.js could not be loaded. Check the script include."
            );

            return;
        }

        isRefreshing = true;

        if (activeController) {
            activeController.abort();
        }

        activeController = new AbortController();

        const timeout = window.setTimeout(() => {
            activeController?.abort();
        }, 15000);

        try {
            const response = await fetch(endpoint, {
                method: "GET",

                credentials: "same-origin",

                cache: "no-store",

                headers: {
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },

                signal: activeController.signal
            });

            if (!response.ok) {
                throw new Error(
                    `Analytics request failed: HTTP ${response.status}`
                );
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(
                    data.message || "Analytics refresh failed."
                );
            }

            const revenueLabels = Array.isArray(data.revenue_labels)
                ? data.revenue_labels
                : [];

            const revenueValues = Array.isArray(data.revenue_values)
                ? data.revenue_values.map(
                    value => Number(value) || 0
                )
                : [];

            const subscriptionLabels = Array.isArray(
                data.subscription_labels
            )
                ? data.subscription_labels
                : ["Active", "Renewals Due", "Expired"];

            const subscriptionValues = Array.isArray(
                data.subscription_values
            )
                ? data.subscription_values.map(
                    value => Number(value) || 0
                )
                : [0, 0, 0];

            if (revenueLabels.length !== revenueValues.length) {
                throw new Error(
                    "Revenue chart labels and values do not match."
                );
            }

            if (
                subscriptionLabels.length !== 3 ||
                subscriptionValues.length !== 3
            ) {
                throw new Error(
                    "Subscription chart data is incomplete."
                );
            }

            /* ---------------------------------------------
               UPDATE REVENUE
            --------------------------------------------- */

            createRevenueChart(
                revenueLabels,
                revenueValues
            );

            setText(
                "saRevenueThisMonth",
                formatCurrency(data.revenue_this_month)
            );

            showMessage("saRevenueChartMessage", "");


            /* ---------------------------------------------
               UPDATE SUBSCRIPTIONS
            --------------------------------------------- */

            createSubscriptionChart(
                subscriptionLabels,
                subscriptionValues
            );

            updateSubscriptionSummary(subscriptionValues);

            showMessage("saSubscriptionChartMessage", "");


            /* ---------------------------------------------
               UPDATE STATUS
            --------------------------------------------- */

            setText(
                "saAnalyticsUpdatedAt",
                formatUpdatedAt(data.updated_at)
            );

        } catch (error) {
            if (error.name === "AbortError") {
                console.warn(
                    "Superadmin analytics request timed out or was cancelled."
                );
            } else {
                console.error(
                    "Superadmin analytics refresh failed:",
                    error
                );
            }

            showMessage(
                "saRevenueChartMessage",
                "Unable to refresh revenue data. The next refresh will retry."
            );

            showMessage(
                "saSubscriptionChartMessage",
                "Unable to refresh subscription data. The next refresh will retry."
            );

        } finally {
            window.clearTimeout(timeout);

            activeController = null;
            isRefreshing = false;
        }
    }


    /* =====================================================
       INITIALIZE + PERIODIC REFRESH
    ====================================================== */

    function initSuperadminAnalytics() {
        const wrapper = getElement("superadminBusinessAnalytics");

        if (!wrapper || wrapper.dataset.initialized === "true") {
            return;
        }

        wrapper.dataset.initialized = "true";

        // Fetch current database values immediately.
        refreshAnalytics();

        // Refresh every 60 seconds without reloading the page.
        refreshTimer = window.setInterval(
            refreshAnalytics,
            REFRESH_INTERVAL
        );

        // Pause periodic refresh in hidden tabs.
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                if (refreshTimer) {
                    window.clearInterval(refreshTimer);
                    refreshTimer = null;
                }

                if (activeController) {
                    activeController.abort();
                }

                return;
            }

            if (!refreshTimer) {
                refreshAnalytics();

                refreshTimer = window.setInterval(
                    refreshAnalytics,
                    REFRESH_INTERVAL
                );
            }
        });

        // Clean up if the page is being unloaded.
        window.addEventListener("pagehide", () => {
            if (refreshTimer) {
                window.clearInterval(refreshTimer);
                refreshTimer = null;
            }

            if (activeController) {
                activeController.abort();
            }
        }, { once: true });
    }


    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initSuperadminAnalytics
        );
    } else {
        initSuperadminAnalytics();
    }

})();



/* =========================================================
   SUPER ADMIN — PLATFORM INSIGHTS
   Independent of Business Analytics charts.
========================================================= */

(() => {
    "use strict";

    function initSchoolStudentChart() {
        const container = document.getElementById("schoolStudentChartData");
        const canvas = document.getElementById("schoolStudentChart");
        const emptyState = document.getElementById("schoolStudentChartEmpty");

        if (!container || !canvas) {
            return;
        }

        // Prevent duplicate initialization.
        if (canvas.dataset.initialized === "true") {
            return;
        }

        let labels = [];
        let values = [];

        try {
            labels = JSON.parse(container.dataset.labels || "[]");
            values = JSON.parse(container.dataset.values || "[]");
        } catch (error) {
            console.error("Platform Insights: Invalid chart data.", error);

            canvas.hidden = true;

            if (emptyState) {
                emptyState.hidden = false;
            }

            return;
        }

        // Validate data received from the backend.
        if (!Array.isArray(labels) || !Array.isArray(values)) {
            canvas.hidden = true;

            if (emptyState) {
                emptyState.hidden = false;
            }

            return;
        }

        const validData = labels
            .map((label, index) => ({
                label: String(label ?? ""),
                value: Number(values[index])
            }))
            .filter(item =>
                item.label.trim() !== "" &&
                Number.isFinite(item.value) &&
                item.value >= 0
            );

        if (validData.length === 0) {
            canvas.hidden = true;

            if (emptyState) {
                emptyState.hidden = false;
            }

            return;
        }

        if (typeof Chart === "undefined") {
            console.error(
                "Platform Insights: Chart.js is not loaded. " +
                "Load Chart.js before this script."
            );

            canvas.hidden = true;

            if (emptyState) {
                emptyState.hidden = false;
            }

            return;
        }

        if (emptyState) {
            emptyState.hidden = true;
        }

        canvas.hidden = false;

        const chartLabels = validData.map(item => item.label);
        const chartValues = validData.map(item => item.value);

        const ctx = canvas.getContext("2d");

        if (!ctx) {
            return;
        }

        // Light gradients for individual school bars.
        const palettes = [
            ["#0bb99d", "#d8f8ef"],
            ["#4387f5", "#e0eaff"],
            ["#9670f4", "#eee5ff"],
            ["#f2a53b", "#fff0d7"],
            ["#ec6c9c", "#ffe3ee"],
            ["#22a6c7", "#dff7ff"],
            ["#6479e8", "#e4e9ff"],
            ["#19a77c", "#d8f5e9"]
        ];

        const gradients = chartValues.map((value, index) => {
            const palette = palettes[index % palettes.length];

            const gradient = ctx.createLinearGradient(0, 0, 0, 280);

            gradient.addColorStop(0, palette[0]);
            gradient.addColorStop(1, palette[1]);

            return gradient;
        });

        canvas.dataset.initialized = "true";

        try {
            new Chart(ctx, {
                type: "bar",

                data: {
                    labels: chartLabels,

                    datasets: [{
                        label: "Students",

                        data: chartValues,

                        backgroundColor: gradients,

                        borderColor: chartValues.map((value, index) =>
                            palettes[index % palettes.length][0]
                        ),

                        borderWidth: 1,

                        borderRadius: 8,

                        borderSkipped: false,

                        maxBarThickness: 52,

                        categoryPercentage: 0.72,

                        barPercentage: 0.82
                    }]
                },

                options: {
                    responsive: true,

                    maintainAspectRatio: false,

                    animation: {
                        duration: 650,
                        easing: "easeOutQuart"
                    },

                    interaction: {
                        mode: "index",
                        intersect: false
                    },

                    layout: {
                        padding: {
                            top: 12,
                            right: 8,
                            bottom: 2,
                            left: 2
                        }
                    },

                    plugins: {
                        legend: {
                            display: false
                        },

                        tooltip: {
                            enabled: true,

                            displayColors: false,

                            backgroundColor: "#17243b",

                            titleColor: "#ffffff",

                            bodyColor: "#e5edf8",

                            padding: 12,

                            cornerRadius: 10,

                            callbacks: {
                                title(items) {
                                    return items.length
                                        ? items[0].label
                                        : "";
                                },

                                label(context) {
                                    const count = Number(context.raw) || 0;

                                    return (
                                        " Students: " +
                                        count.toLocaleString("en-IN")
                                    );
                                }
                            }
                        }
                    },

                    scales: {
                        x: {
                            grid: {
                                display: false
                            },

                            border: {
                                display: false
                            },

                            ticks: {
                                color: "#7b8aa1",

                                font: {
                                    size: window.innerWidth <= 480 ? 9 : 10,
                                    weight: "500"
                                },

                                maxRotation: 0,
                                minRotation: 0,

                                autoSkip: true,
                                maxTicksLimit: window.innerWidth <= 480 ? 3 : 6,

                                callback: function (value) {
                                    const label = this.getLabelForValue(value);
                                    const maxLength = window.innerWidth <= 480 ? 16 : 24;

                                    return label.length > maxLength
                                        ? label.substring(0, maxLength - 1) + "…"
                                        : label;
                                }
                            }
                        },

                        y: {
                            beginAtZero: true,

                            grace: "8%",

                            border: {
                                display: false
                            },

                            grid: {
                                color: "rgba(148, 163, 184, 0.15)",

                                drawTicks: false
                            },

                            ticks: {
                                color: "#8a98ad",

                                precision: 0,

                                padding: 10
                            }
                        }
                    }
                }
            });

        } catch (error) {
            canvas.dataset.initialized = "false";

            console.error(
                "Platform Insights: Chart initialization failed.",
                error
            );
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initSchoolStudentChart
        );
    } else {
        initSchoolStudentChart();
    }

})();