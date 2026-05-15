// Toggle menu
document.querySelector(".menu-toggle").addEventListener("click", function () {
    document.getElementById("navLinks").classList.toggle("active");
});

// Close when clicking outside
document.addEventListener("click", function(e) {
    const menu = document.getElementById("navLinks");
    const toggle = document.querySelector(".menu-toggle");

    if (!menu.contains(e.target) && !toggle.contains(e.target)) {
        menu.classList.remove("active");
    }
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