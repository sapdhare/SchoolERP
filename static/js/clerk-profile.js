/* ==========================================================
   SPL SHALASARTHI
   CLERK PROFILE PAGE
========================================================== */

document.addEventListener("DOMContentLoaded", function () {

    "use strict";


    /* ======================================================
       GLOBAL ELEMENTS
    ======================================================= */

    const profileForm =
        document.getElementById("profileUpdateForm");

    const profileSaveBtn =
        document.getElementById("profileSaveBtn");

    const profileSaveStatus =
        document.getElementById("profileSaveStatus");

    const addressInput =
        document.getElementById("profile_address");

    const addressCounter =
        document.getElementById("addressCounter");

    const csrfToken =
        window.PROFILE_CSRF_TOKEN || "";


    /* ======================================================
       MESSAGE HELPER
    ======================================================= */

    function showMessage(message, type = "error") {

        const box =
            document.getElementById(
                "profilePageMessage"
            );

        if (!box) return;

        box.textContent = message;

        box.className =
            "profile-page-message show " +
            type;

        window.clearTimeout(
            box._hideTimer
        );

        box._hideTimer =
            window.setTimeout(
                function () {

                    box.classList.remove(
                        "show"
                    );

                },
                5000
            );
    }


    /* ======================================================
       FETCH JSON SAFELY
    ======================================================= */
    /* ======================================================
       FETCH JSON SAFELY
    ====================================================== */

    async function fetchJson(
        url,
        options = {}
    ) {

        let response;


        try {

            response =
                await fetch(
                    url,
                    {
                        credentials:
                            "same-origin",

                        ...options
                    }
                );

        } catch (networkError) {

            throw new Error(
                "Unable to connect to the server. Please try again."
            );

        }


        if (
            response.status === 401
        ) {

            window.location.href =
                "/login";

            throw new Error(
                "SESSION_EXPIRED"
            );

        }


        let data;


        try {

            data =
                await response.json();

        } catch (parseError) {

            throw new Error(
                `Server returned an invalid response (${response.status}).`
            );

        }


        if (!response.ok) {

            throw new Error(
                data.message ||
                `Request failed (${response.status}).`
            );

        }


        return data;
    }

    /* ======================================================
       ADDRESS COUNTER
    ======================================================= */

    function updateAddressCounter() {

        if (!addressInput ||
            !addressCounter) {
            return;
        }

        addressCounter.textContent =
            `${addressInput.value.length} / 500`;
    }


    if (addressInput) {

        addressInput.addEventListener(
            "input",
            updateAddressCounter
        );

        updateAddressCounter();
    }


    /* ======================================================
       PROFILE VALIDATION
    ======================================================= */

    function validateProfileForm() {

        const name =
            document
                .getElementById(
                    "profile_name"
                )
                ?.value
                .trim() || "";


        const phone =
            document
                .getElementById(
                    "profile_phone"
                )
                ?.value
                .trim() || "";


        const designation =
            document
                .getElementById(
                    "profile_designation"
                )
                ?.value
                .trim() || "";


        const address =
            document
                .getElementById(
                    "profile_address"
                )
                ?.value
                .trim() || "";


        if (!name) {

            showMessage(
                "Please enter your full name."
            );

            document
                .getElementById(
                    "profile_name"
                )
                ?.focus();

            return false;
        }


        if (name.length > 150) {

            showMessage(
                "Name cannot exceed 150 characters."
            );

            return false;
        }


        if (
            phone &&
            !/^[0-9]{10}$/.test(phone)
        ) {

            showMessage(
                "Please enter a valid 10-digit phone number."
            );

            document
                .getElementById(
                    "profile_phone"
                )
                ?.focus();

            return false;
        }


        if (designation.length > 100) {

            showMessage(
                "Designation cannot exceed 100 characters."
            );

            return false;
        }


        if (address.length > 500) {

            showMessage(
                "Address cannot exceed 500 characters."
            );

            return false;
        }


        return true;
    }


    /* ======================================================
       SAVE PROFILE
    ======================================================= */

    if (profileForm) {

        profileForm.addEventListener(
            "submit",
            async function (event) {

                event.preventDefault();


                if (
                    !validateProfileForm()
                ) {
                    return;
                }

                if (!profileSaveBtn) {
                    return;
                }

                const originalHtml =
                    profileSaveBtn.innerHTML;


                profileSaveBtn.disabled =
                    true;


                profileSaveBtn.innerHTML = `
                    <i class="fa-solid fa-spinner fa-spin"></i>
                    <span>Saving...</span>
                `;


                const formData =
                    new FormData();


                formData.append(
                    "name",
                    document
                        .getElementById(
                            "profile_name"
                        )
                        .value
                        .trim()
                );


                formData.append(
                    "phone",
                    document
                        .getElementById(
                            "profile_phone"
                        )
                        .value
                        .trim()
                );


                formData.append(
                    "designation",
                    document
                        .getElementById(
                            "profile_designation"
                        )
                        .value
                        .trim()
                );


                formData.append(
                    "address",
                    document
                        .getElementById(
                            "profile_address"
                        )
                        .value
                        .trim()
                );


                try {

                    const data =
                        await fetchJson(
                            "/clerk/profile/update",
                            {
                                method: "POST",

                                headers: {
                                    "X-CSRFToken":
                                        csrfToken
                                },

                                body: formData
                            }
                        );


                    if (
                        data.status !==
                        "success"
                    ) {

                        throw new Error(
                            data.message ||
                            "Profile update failed."
                        );
                    }


                    /* ==========================================
                 SUCCESS MESSAGE
              ========================================== */

                    showMessage(
                        data.message ||
                        "Profile updated successfully.",
                        "success"
                    );


                    if (profileSaveStatus) {

                        profileSaveStatus.innerHTML = `
                        <i class="fa-solid fa-circle-check"></i>
                        <span>
                            Changes saved successfully.
                        </span>
                    `;

                    }


                    /* ==========================================
                                    UPDATE HERO NAME
                                 ========================================== */

                    const updatedName =
                        document
                            .getElementById(
                                "profile_name"
                            )
                            .value
                            .trim();


                    document
                        .querySelectorAll(
                            ".profile-hero-name-row h2"
                        )
                        .forEach(
                            element => {

                                element.textContent =
                                    updatedName;

                            }
                        );


                    /* ==========================================
                       UPDATE AVATAR INITIAL
                    ========================================== */

                    const avatar =
                        document.querySelector(
                            ".profile-hero-avatar"
                        );


                    if (
                        avatar &&
                        updatedName
                    ) {

                        avatar.textContent =
                            updatedName
                                .charAt(0)
                                .toUpperCase();

                    }


                } catch (error) {

                    if (
                        error.message ===
                        "SESSION_EXPIRED"
                    ) {
                        return;
                    }


                    showMessage(
                        error.message ||
                        "Unable to update profile."
                    );

                } finally {

                    profileSaveBtn.disabled =
                        false;

                    profileSaveBtn.innerHTML =
                        originalHtml;

                }

            }
        );

    }


    /* ======================================================
       PASSWORD RESET ELEMENTS
    ======================================================= */

    const overlay =
        document.getElementById(
            "passwordResetOverlay"
        );

    const openResetBtn =
        document.getElementById(
            "openPasswordResetBtn"
        );

    const closeResetBtn =
        document.getElementById(
            "closePasswordResetBtn"
        );

    const closeSuccessBtn =
        document.getElementById(
            "closeSuccessBtn"
        );


    const sendOtpBtn =
        document.getElementById(
            "sendOtpBtn"
        );

    const verifyOtpBtn =
        document.getElementById(
            "verifyOtpBtn"
        );

    const updatePasswordBtn =
        document.getElementById(
            "updatePasswordBtn"
        );

    const resendOtpBtn =
        document.getElementById(
            "resendOtpBtn"
        );


    const profileOtp =
        document.getElementById(
            "profileOtp"
        );


    const newPassword =
        document.getElementById(
            "newPassword"
        );


    const confirmPassword =
        document.getElementById(
            "confirmPassword"
        );


    let currentPasswordStep = 1;

    let otpTimerInterval = null;

    let otpSecondsRemaining = 300;


    /* ======================================================
       PASSWORD MODAL OPEN
    ======================================================= */

    function openPasswordReset() {

        if (!overlay) {

            console.error(
                "Password reset overlay not found."
            );

            return;
        }


        resetPasswordUI();


        overlay.classList.add(
            "open"
        );

        overlay.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.classList.add(
            "password-reset-open"
        );

        document.body.style.overflow =
            "hidden";

        requestAnimationFrame(
            function () {

                profileOtp?.focus();

            }
        );
    }


    /* ======================================================
    CLOSE PASSWORD RESET
 ====================================================== */

    function closePasswordReset() {

        if (!overlay) {
            return;
        }


        overlay.classList.remove(
            "open"
        );


        overlay.setAttribute(
            "aria-hidden",
            "true"
        );


        document.body.classList.remove(
            "password-reset-open"
        );


        document.body.style.overflow =
            "";


        stopOtpTimer();

    }


    /* ======================================================
       OPEN BUTTON
    ====================================================== */

    if (openResetBtn) {

        openResetBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                openPasswordReset();

            }
        );

    } else {

        console.error(
            "openPasswordResetBtn not found."
        );

    }

    /* ======================================================
       CLOSE BUTTON
    ====================================================== */

    if (closeResetBtn) {

        closeResetBtn.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                closePasswordReset();

            }
        );

    }


    /* ======================================================
       CLOSE AFTER SUCCESS
    ====================================================== */

    if (closeSuccessBtn) {

        closeSuccessBtn.addEventListener(
            "click",
            function () {

                closePasswordReset();

                window.location.reload();

            }
        );

    }

    /* ======================================================
       CLICK OUTSIDE MODAL
    ====================================================== */

    if (overlay) {

        overlay.addEventListener(
            "click",
            function (event) {

                if (
                    event.target ===
                    overlay
                ) {

                    closePasswordReset();

                }

            }
        );

    }


    /* ======================================================
       ESCAPE
    ====================================================== */

    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape" &&
                overlay &&
                overlay.classList.contains(
                    "open"
                )
            ) {

                closePasswordReset();

            }

        }
    );

    /* ======================================================
       PASSWORD STEP
    ======================================================= */

    function setPasswordStep(step) {

        currentPasswordStep =
            step;


        document
            .querySelectorAll(
                ".password-reset-step"
            )
            .forEach(
                element => {

                    element.classList.remove(
                        "active"
                    );

                }
            );


        const target =
            document.getElementById(
                `passwordStep${step}`
            );


        if (target) {

            target.classList.add(
                "active"
            );

        }


        document
            .querySelectorAll(
                ".password-progress-item"
            )
            .forEach(
                element => {

                    const id =
                        element.id;

                    const number =
                        Number(
                            id.replace(
                                "passwordProgress",
                                ""
                            )
                        );


                    element.classList.toggle(
                        "active",
                        number === step
                    );


                    element.classList.toggle(
                        "completed",
                        number < step
                    );

                }
            );


        const line1 =
            document.getElementById(
                "passwordProgressLine1"
            );

        const line2 =
            document.getElementById(
                "passwordProgressLine2"
            );


        line1?.classList.toggle(
            "active",
            step >= 2
        );


        line2?.classList.toggle(
            "active",
            step >= 3
        );


        const success =
            document.getElementById(
                "passwordResetSuccess"
            );


        if (success) {

            success.classList.remove(
                "active"
            );

        }

    }


    /* ======================================================
       RESET PASSWORD UI
    ======================================================= */

    function resetPasswordUI() {

        stopOtpTimer();

        setPasswordStep(1);


        if (profileOtp) {

            profileOtp.value = "";

        }


        if (newPassword) {

            newPassword.value = "";

        }


        if (confirmPassword) {

            confirmPassword.value = "";

        }


        if (resendOtpBtn) {

            resendOtpBtn.disabled =
                true;

        }


        updatePasswordStrength("");

    }


    /* ======================================================
       OTP TIMER
    ======================================================= */

    function startOtpTimer() {

        stopOtpTimer();


        otpSecondsRemaining =
            300;


        updateOtpTimer();


        otpTimerInterval =
            window.setInterval(
                function () {

                    otpSecondsRemaining--;

                    updateOtpTimer();


                    if (
                        otpSecondsRemaining <=
                        0
                    ) {

                        stopOtpTimer();

                        if (resendOtpBtn) {

                            resendOtpBtn.disabled =
                                false;

                        }

                    }

                },
                1000
            );
    }


    function stopOtpTimer() {

        if (
            otpTimerInterval
        ) {

            clearInterval(
                otpTimerInterval
            );

            otpTimerInterval =
                null;
        }

    }


    function updateOtpTimer() {

        const timer =
            document.getElementById(
                "otpTimer"
            );


        if (!timer) return;


        const minutes =
            Math.floor(
                otpSecondsRemaining /
                60
            );


        const seconds =
            otpSecondsRemaining %
            60;


        timer.textContent =
            `OTP valid for ${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;


        if (
            otpSecondsRemaining <= 0
        ) {

            timer.textContent =
                "OTP expired. Request a new OTP.";

        }

    }


    /* ======================================================
       SEND OTP
    ======================================================= */

    async function sendOtp() {

        if (!sendOtpBtn) return;


        const originalHtml =
            sendOtpBtn.innerHTML;


        sendOtpBtn.disabled =
            true;


        sendOtpBtn.innerHTML = `
            <i class="fa-solid fa-spinner fa-spin"></i>
            <span>Sending...</span>
        `;


        try {

            const data =
                await fetchJson(
                    "/clerk/profile/send-otp",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "X-CSRFToken":
                                csrfToken
                        },

                        body: JSON.stringify({})
                    }
                );


            if (
                data.status !==
                "success"
            ) {

                throw new Error(
                    data.message ||
                    "Unable to send OTP."
                );

            }


            setPasswordStep(2);

            startOtpTimer();

            if (resendOtpBtn) {

                resendOtpBtn.disabled =
                    true;

            }


            profileOtp?.focus();


            showMessage(
                "OTP sent to your registered email.",
                "success"
            );


        } catch (error) {

            if (
                error.message ===
                "SESSION_EXPIRED"
            ) {
                return;
            }


            showMessage(
                error.message ||
                "Unable to send OTP."
            );


        } finally {

            sendOtpBtn.disabled =
                false;

            sendOtpBtn.innerHTML =
                originalHtml;

        }

    }


    if (sendOtpBtn) {

        sendOtpBtn.addEventListener(
            "click",
            sendOtp
        );

    }


    /* ======================================================
       RESEND OTP
    ======================================================= */

    if (resendOtpBtn) {

        resendOtpBtn.addEventListener(
            "click",
            async function () {

                if (
                    resendOtpBtn.disabled
                ) {
                    return;
                }


                await sendOtp();

            }
        );

    }


    /* ======================================================
       OTP INPUT
    ======================================================= */

    if (profileOtp) {

        profileOtp.addEventListener(
            "input",
            function () {

                this.value =
                    this.value
                        .replace(
                            /\D/g,
                            ""
                        )
                        .slice(0, 6);

            }
        );


        profileOtp.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key ===
                    "Enter"
                ) {

                    verifyOtp();

                }

            }
        );

    }


    /* ======================================================
       VERIFY OTP
    ======================================================= */

    async function verifyOtp() {

        const otp =
            profileOtp?.value
                .trim() || "";


        if (
            !/^\d{6}$/.test(otp)
        ) {

            showMessage(
                "Enter the 6-digit OTP sent to your email."
            );

            profileOtp?.focus();

            return;
        }


        const originalHtml =
            verifyOtpBtn.innerHTML;


        verifyOtpBtn.disabled =
            true;


        verifyOtpBtn.innerHTML = `
            <i class="fa-solid fa-spinner fa-spin"></i>
            <span>Verifying...</span>
        `;


        try {

            const data =
                await fetchJson(
                    "/clerk/profile/check-otp",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "X-CSRFToken":
                                csrfToken
                        },

                        body: JSON.stringify({
                            otp: otp
                        })
                    }
                );


            if (
                data.status !==
                "success"
            ) {

                throw new Error(
                    data.message ||
                    "OTP verification failed."
                );

            }


            stopOtpTimer();

            setPasswordStep(3);

            newPassword?.focus();


            showMessage(
                "OTP verified successfully.",
                "success"
            );


        } catch (error) {

            if (
                error.message ===
                "SESSION_EXPIRED"
            ) {
                return;
            }


            showMessage(
                error.message ||
                "OTP verification failed."
            );


        } finally {

            verifyOtpBtn.disabled =
                false;

            verifyOtpBtn.innerHTML =
                originalHtml;

        }

    }


    if (verifyOtpBtn) {

        verifyOtpBtn.addEventListener(
            "click",
            verifyOtp
        );

    }


    /* ======================================================
       PASSWORD VALIDATION
    ======================================================= */

    function getPasswordRequirements(
        password
    ) {

        return {

            length:
                password.length >= 8 &&
                password.length <= 128,

            upper:
                /[A-Z]/.test(password),

            lower:
                /[a-z]/.test(password),

            number:
                /\d/.test(password),

            special:
                /[^A-Za-z0-9]/.test(password)

        };

    }


    function updateRequirement(
        id,
        valid
    ) {

        const element =
            document.getElementById(
                id
            );


        if (!element) return;


        element.classList.toggle(
            "valid",
            valid
        );


        const icon =
            element.querySelector(
                "i"
            );


        if (icon) {

            icon.className =
                valid
                    ? "fa-solid fa-circle-check"
                    : "fa-solid fa-circle";

        }

    }


    function updatePasswordStrength(
        password
    ) {

        const requirements =
            getPasswordRequirements(
                password
            );


        updateRequirement(
            "reqLength",
            requirements.length
        );


        updateRequirement(
            "reqUpper",
            requirements.upper
        );


        updateRequirement(
            "reqLower",
            requirements.lower
        );


        updateRequirement(
            "reqNumber",
            requirements.number
        );


        updateRequirement(
            "reqSpecial",
            requirements.special
        );


        const score =
            Object.values(
                requirements
            )
                .filter(Boolean)
                .length;


        const bar =
            document.getElementById(
                "passwordStrengthBar"
            );


        const text =
            document.getElementById(
                "passwordStrengthText"
            );


        if (!bar || !text) {
            return;
        }


        let width = 0;

        let label =
            "Enter password";


        if (score === 1) {

            width = 20;

            label = "Very weak";

        } else if (score === 2) {

            width = 40;

            label = "Weak";

        } else if (score === 3) {

            width = 60;

            label = "Fair";

        } else if (score === 4) {

            width = 80;

            label = "Strong";

        } else if (score === 5) {

            width = 100;

            label = "Very strong";

        }


        bar.style.width =
            `${width}%`;


        text.textContent =
            label;

    }


    newPassword?.addEventListener(
        "input",
        function () {

            updatePasswordStrength(
                this.value
            );

        }
    );


    /* ======================================================
       PASSWORD VISIBILITY
    ======================================================= */

    document
        .querySelectorAll(
            ".password-visibility-btn"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    function () {

                        const targetId =
                            this.dataset.target;


                        const input =
                            document.getElementById(
                                targetId
                            );


                        if (!input) {
                            return;
                        }


                        const icon =
                            this.querySelector(
                                "i"
                            );


                        if (
                            input.type ===
                            "password"
                        ) {

                            input.type =
                                "text";

                            icon.className =
                                "fa-regular fa-eye-slash";

                        } else {

                            input.type =
                                "password";

                            icon.className =
                                "fa-regular fa-eye";

                        }

                    }
                );

            }
        );


    /* ======================================================
       UPDATE PASSWORD
    ======================================================= */

    async function updatePassword() {

        const password =
            newPassword?.value || "";


        const confirmation =
            confirmPassword?.value || "";


        const requirements =
            getPasswordRequirements(
                password
            );


        if (
            !Object.values(
                requirements
            ).every(Boolean)
        ) {

            showMessage(
                "Please meet all password requirements."
            );

            return;
        }


        if (
            password !==
            confirmation
        ) {

            showMessage(
                "Passwords do not match."
            );

            confirmPassword?.focus();

            return;
        }


        const originalHtml =
            updatePasswordBtn.innerHTML;


        updatePasswordBtn.disabled =
            true;


        updatePasswordBtn.innerHTML = `
            <i class="fa-solid fa-spinner fa-spin"></i>
            <span>Updating...</span>
        `;


        try {

            const data =
                await fetchJson(
                    "/clerk/profile/update-password",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "X-CSRFToken":
                                csrfToken
                        },

                        body: JSON.stringify({
                            password:
                                password
                        })
                    }
                );


            if (
                data.status !==
                "success"
            ) {

                throw new Error(
                    data.message ||
                    "Unable to update password."
                );

            }


            document
                .querySelectorAll(
                    ".password-reset-step"
                )
                .forEach(
                    element => {

                        element.classList.remove(
                            "active"
                        );

                    }
                );


            document
                .getElementById(
                    "passwordResetSuccess"
                )
                ?.classList.add(
                    "active"
                );


            stopOtpTimer();


            /*
             * Clear sensitive fields immediately.
             */

            if (profileOtp) {

                profileOtp.value = "";

            }

            if (newPassword) {

                newPassword.value = "";

            }

            if (confirmPassword) {

                confirmPassword.value = "";

            }


        } catch (error) {

            if (
                error.message ===
                "SESSION_EXPIRED"
            ) {
                return;
            }


            showMessage(
                error.message ||
                "Unable to update password."
            );


        } finally {

            updatePasswordBtn.disabled =
                false;

            updatePasswordBtn.innerHTML =
                originalHtml;

        }

    }


    if (updatePasswordBtn) {

        updatePasswordBtn.addEventListener(
            "click",
            updatePassword
        );

    }


});