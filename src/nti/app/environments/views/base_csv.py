import csv

from io import StringIO
from requests.structures import CaseInsensitiveDict

from nti.app.environments.views.base import BaseView


class CSVBaseView(BaseView):

    _byte_order_mark = '\ufeff'

    def header(self, params=None):
        raise NotImplementedError

    def filename(self):
        raise NotImplementedError

    def records(self, params):
        raise NotImplementedError

    def row_data_for_record(self, record):
        raise NotImplementedError

    def row_data_with_filter(self, data, columns):
        empty, row = True, []
        for column in columns:
            col_data = data.get(column) if data.get(column,None) != None else ""
            if         empty \
                and col_data != "":
                empty = False
            row.append(col_data)
        return empty, row

    def validate_params(self, params=None):
        pass

    def __call__(self):
        params = CaseInsensitiveDict(self.request.params)
        self.validate_params(params)

        response = self.request.response
        response.content_encoding = str('identity')
        response.content_type = str('text/csv; charset=UTF-8')
        response.content_disposition = str('attachment; filename="%s"' % self.filename())

        stream = StringIO()
        if self._byte_order_mark:
            stream.write(self._byte_order_mark)
        writer = csv.writer(stream)

        #sequence for records and header is important.
        records = self.records(params)
        columns = self.header(params)

        if columns is not None:
            writer.writerow(columns)
            for record in records:
                data = self.row_data_for_record(record)
                empty, row = self.row_data_with_filter(data, columns)
                if not empty:
                    writer.writerow(row)
        else:
            for record in records:
                writer.writerow(record)

        stream.flush()
        stream.seek(0)
        response.text = stream.getvalue()
        return response
