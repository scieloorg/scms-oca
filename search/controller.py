import logging
from random import randrange

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.utils.translation import gettext as _

from indicator.models import Indicator
from indicator import choices as indicator_choices
from . import controller
from indicator import controller as indicator_controller


def indicator_detail(request, indicator):
    layouts = ["bar-label-rotation", "categories_1_grid", "categories_2_grids"]
    graphic_type = layouts[int(request.GET.get("g") or 1)]

    if indicator.summarized:
        try:
            version = indicator.summarized["version"]
        except KeyError:
            pass
        else:
            gb = GraphicBuilder(indicator)
            return gb.parameters
        try:
            cat2_name = indicator.summarized["cat2_name"]
        except KeyError:
            return _parameters_for_ranking_indicator(
                indicator, graphic_type, indicator.summarized.get("cat1_name")
            )
        else:
            return _parameters_for_categories_indicator(
                indicator, graphic_type, cat2_name
            )


def _parameters_for_ranking_indicator(indicator, graphic_type, cat1_name=None):
    cat1_name = cat1_name or "name"
    names = []
    values = []
    for item in indicator.summarized["items"]:
        value = item.get("count") or item.get("value")
        name = item.get(cat1_name)
        if name and value:
            names.append(name)
            values.append(value)
    graphic_height = min([len(names) * 10, 30000])
    return {
        "graphic_type": "",
        "object": indicator,
        "table_header": list(indicator.summarized["items"][0].keys()),
        "names": str(names),
        "values": str(values),
        "graphic_height": graphic_height if graphic_height > 400 else 800,
    }


def _parameters_for_categories_indicator(indicator, graphic_type, cat1_name):
    data = _get_matrix(indicator.summarized)
    if graphic_type == "bar-label-rotation":
        label_options = _get_series(
            _get_texts_label_labelOption(len(data["cat2_values"]))
        )
        cat2_name_and_values_list = _name_and_values_by_category(**data)
        cat2_data = _get_cat2_text(cat2_name_and_values_list)
        params = {
            "label_options": label_options,
            "cat2_values": data["cat2_values"],
            "cat1_values": data["cat1_values"],
            "cat2_data": cat2_data,
        }
    else:
        rows = _format_data_as_table(cat1_name, **data)
        if graphic_type == "categories_1_grid":
            # dataset-simple0
            number = len(data["cat1_values"])
            rows = _format_data_as_table("year", **data)
            rows = [rows[0]] + sorted(rows[1:])
            texts = _get_texts_for_1_grid(number)
            if number > 10:
                graphic_type = "categories_1_grid_larger"
        else:
            texts = _get_texts_for_2_grids(
                len(data["cat1_values"]), len(data["cat2_values"])
            )
        series = _get_series(texts)
        params = {
            "source": str(rows),
            "series": series,
        }
    params.update(
        {
            "graphic_type": graphic_type,
            "object": indicator,
            "table_header": list(indicator.summarized["items"][0].keys()),
        }
    )
    return params


def _get_matrix(summarized):
    items = summarized["items"]
    cat1_name = summarized["cat1_name"]
    cat2_name = summarized["cat2_name"]
    cat1_values = summarized.get("cat1_values") or []
    cat2_values = []
    matrix = {}
    for item in items:
        if item[cat1_name] not in cat1_values:
            cat1_values.append(str(item[cat1_name]))
        if item[cat2_name] not in cat2_values:
            cat2_values.append(str(item[cat2_name]))
        key = (item[cat1_name], item[cat2_name])
        matrix[key] = item["count"]
    return dict(
        cat1_values=cat1_values,
        cat2_values=cat2_values,
        matrix=matrix,
    )


def _name_and_values_by_category(matrix, cat1_values, cat2_values):
    items = []
    for cat2_value in cat2_values:
        cat_name = cat2_value
        cat_values = []
        for c1_value in cat1_values:
            key = (c1_value, cat2_value)
            cat_values.append(matrix.get(key) or 0)
        items.append((cat_name, cat_values))
    return items


def _format_data_as_table(cat1_name, matrix, cat1_values, cat2_values):
    """
    Ex.1
        cat1_name = "year"
        cat2_name = "open_access_status"

    Ex.2
        cat1_name = "practice__name"
        cat2_name = "classification"
    """
    rows = [
        [cat1_name] + [v or _("não informado") for v in cat1_values],
        # [cat1_name] + cat1_values
    ]
    for c2_value in cat2_values:
        row = [c2_value]
        for c1_value in cat1_values:
            key = (c1_value, c2_value)
            row.append(matrix.get(key) or 0)
        rows.append(row)
    return rows


