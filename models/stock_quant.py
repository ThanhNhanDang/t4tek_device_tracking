import logging

from odoo import fields, models, api,_
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    @api.model
    def create(self, vals):
        return super(StockQuant,self).create(vals)
    
    def check_quantity(self):
        sn_quants = self.filtered(lambda q: q.product_id.tracking == 'serial' and q.location_id.usage != 'inventory' and q.lot_id)
        if not sn_quants:
            return
        domain = [
            ('product_id', 'in', sn_quants.product_id.ids),
            ('location_id', 'child_of', sn_quants.location_id.ids),
            ('lot_id', 'in', sn_quants.lot_id.ids)
        ]
        groups = self._read_group(
            domain,
            ['product_id', 'location_id', 'lot_id'],
            ['quantity:sum'],
        )
