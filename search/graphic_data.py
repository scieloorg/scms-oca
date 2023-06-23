import logging


class GraphicData:
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

        x_stacks = {}
        y_stacks = {}

        logging.info(self._indicator.summarized["graphic_data"])
        data = {}
        for item in self._indicator.summarized["graphic_data"]:
            y_label = item["y"]
            x_label = item["x"]

            if y_label not in y_items:
                y_items.append(y_label)
            if x_label not in x_items:
                x_items.append(x_label)
                x_stacks[x_label] = item.get("attribute")

            data[(x_label, y_label)] = item["count"]

        series = []
        for x_label in x_items:
            d = {"name": x_label, "stack": x_stacks[x_label]}
            numbers = []
            for y_label in y_items:
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
            "graphic_height": 150 * len(self.graphic_data["series"]) + 200,
            "table_header": self._indicator.summarized["table_header"],
        }
        logging.info(data)
        return data

    def format_as_str_list(self, items):
        return str([item for item in items]).replace('"', "'")

    @property
    def category(self):
        # ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        return str(self.graphic_data["category"]).replace('"', "'")

    @property
    def series(self):
        items = []
        logging.info(self.graphic_data["series"])
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
        logging.info(f"serie: {serie}")
        stack_name = serie.get("stack") or "total"
        name = serie["name"]
        numbers = [n or "null" for n in serie["numbers"]]

        return """
            {
              name: '%s',
              type: 'bar',
              stack: '%s',
              barCategoryGap: '%s',
              barMinWidth: '%s',
              barMaxWidth: '%s',
              label: {
                show: true
              },
              emphasis: {
                focus: 'series'
              },
              data: %s
            }""" % (
            name,
            stack_name,
            "20%",
            "20%",
            "20%",
            str(numbers).replace("'null'", "null"),
        )
