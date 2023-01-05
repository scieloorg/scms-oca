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


def get_generic_article_values(user, json):
    entity_id = json.get('entity_id')
    keyword = json.get('fields').get('keyword')  # it's a list
    document_title = json.get('fields').get('title')  # it's a list
    authors = []
    for author in json.get('relations').get('Authorship') or []:
        orcid = get_value_in_a_list(author.get('fields').get('identifier.orcid'))
        id_lattes = get_value_in_a_list(author.get('fields').get('identifier.lattes'))
        names = author.get('fields').get('name')  # it's a list
        citation_names = author.get('fields').get('citationName')  # it's a list
        research_areas = author.get('fields').get('researchArea')  # it's a list
        birth_city = get_value_in_a_list(author.get('fields').get('birthCity'))
        birth_state = get_value_in_a_list(author.get('fields').get('birthState'))
        birth_country = get_value_in_a_list(author.get('fields').get('birthCountry'))
        try:
            authors.append(
                Authorship.authorship_get_or_create(
                    user=user,
                    orcid=orcid,
                    id_lattes=id_lattes,
                    names=names,
                    citation_names=citation_names,
                    research_areas=research_areas,
                    birth_city=birth_city,
                    birth_state=birth_state,
                    birth_country=birth_country
                )
            )
        except:
            pass
    publication_date = get_value_in_a_list(json.get('fields').get('publicationDate'))
    document_type = get_value_in_a_list(json.get('fields').get('type'))
    language = get_value_in_a_list(json.get('fields').get('language'))
    research_area = json.get('fields').get('researchArea.cnpq')  # it's a list
    start_page = get_value_in_a_list(json.get('fields').get('starPage'))
    end_page = get_value_in_a_list(json.get('fields').get('endPage'))
    volume = get_value_in_a_list(json.get('fields').get('volume'))

    return entity_id, keyword, document_title, authors, publication_date, document_type, language, research_area, \
        start_page, end_page, volume


def load_thesis(user, record):
    json = record.json

    # attribs to GenericArticle
    entity_id, keyword, document_title, authors, publication_date, document_type, language, research_area, start_page, \
        end_page, volume = get_generic_article_values(user=user, json=json)

    # attribs to Thesis
    advisors = []
    for advisor in json.get('relations').get('Adivisoring') or []:
        orcid = get_value_in_a_list(advisor.get('fields').get('identifier.orcid'))
        id_lattes = get_value_in_a_list(advisor.get('fields').get('identifier.lattes'))
        names = advisor.get('fields').get('name')  # it's a list
        citation_names = advisor.get('fields').get('citationName')  # it's a list
        research_areas = advisor.get('fields').get('researchArea')  # it's a list
        birth_city = get_value_in_a_list(advisor.get('fields').get('birthCity'))
        birth_state = get_value_in_a_list(advisor.get('fields').get('birthState'))
        birth_country = get_value_in_a_list(advisor.get('fields').get('birthCountry'))
        try:
            advisors.append(
                Authorship.authorship_get_or_create(
                    user=user,
                    orcid=orcid,
                    id_lattes=id_lattes,
                    names=names,
                    citation_names=citation_names,
                    research_areas=research_areas,
                    birth_city=birth_city,
                    birth_state=birth_state,
                    birth_country=birth_country
                )
            )
        except:
            pass

    try:
        Thesis.thesis_get_or_create(
            user=user,
            entity_id=entity_id,
            keyword=keyword,
            document_title=document_title,
            authors=authors,
            publication_date=publication_date,
            document_type=document_type,
            language=language,
            research_area=research_area,
            start_page=start_page,
            end_page=end_page,
            volume=volume,
            advisors=advisors
        )
    except:
        pass


def load_conference(user, record):
    json = record.json

    # attribs to GenericArticle
    entity_id, keyword, document_title, authors, publication_date, document_type, language, research_area, start_page, \
        end_page, volume = get_generic_article_values(user=user, json=json)

    try:
        ConferenceProceedings.conference_get_or_create(
            user=user,
            entity_id=entity_id,
            keyword=keyword,
            document_title=document_title,
            authors=authors,
            publication_date=publication_date,
            document_type=document_type,
            language=language,
            research_area=research_area,
            start_page=start_page,
            end_page=end_page,
            volume=volume
        )
    except:
        pass


def load_article(user, record):
    json = record.json

    # attribs to GenericArticle
    entity_id, keyword, document_title, authors, publication_date, document_type, language, research_area, start_page, \
        end_page, volume = get_generic_article_values(user=user, json=json)

    # attribs to JournalArticle
    series = get_value_in_a_list(json.get('fields').get('series'))
    issn = []
    journal_title = []
    for item in json.get('relations').get('PublisherJournal') or []:
        issn.extend(item.get('fields').get('identifier.issn'))
        journal_title.extend(item.get('fields').get('title'))

    try:
        JournalArticle.journal_get_or_create(
            user=user,
            entity_id=entity_id,
            keyword=keyword,
            document_title=document_title,
            authors=authors,
            publication_date=publication_date,
            document_type=document_type,
            language=language,
            research_area=research_area,
            start_page=start_page,
            end_page=end_page,
            volume=volume,
            series=series,
            issn=issn,
            journal_title=journal_title
        )
    except:
        pass
