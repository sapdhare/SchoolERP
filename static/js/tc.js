  
function setLanguage(lang) {

    // ===== BUTTON ACTIVE STATE =====
    const btnMr = document.getElementById("btn-mr");
    const btnEn = document.getElementById("btn-en");

    if (btnMr && btnEn) {
        btnMr.classList.remove("active");
        btnEn.classList.remove("active");

        if (lang === "en") {
            btnEn.classList.add("active");
        } else {
            btnMr.classList.add("active");
        }
    }

    // ===== SAVE LANGUAGE =====
    localStorage.setItem("tcLang", lang);


    if (lang === "en") {

        document.getElementById("tcTitle").innerText = "School Leaving Certificate";

        // HEADER
        document.getElementById("h1").innerText = "Management Name :- " + "{{ school_name }}";
        document.getElementById("h2").innerHTML = "School Name :- <strong>{{ school_name }}</strong>";
        document.getElementById("h3").innerText = "Address :- " + "{{ school_address }}";
        document.getElementById("h4").innerText = "Phone :- " + "{{ school_phone }}";
        document.getElementById("h5").innerText = "District :- " + "{{ school_address }}";
        document.getElementById("h6").innerText = "Email :- " + "{{ school_email }}";
        document.getElementById("h7").innerText = "UDISE :- " + "{{ school_udise }}";

        // BODY
        document.getElementById("l1").innerText = "Student ID :";
        document.getElementById("l2").innerText = "UID (Aadhaar No) :";
        document.getElementById("l3").innerText = "Student Name :";
        document.getElementById("l3a").innerText = "Father Name :";
        document.getElementById("l4").innerText = "Mother Name :";
        document.getElementById("l5").innerText = "Nationality :";
        document.getElementById("l6").innerText = "Mother Tongue :";
        document.getElementById("l7").innerText = "Religion :";
        document.getElementById("l8").innerText = "Caste :";
        document.getElementById("l9").innerText = "Birth Place :";
        document.getElementById("l10").innerText = "Taluka :";
        document.getElementById("l11").innerText = "District :";
        document.getElementById("l12").innerText = "State :";
        document.getElementById("l13").innerText = "Date of Birth :";
        document.getElementById("l14").innerText = "Previous School :";
        document.getElementById("l15").innerText = "Admission Date :";
        document.getElementById("l16").innerText = "Class :";
        document.getElementById("l17").innerText = "Progress :";
        document.getElementById("l18").innerText = "Conduct :";
        document.getElementById("l19").innerText = "Leaving Date :";
        document.getElementById("l21").innerText = "Reason for Leaving :";
        document.getElementById("l22").innerText = "Remark :";

        // FOOTER
        document.getElementById("f1").innerText = "Class Teacher";
        document.getElementById("f2").innerText = "Clerk";
        document.getElementById("f3").innerText = "Principal";

    } else {

        // ===== MARATHI =====
        document.getElementById("tcTitle").innerText = "शाळा सोडल्याचे प्रमाणपत्र";

        // HEADER
        document.getElementById("h1").innerText = "व्यवस्थापनाचे नाव :- " + "{{ school_name }}";
        document.getElementById("h2").innerHTML = "शाळेचे नाव :- <strong>{{ school_name }}</strong>";
        document.getElementById("h3").innerText = "पत्ता :- " + "{{ school_address }}";
        document.getElementById("h4").innerText = "फोन :- " + "{{ school_phone }}";
        document.getElementById("h5").innerText = "जिल्हा :- " + "{{ school_address }}";
        document.getElementById("h6").innerText = "ई-मेल :- " + "{{ school_email }}";
        document.getElementById("h7").innerText = "UDISE :- " + "{{ school_udise }}";

        // BODY
        document.getElementById("l1").innerText = "स्टुडंट आय डी :";
        document.getElementById("l2").innerText = "यू.आय.डी. नं. :";
        document.getElementById("l3").innerText = "विद्यार्थ्याचे नाव :";
        document.getElementById("l3a").innerText = "वडिलांचे नाव :";
        document.getElementById("l4").innerText = "आईचे नाव :";
        document.getElementById("l5").innerText = "राष्ट्रीयत्व :";
        document.getElementById("l6").innerText = "मातृभाषा :";
        document.getElementById("l7").innerText = "धर्म :";
        document.getElementById("l8").innerText = "जात :";
        document.getElementById("l9").innerText = "जन्मस्थळ :";
        document.getElementById("l10").innerText = "तालुका :";
        document.getElementById("l11").innerText = "जिल्हा :";
        document.getElementById("l12").innerText = "राज्य :";
        document.getElementById("l13").innerText = "जन्म दिनांक :";
        document.getElementById("l14").innerText = "मागील शाळा :";
        document.getElementById("l15").innerText = "प्रवेश दिनांक :";
        document.getElementById("l16").innerText = "इयत्ता :";
        document.getElementById("l17").innerText = "प्रगती :";
        document.getElementById("l18").innerText = "वर्तणूक :";
        document.getElementById("l19").innerText = "शाळा सोडल्याचा दिनांक :";
        document.getElementById("l21").innerText = "शाळा सोडल्याचे कारण :";
        document.getElementById("l22").innerText = "शेरा :";

        // FOOTER
        document.getElementById("f1").innerText = "वर्गशिक्षक";
        document.getElementById("f2").innerText = "लिपिक";
        document.getElementById("f3").innerText = "मुख्याध्यापक";
    }
}


// ===== AUTO LOAD SAVED LANGUAGE =====
window.onload = function () {
    const savedLang = localStorage.getItem("tcLang") || "mr";
    setLanguage(savedLang);
};


function printTC() {
    window.print();
}
 