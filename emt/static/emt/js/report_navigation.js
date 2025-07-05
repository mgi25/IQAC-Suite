document.addEventListener("DOMContentLoaded", () => {
    const pages = document.querySelectorAll(".report-page");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const submitBtn = document.querySelector(".submit-btn");
    const exportBtn = document.getElementById("exportPdfBtn");
    const form = document.getElementById("reportForm");
    const textareas = document.querySelectorAll("textarea");
    let currentPage = 0;
    function updatePage() {
        pages.forEach((pg, i) => {
            pg.classList.toggle("active", i === currentPage);
        });
        prevBtn.style.display = currentPage === 0 ? "none" : "inline-block";
        nextBtn.style.display = currentPage === pages.length - 1 ? "none" : "inline-block";
        submitBtn.style.display = currentPage === pages.length - 1 ? "inline-block" : "none";
    }

    nextBtn.addEventListener("click", () => {
        if (currentPage < pages.length - 1) {
            currentPage++;
            updatePage();
        }
    });

    prevBtn.addEventListener("click", () => {
        if (currentPage > 0) {
            currentPage--;
            updatePage();
        }
    });
    textareas.forEach(textarea => {
        const counter = textarea.nextElementSibling;
        const limit = parseInt(counter.dataset.limit);
        textarea.addEventListener("input", () => {
            const words = textarea.value.trim().split(/\s+/).filter(Boolean).length;
            counter.textContent = `${words} / ${limit} words`;
            if (words > limit) {
                counter.style.color = "red";
                textarea.setCustomValidity("Word limit exceeded.");
            } else {
                counter.style.color = "#65788b";
                textarea.setCustomValidity("");
            }
        });
    });
    exportBtn.addEventListener("click", () => {
        form.action = "/generate-report-pdf/";
        form.target = "_blank";
        form.submit();
        // Reset
        form.action = "";
        form.target = "";
    });
    updatePage();
});