def _get_series(n_and_text_tuples):
    texts = []
    for n, text in n_and_text_tuples:
        texts.extend(n * [text])
    return f"[{', '.join(texts)}]"


def _get_texts_for_2_grids(cat1_len, cat2_len):
    return [
        (cat2_len, "{ type: 'bar', seriesLayoutBy: 'row' }"),
        (cat1_len, "{ type: 'bar', xAxisIndex: 1, yAxisIndex: 1 }"),
    ]


def _get_texts_for_1_grid(cat1_len):
    return [
        (cat1_len, "{ type: 'bar' }"),
    ]


def _get_texts_label_labelOption(cat1_len):
    return [
        (cat1_len, "{ label: labelOption }"),
    ]


def _get_cat2_text(cat2_name_and_values_list):
    text = """
        {
            name: '%s', type: 'bar', barGap: 0, label: labelOption,
            emphasis: {
                focus: 'series'
            },
            data: %s
        }
        """
    items = []
    for name, values in cat2_name_and_values_list:
        items.append(text % (name, str(values)))

    return "[" + ", ".join(items) + "]"


class GraphicBuilder:
    def __init__(self, indicator):
        self._indicator = indicator

    @property
    def graphic_data(self):
        if not hasattr(self, "_graphic_data"):
            self._graphic_data = self.get_data_for_graphic()
        return self._graphic_data

    def get_data_for_graphic(self):
        """
        https://echarts.apache.org/examples/en/editor.html?c=bar-y-category-stack
        """
        x_items = []
        y_items = []

        data = {}
        items = sorted(
            self._indicator.summarized["graphic_data"], key=lambda item: item["count"]
        )
        for item in items:
            y_label = item["y"]
            x_label = item["x"]

            if y_label not in y_items:
                y_items.append(y_label)
            if x_label not in x_items:
                x_items.append(x_label)

            data[(x_label, y_label)] = item["count"]

        changed = False
        if len(x_items) > len(y_items):
            x_items, y_items = y_items, x_items
            changed = True

        series = []
        for x_label in x_items:
            d = {"name": x_label}
            numbers = []
            for y_label in y_items:
                if changed:
                    numbers.append(data.get((y_label, x_label)) or "null")
                else:
                    numbers.append(data.get((x_label, y_label)) or "null")
            d["numbers"] = numbers
            series.append(d)

        return {
            "category": y_items,
            "series": series,
        }

    @property
    def parameters(self):
        data = {
            "graphic_type": "bar-y-category-stack",
            "object": self._indicator,
            "category": self.category,
            # "serie_names": self.serie_names,
            "series": self.series,
            "graphic_height": 150 * len(self.graphic_data["series"]) + 300,
            "table_header": self._indicator.summarized["table_header"],
            "colors": self.format_as_str_list(self.colors),
        }
        logging.info(data)
        return data

    def format_as_str_list(self, items):
        return str([item for item in items]).replace('"', "'")

    @property
    def colors(self):
        items = []
        for i in self.category:
            while True:
                number = randrange(5000, 2 ** 24)
                hex_color = "#" + str(number)
                if hex_color not in items:
                    items.append(hex_color)
                    break
        return items

    @property
    def category(self):
        # ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return str(self.graphic_data["category"]).replace('"', "'")

    @property
    def series(self):
        items = []
        for serie in self.graphic_data["series"]:
            items.append(self.serie_item(serie))
        return ",".join(items)

    def serie_item(self, serie):
        """
        {
          name: 'Affiliate Ad',
          type: 'bar',
          stack: 'total',
          label: {
            show: true
          },
          emphasis: {
            focus: 'series'
          },
          data: [220, 182, 191, 234, 290, 330, 310]
        }
        """
        name = serie["name"]
        numbers = [n or "null" for n in serie["numbers"]]
        logging.info(name)
        logging.info(numbers)

        return """
            {
              name: '%s',
              type: 'bar',
              stack: 'total',
              barMaxWidth: '%s',
              barGap: '%s',
              label: {
                show: true
              },
              emphasis: {
                focus: 'series'
              },
              data: %s
            }""" % (
            name,
            "30px",
            "10px",
            str(numbers).replace("'null'", "null"),
        )
