import orjson

from .models import RawArticle, JournalArticle, Thesis, ConferenceProceedings
from .core import Authorship


def load_raw_data(row, user):
    row = orjson.loads(row)
    document_type = row.get('fields').get('type')[0]
    document_id = row.get('entity_id')

    try:
        rawrecord = RawArticle.objects.filter(entity_id=document_id, document_type=document_type)[0]
    except IndexError:
        rawrecord = RawArticle()
        rawrecord.document_type = document_type
        rawrecord.entity_id = document_id
        rawrecord.json = row
        rawrecord.creator = user
        rawrecord.save()

    return rawrecord


def get_value_in_a_list(list_of_values):
    try:
        return list_of_values[0]
    except (IndexError, TypeError):
        return


def get_common_person_data_values(person):
    orcid = get_value_in_a_list(person.get('identifier.orcid'))
    id_lattes = get_value_in_a_list(person.get('identifier.lattes'))
    names = person.get('name')  # it's a list
    citation_names = person.get('citationName')  # it's a list
    person_research_areas = person.get('researchArea')  # it's a list
    birth_city = get_value_in_a_list(person.get('birthCity'))
    birth_state = get_value_in_a_list(person.get('birthState'))
    birth_country = get_value_in_a_list(person.get('birthCountry'))

    return orcid, id_lattes, names, citation_names, person_research_areas, \
        birth_city, birth_state, birth_country


def get_common_publication_data_values(user, json):
    fields = json['fields']
    entity_id = json.get('entity_id')
    keywords = fields.get('keyword')  # it's a list
    document_titles = fields.get('title')  # it's a list
    authors = []
    for author in json.get('relations').get('Authorship') or []:
        orcid, id_lattes, names, citation_names, person_research_areas, \
            birth_city, birth_state, birth_country = get_common_person_data_values(author.get('fields'))
        try:
            authors.append(
                Authorship.authorship_get_or_create(
                    user=user,
                    orcid=orcid,
                    id_lattes=id_lattes,
                    names=names,
                    citation_names=citation_names,
                    person_research_areas=person_research_areas,
                    birth_city=birth_city,
                    birth_state=birth_state,
                    birth_country=birth_country
                )
            )
        except:
            pass

    publication_date = get_value_in_a_list(fields.get('publicationDate'))
    document_type = get_value_in_a_list(fields.get('type'))
    language = get_value_in_a_list(fields.get('language'))
    research_areas = fields.get('researchArea.cnpq')  # it's a list
    start_page = get_value_in_a_list(fields.get('starPage'))
    end_page = get_value_in_a_list(fields.get('endPage'))
    volume = get_value_in_a_list(fields.get('volume'))

    return entity_id, keywords, document_titles, authors, publication_date, document_type, language, research_areas, \
        start_page, end_page, volume


def load_thesis(user, record):
    json = record.json

    # attribs to CommonPublicationData
    entity_id, keywords, document_titles, authors, publication_date, document_type, language, research_areas, \
        start_page, end_page, volume = get_common_publication_data_values(user=user, json=json)

    # attribs to Thesis
    advisors = []
    for advisor in json.get('relations').get('Adivisoring') or []:
        orcid = get_value_in_a_list(advisor.get('fields').get('identifier.orcid'))
        id_lattes = get_value_in_a_list(advisor.get('fields').get('identifier.lattes'))
        names = advisor.get('fields').get('name')  # it's a list
        citation_names = advisor.get('fields').get('citationName')  # it's a list
        person_research_areas = advisor.get('fields').get('researchArea')  # it's a list
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
                    person_research_areas=person_research_areas,
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
            keywords=keywords,
            document_titles=document_titles,
            authors=authors,
            publication_date=publication_date,
            document_type=document_type,
            language=language,
            research_areas=research_areas,
            start_page=start_page,
            end_page=end_page,
            volume=volume,
            advisors=advisors
        )
    except:
        pass


def load_conference(user, record):
    json = record.json

    # attribs to CommonPublicationData
    entity_id, keywords, document_titles, authors, publication_date, document_type, language, research_areas, \
        start_page, end_page, volume = get_common_publication_data_values(user=user, json=json)

    try:
        ConferenceProceedings.conference_get_or_create(
            user=user,
            entity_id=entity_id,
            keywords=keywords,
            document_titles=document_titles,
            authors=authors,
            publication_date=publication_date,
            document_type=document_type,
            language=language,
            research_areas=research_areas,
            start_page=start_page,
            end_page=end_page,
            volume=volume
        )
    except:
        pass


def load_article(user, record):
    json = record.json

    # attribs to CommonPublicationData
    entity_id, keywords, document_titles, authors, publication_date, document_type, language, research_areas, \
        start_page, end_page, volume = get_common_publication_data_values(user=user, json=json)

    # attribs to JournalArticle
    series = get_value_in_a_list(json.get('fields').get('series'))
    issns = []
    journal_titles = []
    for item in json.get('relations').get('PublisherJournal') or []:
        issns.extend(item.get('fields').get('identifier.issn'))
        journal_titles.extend(item.get('fields').get('title'))

    try:
        JournalArticle.journal_get_or_create(
            user=user,
            entity_id=entity_id,
            keywords=keywords,
            document_titles=document_titles,
            authors=authors,
            publication_date=publication_date,
            document_type=document_type,
            language=language,
            research_areas=research_areas,
            start_page=start_page,
            end_page=end_page,
            volume=volume,
            series=series,
            issns=issns,
            journal_titles=journal_titles
        )
    except:
        pass
