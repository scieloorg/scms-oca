from harvest.models import HarvestedPreprint, HarvestErrorLogPreprint

from .harvest_common import harvest_records

NODES = [
    "title",
    "subject",
    "identifier",
    "rights",
    "publisher",
    "description",
    "publisher",
    "relation",
    "type",
]

def harvest_preprint(recs, user):
    harvest_records(
        recs=recs,
        user=user,
        nodes=NODES,
        model=HarvestedPreprint,
        log_model=HarvestErrorLogPreprint,
        fk_field="preprint",
        label="preprint",
    )


