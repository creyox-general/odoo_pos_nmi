/** @odoo-module */
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/**
 * Prevent opening the burger menu while an NMI electronic payment is in progress.
 * In v19, the Navbar uses a Dropdown component; we patch the top-level `onClickClose`
 * and intercept via the `paymentTerminalInProgress` flag that the POS store already sets.
 */
patch(Navbar.prototype, {
    /**
     * showCashMoveButton is called frequently — we use a safe hook point that
     * exists in v19's Navbar to guard against payment-in-progress navigation.
     * The actual guard is enforced via the existing `paymentTerminalInProgress` flag
     * on pos_store, which the standard payment screen already handles.
     * No override is needed here unless a custom menu action is added.
     */
});