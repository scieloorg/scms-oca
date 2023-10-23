import logging

import pandas as pd
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from article import models
from config import celery_app
from core.models import Source
from core.utils import utils as core_utils

from institution.models import Institution

logger = logging.getLogger(__name__)

User = get_user_model()


@celery_app.task(name="Load OpenAlex data to SourceArticle")
def load_openalex(user_id, date=2012, length=None, country="BR"):
    """
    Retrieves article data from OpenALex API for a specific year and populate the article.models.Article

    Sync or Async
    Param: date is a integer representing the date range in the format 'YYYY'.

    The endpoint OpenAlex: https://api.openalex.org/works/?filter=institutions.country_code:{country},publication_year:{date}&per-page=200&cursor=*"

    The API of OpenALex only allow 200 itens per request.

    Example running this function on python terminal

        from article import tasks

        tasks.load_openalex(date=2012)


    Running using a script:

    python manage.py runscript load_openalex --script-args 1 2012

    The OpenAlex API format is something like the format below:
      "meta":{
         "count":97151,
         "db_response_time_ms":60,
         "page":null,
         "per_page":100,
         "next_cursor":"IlszODksICdodHRwczovL29wZW5hbGV4Lm9yZy9XMTk2NjA4NDkxNSddIg=="
      },
      "results":[
         {
            "id":"https://openalex.org/W2114538920",
            "doi":"https://doi.org/10.1016/s0140-6736(12)60646-1",
            "title":"Global physical activity levels: surveillance progress, pitfalls, and prospects",
            "display_name":"Global physical activity levels: surveillance progress, pitfalls, and prospects",
            "publication_year":2012,
            "publication_date":"2012-07-01",
            "ids":{
               "openalex":"https://openalex.org/W2114538920",
               "doi":"https://doi.org/10.1016/s0140-6736(12)60646-1",
               "mag":"2114538920",
               "pmid":"https://pubmed.ncbi.nlm.nih.gov/22818937"
            },
            "language":"en",
            "primary_location":{
               "is_oa":false,
               "landing_page_url":"https://doi.org/10.1016/s0140-6736(12)60646-1",
               "pdf_url":null,
               "source":{
                  "id":"https://openalex.org/S49861241",
                  "display_name":"The Lancet",
                  "issn_l":"0140-6736",
                  "issn":[
                     "1474-547X",
                     "0099-5355",
                     "0140-6736"
                  ],
                  "is_oa":false,
                  "is_in_doaj":false,
                  "host_organization":"https://openalex.org/P4310320990",
                  "host_organization_name":"Elsevier BV",
                  "host_organization_lineage":[
                     "https://openalex.org/P4310320990"
                  ],
                  "host_organization_lineage_names":[
                     "Elsevier BV"
                  ],
                  "type":"journal"
               },
               "license":null,
               "version":null
            },
            "type":"journal-article",
            "open_access":{
               "is_oa":true,
               "oa_status":"green",
               "oa_url":"https://api.research-repository.uwa.edu.au/ws/files/79079771/AAM_Global_physical_activity_levels.pdf",
               "any_repository_has_fulltext":true
            },
            "authorships":[
               {
                  "author_position":"first",
                  "author":{
                     "id":"https://openalex.org/A4354288008",
                     "display_name":"Pedro C. Hallal",
                     "orcid":null
                  },
                  "institutions":[
                     {
                        "id":"https://openalex.org/I169248161",
                        "display_name":"Universidade Federal de Pelotas",
                        "ror":"https://ror.org/05msy9z54",
                        "country_code":"BR",
                        "type":"education"
                     }
                  ],
                  "is_corresponding":true,
                  "raw_affiliation_string":"Universidade Federal de Pelotas, Pelotas, Brazil",
                  "raw_affiliation_strings":[
                     "Universidade Federal de Pelotas, Pelotas, Brazil"
                  ]
               },
               {
                  "author_position":"middle",
                  "author":{
                     "id":"https://openalex.org/A4359769260",
                     "display_name":"Lars Bo Andersen",
                     "orcid":null
                  },
                  "institutions":[
                     {
                        "id":"https://openalex.org/I177969490",
                        "display_name":"University of Southern Denmark",
                        "ror":"https://ror.org/03yrrjy16",
                        "country_code":"DK",
                        "type":"education"
                     },
                     {
                        "id":"https://openalex.org/I76283144",
                        "display_name":"Norwegian School of Sport Sciences",
                        "ror":"https://ror.org/045016w83",
                        "country_code":"NO",
                        "type":"education"
                     }
                  ],
                  "is_corresponding":false,
                  "raw_affiliation_string":"Department of Sport Medicine, Norwegian School of Sport Sciences, Oslo, Norway; Department of Exercise Epidemiology, Centre for Research in Childhood Health, University of Southern Denmark, Odense, Denmark",
                  "raw_affiliation_strings":[
                     "Department of Sport Medicine, Norwegian School of Sport Sciences, Oslo, Norway",
                     "Department of Exercise Epidemiology, Centre for Research in Childhood Health, University of Southern Denmark, Odense, Denmark"
                  ]
               }
        }
    """
    url = (
        settings.URL_API_OPENALEX
        + f"?filter=institutions.country_code:{country},publication_year:{date}&per-page=200&cursor=*"
    )

    _source, _ = Source.objects.get_or_create(name="OPENALEX")

    try:
        flag = True
        article_count = 0

        while flag:
            payload = core_utils.fetch_data(url, json=True, timeout=30, verify=True)

            if payload.get("results"):
                for item in payload.get("results"):
                    article = {}
                    article["specific_id"] = item.get("id")
                    article["doi"] = item.get("doi")
                    article["year"] = item.get("publication_year")
                    article["is_paratext"] = item.get("is_paratext")
                    article["updated"] = item.get("updated_date")
                    article["created"] = item.get("created_date")
                    article["source"] = _source
                    article["raw"] = item

                    article, created = models.SourceArticle.create_or_update(**article)

                    logger.info(
                        "%s: %s"
                        % (
                            "Created article" if created else "Updated article",
                            article,
                        )
                    )
                    article_count += 1

                cursor = payload["meta"]["next_cursor"]

                # Url with new cursor
                url = url.split("cursor=")[0] + "cursor=" + cursor

                if length and (length <= article_count):
                    flag = False

            else:
                logger.info("No more articles found.")
                return
    except Exception as e:
        logger.info(f"Unexpected error: {e}")


