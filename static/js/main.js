
//hero js

const slides =
document.querySelectorAll(".hero-slide");

let currentSlide = 0;

if(slides.length){

    setInterval(() => {

        slides[currentSlide]
        .classList.remove("active");

        currentSlide++;

        if(currentSlide >= slides.length){
            currentSlide = 0;
        }

        slides[currentSlide]
        .classList.add("active");

    }, 5000);

}



// ======================================
// NAVBAR SCROLL EFFECT
// ======================================

const navbar =
document.getElementById("navbar");

if(navbar){

    window.addEventListener("scroll", () => {

        if(window.scrollY > 50){

            navbar.classList.add("scrolled");

        }else{

            navbar.classList.remove("scrolled");
        }

    });

}
// ======================================
// MOBILE SIDEBAR MENU
// ======================================

const menuToggle =
document.getElementById("menuToggle");

const closeMenu =
document.getElementById("closeMenu");

const navLinks =
document.getElementById("navLinks");

const overlay =
document.getElementById("mobileOverlay");

function openMenu(){

    navLinks.classList.add("active");

    overlay.classList.add("active");

    document.body.style.overflow = "hidden";
}

function closeSidebar(){

    navLinks.classList.remove("active");

    overlay.classList.remove("active");

    document.body.style.overflow = "";
}

if(menuToggle){

    menuToggle.addEventListener(
        "click",
        openMenu
    );
}

if(closeMenu){

    closeMenu.addEventListener(
        "click",
        closeSidebar
    );
}

if(overlay){

    overlay.addEventListener(
        "click",
        closeSidebar
    );
}

document
.querySelectorAll(
".mobile-nav-links a"
)
.forEach(link=>{

    link.addEventListener(
        "click",
        closeSidebar
    );

});



// Floating message tilt
const hero = document.querySelector('.hero-right');
const card = document.querySelector('.floating-msg');

