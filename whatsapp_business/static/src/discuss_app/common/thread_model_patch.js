import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";

import { toRaw } from "@odoo/owl";

patch(Thread.prototype, {

    /** @param {string} name */
    async rename(name) {
        const newName = name.trim();
        if (
            newName !== this.displayName &&
            ((newName && this.channel_type === "channel") ||
                this.channel_type === "chat" || this.channel_type === "whatsapp" ||
                this.channel_type === "group")
        ) {
            if (this.channel_type === "channel" || this.channel_type === "group" || this.channel_type === "whatsapp") {
                this.name = newName;
                await this.store.env.services.orm.call(
                    "discuss.channel",
                    "channel_rename",
                    [[this.id]],
                    { name: newName }
                );
            } else if (this.channel_type === "chat") {
                this.custom_channel_name = newName;
                await this.store.env.services.orm.call(
                    "discuss.channel",
                    "channel_set_custom_name",
                    [[this.id]],
                    { name: newName }
                );
            }
        }
        return super.rename;
    },


    get importantCounter() {
        if (this.channel_type === "whatsapp") {
            return this.selfMember?.message_unread_counter || this.message_needaction_counter;
        }
        return super.importantCounter;
    },
    get autoOpenChatWindowOnNewMessage() {
        return this.channel_type === "whatsapp" || super.autoOpenChatWindowOnNewMessage;
    },
    get canLeave() {
        return this.channel_type !== "whatsapp" && super.canLeave;
    },
    get canUnpin() {
        if (this.channel_type === "whatsapp") {
            return this.importantCounter === 0;
        }
        return super.canUnpin;
    },

    get avatarUrl() {
        if (this.channel_type === "whatsapp" && this.correspondent) {
            return this.correspondent.persona.avatarUrl;
        }
        return super.avatarUrl;
    },

    get isChatChannel() {
        return this.channel_type === "whatsapp" || super.isChatChannel;
    },

    get whatsappChannelValidUntilDatetime() {
        if (!this.whatsapp_channel_valid_until) {
            return undefined;
        }
        return toRaw(deserializeDateTime(this.whatsapp_channel_valid_until));
    },
});
