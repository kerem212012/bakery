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

            name.name = `product_${index}_name`;
            name.id = `id_product_${index}_name`;
            name.labels[0].htmlFor = name.id;
            nameEn.name = `product_${index}_name_en`;
            nameEn.id = `id_product_${index}_name_en`;
            nameEn.labels[0].htmlFor = nameEn.id;
            price.name = index === 0 ? "base_unit_price" : `product_${index}_base_price`;
            price.id = `id_${price.name}`;
            price.labels[0].htmlFor = price.id;

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
