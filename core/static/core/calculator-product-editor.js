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
            const sizes = row.querySelector("[data-product-sizes]");
            const modifiers = row.querySelector("[data-product-modifiers]");
            const leadTimeRules = row.querySelector("[data-product-lead-time-rules]");

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
            sizes.name = `product_${index}_sizes_json`;
            sizes.id = `id_${sizes.name}`;
            modifiers.name = `product_${index}_modifier_groups_json`;
            modifiers.id = `id_${modifiers.name}`;
            leadTimeRules.name = `product_${index}_lead_time_rules_json`;
            leadTimeRules.id = `id_${leadTimeRules.name}`;

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
        row.dispatchEvent(new CustomEvent("calculator-product-added", { bubbles: true }));
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
    const english = document.documentElement.lang === "en";
    const labels = english
        ? {
            size: "Size value", sizeLabel: "Size label", price: "Base price (RUB)",
            group: "Group value", groupLabel: "Group name (Russian)",
            groupLabelEn: "Group name (English)", option: "Option value",
            optionLabel: "Option name (Russian)", optionLabelEn: "Option name (English)",
            amount: "Price addition", amountType: "Price type", fixed: "RUB",
            percent: "%", addOption: "Add option", remove: "Delete",
            leadTimeCoating: "Coating", selectCoating: "Select coating",
            minQuantity: "Minimum quantity", leadTimeDays: "Production time (days)",
            paymentValue: "Payment value", paymentLabel: "Name (Russian)",
            paymentLabelEn: "Name (English)", discountValue: "Rule value",
            trigger: "Trigger", quantity: "Minimum quantity", payment: "Payment method",
            triggerValue: "Trigger value", percentDiscount: "Percent (%)",
        }
        : {
            size: "Значение размера", sizeLabel: "Название размера", price: "Базовая цена (₽)",
            group: "Значение группы", groupLabel: "Название группы (русский)",
            groupLabelEn: "Название группы (английский)", option: "Значение опции",
            optionLabel: "Название опции (русский)", optionLabelEn: "Название опции (английский)",
            amount: "Доплата", amountType: "Тип цены", fixed: "₽",
            percent: "%", addOption: "Добавить опцию", remove: "Удалить",
            leadTimeCoating: "Покрытие", selectCoating: "Выберите покрытие",
            minQuantity: "Минимальное количество", leadTimeDays: "Срок изготовления (дней)",
            paymentValue: "Значение способа оплаты", paymentLabel: "Название (русский)",
            paymentLabelEn: "Название (английский)", discountValue: "Значение правила",
            trigger: "Условие", quantity: "Минимальное количество", payment: "Способ оплаты",
            triggerValue: "Значение условия", percentDiscount: "Скидка (%)",
        };

    function field(container, label, value, type = "text", onChange = null, minimum = 0) {
        const wrapper = document.createElement("div");
        wrapper.className = "site-content-form-field";
        const labelElement = document.createElement("label");
        labelElement.textContent = label;
        const input = document.createElement("input");
        input.className = "site-content-form-control";
        input.type = type;
        input.value = value ?? "";
        if (type === "number") {
            input.min = String(minimum);
            input.step = "0.01";
        }
        labelElement.htmlFor = `calculator-config-${Math.random().toString(36).slice(2)}`;
        input.id = labelElement.htmlFor;
        if (onChange) {
            input.addEventListener("input", onChange);
        }
        wrapper.append(labelElement, input);
        container.append(wrapper);
        return input;
    }

    function removeButton(container, onRemove) {
        const button = document.createElement("button");
        button.className = "admin-dashboard-site-link";
        button.type = "button";
        button.textContent = labels.remove;
        button.addEventListener("click", onRemove);
        container.append(button);
    }

    function initializeProductPricing(editor) {
        if (editor.dataset.initialized) {
            return;
        }
        editor.dataset.initialized = "true";
        const row = editor.closest("[data-product-row]");
        const sizesInput = row.querySelector("[data-product-sizes]");
        const groupsInput = row.querySelector("[data-product-modifiers]");
        const leadTimeInput = row.querySelector("[data-product-lead-time-rules]");
        const sizesList = editor.querySelector("[data-sizes-list]");
        const groupsList = editor.querySelector("[data-modifier-groups-list]");
        const leadTimeRulesList = editor.querySelector("[data-lead-time-rules-list]");
        const read = (input) => {
            try {
                const value = JSON.parse(input.value || "[]");
                return Array.isArray(value) ? value : [];
            } catch {
                return [];
            }
        };
        let sizes = read(sizesInput);
        let groups = read(groupsInput);
        let leadTimeRules = read(leadTimeInput);
        const save = () => {
            sizesInput.value = JSON.stringify(sizes);
            groupsInput.value = JSON.stringify(groups);
            leadTimeInput.value = JSON.stringify(leadTimeRules);
        };

        function renderSizes() {
            sizesList.replaceChildren();
            sizes.forEach((size, index) => {
                const card = document.createElement("article");
                card.className = "calculator-option-image-card";
                const changed = () => save();
                field(card, labels.size, size.value, "text", (event) => {
                    size.value = event.target.value;
                    changed();
                });
                field(card, labels.sizeLabel, size.label, "text", (event) => {
                    size.label = event.target.value;
                    changed();
                });
                field(card, labels.price, size.base_price, "number", (event) => {
                    size.base_price = event.target.value;
                    changed();
                });
                removeButton(card, () => {
                    sizes.splice(index, 1);
                    renderSizes();
                    save();
                });
                sizesList.append(card);
            });
        }

        function renderGroups() {
            groupsList.replaceChildren();
            groups.forEach((group, groupIndex) => {
                const card = document.createElement("article");
                card.className = "calculator-option-image-card";
                const changed = () => save();
                field(card, labels.group, group.value, "text", (event) => {
                    group.value = event.target.value;
                    changed();
                    renderLeadTimeRules();
                });
                field(card, labels.groupLabel, group.label, "text", (event) => {
                    group.label = event.target.value;
                    changed();
                    renderLeadTimeRules();
                });
                field(card, labels.groupLabelEn, group.label_en, "text", (event) => {
                    group.label_en = event.target.value;
                    changed();
                    renderLeadTimeRules();
                });
                const optionsList = document.createElement("div");
                optionsList.className = "calculator-option-image-grid";
                (group.options || []).forEach((option, optionIndex) => {
                    const optionCard = document.createElement("div");
                    optionCard.className = "calculator-option-image-card";
                    field(optionCard, labels.option, option.value, "text", (event) => {
                        option.value = event.target.value;
                        changed();
                        renderLeadTimeRules();
                    });
                    field(optionCard, labels.optionLabel, option.label, "text", (event) => {
                        option.label = event.target.value;
                        changed();
                    });
                    field(optionCard, labels.optionLabelEn, option.label_en, "text", (event) => {
                        option.label_en = event.target.value;
                        changed();
                    });
                    field(
                        optionCard,
                        labels.amount,
                        option.amount,
                        "number",
                        (event) => {
                            option.amount = event.target.value;
                            changed();
                        },
                        -1000000000,
                    );
                    const typeWrapper = document.createElement("div");
                    typeWrapper.className = "site-content-form-field";
                    const typeLabel = document.createElement("label");
                    typeLabel.textContent = labels.amountType;
                    const typeSelect = document.createElement("select");
                    typeSelect.className = "site-content-form-control";
                    [[labels.fixed, "fixed"], [labels.percent, "percent"]].forEach(([text, value]) => {
                        const optionElement = document.createElement("option");
                        optionElement.value = value;
                        optionElement.textContent = text;
                        typeSelect.append(optionElement);
                    });
                    typeSelect.value = option.amount_type || "fixed";
                    typeSelect.addEventListener("change", () => {
                        option.amount_type = typeSelect.value;
                        changed();
                    });
                    typeWrapper.append(typeLabel, typeSelect);
                    optionCard.append(typeWrapper);
                    removeButton(optionCard, () => {
                        group.options.splice(optionIndex, 1);
                        renderGroups();
                        save();
                    });
                    optionsList.append(optionCard);
                });
                const addOption = document.createElement("button");
                addOption.className = "admin-dashboard-site-link";
                addOption.type = "button";
                addOption.textContent = labels.addOption;
                addOption.addEventListener("click", () => {
                    group.options = group.options || [];
                    group.options.push({
                        value: "", label: "", label_en: "", amount: "0", amount_type: "fixed",
                    });
                    renderGroups();
                    renderLeadTimeRules();
                    save();
                });
                card.append(optionsList, addOption);
                removeButton(card, () => {
                    groups.splice(groupIndex, 1);
                    renderGroups();
                    renderLeadTimeRules();
                    save();
                });
                groupsList.append(card);
            });
        }

        function renderLeadTimeRules() {
            if (!leadTimeRulesList) {
                return;
            }
            leadTimeRulesList.replaceChildren();
            const coatingGroup = groups.find((group) => (
                ["coating", "coatings"].includes(String(group.value || "").trim().toLowerCase())
                || String(group.label || "").trim().toLowerCase() === "покрытие"
                || String(group.label_en || "").trim().toLowerCase() === "coating"
            ));
            const coatingOptions = (coatingGroup?.options || []).map((option) => ({
                value: option.value,
                label: english
                    ? (option.label_en || option.label)
                    : (option.label || option.label_en),
            }));
            leadTimeRules.forEach((rule, index) => {
                const card = document.createElement("article");
                card.className = "calculator-option-image-card";
                const coatingWrapper = document.createElement("div");
                coatingWrapper.className = "site-content-form-field";
                const coatingLabel = document.createElement("label");
                coatingLabel.textContent = labels.leadTimeCoating;
                const coatingSelect = document.createElement("select");
                coatingSelect.className = "site-content-form-control";
                const placeholder = document.createElement("option");
                placeholder.value = "";
                placeholder.textContent = labels.selectCoating;
                coatingSelect.append(placeholder);
                coatingOptions.forEach((coating) => {
                    const option = document.createElement("option");
                    option.value = coating.value;
                    option.textContent = coating.label;
                    coatingSelect.append(option);
                });
                if (
                    rule.coating_value
                    && !coatingOptions.some((option) => option.value === rule.coating_value)
                ) {
                    const missingOption = document.createElement("option");
                    missingOption.value = rule.coating_value;
                    missingOption.textContent = `${rule.coating_value} (missing)`;
                    coatingSelect.append(missingOption);
                }
                coatingSelect.value = rule.coating_value || "";
                coatingLabel.htmlFor = `calculator-lead-coating-${row.dataset.productIndex}-${index}`;
                coatingSelect.id = coatingLabel.htmlFor;
                coatingSelect.addEventListener("change", () => {
                    rule.coating_value = coatingSelect.value;
                    save();
                });
                coatingWrapper.append(coatingLabel, coatingSelect);
                const minQuantity = field(card, labels.minQuantity, rule.min_quantity, "number", (event) => {
                    rule.min_quantity = event.target.value;
                    save();
                }, 1);
                minQuantity.step = "1";
                minQuantity.max = "10000";
                const days = field(card, labels.leadTimeDays, rule.days, "number", (event) => {
                    rule.days = event.target.value;
                    save();
                }, 1);
                days.step = "1";
                days.max = "365";
                card.prepend(coatingWrapper);
                removeButton(card, () => {
                    leadTimeRules.splice(index, 1);
                    renderLeadTimeRules();
                    save();
                });
                leadTimeRulesList.append(card);
            });
        }

        editor.querySelector("[data-add-size]").addEventListener("click", () => {
            sizes.push({ value: "", label: "", base_price: "0" });
            renderSizes();
            save();
        });
        editor.querySelector("[data-add-modifier-group]").addEventListener("click", () => {
            groups.push({
                value: "", label: "", label_en: "",
                options: [{ value: "", label: "", label_en: "", amount: "0", amount_type: "fixed" }],
            });
            renderGroups();
            renderLeadTimeRules();
            save();
        });
        editor.querySelector("[data-add-lead-time-rule]").addEventListener("click", () => {
            if (leadTimeRules.length >= 100) {
                return;
            }
            leadTimeRules.push({ coating_value: "", min_quantity: "1", days: "1" });
            renderLeadTimeRules();
            save();
        });
        renderSizes();
        renderGroups();
        renderLeadTimeRules();
    }

    document.querySelectorAll("[data-product-pricing]").forEach(initializeProductPricing);
    document.addEventListener("calculator-product-added", (event) => {
        const editor = event.target.querySelector("[data-product-pricing]");
        if (editor) {
            initializeProductPricing(editor);
        }
    });

    document.querySelectorAll("[data-configuration-editor]").forEach((editor) => {
        const key = editor.dataset.configurationEditor;
        const hidden = editor.querySelector('input[type="hidden"]');
        const list = editor.querySelector("[data-configuration-items]");
        let entries = [];
        try {
            entries = JSON.parse(hidden.value || "[]");
        } catch {
            entries = [];
        }
        const sync = () => { hidden.value = JSON.stringify(entries); };
        const isPayment = key === "payment_methods";
        function renderEntries() {
            list.replaceChildren();
            entries.forEach((entry, index) => {
            const card = document.createElement("article");
            card.className = "calculator-option-image-card";
            const onInput = () => sync();
            if (isPayment) {
                field(card, labels.paymentValue, entry.value, "text", (event) => { entry.value = event.target.value; onInput(); });
                field(card, labels.paymentLabel, entry.label, "text", (event) => { entry.label = event.target.value; onInput(); });
                field(card, labels.paymentLabelEn, entry.label_en, "text", (event) => { entry.label_en = event.target.value; onInput(); });
            } else {
                field(card, labels.discountValue, entry.value, "text", (event) => { entry.value = event.target.value; onInput(); });
                field(card, labels.paymentLabel, entry.label, "text", (event) => { entry.label = event.target.value; onInput(); });
                field(card, labels.paymentLabelEn, entry.label_en, "text", (event) => { entry.label_en = event.target.value; onInput(); });
                const triggerWrapper = document.createElement("div");
                triggerWrapper.className = "site-content-form-field";
                const triggerLabel = document.createElement("label");
                triggerLabel.textContent = labels.trigger;
                const triggerSelect = document.createElement("select");
                triggerSelect.className = "site-content-form-control";
                [[labels.quantity, "quantity"], [labels.payment, "payment"]].forEach(([text, value]) => {
                    const option = document.createElement("option");
                    option.value = value;
                    option.textContent = text;
                    triggerSelect.append(option);
                });
                triggerSelect.value = entry.trigger || "quantity";
                triggerSelect.addEventListener("change", () => { entry.trigger = triggerSelect.value; onInput(); });
                triggerWrapper.append(triggerLabel, triggerSelect);
                card.append(triggerWrapper);
                field(card, entry.trigger === "payment" ? labels.payment : labels.quantity, entry.trigger_value, "text", (event) => { entry.trigger_value = event.target.value; onInput(); });
                field(card, labels.amount, entry.amount, "number", (event) => { entry.amount = event.target.value; onInput(); });
                const amountType = document.createElement("select");
                amountType.className = "site-content-form-control";
                [["RUB", "fixed"], [labels.percentDiscount, "percent"]].forEach(([text, value]) => {
                    const option = document.createElement("option");
                    option.value = value;
                    option.textContent = text;
                    amountType.append(option);
                });
                amountType.value = entry.amount_type || "percent";
                amountType.addEventListener("change", () => { entry.amount_type = amountType.value; onInput(); });
                card.append(amountType);
            }
            removeButton(card, () => { entries.splice(index, 1); card.remove(); sync(); });
            list.append(card);
            });
        }
        renderEntries();
        editor.querySelector("[data-add-configuration-item]").addEventListener("click", () => {
            entries.push(isPayment
                ? { value: "", label: "", label_en: "" }
                : { value: "", label: "", label_en: "", trigger: "quantity", trigger_value: "", amount_type: "percent", amount: "0" });
            renderEntries();
            sync();
        });
        sync();
    });
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
