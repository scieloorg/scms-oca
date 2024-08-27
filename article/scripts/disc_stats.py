import pandas as pd
import pysolr
from django.conf import settings
from django.utils.translation import gettext as _

solr = pysolr.Solr(
    settings.HAYSTACK_CONNECTIONS["default"]["URL"],
    timeout=settings.HAYSTACK_CONNECTIONS["default"]["SOLR_TIMEOUT"],
)

def run():
    """
    Generate a excel file about the sucupira and openalex data.
    """

    sources = ["OPENALEX", "SUCUPIRA"]

    for source in sources:
        data = []
        item = {}
        filters = {
                    "Total de registros com programa": "source:%s AND program:*" % source, 
                    "Total de registros com DOI": "source:%s AND doi:*" % source, 
                    "Total de registros sem DOI": "source:%s AND -doi:*" % source, 
                    "Total de registros com programa e com DOI": "source:%s AND doi:* AND program:*" % source, 
                    "Total de registros com programa e sem DOI": "source:%s AND -doi:* AND program:*" % source, 
                    "Total de registros com programa e sem DOI": "source:%s AND -doi:* AND program:*" % source, 
                    "Total de registros sem programa e sem DOI": "source:%s AND -doi:* AND -program:*" % source, 
                    "Total de registros": "source:%s" % source, 
                }

        for label, filter in filters.items(): 
            result = solr.search(filter)
            item[label] = result.hits
            
        data.append(item)

        writer = pd.ExcelWriter("discrete_statistics_%s.xlsx" % source, engine="xlsxwriter")

        # DataFrame para os dados estatísticos 
        df1 = pd.DataFrame(data=data)
        df1_transpose = df1.T
        df1_transpose.to_excel(writer, sheet_name="Discrete Statistics %s" % source)

        # DataFrame para os DOIs de cada fonte
        q = "source:%s AND doi:*" % source
        result = solr.search(q, rows=1000000, fl="doi")
        df2 = pd.DataFrame(data={"doi":[r.get("doi") for r in result.docs]})
        df2.to_excel(writer, sheet_name="DOIs %s" % source)

        writer.close()