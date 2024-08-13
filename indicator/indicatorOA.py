import logging

from django.conf import settings
from pyalex import Works

from search import choices


class Indicator:
    """This class do all the necessary work to generate the discrete mathematics
       of Brazilian production data stored and modeled in OCABr based on a
       lucene index.

    Attributes:
        filters: A list of dict with key:value to filter the data on indice
                 Example: [{"apc": "yes"}, {"apc": "no"}] (Lucene query syntax)
        title: The title of the indicator.
        facet_by: Indicates by which data we will group the result.
        context_by: This param is a list of string that define keys on the index
        to dynamic generate a filters.
                Example: ["thematic_level_2"]
                This will produce ["thematic_level_2"]*["a", "b", "c"]
                The result will be [
                                    "thematic_level_2:a",
                                    "thematic_level_2:b",
                                    "thematic_level_2:c"
                                   ]
        default_filter: Can be define a default dict with Lucene query syntax
        key:value to be add on filters param, default: {"year": "[2012 TO 2023]"}.
        solr_instance: A instance of pysolr.Sorl, more about see:
        https://pypi.org/project/pysolr/
    """

    def __init__(
        self,
        filters,
        group_by="publication_year",
        range_filter={"filter_name": "year", "range": {"start": 2014, "end": 2023}},
    ):
        """Initializes the instance indicator class.

        Args:
          filters: List of filters.
          group_by: DEfine the group Ex.: is_oa, oa_status, best_oa_location.license
          fill_range: this set a default values to be filled on range filter. Ex.: { "filter_name": "year", "range": {"start": 2014, "end": 2023}}
        """
        self.filters = filters
        self.group_by = group_by
        # range_filter = { "filter_name": "year", "range": {"start": 2014, "end": 2023}}
        self.range_filter = range_filter
        self.logger = logging.getLogger(__name__)

    def generate(self, key=False):
        """This will produce the discrete mathematics based on filters to index.

        Args:
            No args

        Returns:
            A list of dictionary, something like:
                [
                    {
                        "example_key": {
                            "items": [
                                "2012",
                            ],
                            "counts": [
                                1856,
                            ],
                        }
                    },
                ]

        Raises:
            This function dont raise any exception
        """

        ret = {}
        counts = []

        for year in range(
            int(self.range_filter.get("range").get("start")),
            int(self.range_filter.get("range").get("end")) + 1,
        ):
            result, meta = (
                Works()
                .filter(**self.filters)
                .filter(publication_year=year)
                .group_by(self.group_by)
                .get(return_meta=True)
            )
            print(meta)
            if not key:
                for re in result:
                    key_display_name = re.get("key_display_name")
                    count = re.get("count")
                    ret.setdefault(key_display_name, []).append(count)
            else:
                if result:
                    counts.append(result[0].get("count"))

        print(ret)
        return ret if not counts else counts

    def generate_by_region(
        self, target_key=False, regions=choices.scimago_region, indicator_list=False, indicator_dict=True
    ):
        """This will produce the discrete mathematics based on filters to index.

        Args:
            No args

        Returns:
            A list of dictionary, something like:
                {
                'Latin America': {
                    '2023': 449364,
                    '2022': 454245,
                    '2021': 514552,
                    '2020': 504690,
                    '2019': 431683,
                    '2018': 399696,
                    '2015': 332322,
                    '2014': 280477,
                    '2017': 370061,
                    '2016': 335551},
                'Asiatic Region': {
                    '2023': 2504273,
                    '2022': 2367105,
                    '2021': 2161980,
                    '2020': 1944761,
                    '2019': 1670192,
                    '2018': 1482810,
                    '2016': 1181621,
                    '2017': 1310592,
                    '2014': 1260167,
                    '2015': 1217707}
                }
        Raises:
            This function dont raise any exception
        """

        # Loop to all regions
        ret = {} 
        if target_key:
            if target_key in regions:
                regions =  {target_key: regions[target_key]}

        for region, keys in regions.items():
            # Each region have a list of keys
            for key in keys:

                result, meta = (
                    Works()
                    .filter(**self.filters)
                    .filter(institutions={"country_code": key})
                    .filter(
                        publication_year=str(
                            self.range_filter.get("range").get("start")
                        )
                        + "-"
                        + str(self.range_filter.get("range").get("end"))
                    )
                    .group_by(self.group_by)
                    .get(return_meta=True)
                )

                for re in result:
                    count = re.get("count")
                    print(ret)
                    # Se a região está no dicionário
                    if region in ret:
                        # Se a chave de ano está na região
                        if re.get("key") in ret.get(region):
                            # adiciona na região o valor que tem mais o count
                            ret.get(region).update(
                                {re.get("key"): ret.get(region)[re.get("key")] + count}
                            )
                        else:
                            # atualizar o dicionário com o ano e o valor de count
                            ret.get(region).update({re.get("key"): count})
                    else:
                        # cria a região no dicionário com o valor do ano com um valor de count inicial
                        ret.setdefault(region, {re.get("key"): count})

        if indicator_list:
            return self.convert_to_indicator_list(ret) 
        elif indicator_dict:
            return self.convert_to_indicator_dict(ret) 
        else:
            ret


    def generate_by_country(
        self, target_key=False, countries=choices.country_list, indicator_list=False, indicator_dict=True
    ):
        """This will produce the discrete mathematics based on filters to index.

        Args:
            No args

        Returns:
            A list of dictionary, something like:
                {
                    'us': {
                        '2023': 449364,
                        '2022': 454245,
                        '2021': 514552,
                        '2020': 504690,
                        '2019': 431683,
                        '2018': 399696,
                        '2015': 332322,
                        '2014': 280477,
                        '2017': 370061,
                        '2016': 335551},
                    'ch': {
                        '2023': 2504273,
                        '2022': 2367105,
                        '2021': 2161980,
                        '2020': 1944761,
                        '2019': 1670192,
                        '2018': 1482810,
                        '2016': 1181621,
                        '2017': 1310592,
                        '2014': 1260167,
                        '2015': 1217707}
                    }
                }
        Raises:
            This function dont raise any exception
        """

        # Loop to all countries
        ret = {} 

        for country, key in countries:

            result, meta = (
                Works()
                .filter(**self.filters)
                .filter(authorships={"institutions": {"country_code": key}})
                .filter(
                    publication_year=str(
                        self.range_filter.get("range").get("start")
                    )
                    + "-"
                    + str(self.range_filter.get("range").get("end"))
                )
                .group_by(self.group_by)
                .get(return_meta=True)
            )

            for re in result:
                count = re.get("count")
                print(ret)
                # Se a região está no dicionário
                if country in ret:
                    # Se a chave de ano está na região
                    if re.get("key") in ret.get(country):
                        # adiciona na região o valor que tem mais o count
                        ret.get(country).update(
                            {re.get("key"): ret.get(country)[re.get("key")] + count}
                        )
                    else:
                        # atualizar o dicionário com o ano e o valor de count
                        ret.get(country).update({re.get("key"): count})
                else:
                    # cria a região no dicionário com o valor do ano com um valor de count inicial
                    ret.setdefault(country, {re.get("key"): count})

        if indicator_list:
            return self.convert_to_indicator_list(ret) 
        elif indicator_dict:
            print(self.convert_to_indicator_dict(ret))
            return self.convert_to_indicator_dict(ret) 
        else:
            ret


    def convert_to_indicator_list(self, data):
        """Converts a dictionary of items and years into a formatted list.

        Args:
            data: A dictionary in the specified format.

        Returns:
            A list in the desired format.
        """

        return [
            {
                item: {
                    "items": list(year_data.keys()),
                    "counts": list(year_data.values()),
                }
            }
            for item, year_data in data.items()
        ]

    def convert_to_indicator_dict(self, data):
        """Converts a dictionary of regions and years into a formatted dict.

        Args:
            data: A dictionary in the specified format.

        Returns:
            A list in the desired format.
        """

        return { region: list(year_data.values()) for region, year_data in data.items() }
