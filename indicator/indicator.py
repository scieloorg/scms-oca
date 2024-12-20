import itertools
import json
import logging
import os
import re
import zipfile

import pandas as pd
import pysolr
from django.conf import settings


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
        title,
        description,
        facet_by,
        context_by=None,
        default_filter={},
        # range_filter={"filter_name": "year", "range": {"start": 2014, "end": 2014}},
        range_filter=None,
        fill_range=True,
        fill_range_value=0,
        solr_instance=None,
        include_all=False,
    ):
        """Initializes the instance indicator class.

        Args:
          filters: List of Lucene query syntax.
          title: The title of the indicador.
          facet_by: A string with the facet of the index in which the data will
          the group.
          context_by: A list of string that define keys on the index to dynamic
          generate a filters and consequently indicadors, this generate a produt
          of this items.
          fill_range: this set a default values to be filled on range filter.
          default_filter: A lucene query syntax to be default on filters.
          include_all: Include all itens since the values is 0 to all key(years)
        """
        self.filters = filters
        self.title = title
        self.facet_by = facet_by
        self.context_by = context_by
        self.default_filter = default_filter
        self.range_filter = range_filter
        self.fill_range = fill_range
        self.fill_range_value = fill_range_value
        self.ids = {}
        self.keys = []
        self.include_all = include_all
        self.description = description

        self.solr = solr_instance or pysolr.Solr(
            settings.HAYSTACK_CONNECTIONS["default"]["URL"],
            timeout=settings.HAYSTACK_CONNECTIONS["default"]["SOLR_TIMEOUT"],
        )
        self.result = None

        self.logger = logging.getLogger(__name__)

    def _convert_list_dict(self, lst):
        """Convert list to dict.

        Args:
            lis: A list to the convert, example:
            ['a', 1, 'c', 2, 'e', 3]

        Returns:
            This function return a dict, something like this:
            ['a: 1, 'c', 2, 'e', 3]

        Raises:
            This function dont raise any exception
        """
        res_dct = map(lambda i: (lst[i], lst[i + 1]), range(len(lst) - 1)[::2])
        return dict(res_dct)

    def _product(self, *lst):
        """Generate a product of lists

        Args:
            lst: Can be a list of lists, like:

                [["a", "b", "c"], ["1", "2", "3"]]

        Returns:
            Produce a list with the product of [["a", "b", "c"], ["1", "2", "3"]], like:
                [
                 ('a', '1'),
                 ('a', '2'),
                 ('a', '3'),
                 ('b', '1'),
                 ('b', '2'),
                 ('b', '3'),
                 ('c', '1'),
                 ('c', '2'),
                 ('c', '3')
                ]

        Raises:
            This function dont raise any exception
        """
        return list(itertools.product(*lst))

    def get_facet(self, facet_name, result=None, convert_dict=True, sort=True):
        """Get the facet from index.

        Args:
            result: This is a pysolr.Results.

        Returns:
            This method can return None when ``facet_name`` doesnt exists
            Can return a list with the facet result or a dict.

        Raises:
            This function dont raise any exception
        """

        result = result or self.solr.search("*:*")

        facet = result.facets.get("facet_fields").get(facet_name)

        if facet: 
            if convert_dict:
                return (
                    dict(sorted(self._convert_list_dict(facet).items())) if sort else facet
                )
            else:
                return facet

    def update_filters(self, filter_dict):
        """This update the self.filters, this check if exists default filter and
        the range filter.

        Args:
            No args, this change an instance attribute.

        Returns:
            No return.

        Raises:
            This function dont raise any exception
        """

        self.filters.append(filter_dict)

    def get_ids(self):
        """
        This will return all the ids to the indicator.
        """
        return self.ids

    def get_keys(self):
        """
        This will return all the ids to the indicator.
        """
        return self.get_facet(self.facet_by).keys()

    def dynamic_filters(self, key_list=None):
        """
        This get the facets in index and update the filters attribute.

        Args:
            No args

        Returns:
            No args, this change an self.filters instance attribute.

        Raises:
            This function dont raise any exception
        """

        q = "%s" % ("*:*")

        result = self.solr.search(q)
        context_list = []

        for context in self.context_by:
            context_result = self.get_facet(context, result)
            if key_list:
                inter_list=[]
                for key in context_result.keys():
                    if key in key_list:
                        inter_list.append('%s:"%s"' % (context, key))
                context_list.append(inter_list)
            else:
                context_list.append(
                    ['%s:"%s"' % (context, keys) for keys in context_result.keys()]
                )

        context_prod = self._product(*context_list)

        for prod in context_prod:
            self.update_filters(
                {f'{p.split(":")[0]}': f'{p.split(":")[1]}' for p in prod}
            )

        self.logger.info(self.filters)

    def generate(self, key_list=None):
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
        ret = []
        q_list = []

        if self.context_by:
            self.dynamic_filters(key_list)

        for filter in self.filters:
            filters = {}
            # add the default filter
            filters.update(filter)
            filters.update(self.default_filter)

            if self.range_filter:
                filters.update(
                    {
                        self.range_filter.get("filter_name"): "[%s TO %s]"
                        % (
                            self.range_filter.get("range").get("start"),
                            self.range_filter.get("range").get("end"),
                        )
                    }
                )

            q = "%s" % (" AND ".join(["%s:%s" % (k, v) for k, v in filters.items()]))

            self.logger.info(q)
            q_list.append(q)

            result = self.solr.search(q)

            result = self._convert_list_dict(
                result.facets.get("facet_fields").get(self.facet_by)
            )

            result = dict(sorted(result.items()))

            # fill the range
            # range with end +1 to include the last item
            if self.fill_range:
                if self.range_filter:
                    for dy in range(
                        self.range_filter.get("range").get("start"),
                        self.range_filter.get("range").get("end") + 1,
                    ):
                        result.setdefault(str(dy), self.fill_range_value)
                else:
                    # this is the keys facet
                    for key in self.get_facet(self.facet_by).keys():
                        result.setdefault(str(key), self.fill_range_value)

            result = dict(sorted(result.items()))

            values = result.values()

            result = dict(
                {
                    "%s"
                    % (
                        "-".join(
                            [
                                value.replace('"', "").lower().strip()
                                for value in filter.values()
                            ]
                        ),
                    ): {
                        "items": [k for k in sorted(result.keys())],
                        "counts": [v for v in values],
                        "filters": q_list,
                    }
                }
            )

            if self.include_all:
                ret.append(result)
            else:
                if any(values):
                    ret.append(result)

        return ret

    def build_filters(self, filter_by_year=False):
        """
        This will build all filters.

        This return something a list with all filters, something like:

        """
        filters = {}
        filters_list = []

        for filter in self.filters:

            filters.update(filter)
            filters.update(self.default_filter)

            if not filter_by_year:

                if self.range_filter:
                    filters.update(
                        {
                            self.range_filter.get("filter_name"): "[%s TO %s]"
                            % (
                                self.range_filter.get("range").get("start"),
                                self.range_filter.get("range").get("end"),
                            )
                        }
                    )

                q = "%s" % (
                    " AND ".join(["%s:%s" % (k, v) for k, v in filters.items()])
                )

                self.logger.info(q)
                filters_list.append(q)
            else:
                for year in range(
                    self.range_filter.get("range").get("start"),
                    self.range_filter.get("range").get("end") + 1,
                ):
                    filters.update(
                        {
                            self.range_filter.get("filter_name"): "[%s TO %s]"
                            % (
                                year,
                                year,
                            )
                        }
                    )

                    q = "%s" % (
                        " AND ".join(["%s:%s" % (k, v) for k, v in filters.items()])
                    )
                    self.logger.info(q)
                    filters_list.append(q)

        return filters_list

    def save_csv(
        self,
        data_dict,
        dir_name,
        file_name,
        join=True,
        joins_columns=[
            "contributors",
            "concepts",
            "affiliations",
            "thematic_level_0",
            "thematic_level_1",
            "thematic_level_2",
            "institutions",
            "sources",
            "states",
            "regions",
            "license",
            "cities",
        ],
        join_columns_caracter="|",
    ):
        # Cria um DataFrame a partir do dicionário
        df = pd.DataFrame.from_dict(data_dict, orient="columns")

        if join:
            for column in joins_columns:
                if column in df:
                    df[column] = df[column].apply(
                        lambda x: (
                            join_columns_caracter.join(x) if type(x) == list else ""
                        )
                    )

        # Salva o DataFrame em um arquivo CSV
        df.to_csv(os.path.join(dir_name, file_name), index=False)

        zip_path = self.create_zip_file(dir_name, file_name, suffix="csv")

        self.logger.info(f"Data has been saved to '{zip_path}' successfully.")

        return zip_path

    def create_zip_file(self, dir_name, file_name, suffix=None, origin_file=False):

        file_path = os.path.join(dir_name, file_name)

        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            self.logger.info(f"File '{file_path}' not found.")
            return None

        # Define o nome do arquivo ZIP
        if suffix:
            zip_file = os.path.join(
                dir_name, f"{os.path.splitext(file_path)[0]}{suffix}.zip"
            )
        else:
            zip_file = os.path.join(dir_name, f"{os.path.splitext(file_path)[0]}.zip")

        # Cria um arquivo ZIP
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Adiciona o arquivo ao arquivo ZIP
            zipf.write(file_path, os.path.basename(file_path))

        if not origin_file:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"File '{file_path}' removed successfully.")
            else:
                self.logger.info(f"File '{file_path}' not found.")

        self.logger.info(f"ZIP file '{zip_file}' created successfully.")

        return zip_file

    def save_jsonl(self, dicts, dir_name, file_name):
        if not dicts:
            self.logger.info("The dicts is empty.")
            return

        # Abre o arquivo JSONLines em modo de escrita
        with open(os.path.join(dir_name, file_name), "w") as jsonl_file:
            # Escreve cada dicionário como uma linha no arquivo JSONLines
            for dictionary in dicts:
                jsonl_file.write(json.dumps(dictionary) + "\n")

        zip_file = self.create_zip_file(dir_name, file_name, suffix="jsonl")

        self.logger.info(
            f"The data has been saved to the file '{zip_file}' successfully."
        )

        return zip_file

    def get_data(self, rows=10000, files_by_year=False):
        """
        This get the data from Lucene.

        Args:
            No args

        Returns:
            Return a string from the format.

        Raises:
            This function dont raise any exception
        """

        unwanted_chars = [":", "AND", '"', "[", "]", " "]

        if not files_by_year:

            for q in self.build_filters():
                data = []
                ids = set()

                result = self.solr.search(q, cursorMark="*", sort="id asc", rows=rows)

                for doc in result:
                    # Ensure that the id is not in ``data``.
                    if not doc.get("id") in ids:
                        data.append(doc)
                        ids.add(doc.get("id"))

                clq = q
                for char in unwanted_chars:
                    clq = clq.replace(char, "_")

                self.logger.info("Filter: %s (%s)" % (q, len(data)))

                yield (
                    "%s" % (str(re.sub(r"_{2,}", "_", clq.lower()))),
                    data,
                )
        else:

            for q in self.build_filters(filter_by_year=True):
                data = []
                ids = set()
                result = self.solr.search(q, cursorMark="*", sort="id asc", rows=rows)

                for doc in result:
                    # Ensure that the id is not in ``data``.
                    if not doc.get("id") in ids:
                        data.append(doc)
                        ids.add(doc.get("id"))

                clq = q
                for char in unwanted_chars:
                    clq = clq.replace(char, "_")

                self.logger.info("Filter: %s (%s)" % (q, len(data)))

                yield (
                    "%s" % (str(re.sub(r"_{2,}", "_", clq.lower()))),
                    data,
                )
