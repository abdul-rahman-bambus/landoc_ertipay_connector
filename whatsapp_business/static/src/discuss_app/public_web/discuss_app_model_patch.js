/* @odoo-module */

import { DiscussApp } from "@mail/core/public_web/discuss_app_model";
import { Record } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
// very important functin for showing wh menu.
patch(DiscussApp, {
    new(data) {
        const res = super.new(data);
        res.whatsapp = {
            extraClass: "o-mail-DiscussSidebarCategory-whatsapp",
            icon: "fa fa-whatsapp",
            id: "whatsapp",
            name: _t("WhatsApp"),
           hideWhenEmpty: true,
            canView: false,
            canAdd: true,
            addTitle: _t("Search WhatsApp Channel"),
            serverStateKey: "is_discuss_sidebar_category_whatsapp_business_open",
            sequence: 20,
        };
        return res;
    },
});

patch(DiscussApp.prototype, {
    setup(env) {
        super.setup(env);
        this.whatsapp = Record.one("DiscussAppCategory");
    },
});