@celery_app.task(name=_("Sanitize all Journals"))
def article_source_to_article(
    user_id, source_name="OPENALEX", size=None, loop_size=1000
):
    """ """
    count = 0

    size=1000 if size and size < 1000 else size

    sarticle = (
        models.SourceArticle.objects.filter(source__name=source_name).order_by("id")[0 : int(size)]
        if size
        else models.SourceArticle.objects.filter(source__name="OPENALEX")
    )
    total = sarticle.count()
    offset = loop_size

    for i in range(int(total / loop_size) + 1):
        _article = sarticle[count:offset]
        load_openalex_article.apply_async(
            kwargs={
                "user_id": user_id,
                "article_ids": [article.id for article in _article],
            }
        )
        count += loop_size
        offset += loop_size

        if offset > total:
            offset = total


@celery_app.task(name="Load OpenAlex to Article models")
def load_openalex_article(user_id, article_ids, update=False):
    """
    This task read the article.models.SourceArticle
    and add the articles to article.models.Article

    Only associaded the official institutions when exists and if from MEC.

    Param update: If update == True all articles will be update otherwise just the article will created.
    """

    user = User.objects.get(id=user_id)

    for id in article_ids:
        article = models.SourceArticle.objects.get(id=id)
        try:
            doi = article.doi
            # title
            title = core_utils.nestget(article.raw, "title")

            if not update:
                if doi:
                    if models.Article.objects.filter(doi=doi).exists():
                        print("ja existe")
                        continue

                if title:
                    if models.Article.objects.filter(title=title).exists():
                        continue

            # Number
            number = core_utils.nestget(article.raw, "biblio", "issue")
            # Volume
            volume = core_utils.nestget(article.raw, "biblio", "volume")
            # Year
            year = core_utils.nestget(article.raw, "publication_year")

            # Get the journal data
            if article.raw.get("primary_location"):
                journal_data = core_utils.nestget(article.raw, "primary_location", "source")
                if journal_data:
                    j_issn_l = journal_data.get("issn_l")
                    if journal_data.get("issn"):
                        j_issns = ",".join(journal_data.get("issn"))
                    j_name = journal_data.get("display_name")
                    j_is_in_doaj = journal_data.get("is_in_doaj")

                journal, _ = models.Journal.create_or_update(
                    **{
                        "journal_issn_l": j_issn_l,
                        "journal_issns": j_issns,
                        "journal_name": j_name,
                        "journal_is_in_doaj": j_is_in_doaj,
                    },
                )
            else:
                journal = None

            # APC
            is_apc = "YES" if bool(core_utils.nestget(article.raw, "apc_list")) else "NO"

            # Open Access Status
            oa_status = core_utils.nestget(article.raw, "open_access", "oa_status")

            # license
            if article.raw.get("primary_location"):
                if core_utils.nestget(article.raw, "primary_location", "license"):
                    license, _ = models.License.create_or_update(
                        **{
                            "name": core_utils.nestget(
                                article.raw, "primary_location", "license"
                            )
                        }
                    )
                else:
                    license = None

            # contributors
            contributors = []

            for au in core_utils.nestget(article.raw, "authorships"):
                # if exists author
                if au.get("author"):
                    display_name = au.get("author").get("display_name")

                    if display_name:
                        family = (
                            " ".join(display_name.split(" ")[1:]).strip()
                            if display_name
                            else ""
                        )
                        given = display_name.split(" ")[0].strip() if display_name else ""

                        author_dict = {
                            "family": family,
                            "given": given,
                            "orcid": au.get("author").get("orcid"),
                            "author_position": au.get("author_position"),
                        }

                        # Here we are adding the affiliation to the contributor
                        if au.get("raw_affiliation_strings"):
                            affs = []
                            aff_obj, _ = models.Affiliation.create_or_update(
                                **{"name": "|".join(au.get("raw_affiliation_strings"))}
                            )
                            affs.append(aff_obj)

                            author_dict.update(
                                {
                                    "affiliations": affs,
                                }
                            )

                        # Add the institutions
                        if au.get("institutions"):
                            insts = []
                            source = Source.objects.get(name="OPENALEX")
                            for inst in au.get("institutions"):
                                inst_obj, _ = models.SourceInstitution.create_or_update(
                                    **{"specific_id": inst.get("id"), "source": source}
                                )
                                insts.append(inst_obj)

                            author_dict.update(
                                {
                                    "institutions": insts,
                                }
                            )
                        contributor, _ = models.Contributor.create_or_update(**author_dict)

                        contributors.append(contributor)

            article_dict = {
                "doi": doi,
                "title": title,
                "number": number,
                "volume": volume,
                "year": year,
                "is_oa": core_utils.nestget(article.raw, "open_access", "is_oa"),
                "sources": [Source.objects.get(name="OPENALEX")],
                "journal": journal,
                "apc": is_apc,
                "open_access_status": oa_status,
                "contributors": contributors,
                "license": license,
            }

            article, created = models.Article.create_or_update(**article_dict)

            logger.info("Article: %s, %s" % (article, created))
        except Exception as e:
            logger.error("Erro on save article: %s" % e)


