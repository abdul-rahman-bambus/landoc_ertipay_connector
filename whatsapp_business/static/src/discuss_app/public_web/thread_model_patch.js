import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

// Main Functionality... without computeDiscussAppCategory it will not short listed.

patch(Thread.prototype, {
    _computeDiscussAppCategory() {
        return this.channel_type === "whatsapp"
            ? this.store.discuss.whatsapp
            : super._computeDiscussAppCategory();
    },
});
