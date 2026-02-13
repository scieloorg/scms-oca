import traceback
from datetime import datetime

class ExceptionContext:
    def __init__(self, harvest_object, log_model, fk_field):
        self.harvest_object = harvest_object
        self.log_model = log_model
        self.fk_field = fk_field
        self.exceptions = []

    def add_exception(
        self,
        exception,
        field_name,
        context_data=None,
    ):
        occurrence_date = datetime.now()
        self.exceptions.append(
            {
                "field_name": field_name,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
                "exception_traceback": traceback.format_exc(),
                "context_data": context_data or {},
                "ocorrence_date": occurrence_date
            }
        )

    def has_exceptions(self) -> bool:
        return len(self.exceptions) > 0

    def get_exceptions_by_field(self, field_name):
        return [e for e in self.exceptions if e.get("field_name") == field_name]

    def verify_obj_as_failed(self):
        if self.exceptions:
            self.harvest_object.harvest_status = "failed"
            self.harvest_object.save(update_fields=["harvest_status"])

    def mark_status_harvest(self):
        if self.exceptions:
            self.harvest_object.mark_as_failed()
        else:
            self.harvest_object.mark_as_success()

    def verify_obj_as_failed_index(self):
        if self.exceptions:
            if hasattr(self.harvest_object, "mark_as_index_failed"):
                self.harvest_object.mark_as_index_failed()
            else:
                self.harvest_object.save()

    def save_to_db(self):
        for exc in self.exceptions:
            payload = {
                self.fk_field: self.harvest_object,
                "field_name": exc.get("field_name"),
                "exception_type": exc.get("exception_type"),
                "exception_message": exc.get("exception_message"),
                "exception_traceback": exc.get("exception_traceback"),
                "context_data": exc.get("context_data", {}),
                "ocorrence_date": exc.get("ocorrence_date")
            }
            self.log_model.objects.create(**payload)