@celery_app.task(
    name="Concatenates the Sucupira intellectual production with the details of the production"
)
def concat_article_sucupira_detail(production_file_csv, detail_file_csv, json=False):
    """
    This task concate the a file with the article production in CAPES.

    The source of the production_file_csv: https://dadosabertos.capes.gov.br/dataset/2017-a-2020-autor-da-producao-intelectual-de-programas-de-pos-graduacao-stricto-sensu

    The columns of the production_file_csv:

        ['CD_PROGRAMA_IES', 'NM_PROGRAMA_IES', 'SG_ENTIDADE_ENSINO',
         'NM_ENTIDADE_ENSINO', 'AN_BASE', 'ID_ADD_PRODUCAO_INTELECTUAL',
         'ID_PRODUCAO_INTELECTUAL', 'NM_PRODUCAO', 'ID_TIPO_PRODUCAO',
         'NM_TIPO_PRODUCAO', 'ID_SUBTIPO_PRODUCAO', 'NM_SUBTIPO_PRODUCAO',
         'ID_FORMULARIO_PRODUCAO', 'NM_FORMULARIO', 'ID_AREA_CONCENTRACAO',
         'NM_AREA_CONCENTRACAO', 'ID_LINHA_PESQUISA', 'NM_LINHA_PESQUISA',
         'ID_PROJETO', 'NM_PROJETO', 'DH_INICIO_AREA_CONC', 'DH_FIM_AREA_CONC',
         'DH_INICIO_LINHA', 'DH_FIM_LINHA', 'IN_GLOSA',
         'IN_PRODUCAO_COM_VINCULO_TCC', 'ID_ADD_TRABALHO_CONCLUSAO_CT'],

    The dictionary of the data is in this file: https://dadosabertos.capes.gov.br/dataset/de69242b-03b0-4d38-b5b2-a9169abd84c2/resource/40b83217-dc80-4d30-8db1-4ee91dea3ecc/download/metadados_autor_producao_intelectual_2017_2020.pdf

    The source of the detail_file_csv: https://dadosabertos.capes.gov.br/dataset/2017-a-2020-detalhes-da-producao-intelectual-bibliografica-de-programas-de-pos-graduacao

    The columns of the detail_file_csv:
        ['CD_PROGRAMA_IES', 'NM_PROGRAMA_IES', 'SG_ENTIDADE_ENSINO',
         'NM_ENTIDADE_ENSINO', 'AN_BASE_PRODUCAO', 'ID_ADD_PRODUCAO_INTELECTUAL',
         'ID_TIPO_PRODUCAO', 'ID_SUBTIPO_PRODUCAO', 'DS_NATUREZA', 'NR_VOLUME',
         'DS_FASCICULO', 'NR_SERIE', 'NR_PAGINA_FINAL', 'NR_PAGINA_INICIAL',
         'DS_IDIOMA', 'DS_DIVULGACAO', 'DS_URL', 'DS_OBSERVACOES', 'NM_EDITORA',
         'NM_CIDADE', 'DS_DOI', 'DS_ISSN', 'ID_VALOR_LISTA', 'DS_URL_DOI',
         'IN_GLOSA']

    The dictionary of the data is in this file: https://dadosabertos.capes.gov.br/dataset/8498a5f7-de52-4fb9-8c62-b827cb27bcf9/resource/c6064162-3e13-4b71-ac47-114f83771002/download/metadados_detalhes_producao_intelectual_bibliografica_2017a2020.pdf
    """
    df = pd.read_csv(production_file_csv, encoding="iso-8859-1", delimiter=";")

    ddf = pd.read_csv(
        detail_file_csv, encoding="iso-8859-1", delimiter=";", low_memory=False
    )

    # Cria lista de colunas e preserva coluna ID_ADD_PRODUCAO_INTELECTUAL
    diff_cols = ["ID_ADD_PRODUCAO_INTELECTUAL"]

    # Encontre as colunas que não estão no primeiro DataFrame e extenda a lista de colunas
    diff_cols.extend(list(ddf.columns.difference(df.columns)))

    # Recrie o DDF com somente as colunas diferentes
    ddf2 = ddf[diff_cols]

    # Aplica o Merge dos 2 DFs
    dfj = pd.merge(df, ddf2, on="ID_ADD_PRODUCAO_INTELECTUAL", how="left")

    logger.info("Total of lines concatenates: %s" % str(dfj.shape))
    logger.info("Columns: %s" % set(dfj.columns))

    return dfj.to_json() if json else dfj


