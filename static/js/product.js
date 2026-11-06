/* Product page: plus/minus buttons and a live total for the quantity.
   The real price is always worked out again on the server. */
(function () {
    "use strict";

    var input = document.getElementById("quantity");
    var totalOutput = document.getElementById("live-total");
    if (!input || !totalOutput) {
        return;
    }

    var price = parseFloat(input.getAttribute("data-price"));
    var min = parseInt(input.min, 10) || 1;
    var max = parseInt(input.max, 10) || 99;

    function clamp(value) {
        if (isNaN(value)) {
            return min;
        }
        return Math.min(Math.max(value, min), max);
    }

    function showTotal() {
        var quantity = clamp(parseInt(input.value, 10));
        totalOutput.textContent = "£" + (quantity * price).toFixed(2);
    }

    var stepButtons = document.querySelectorAll("[data-quantity-step]");
    Array.prototype.forEach.call(stepButtons, function (button) {
        button.addEventListener("click", function () {
            var step = parseInt(button.getAttribute("data-quantity-step"), 10);
            input.value = clamp(parseInt(input.value, 10) + step);
            showTotal();
        });
    });

    input.addEventListener("input", showTotal);
    showTotal();
}());