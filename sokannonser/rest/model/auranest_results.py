from flask_restplus import fields
from sokannonser.rest import ns_auranest

annons = ns_auranest.model('Annons', {
    'id': fields.String(attribute='_source.id'),
    'header': fields.String(attribute='_source.header'),
    'content': fields.String(attribute='_source.content.text'),
    'employer': fields.Nested({
        'name': fields.String(),
        'logoUrl': fields.String()
    }, attribute='employer', skip_none=True),
    'location': fields.String(attribute='_source.location.translations.sv-SE'),
    'application': fields.Nested({
        'url': fields.String(),
        'email': fields.String(),
        'deadline': fields.DateTime(),
        'reference': fields.String(),
        'site': fields.Nested({
            'url': fields.String(),
            'name': fields.String()
        })
    }, attribute='_source.application', skip_none=True)
})


stat_item = ns_auranest.model('StatItem', {
    'value': fields.String(attribute='key'),
    'count': fields.Integer(attribute='doc_count')
})

statistics = ns_auranest.model('Statistics', {
    'employers': fields.List(fields.Nested(stat_item), attribute='employers.buckets'),
    'sites': fields.List(fields.Nested(stat_item), attribute='sites.buckets'),
    'locations': fields.List(fields.Nested(stat_item), attribute='locations.buckets'),
})

auranest_lista = ns_auranest.model('Annonser', {
    'total': fields.Integer(attribute='hits.total'),
    'stats': fields.Nested(statistics, attribute='aggregations', skip_none=True),
    'hits': fields.List(fields.Nested(annons), attribute='hits.hits')
})

