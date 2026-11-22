(() => {
    const editor = document.querySelector("[data-product-editor]");
    const template = document.querySelector("#calculator-product-row-template");
    const addButton = document.querySelector("[data-add-product]");
    const countInput = document.querySelector("#id_product_count");

    if (!editor || !template || !addButton || !countInput) {
        return;
    }

    const maximumProducts = 30;

    function reindexRows() {
        const rows = [...editor.querySelectorAll("[data-product-row]")];
        rows.forEach((row, index) => {
            row.dataset.productIndex = index;
            const name = row.querySelector("[data-product-name]");
            const nameEn = row.querySelector("[data-product-name-en]");
            const price = row.querySelector("[data-product-price]");
            const image = row.querySelector("[data-product-image]");
            const originalValue = row.querySelector("[data-product-original-value]");

            name.name = `product_${index}_name`;
            name.id = `id_product_${index}_name`;
            name.labels[0].htmlFor = name.id;
            nameEn.name = `product_${index}_name_en`;
            nameEn.id = `id_product_${index}_name_en`;
            nameEn.labels[0].htmlFor = nameEn.id;
            price.name = index === 0 ? "base_unit_price" : `product_${index}_base_price`;
            price.id = `id_${price.name}`;
            price.labels[0].htmlFor = price.id;
            image.name = `product_${index}_image`;
            image.id = `id_${image.name}`;
            image.labels[0].htmlFor = image.id;
            originalValue.name = `product_${index}_original_value`;
            originalValue.id = `id_${originalValue.name}`;

            const removeButton = row.querySelector("[data-remove-product]");
            removeButton.hidden = index === 0;
        });

        countInput.value = String(rows.length);
        addButton.disabled = rows.length >= maximumProducts;
    }

    addButton.addEventListener("click", () => {
        const rows = editor.querySelectorAll("[data-product-row]");
        if (rows.length >= maximumProducts) {
            return;
        }

        const index = rows.length;
        const row = template.content.firstElementChild.cloneNode(true);
        row.innerHTML = row.innerHTML.replaceAll("__prefix__", String(index));
        editor.append(row);
        reindexRows();
        row.querySelector("[data-product-name]").focus();
    });

    editor.addEventListener("click", (event) => {
        const removeButton = event.target.closest("[data-remove-product]");
        if (!removeButton || editor.querySelectorAll("[data-product-row]").length <= 1) {
            return;
        }

        removeButton.closest("[data-product-row]").remove();
        reindexRows();
    });

    reindexRows();
})();

(() => {
    const template = document.querySelector("#calculator-option-row-template");
    const maximumOptions = 30;

    document.querySelectorAll("[data-option-editor]").forEach((editor) => {
        const group = editor.dataset.optionGroup;
        const section = editor.closest(".calculator-option-image-section");
        const countInput = section.querySelector("[data-option-count]");
        const addButton = section.querySelector("[data-add-option]");

        if (!group || !countInput || !addButton || !template) {
            return;
        }

        function reindexRows() {
            const rows = [...editor.querySelectorAll("[data-option-row]")];
            rows.forEach((row, index) => {
                row.querySelectorAll("[data-option-input]").forEach((input) => {
                    const kind = input.dataset.optionInput;
                    const name = kind === "image"
                        ? `option_image_${group}_${index}`
                        : `option_${group}_${index}_${kind.replace("-", "_")}`;
                    input.name = name;
                    input.id = `id_${name}`;
                    const field = input.closest(".site-content-form-field");
                    const label = field ? field.querySelector("label") : null;
                    if (label) {
                        label.htmlFor = input.id;
                    }
                    if (kind === "image" && field) {
                        const clearInput = field.querySelector(
                            'input[type="checkbox"][name$="-clear"]'
                        );
                        if (clearInput) {
                            clearInput.name = `${name}-clear`;
                            clearInput.id = `${input.id}-clear_id`;
                            field.querySelectorAll("label").forEach((clearLabel) => {
                                if (clearLabel.htmlFor.endsWith("_clear_id")) {
                                    clearLabel.htmlFor = clearInput.id;
                                }
                            });
                        }
                    }
                });

                const removeButton = row.querySelector("[data-remove-option]");
                removeButton.hidden = rows.length <= 1;
            });

            countInput.value = String(rows.length);
            addButton.disabled = rows.length >= maximumOptions;
        }

        addButton.addEventListener("click", () => {
            const rows = editor.querySelectorAll("[data-option-row]");
            if (rows.length >= maximumOptions) {
                return;
            }

            const row = template.content.firstElementChild.cloneNode(true);
            row.innerHTML = row.innerHTML
                .replaceAll("__group__", group)
                .replaceAll("__prefix__", String(rows.length));
            if (group === "shapes") {
                const extraField = row.querySelector("[data-option-extra-field]");
                if (extraField) {
                    extraField.remove();
                }
            }
            editor.append(row);
            reindexRows();
            row.querySelector('[data-option-input="label"]').focus();
        });

        editor.addEventListener("click", (event) => {
            const removeButton = event.target.closest("[data-remove-option]");
            if (!removeButton) {
                return;
            }

            removeButton.closest("[data-option-row]").remove();
            reindexRows();
        });

        reindexRows();
    });
})();