@celery_app.task(name="Concatenates the author with the details of the production")
def concat_author_sucupira(djf, author_files, json=False):
    """
    This task concate the author files of sucupira with the result of ``concat_article_sucupira_detail`` task.

    The djf is a dataframe with the columns:

        {'DS_OBSERVACOES', 'NM_PROGRAMA_IES', 'ID_PRODUCAO_INTELECTUAL', 'NR_SERIE', 'DS_FASCICULO', 'ID_ADD_TRABALHO_CONCLUSAO_CT', 'DS_URL_DOI', 'DH_INICIO_LINHA', 'ID_ADD_PRODUCAO_INTELECTUAL', 'NM_CIDADE', 'ID_AREA_CONCENTRACAO', 'DS_DIVULGACAO', 'DS_IDIOMA', 'NM_ENTIDADE_ENSINO', 'AN_BASE', 'ID_LINHA_PESQUISA', 'ID_VALOR_LISTA', 'NM_TIPO_PRODUCAO', 'NM_AREA_CONCENTRACAO', 'ID_PROJETO', 'CD_PROGRAMA_IES', 'ID_FORMULARIO_PRODUCAO', 'DH_INICIO_AREA_CONC', 'DS_NATUREZA', 'NM_FORMULARIO', 'SG_ENTIDADE_ENSINO', 'NR_PAGINA_FINAL', 'NM_SUBTIPO_PRODUCAO', 'ID_TIPO_PRODUCAO', 'NR_VOLUME', 'NR_PAGINA_INICIAL', 'ID_SUBTIPO_PRODUCAO', 'IN_GLOSA', 'AN_BASE_PRODUCAO', 'DS_DOI', 'NM_PRODUCAO', 'NM_PROJETO', 'DH_FIM_LINHA', 'DS_ISSN', 'IN_PRODUCAO_COM_VINCULO_TCC', 'DH_FIM_AREA_CONC', 'NM_EDITORA', 'NM_LINHA_PESQUISA', 'DS_URL'}

    The source of the author_files: https://dadosabertos.capes.gov.br/dataset/2017-a-2020-autor-da-producao-intelectual-de-programas-de-pos-graduacao-stricto-sensu

    The columns of the production_file_csv:
        ['AN_BASE', 'ID_TIPO_PRODUCAO', 'ID_SUBTIPO_PRODUCAO',
         'QT_ANO_EGRESSO_M', 'QT_ANO_EGRESSO_F', 'QT_ANO_EGRESSO_D',
         'QT_ANO_EGRESSO_R', 'CD_PROGRAMA_IES', 'NM_PROGRAMA_IES',
         'SG_ENTIDADE_ENSINO', 'NM_ENTIDADE_ENSINO',
         'ID_ADD_PRODUCAO_INTELECTUAL', 'NR_ORDEM', 'ID_PESSOA_DISCENTE',
         'ID_PESSOA_DOCENTE', 'ID_PARTICIPANTE_PPG_IES',
         'ID_PESSOA_PART_EXTERNO', 'ID_PESSOA_POS_DOC', 'ID_PESSOA_EGRESSO',
         'NM_AUTOR', 'TP_AUTOR', 'NM_TP_CATEGORIA_DOCENTE', 'NM_NIVEL_DISCENTE',
         'NM_ABNT_AUTOR', 'CD_AREA_CONHECIMENTO', 'NM_AREA_CONHECIMENTO',
         'ID_NATUREZA_ATUACAO', 'NM_NATUREZA_ATUACAO', 'ID_PAIS', 'NM_PAIS',
         'IN_GLOSA']

    The dictionary of the data is in this file: https://dadosabertos.capes.gov.br/dataset/de69242b-03b0-4d38-b5b2-a9169abd84c2/resource/40b83217-dc80-4d30-8db1-4ee91dea3ecc/download/metadados_autor_producao_intelectual_2017_2020.pdf
    """
    dfas = pd.DataFrame()

    for file in author_files:
        data = pd.read_csv(file, encoding="iso-8859-1", delimiter=";")
        dfas = pd.concat([dfas, data], axis=0)

    dfgrupa = pd.DataFrame(
        dfas.groupby(["ID_ADD_PRODUCAO_INTELECTUAL"])
        .apply(
            lambda x: x[
                ["NM_AUTOR", "NM_PROGRAMA_IES", "SG_ENTIDADE_ENSINO", "NM_ABNT_AUTOR"]
            ].to_dict(orient="records")
        )
        .rename("DICT_AUTORES")
    ).reset_index()

    djau = pd.merge(djf, dfgrupa, on="ID_ADD_PRODUCAO_INTELECTUAL", how="left")

    logger.info("Total of authors lines concatenates: %s" % str(djau.shape))
    logger.info("Columns: %s" % set(djau.columns))

    return djau.to_json() if json else djau


