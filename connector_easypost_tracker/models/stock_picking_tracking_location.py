# -*- coding: utf-8 -*-
# Copyright 2016-2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import fields, models
from odoo.addons.connector.unit.mapper import (
    mapping,
    only_create,
)
from odoo.addons.connector_easypost.backend import easypost
from odoo.addons.connector_easypost.unit.backend_adapter import (
    EasypostCRUDAdapter,
)
from odoo.addons.connector_easypost.unit.import_synchronizer import (
    EasypostImporter,
)
from odoo.addons.connector_easypost.unit.mapper import (
    EasypostImportMapper,
    eval_false,
)


_logger = logging.getLogger(__name__)


class EasypostShipmentTrackingLocation(models.Model):
    """ Binding Model for the Easypost StockPickingTrackingLocation"""
    _name = 'easypost.shipment.tracking.location'
    _inherit = 'easypost.binding'
    _inherits = {'stock.picking.tracking.location': 'odoo_id'}
    _description = 'Easypost StockPickingTrackingLocation'
    _easypost_model = 'Tracker'

    odoo_id = fields.Many2one(
        comodel_name='stock.picking.tracking.location',
        string='Stock Picking Tracking Location',
        required=True,
        ondelete='cascade',
    )


class StockPickingTrackingLocation(models.Model):
    """ Adds the ``one2many`` relation to the Easypost bindings
    (``easypost_bind_ids``)
    """
    _inherit = 'stock.picking.tracking.location'

    easypost_bind_ids = fields.One2many(
        comodel_name='easypost.shipment.tracking.location',
        inverse_name='odoo_id',
        string='Easypost Bindings',
    )


@easypost
class EasypostShipmentTrackingLocationAdapter(EasypostCRUDAdapter):
    """ Backend Adapter for the Easypost
    EasypostShipmentTrackingLocation """
    _model_name = 'easypost.shipment.tracking.location'


@easypost
class StockPickingTrackingLocationImportMapper(EasypostImportMapper):
    _model_name = 'easypost.shipment.tracking.location'

    direct = [
        (eval_false('city'), 'city'),
        (eval_false('zip'), 'zip'),
    ]

    @mapping
    @only_create
    def odoo_id(self, record):
        rec = self.env['easypost.shipment.tracking.location'].search([
            ('external_id', '=', record.id),
            ('backend_id', '=', self.backend_record.id),
        ])
        if rec:
            return {'odoo_id': rec.odoo_id.id}

    @mapping
    @only_create
    def country_id(self, record):
        """ Load the country ID from the state code if it's not set.
        This is because the country code is not always included in
        `TrackingLocation` objects but the state is """
        if record.country:
            country = self.env['res.country'].search([
                ('code', '=', record.country),
            ])
            return {'country_id': country.id}
        else:
            state = self.env['res.country.state'].search([
                ('code', '=', record.state),
            ])
            return {'country_id': state.country_id.id}

    @mapping
    @only_create
    def state_id(self, record):
        state = self.env['res.country.state'].search([
            ('code', '=', record.state),
        ])
        return {'state_id': state.id}


@easypost
class StockPickingTrackingLocationImporter(EasypostImporter):
    _model_name = ['easypost.shipment.tracking.location']
    _base_mapper = StockPickingTrackingLocationImportMapper
    _id_prefix = 'loc'
    _hashable_attrs = ('city', 'zip', 'state')

    def default_easypost_values(self, defaults_obj):
        """ Get Default values from a given object to fill in any missing
        data in `self.easypost_record`
        :param defaults_obj: Record that we are filling in the gaps from
        """
        for attr in self._hashable_attrs:
            rec_val = getattr(self.easypost_record, attr)
            if not rec_val:
                if attr == 'state':
                    # Handle by getting the code from the ID
                    val = getattr(defaults_obj, '%s_id' % attr)
                    setattr(self.easypost_record, attr, val.code)
                else:
                    setattr(self.easypost_record, attr,
                            getattr(defaults_obj, attr))
