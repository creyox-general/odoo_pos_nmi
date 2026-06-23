/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

console.log("Enhanced POS Store patch loaded");

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);

        // Initialize terminal data
        this.pos_terminals = (this.models["pos.terminal"] && Array.isArray(this.models["pos.terminal"].records))
        ? this.models["pos.terminal"].records
        : [];
        this.pos_terminal_by_id = {};

        // Create terminal lookup
        for (const terminal of this.pos_terminals) {
            this.pos_terminal_by_id[terminal.id] = terminal;
        }

        console.log("Initialized terminals:", this.pos_terminals.length);
        console.log("Terminal lookup:", this.pos_terminal_by_id);

        // Initialize NMI payment processing state
        this.nmi_payment_status = 'ready'; // ready, processing, error
        this.nmi_current_transaction = null;

        // Setup NMI event listeners if needed
        this.setupNMIEventHandlers();
    },

    /**
     * Setup NMI-specific event handlers
     */
    setupNMIEventHandlers() {
        // Listen for payment terminal availability changes
        this.env.bus.addEventListener('nmi_terminal_status_changed', (event) => {
            this.handleTerminalStatusChange(event.detail);
        });

        // Listen for transaction updates
        this.env.bus.addEventListener('nmi_transaction_update', (event) => {
            this.handleTransactionUpdate(event.detail);
        });
    },

    /**
     * Handle terminal status changes
     */
    handleTerminalStatusChange(statusData) {
        const terminalId = statusData.terminal_id;
        const terminal = this.pos_terminal_by_id[terminalId];

        if (terminal) {
            terminal.device_status = statusData.status;
            terminal.last_test_result = statusData.message;
            terminal.last_test_date = new Date().toISOString();

            console.log(`Terminal ${terminal.name} status changed to: ${statusData.status}`);
        }
    },

    /**
     * Handle transaction updates
     */
    handleTransactionUpdate(updateData) {
        this.nmi_current_transaction = updateData;

        // Trigger UI updates if needed
        if (updateData.status === 'completed') {
            this.nmi_payment_status = 'ready';
            this.nmi_current_transaction = null;
        } else if (updateData.status === 'error') {
            this.nmi_payment_status = 'error';
        }

        console.log("Transaction update:", updateData);
    },

    /**
     * Get terminal by payment method
     */
    getTerminalByPaymentMethod(paymentMethodId) {
        const paymentMethod = this.payment_methods_by_id[paymentMethodId];
        if (paymentMethod && paymentMethod.pos_terminal_id) {
            return this.pos_terminal_by_id[paymentMethod.pos_terminal_id[0]];
        }
        return null;
    },

    /**
     * Get all NMI payment methods
     */
    getNMIPaymentMethods() {
        return this.payment_methods.filter(pm => pm.use_payment_terminal === 'nmi');
    },

    /**
     * Check if any NMI terminal is available
     */
    hasAvailableNMITerminal() {
        const nmiPaymentMethods = this.getNMIPaymentMethods();

        for (const pm of nmiPaymentMethods) {
            const terminal = this.getTerminalByPaymentMethod(pm.id);
            if (terminal && terminal.device_status === 'available' && terminal.active) {
                return true;
            }
        }

        return false;
    },

    /**
     * Get NMI terminal configuration for payment method
     */
    getNMITerminalConfig(paymentMethodId) {
        const paymentMethod = this.payment_methods_by_id[paymentMethodId];
        const terminal = this.getTerminalByPaymentMethod(paymentMethodId);

        if (!paymentMethod || !terminal) {
            return null;
        }

        return {
            payment_method: {
                id: paymentMethod.id,
                name: paymentMethod.name,
                nmi_server_url: paymentMethod.nmi_server_url,
                nmi_timeout: paymentMethod.nmi_timeout,
                nmi_auto_confirm: paymentMethod.nmi_auto_confirm,
                nmi_tipping_support: paymentMethod.nmi_tipping_support,
                nmi_print_receipt: paymentMethod.nmi_print_receipt,
            },
            terminal: {
                id: terminal.id,
                name: terminal.name,
                device_id: terminal.device_id,
                device_model: terminal.device_model,
                connection_type: terminal.connection_type,
                server_address: terminal.server_address,
                server_port: terminal.server_port,
                api_key: terminal.api_key,
                environment: terminal.environment,
                ip_address: terminal.ip_address,
                tcp_port: terminal.tcp_port,
                com_port: terminal.com_port,
                baudrate: terminal.baudrate,
                timeout: terminal.timeout,
                auto_confirm: terminal.auto_confirm,
            }
        };
    },

    /**
     * Validate NMI payment method configuration
     */
    validateNMIPaymentMethod(paymentMethodId) {
        const config = this.getNMITerminalConfig(paymentMethodId);

        if (!config) {
            return { valid: false, error: 'Payment method or terminal not found' };
        }

        const { payment_method, terminal } = config;

        // Check basic configuration
        if (!payment_method.nmi_server_url) {
            return { valid: false, error: 'NMI Server URL not configured' };
        }

        if (!terminal.api_key) {
            return { valid: false, error: 'Gateway API Key not configured' };
        }

        if (!terminal.device_id) {
            return { valid: false, error: 'Device ID not configured' };
        }

        // Check connection-specific configuration
        if (terminal.connection_type === 'TCP') {
            if (!terminal.ip_address || !terminal.tcp_port) {
                return { valid: false, error: 'TCP/IP configuration incomplete' };
            }
        } else if (terminal.connection_type === 'SERIAL') {
            if (!terminal.com_port) {
                return { valid: false, error: 'COM Port not configured' };
            }
        }

        // Check terminal status
        if (!terminal.active) {
            return { valid: false, error: 'Terminal is not active' };
        }

        return { valid: true };
    },

    /**
     * Set NMI payment processing status
     */
    setNMIPaymentStatus(status, transactionData = null) {
        this.nmi_payment_status = status;
        this.nmi_current_transaction = transactionData;

        // Update payment terminal in progress flag
        this.paymentTerminalInProgress = (status === 'processing');

        // Trigger UI update
        this.env.bus.trigger('nmi_status_changed', {
            status: status,
            transaction: transactionData
        });
    },

    /**
     * Get current NMI payment status
     */
    getNMIPaymentStatus() {
        return {
            status: this.nmi_payment_status,
            transaction: this.nmi_current_transaction,
            terminal_in_progress: this.paymentTerminalInProgress
        };
    },

    /**
     * Test NMI terminal connection
     */
    async testNMITerminalConnection(terminalId) {
        const terminal = this.pos_terminal_by_id[terminalId];
        if (!terminal) {
            return { success: false, error: 'Terminal not found' };
        }

        try {
            const serverUrl = terminal.nmi_server_url || 'http://localhost:5000';
            const response = await fetch(`${serverUrl}/health`, {
                method: 'GET',
                timeout: 5000
            });

            if (response.ok) {
                terminal.device_status = 'available';
                terminal.last_test_date = new Date().toISOString();
                terminal.last_test_result = 'Connection successful';

                return { success: true, message: 'Connection successful' };
            } else {
                terminal.device_status = 'error';
                terminal.last_test_result = `HTTP ${response.status}`;

                return { success: false, error: `HTTP ${response.status}` };
            }
        } catch (error) {
            terminal.device_status = 'error';
            terminal.last_test_result = error.message;

            return { success: false, error: error.message };
        }
    },

    /**
     * Enhanced getPendingPaymentLine with NMI support
     */
    getPendingPaymentLine(paymentMethod) {
        const result = super.getPendingPaymentLine(paymentMethod);

        // Add NMI-specific handling if needed
        if (paymentMethod === 'nmi' || (result && result.payment_method.use_payment_terminal === 'nmi')) {
            // Add any NMI-specific processing here
            if (result && this.nmi_current_transaction) {
                result.nmi_transaction_data = this.nmi_current_transaction;
            }
        }

        return result;
    }
});