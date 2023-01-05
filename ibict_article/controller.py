import orjson

from .models import RawArticle, JournalArticle, Thesis, ConferenceProceedings
from .core import Authorship, GenericArticle


def load_raw_ibict(row, user):
    row = orjson.loads(row)
    document_type = row.get('fields').get('type')[0]
    document_id = row.get('entity_id')

    try:
        rawrecord = RawArticle.objects.filter(entity_id=document_id, document_type=document_type)
        if rawrecord:
            pass
        else:
            rawrecord = RawArticle()
            rawrecord.document_type = document_type
            rawrecord.entity_id = document_id
            rawrecord.json = row
            rawrecord.creator = user
            rawrecord.save()
    except Exception as e:
        print(str(e))


def get_value_in_a_list(list_of_values):
    try:
        return list_of_values[0]
    except (IndexError, TypeError):
        return


