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
from .stock_picking_tracking_location import (
    StockPickingTrackingLocationImporter,
)

_logger = logging.getLogger(__name__)


class EasypostShipmentTrackingEvent(models.Model):
    """ Binding Model for the Easypost StockPickingTrackingEvent"""
    _name = 'easypost.shipment.tracking.event'
    _inherit = 'easypost.binding'
    _inherits = {'stock.picking.tracking.event': 'odoo_id'}
    _description = 'Easypost StockPickingTrackingEvent'
    _easypost_model = 'Tracker'

    odoo_id = fields.Many2one(
        comodel_name='stock.picking.tracking.event',
        string='Stock Picking Tracking Event',
        required=True,
        ondelete='cascade',
    )


class StockPickingTrackingEvent(models.Model):
    """ Adds the ``one2many`` relation to the Easypost bindings
    (``easypost_bind_ids``)
    """
    _inherit = 'stock.picking.tracking.event'

    easypost_bind_ids = fields.One2many(
        comodel_name='easypost.shipment.tracking.event',
        inverse_name='odoo_id',
        string='Easypost Bindings',
    )


@easypost
class EasypostShipmentTrackingEventAdapter(EasypostCRUDAdapter):
    """ Backend Adapter for the Easypost EasypostShipment """
    _model_name = 'easypost.shipment.tracking.event'


@easypost
class StockPickingTrackingEventImportMapper(EasypostImportMapper):
    _model_name = 'easypost.shipment.tracking.event'

    direct = [
        (eval_false('message'), 'message'),
        (eval_false('status'), 'state'),
        (eval_false('source'), 'source'),
        (eval_false('datetime'), 'date_created'),
    ]

    @mapping
    @only_create
    def group_id(self, record):
        """ `group_id` is not present in the event object and should be
        injected by the caller """
        return {'group_id': record.group.id}

    @mapping
    @only_create
    def location_id(self, record):
        return {'location_id': record.location_id}


@easypost
class StockPickingTrackingEventImporter(EasypostImporter):
    _model_name = ['easypost.shipment.tracking.event']
    _base_mapper = StockPickingTrackingEventImportMapper
    _id_prefix = 'det'
    _hashable_attrs = ('message', 'status', 'source', 'datetime')

    def _before_import(self):
        """ Prior to import, export the TrackingLocation and add the resulting
        `location_id` to our easypost_record for mapping """
        importer = self.unit_for(
            StockPickingTrackingLocationImporter,
            model='easypost.shipment.tracking.location'
        )
        importer.easypost_record = self.easypost_record.tracking_location
        importer.default_easypost_values(
            self.easypost_record.group.picking_id.company_id
        )
        ret = importer.run()
        self.easypost_record.location_id = ret.odoo_id.id
