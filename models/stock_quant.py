import logging

from odoo import fields, models, api,_
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    @api.model
    def create(self, vals):
        return super(StockQuant,self).create(vals)
