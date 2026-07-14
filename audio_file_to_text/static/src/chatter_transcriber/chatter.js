import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },

    async openTranscriber(){
        let record = this.env.model.config
        
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "audio.transcriber.wizard",
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
            context: {
                "res_id": record.resId,
                "res_model":record.resModel,
            }
        });
    }

});
