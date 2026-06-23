/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { rpc } from "@web/core/network/rpc";

console.log("PaymentNMI Class loaded");

export class PaymentNMI extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.paymentTerminalInProgress = false;
        this.currentTransaction = null;
        this.pollingActive = false;
        this.asyncStatusGuid = null;
        this.pollTimeout = null;
    }

    /**
     * Send payment request to NMI Cloud API
     * @param {string} uuid - The uuid of the paymentline
     */
    async sendPaymentRequest(uuid) {
        return this._process_nmi_payment(uuid);
    }

    /**
     * Cancel payment request (triggered when cashier clicks cancel/retry in POS UI)
     * @param {object} order - The current order
     * @param {string} uuid - The uuid of the paymentline
     */
    async sendPaymentCancel(order, uuid) {
        this._stopPolling();

        const line = order?.getSelectedPaymentline();
        if (line) {
            line.setPaymentStatus("retry");
            // Call backend terminate to cancel the in-progress device transaction
            try {
                await rpc("/pos/nmi/payment/terminate", {
                    payment_method_id: line.payment_method_id.id
                });
            } catch (err) {
                console.warn("Failed to terminate NMI transaction on device:", err);
            }
        }

        this._clearTransactionInProgress();
        return true;
    }

    /**
     * Reverse (void/refund) a completed payment
     * @param {string} uuid - The uuid of the paymentline
     */
    async sendPaymentReversal(uuid) {
        const order = this.pos.getOrder();
        const line = order.getPaymentlineByUuid(uuid);

        if (!line || !line.transaction_id) {
            this._showError(_t("No NMI Transaction ID found for voiding."));
            return false;
        }

        try {
            this._showNotification(_t("NMI Void"), _t("Processing void/refund request..."));

            // Call void_refund route on backend. Since voids are backend-to-backend, it's instant.
            const result = await rpc("/pos/nmi/payment/void_refund", {
                payment_method_id: line.payment_method_id.id,
                transaction_id: line.transaction_id,
                amount: Math.abs(line.amount),
                type: line.amount < 0 ? 'refund' : 'void'
            });

            if (result.status === 'Approved') {
                line.setPaymentStatus("reversed");
                this._showSuccessMessage(
                    _t("Transaction Voided"),
                    _t("Transaction has been successfully voided/refunded.")
                );
                return true;
            } else {
                const errorMsg = result.error || _t("Void request was declined.");
                this._showError(errorMsg, _t("NMI Void Error"));
                return false;
            }
        } catch (error) {
            console.error("NMI Void Exception:", error);
            this._showError(error.message || _t("Void transaction failed."));
            return false;
        }
    }

    /**
     * Close transaction in progress state
     */
    _clearTransactionInProgress() {
        this.pos.paymentTerminalInProgress = false;
        this.paymentTerminalInProgress = false;
        this.currentTransaction = null;
        this.asyncStatusGuid = null;
    }

    /**
     * Main payment processing function
     * @param {string} uuid - The uuid of the paymentline
     */
    async _process_nmi_payment(uuid) {
        const order = this.pos.getOrder();
        const line = order.getPaymentlineByUuid(uuid);

        if (!line) {
            return false;
        }

        // Prepare amount & transaction type
        const amount = line.amount;
        const reference = `NMI-${order.name}-${Date.now()}`;
        const transactionType = amount < 0 ? 'credit' : 'sale';
        const absAmount = Math.abs(amount);

        // Mark as in-progress in UI
        this.pos.paymentTerminalInProgress = true;
        this.paymentTerminalInProgress = true;
        line.setPaymentStatus("waitingCard");

        this._showNotification(_t("NMI Payment"), _t("Initiating cloud transaction..."));

        try {
            // Initiate transaction via backend route
            const result = await rpc("/pos/nmi/payment/initiate", {
                payment_method_id: line.payment_method_id.id,
                amount: absAmount,
                reference: reference,
                transaction_type: transactionType
            });

            if (result.error) {
                this._handleTransactionError(new Error(result.error), line);
                return false;
            }

            if (result.status === 'inFlight' && result.async_status_guid) {
                this.asyncStatusGuid = result.async_status_guid;
                this._showNotification(
                    _t("NMI Payment"),
                    _t("Please insert, swipe, or tap card on the terminal.")
                );

                // Start status polling loop
                return await this._pollTransactionStatus(line);
            } else {
                this._handleTransactionError(new Error(_t("Unexpected initiation response from gateway")), line);
                return false;
            }

        } catch (error) {
            this._handleTransactionError(error, line);
            return false;
        }
    }

    /**
     * Poll NMI transaction status until complete, cancelled, or timed out
     */
    async _pollTransactionStatus(line) {
        this.pollingActive = true;
        const pollIntervalMs = 2000; // poll every 2 seconds

        const checkStatus = async () => {
            if (!this.pollingActive || !this.asyncStatusGuid) {
                return false;
            }

            try {
                const result = await rpc("/pos/nmi/payment/poll", {
                    payment_method_id: line.payment_method_id.id,
                    async_status_guid: this.asyncStatusGuid
                });

                if (result.error) {
                    this._handleTransactionError(new Error(result.error), line);
                    return false;
                }

                if (result.status === 'inFlight') {
                    // Update user feedback and schedule next poll
                    this._showNotification(_t("NMI Payment"), result.message || _t("Waiting for card..."));
                    return new Promise((resolve) => {
                        this.pollTimeout = setTimeout(() => {
                            resolve(checkStatus());
                        }, pollIntervalMs);
                    });
                } else if (result.status === 'Approved') {
                    this._stopPolling();
                    this._clearTransactionInProgress();

                    // Update payment line fields
                    line.setPaymentStatus("done");
                    line.nmi_reference = result.transaction_id;
                    line.transaction_id = result.transaction_id;
                    line.transaction_auth_code = result.auth_code;
                    line.primary_acc_number = result.primary_acc_number;
                    line.transaction_date = result.transaction_date;
                    line.card_name = result.card_name;

                    this._showSuccessMessage(
                        _t("Payment Approved"),
                        _t("Transaction completed successfully. Auth: %s", result.auth_code)
                    );
                    return true;
                } else if (result.status === 'Declined') {
                    this._stopPolling();
                    this._handleTransactionError(new Error(result.error || _t("Transaction was declined.")), line);
                    return false;
                } else if (result.status === 'Cancelled') {
                    this._stopPolling();
                    this._handleTransactionError(new Error(result.error || _t("Transaction was cancelled.")), line);
                    return false;
                } else {
                    this._stopPolling();
                    this._handleTransactionError(new Error(result.error || _t("Payment error occurred.")), line);
                    return false;
                }

            } catch (err) {
                // If RPC fails, we still continue polling unless explicitly stopped, to handle network hiccups.
                console.warn("Error during NMI status poll:", err);
                return new Promise((resolve) => {
                    this.pollTimeout = setTimeout(() => {
                        resolve(checkStatus());
                    }, pollIntervalMs);
                });
            }
        };

        return checkStatus();
    }

    _stopPolling() {
        this.pollingActive = false;
        if (this.pollTimeout) {
            clearTimeout(this.pollTimeout);
            this.pollTimeout = null;
        }
    }

    _handleTransactionError(error, line) {
        this._stopPolling();
        this._clearTransactionInProgress();
        line.setPaymentStatus("retry");
        this._showError(error.message || _t("Payment transaction failed."));
    }

    _showError(errorMsg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("NMI Payment Error"),
            body: errorMsg,
        });
    }

    _showSuccessMessage(title, message) {
        this.env.services.notification.add(message, {
            title: title,
            type: 'success',
            sticky: false,
        });
    }

    _showNotification(title, message) {
        this.env.services.notification.add(message, {
            title: title,
            type: 'info',
            sticky: false,
        });
    }

    // Fast payments not supported (camelCase for v19)
    get fastPayments() {
        return false;
    }
}