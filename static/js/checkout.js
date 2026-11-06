/* Shows progress and stops double clicks on forms marked data-busy-message. */
(function () {
    "use strict";

    var forms = document.querySelectorAll("form[data-busy-message]");

    Array.prototype.forEach.call(forms, function (form) {
        form.addEventListener("submit", function () {
            var button = form.querySelector("button[type='submit']");
            if (button) {
                button.disabled = true;
                button.textContent = form.getAttribute("data-busy-message");
            }
        });
    });
}());