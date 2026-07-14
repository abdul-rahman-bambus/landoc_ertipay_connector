/* @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";


patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.state.is_whatsapp_btn = true;
    },

    popupWhatsapp() {
        return this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "chatter.preview",
                views: [[false, "form"]],
                target: "new",
                context: {
                    active_model: this.props.threadModel,
                    active_id: this.props.threadId,
                },
            },
            {
                onClose: result => Promise.resolve(result ?? null),
            }
        );
    },
});
