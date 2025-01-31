import logging
import json
import time
import zipfile
from flask_restplus import Namespace
from datetime import date, timedelta
from io import BytesIO
from elasticsearch.helpers import scan
from sokannonser import settings
from sokannonser.repository import elastic
from sokannonser.rest.model.platsannons_results import job_ad

log = logging.getLogger(__name__)
marshaller = Namespace('Marhsaller')

def _es_dsl():
    dsl = {
        "query": {
            "bool": {
                'filter': [
                    {
                        'range': {
                            'publication_date': {
                                'lte': 'now/m'
                            }
                        }
                    },
                    {
                        'range': {
                            'last_publication_date': {
                                'gte': 'now/m'
                            }
                        }
                    },
                    {
                        "term": {
                            "removed": False
                        }
                    }
                ]
            }
        },
    }
    return dsl


def zip_ads(day, start_time=0):
    if start_time == 0:
        start_time = int(time.time() * 1000)

    dsl = _es_dsl()

    if day == 'all':
        dsl['query']['bool']['must'] = [{"match_all": {}}]
    else:
        ts_from = convert_to_timestamp('%sT00:00:00' % str(day))
        ts_to = convert_to_timestamp('%sT23:59:59' % str(day))

        dsl['query']['bool']['must'] = [{
            "range": {
                "timestamp": {
                    "gte": ts_from,
                    "lte": ts_to
                }
            }
        }]
    log.debug('zip_ads, dsl: %s' % dsl)
    scan_result = scan(elastic, dsl, index=settings.ES_INDEX)
    in_memory = BytesIO()
    zf = zipfile.ZipFile(in_memory, "w", zipfile.ZIP_DEFLATED)

    ads = [remove_sensitive_data(ad['_source']) for ad in scan_result]
    log.debug("Number of ads: %d" % len(ads))
    zf.writestr(f"ads_{day}.json", json.dumps(ads))
    zf.close()
    in_memory.seek(0)
    log.debug("File constructed after %d milliseconds."
              % (int(time.time() * 1000) - start_time))
    return in_memory


def convert_to_timestamp(day):
    if not day:
        return None

    ts = 0
    for dateformat in [
        '%Y-%m-%dT%H:%M:%S'
    ]:

        try:
            ts = time.mktime(time.strptime(day, dateformat)) * 1000
            log.debug("Converted date %s to %d" % (day, ts))
            break
        except ValueError as e:
            log.debug("Failed to convert date %s" % day, e)

    return int(ts)


# Generator function
def load_all(since):
    if since == 'yesterday':
        since = (date.today() - timedelta(1)).strftime('%Y-%m-%d')

    ts = time.mktime(since.timetuple()) * 1000

    dsl = _es_dsl()
    dsl['query']['bool']['must'] = [{
        "range": {
            "timestamp": {
                "gte": ts
            }
        }
    }]
    log.debug('load_all, dsl: %s' % dsl)
    scan_result = scan(elastic, dsl, index=settings.ES_INDEX)
    counter = 0
    yield '['
    for ad in scan_result:
        if counter > 0:
            yield ','
        source = ad['_source']
        remove_sensitive_data(source)
        yield json.dumps(format_ad(source))
        # yield json.dumps(source)
        counter += 1
    log.debug("Delivered %d ads as stream" % counter)
    yield ']'


@marshaller.marshal_with(job_ad)
def format_ad(ad_data):
    return ad_data


def remove_sensitive_data(source):
    try:
        # Remove enriched
        if 'keyword' in source:
            del source['keywords']
        # Remove personal number
        org_nr = source['employer']['organization_number']
        if org_nr and int(org_nr[2]) < 2:
            source['employer']['organization_number'] = None
    except KeyError:
        pass
    except ValueError:
        pass
    return source
