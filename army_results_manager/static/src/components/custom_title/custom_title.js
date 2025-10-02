/** @odoo-module **/

import { registry } from "@web/core/registry";

export const customTitleService = {
    start() {
        const titleParts = {};

        function getParts() {
            return { ...titleParts };
        }

        function setParts(parts) {
            for (const key in parts) {
                const val = parts[key];
                if (!val) {
                    delete titleParts[key];
                } else {
                    titleParts[key] = val;
                }
            }
            const titles = Object.values(titleParts).filter(t => t !== "Odoo");
            document.title = titles.join(" - ");
        }

        return {
            get current() {
                return document.title;
            },
            getParts,
            setParts,
        };
    },
};

// Ghi đè service gốc
registry.category("services").add("title", customTitleService, { force: true });
