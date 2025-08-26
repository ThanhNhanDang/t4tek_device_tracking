import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'
    lot_id = fields.Many2one('stock.lot', string='Số Lô / Số Seri', ondelete='restrict', tracking=True)
    def _merge_moves(self, merge_into=False):
        return self
    