// student modal js
function openModal(button) {

    const val = (v) => v && v.trim() !== "" ? v : "-";

    document.getElementById("studentModal").style.display = "flex";

    document.getElementById("mRegister").innerText = val(button.dataset.register);
    document.getElementById("mName").innerText = val(button.dataset.name);
    document.getElementById("mClass").innerText = val(button.dataset.class);
    document.getElementById("mAdmission").innerText = val(button.dataset.admission);
    document.getElementById("mMobile").innerText = val(button.dataset.mobile);

    document.getElementById("mFather").innerText = val(button.dataset.father);
    document.getElementById("mMother").innerText = val(button.dataset.mother);
    document.getElementById("mStudentUid").innerText = val(button.dataset.uid);

    document.getElementById("mApaar").innerText = val(button.dataset.apaar);
    document.getElementById("mAadhaar").innerText = val(button.dataset.aadhaar);
    document.getElementById("mDob").innerText = val(button.dataset.dob);

    document.getElementById("mProgress").innerText = val(button.dataset.progress);
    document.getElementById("mConduct").innerText = val(button.dataset.conduct);
}

function closeModal() {
    document.getElementById("studentModal").style.display = "none";
}

/* ================= SEARCH + FILTER JS ================= */

const searchInput = document.getElementById("searchInput");
const classFilter = document.getElementById("classFilter");
const rows = document.querySelectorAll(".students-table tbody tr");

// SEARCH + FILTER FUNCTION
function filterTable() {

    const searchValue = searchInput.value.toLowerCase();
    const classValue = classFilter.value;

    rows.forEach(row => {

        const register = row.children[0].innerText.toLowerCase();
        const name = row.children[1].innerText.toLowerCase();
        const cls = row.children[2].innerText;
        const admission = row.children[3].innerText.toLowerCase();
        const studentUid = row.children[4].innerText.toLowerCase();

const matchSearch =
    register.includes(searchValue) ||
    name.includes(searchValue) ||
    admission.includes(searchValue) ||
    studentUid.includes(searchValue);

        const matchClass =
            classValue === "" || cls === classValue;

        if (matchSearch && matchClass) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }

    });
}

// EVENTS
searchInput.addEventListener("keyup", filterTable);
classFilter.addEventListener("change", filterTable);

// RESET BUTTON
document.getElementById("resetFilter").addEventListener("click", function() {
    searchInput.value = "";
    classFilter.value = "";
    filterTable();
});