# -*- coding: utf-8 -*-
"""Settings for the Warung Lakku loyalty + affiliate module.

Three commission-related knobs:
  - wl_commission_rate_percent   (Float, default 1.0)
        Percentage of the referred order's total that becomes the
        affiliate commission (in IDR). Example: 1.0 = 1% of order total.

  - wl_points_per_rupiah         (Integer, default 100)
        How many IDR of commission equals 1 point.
        Example: 100 means Rp 100 commission = 1 point.
        So order Rp 10.000 × 1% = Rp 100 commission = 1 point.

  - wl_default_commission_points (Integer, default 50)  [LEGACY]
        Used only as a fallback when a wl.affiliate.order record is
        created without a sale.order attached (manual admin entry).
        For normal referral flow, the points are computed from
        order_total × rate% ÷ points_per_rupiah.

Plus the affiliate cookie duration + the public base URL used in
affiliate share links (so the share widget can build absolute URLs
even when the page is loaded from a different domain).
"""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Commission model (v1.1.0+) ---
    wl_commission_rate_percent = fields.Float(
        string='Komisi Affiliate (%)',
        config_parameter='warunglakku_loyalty.commission_rate_percent',
        default=1.0,
        digits=(5, 2),
        help="Persentase komisi dari nilai penjualan yang dikonversi "
             "menjadi poin untuk affiliate. Contoh: 1.0 = 1% dari "
             "total order. Order Rp 10.000 × 1% = Rp 100 komisi.",
    )
    wl_points_per_rupiah = fields.Integer(
        string='Konversi Rupiah ke Poin',
        config_parameter='warunglakku_loyalty.points_per_rupiah',
        default=100,
        help="Berapa rupiah komisi = 1 poin. Contoh: 100 = Rp 100 "
             "komisi menjadi 1 poin. Jadi order Rp 10.000 × 1% = "
             "Rp 100 = 1 poin untuk affiliate.",
    )

    # --- Legacy fallback (kept for backward compatibility) ---
    wl_default_commission_points = fields.Integer(
        string='Default Commission (legacy, points)',
        config_parameter='warunglakku_loyalty.default_commission_points',
        default=50,
        help="[LEGACY] Hanya dipakai sebagai fallback ketika record "
             "wl.affiliate.order dibuat tanpa sale.order terkait "
             "(entry manual admin). Untuk alur referral normal, "
             "poin dihitung otomatis dari (order_total × komisi%) "
             "÷ konversi rupiah-ke-poin.",
    )

    # --- Cookie + URL ---
    wl_affiliate_cookie_days = fields.Integer(
        string='Affiliate Cookie Duration (days)',
        config_parameter='warunglakku_loyalty.cookie_days',
        default=30,
        help="How long the wl_aff_code cookie persists in the "
             "visitor's browser after they click an affiliate link.",
    )
    wl_affiliate_base_url = fields.Char(
        string='Affiliate Base URL',
        config_parameter='warunglakku_loyalty.base_url',
        default='https://odoo.warunglakku.com',
        help="The public base URL used in affiliate share links. "
             "Should match your production Odoo domain.",
    )
