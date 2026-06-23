/** @odoo-module */
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(Navbar.prototype, {
    openMenu() {
        if (this.pos.payment_processing) {
            this.env.services.dialog.add(ConfirmationDialog, {
                title: _t("NMI Error"),
                body: _t("There is already an electronic payment in progress."),
            });
            return false;
        }
        return super.openMenu();
    },
});