document.addEventListener("DOMContentLoaded", () => {
const question = document.getElementById("question");
const charCount = document.getElementById("char-count");
const askButton = document.getElementById("ask-button");

function updateCount() {
    if (question && charCount) {
        charCount.textContent = question.value.length;
    }
}

if (question) {
    updateCount();
    question.addEventListener("input", updateCount);
}

const questionForm = question ? question.closest("form") : null;

if (questionForm && askButton) {
    questionForm.addEventListener("submit", (event) => {
        if (!question.value.trim()) {
            event.preventDefault();
            question.focus();
            return;
        }

        askButton.disabled = true;
        askButton.textContent = "Checking...";
    });
}

});