if (hero && card) {
    hero.addEventListener('mousemove', (e) => {
        const x = (window.innerWidth / 2 - e.pageX) / 25;
        const y = (window.innerHeight / 2 - e.pageY) / 25;

        card.style.transform = `rotateY(${x}deg) rotateX(${y}deg)`;
    });
}
// feature section js
document.querySelectorAll(".feature-card").forEach(card => {
    card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const rotateX = -(y - rect.height / 2) / 10;
        const rotateY = (x - rect.width / 2) / 10;

        card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.03)`;
    });

    card.addEventListener("mouseleave", () => {
        card.style.transform = "rotateX(0) rotateY(0)";
    });
});


// HERO PREVIEW JS 

const previewData = {

    dashboard:{
        image:"/static/images/dashboard_preview.png",
        badge1:"📊 Live Dashboard",
        badge2:"☁ Cloud Based",
        badge3:"⚡ Real Time Data"
    },

    students:{
        image:"/static/images/student_preview.png",
        badge1:"👨‍🎓 Student Records",
        badge2:"📋 Admission Tracking",
        badge3:"🔍 Instant Search"
    },

    fees:{
        image:"/static/images/fees_preview.png",
        badge1:"💰 Fee Collection",
        badge2:"📈 Payment Reports",
        badge3:"🧾 Receipt Generation"
    },

    certificates:{
        image:"/static/images/certificate_preview.png",
        badge1:"📜 Bonafide",
        badge2:"🎓 TC Generation",
        badge3:"⚡ One Click Download"
    },

    reports:{
        image:"/static/images/report_preview.png",
        badge1:"📊 Analytics",
        badge2:"📈 Smart Reports",
        badge3:"🎯 Decision Insights"
    },

    staff:{
        image:"/static/images/staff_preview.png",
        badge1:"👩‍🏫 Staff Management",
        badge2:"📝 Attendance",
        badge3:"📋 Teacher Records"
    }

};

const tabs = document.querySelectorAll('.preview-tab');

tabs.forEach(tab=>{

    tab.addEventListener('click',()=>{

        tabs.forEach(t=>t.classList.remove('active'));

        tab.classList.add('active');

        const key = tab.dataset.tab;

        document.getElementById('previewImage').src =
        previewData[key].image;

        document.getElementById('badge1').textContent =
        previewData[key].badge1;

        document.getElementById('badge2').textContent =
        previewData[key].badge2;

        document.getElementById('badge3').textContent =
        previewData[key].badge3;

    });

});


// hero plans

function toggleBilling(type,btn){

    document
    .querySelectorAll('.billing-btn')
    .forEach(b=>b.classList.remove('active'));

    btn.classList.add('active');

    document
    .querySelectorAll('.amount')
    .forEach(price=>{

        price.innerText =
        '₹' +
        Number(
            type === 'monthly'
            ? price.dataset.month
            : price.dataset.year
        ).toLocaleString('en-IN');
    });

    document
    .querySelectorAll('.duration')
    .forEach(duration=>{

        duration.innerText =
        type === 'monthly'
        ? '/month'
        : '/year';
    });
}

//modal js

function openPlanModal(plan){

    // close mobile sidebar first

    if(typeof closeSidebar === "function"){
        closeSidebar();
    }

    document.getElementById(
        "planModal"
    ).style.display = "flex";

    document.getElementById(
        "selectedPlan"
    ).value = plan;

    document.getElementById(
        "selectedPlanDisplay"
    ).value = plan + " Plan";
}

function closePlanModal(){

    document.getElementById(
        "planModal"
    ).style.display="none";
}

function closeSuccessPopup(){

    document.getElementById(
        "successPopup"
    ).style.display="none";
}
// =====================================================
// 📞 SAVE LEAD FORM
// =====================================================

const leadForm =
document.getElementById("demoForm");

if (leadForm) {

    leadForm.addEventListener(
    "submit",

    async function (e) {

        e.preventDefault();

        const school =
        document.getElementById(
        "schoolName").value;

        const person =
        document.getElementById(
        "personName").value;

        const mobile =
        document.getElementById(
        "mobile").value;

        const email =
        document.getElementById(
        "email").value;

        const students =
        document.getElementById(
        "students").value;

        const plan =
        document.getElementById(
        "selectedPlan").value;

        const userMessage =
        document.getElementById(
        "message").value;

        try {

            const response =
            await fetch(
            "/submit-lead",

            {

                method: "POST",

                headers: {

                    "Content-Type":
                    "application/json"

                },

                body: JSON.stringify({

                    lead_source:
                    "Landing Page",

                    school_name:
                    school,

                    contact_person:
                    person,

                    mobile:
                    mobile,

                    email:
                    email,

                    student_strength:
                    students,

                    selected_plan:
                    plan,

                    message:
                    userMessage

                })

            });

            const result =
            await response.json();

            if (result.success) {

                // Close modal

                if (
                    typeof closePlanModal
                    === "function"
                ) {

                    closePlanModal();

                }

                // Show success popup

                const successPopup =
                document.getElementById(
                "successPopup"
                );

                if (successPopup) {

                    successPopup.style.display =
                    "flex";

                } else {

                    alert(
                    "Demo request submitted successfully!"
                    );

                }

                // Reset form

                leadForm.reset();

            }

            else {

                alert(

                    result.message ||

                    "Failed to save lead."

                );

            }

        }

        catch (error) {

            console.error(

                "LEAD ERROR:",
                error

            );

            alert(

                "Something went wrong. Please try again."

            );

        }

    });

}


// faq section js

document.querySelectorAll('.faq-question').forEach(btn => {

    btn.addEventListener('click', () => {

        const item = btn.parentElement;

        document.querySelectorAll('.faq-item').forEach(faq => {

            if(faq !== item){

                faq.classList.remove('active');

            }

        });

        item.classList.toggle('active');

    });

});