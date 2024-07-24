import logging

from django.conf import settings
from pyalex import Works


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
        print(self.filters)
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
        print(counts)
        print(ret)
        return ret if not counts else counts


    def generate_by_country_code(self, keys=[]):
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

        for key in keys:
            print(ret)
            for year in range(
                int(self.range_filter.get("range").get("start")),
                int(self.range_filter.get("range").get("end")) + 1,
            ):
                result, meta = (
                    Works()
                    .filter(**self.filters)
                    .filter(institutions={"country_code": key})
                    .filter(publication_year=year)
                    .group_by(self.group_by)
                    .get(return_meta=True)
                )
                print(meta)           
                
                for re in result:
                    key_display_name = re.get("key_display_name")
                    count = re.get("count")
                    if key_display_name in ret:
                        ret[key_display_name] = ret.get(key_display_name) + count
                    else:
                        ret.setdefault(key_display_name, count)
            print(ret)
        return ret 


    def filter_dictionary(dictionary, valid_licenses):
        """Filters a dictionary of licenses, grouping unmatched entries under 'others'.

        Args:
            dictionary (dict): The dictionary of licenses.
            valid_licenses (list): The list of valid licenses.

        Returns:
            dict: The filtered dictionary.
        """

        filtered_dict = {}
        others = []

        for key, value in dictionary.items():
            normalized_key = key.replace(" ", "-").upper()
            if any(normalized_key in license for license in valid_licenses):
                filtered_dict[key] = value
            else:
                others.extend(value)

        if others:
            filtered_dict['others'] = others

        return filtered_dict