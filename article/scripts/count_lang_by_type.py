import pandas as pd
from django.conf import settings
from django.utils.translation import gettext as _
from core.utils import utils as core_utils


def run():
    """
    Generate a excel file type on OpenAlex.
    """
    years = ["2020", "2021", "2022"]

    url = settings.URL_API_OPENALEX + f"?group_by=type"

    _types = core_utils.fetch_data(url, json=True, timeout=30, verify=True)

    writer = pd.ExcelWriter("count_by_type.xlsx", engine="xlsxwriter")

    # DataFrame para os dados estatísticos
    df1 = pd.DataFrame(data=_types.get("group_by"))
    # df1_transpose = df1.T
    df1.to_excel(writer, sheet_name="OpenAlex types")

    for year in years: 
        for ty in _types.get("group_by"): 
            
            key_type = ty.get("key")

            url = settings.URL_API_OPENALEX + "?group_by=language&filter=type:%s,publication_year:%s" % (key_type, year)

            tyitems = core_utils.fetch_data(url, json=True, timeout=30, verify=True)

            # DataFrame para os DOIs de cada fonte
            df2 = pd.DataFrame(data=tyitems.get("group_by"))
            df2.to_excel(writer, sheet_name="lang_%s_%s" % (key_type, year))

    writer.close()
