document.addEventListener("DOMContentLoaded", function() {
    // Dashboard-аас ирсэн expired_count утгыг хайх (эсвэл API-аас fetch хийх)
    const expiredCount = document.getElementById('expired-count-data')?.textContent;
    
    if (expiredCount && parseInt(expiredCount) > 0) {
        // Sidebar дахь "Ерөнхий мэдээлэл" холбоосыг олох
        const navLinks = document.querySelectorAll('.nav-sidebar .nav-link');
        navLinks.forEach(link => {
            if (link.innerText.includes("Ерөнхий мэдээлэл")) {
                const badge = document.createElement('span');
                badge.className = 'badge badge-danger right pulse';
                badge.style.marginLeft = "10px";
                badge.innerText = expiredCount;
                link.appendChild(badge);
            }
        });
    }
});