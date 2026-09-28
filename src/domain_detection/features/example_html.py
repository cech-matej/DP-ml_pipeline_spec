from .contracts import FeatureSchema


class HtmlJsExtractor:
    def __init__(self, schema: FeatureSchema):
        self.schema = schema

    def extract(self, html: str):
        values = {
            "script_count": html.count("<script"),
            "external_script_ratio": 0.0,
            "form_count": html.count("<form"),
            "inline_js_entropy": 0.0,
        }
        return self.schema.validate(values)
