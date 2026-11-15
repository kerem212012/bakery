(() => {
    const form = document.getElementById("registration-form");
    const selector = form?.querySelector("[data-tax-identifier-type]");
    if (!selector) return;

    const fields = form.querySelectorAll("[data-tax-identifier-field]");

    const updateIdentifierField = () => {
        fields.forEach((field) => {
            const input = field.querySelector("input");
            const isSelected = field.dataset.taxIdentifierField === selector.value;

            field.hidden = !isSelected;
            input.disabled = !isSelected;
            input.required = isSelected;
        });
    };

    selector.addEventListener("change", updateIdentifierField);
    updateIdentifierField();
})();
