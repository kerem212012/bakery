document.querySelectorAll('select[name="filter_type"]').forEach((filterType) => {
    const form = filterType.form;
    const descriptionFields = form.querySelectorAll(
        '[name="description"], [name="description_en"]'
    );

    function updateDescriptionVisibility() {
        const showDescriptions = ["coating", "dough"].includes(filterType.value);
        descriptionFields.forEach((field) => {
            const wrapper = field.closest(".site-content-form-field, .form-row");
            if (wrapper) {
                wrapper.hidden = !showDescriptions;
                wrapper.style.display = showDescriptions ? "" : "none";
            }
        });
    }

    filterType.addEventListener("change", updateDescriptionVisibility);
    updateDescriptionVisibility();
});