@celery_app.task(name="Load Sucupira data to SourceArticle")
def load_sucupira(production_file_csv, detail_file_csv, authors):
    """
    This task read the sucupira_file and add the article to ``article.models.SourceArticle``
    """

    dfau = concat_author_sucupira(
        concat_article_sucupira_detail(production_file_csv, detail_file_csv), authors
    )

    _source, _ = Source.objects.get_or_create(name="SUCUPIRA")

    for index, row in dfau.iterrows():
        doi = "" if str(row["DS_DOI"]) == "nan" else row["DS_DOI"]

        # Try to fill the doi by DS_URL_DOI
        if not doi:
            doi = "" if str(row["DS_URL_DOI"]) == "nan" else row["DS_URL_DOI"]

        specific_id = str(row["ID_ADD_PRODUCAO_INTELECTUAL"])

        article_source_dict = {
            "doi": doi,
            "specific_id": specific_id,
            "year": row["AN_BASE_PRODUCAO"],
            "source": _source,
            "raw": row.to_json(),
        }

        article, created = models.SourceArticle.create_or_update(**article_source_dict)

        logger.info(
            "####%s####, %s, %s"
            % (index.numerator, article.doi or article.specific_id, created)
        )

@celery_app.task(name="Match between institutions and affiliations")
def match_contrib_inst_aff(user_id):
    """
    This task loop to all contributor looking for contributor.institutions and find the affiliation
    """
    user = User.objects.get(id=user_id)

    for co in models.Contributor.objects.all():
        # Loop to all contributor institutions
        for inst in co.institutions.all():
            # Loop to all affiliations
            for aff in co.affiliations.all():
                # check if institution name is in aff.name
                if inst.display_name:
                    if inst.display_name in aff.name:
                        print("Update the contributor affiliation: %s(%s)" % (co, co.id))
                        aff.source = inst
                        aff.save()


@celery_app.task(name="Match between affiliation.source and Institution[MEC]")
def match_contrib_aff_source_with_inst_MEC(user_id):
    """
    This task loop to all affiliations looking for affiliation.source and find the instiution from MEC
    """

    for aff in models.Affiliation.objects.all():
        if aff.source:

            insts = Institution.objects.filter(
                name__icontains=aff.source.display_name, source="MEC"
            )
            if insts:
                aff.official = insts[0]
                aff.save()

