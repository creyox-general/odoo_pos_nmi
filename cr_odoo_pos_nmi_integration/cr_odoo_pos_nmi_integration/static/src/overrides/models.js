/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentNMI } from "../app/payment_nmi";

register_payment_method('nmi', PaymentNMI);
console.log("PaymentNmi registered:", PaymentNMI);