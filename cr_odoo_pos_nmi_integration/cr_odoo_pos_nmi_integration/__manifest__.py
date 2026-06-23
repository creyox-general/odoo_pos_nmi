# -*- coding: utf-8 -*-
# Part of Creyox Technologies
{
    'name': 'Advanced NMI POS Integration – Seamless Tap & Swipe Payments in Odoo',
    'version': '19.0.1.0.3',
    'category': 'Point of Sale',
    'summary': 'Seamlessly integrate NMI POS with Odoo. Enable fast tap & swipe payments, real-time authorization, and automatic POS order completion.',
    'description': """
        <h1>Advanced NMI POS Integration for Odoo – Faster, Smarter, Secure Payments</h1>

        <p class="lead">
        The <b>NMI POS Integration for Odoo</b> is an industry-standard solution to <b>integrate NMI payment terminals with Odoo POS</b>, enabling instant tap & swipe card payments with zero manual effort.
        </p>
        
        <blockquote>
        One click. One tap. Payment completed — automatically in Odoo POS.
        </blockquote>
        
        <h2>Overview</h2>
        <p>
        The <b>NMI POS Integration</b> empowers retailers to automate in-store card payments by directly connecting Odoo POS with NMI payment terminals.
        With a single click on the <b>NMI payment method</b>, payment details are securely sent to the terminal. Once the customer taps or swipes their card, the transaction is authorized in real time and the POS order is completed automatically.
        </p>
        <p>
        This <b>advanced NMI POS integration</b> eliminates manual entry, reduces payment errors, and significantly speeds up checkout — delivering a premium in-store experience comparable (or superior) to Odoo Enterprise POS payments.
        </p>
        
        <h2>Key Features</h2>
        <ul>
          <li><i class="fa fa-check"></i> <b>Seamless NMI POS Integration</b> with Odoo</li>
          <li><i class="fa fa-check"></i> <b>Tap & Swipe Card Support</b></li>
          <li><i class="fa fa-check"></i> <b>Automatic POS Order Completion</b></li>
          <li><i class="fa fa-check"></i> <b>Real-Time Payment Authorization</b></li>
          <li><i class="fa fa-check"></i> <b>User-Friendly POS Interface</b></li>
          <li><i class="fa fa-check"></i> <b>Multi-Card Compatibility</b></li>
        </ul>
        
        <h2>Detailed Features</h2>
        <p>
        <b>🔹 One-Click Payment Processing</b><br/>
        Initiate NMI payments directly from Odoo POS with a single click — no extra steps, no confusion.
        </p>
        
        <p>
        <b>🔹 Real-Time Transaction Sync</b><br/>
        Payment authorization is processed instantly on the NMI terminal and synced back to Odoo POS in real time.
        </p>
        
        <p>
        <b>🔹 Zero Manual Data Entry</b><br/>
        Orders are automatically validated and completed once payment succeeds — reducing human error and cashier workload.
        </p>
        
        <p>
        <b>🔹 Secure & Reliable Payments</b><br/>
        Built to meet modern POS security expectations while ensuring fast and reliable payment execution.
        </p>
        
        <h3>FAQs</h3>
        <p>
        <b>Q1. Does this module support tap and swipe cards?</b><br/>
        Yes, the module fully supports both tap and swipe card payments via NMI POS terminals.
        </p>
        
        <p>
        <b>Q2. Is the POS order completed automatically after payment?</b><br/>
        Absolutely. Once the transaction is approved, the order is completed automatically in Odoo POS.
        </p>
        
        <p>
        <b>Q3. Does this require manual payment confirmation?</b><br/>
        No. The entire process is automated from payment initiation to order completion.
        </p>
        
        <p>
        <b>Q4. Is this compatible with standard Odoo POS?</b><br/>
        Yes, it integrates seamlessly with the standard Odoo POS interface.
        </p>
        
        <h2>Why Choose Us?</h2>
        <ul>
          <li><i class="fa fa-check"></i> Enterprise-grade quality with community flexibility</li>
          <li><i class="fa fa-check"></i> Clean, scalable, and upgrade-safe code</li>
          <li><i class="fa fa-check"></i> Regular updates and long-term support</li>
          <li><i class="fa fa-check"></i> Trusted by businesses for mission-critical POS workflows</li>
        </ul>
        
        <hr/>
        
        <p>
        For custom Odoo integrations and CRM enhancements, visit <b>Creyox Technologies</b>
        </p>
        <p>
        Watch the youtube video, visit <b>Creyox Technologies YouTube Videos</b>
        </p>
        <p>
        Read our blog post, visit <b>Creyox Technologies Blogs</b>
        </p>
        <p>
        Visit Our Linkedin Page <b>Creyox Technologies Linkedin Page</b>
        </p>
    """,
    "author": "Creyox Technologies",
    "website": "https://www.creyox.com",
    "support": "support@creyox.com",
    'live_test_url': 'https://www.creyox.com/helpdesk?module_tech_name=cr_odoo_pos_nmi_integration&version=19.0',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_payment_method_views.xml',
        'views/pos_terminal.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'cr_odoo_pos_nmi_integration/static/src/**/*',
        ],
    },
    "images": ["static/description/banner.png"],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
    'price': 530,
    'currency': 'USD',
}
