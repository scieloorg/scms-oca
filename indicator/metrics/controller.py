from search_gateway.client import get_opensearch_client
from search_gateway.models import DataSource

from indicator.metrics.engine import MetricEngine


def get_indicator_data(data_source_name, filters, study_unit="document"):
    es = get_opensearch_client()
    if not es:
        return None, "Service unavailable"

    data_source = DataSource.get_by_index_name(index_name=data_source_name)
    if not data_source:
        return None, "Invalid data_source"

    return MetricEngine(data_source=data_source, filters=filters, study_unit=study_unit).run(es)
