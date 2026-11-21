"""Layout step for the sample dashboard: data -> list of element dicts.

See src/dashlib/elements/builtin.py for the built in element types.
"""


def layout(data, ctx):
    return [
        {"type": "title", "text": "Sample Dashboard",
         "subtitle": f"Generated {ctx.format_time(data['generated_at'])}"},
        {"type": "banner", "text": f"{data['label']} - NOT REAL"},
        {"type": "text", "text": data["headline"], "size": "medium"},
        {"type": "kv", "items": [[m["name"], m["value"]] for m in data["metrics"]]},
        {"type": "divider"},
        {"type": "list", "items": data["notes"], "size": "small"},
        {"type": "table", "columns": data["table"]["columns"],
         "rows": data["table"]["rows"], "widths": [3, 2, 1]},
    ]
