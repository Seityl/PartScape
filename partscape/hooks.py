app_name = "partscape"
app_title = "PartScape"
app_publisher = "Seityl Group Ltd."
app_description = "Auto-parts intelligence system for fleet and parts management"
app_email = "contact@seityl.com"
app_license = "MIT"
app_icon = "octicon octicon-tools"
app_color = "#1abc9c"
app_home = "/desk"

# Add to Frappe apps screen (v15+)
add_to_apps_screen = [
	{
		"name": app_name,
		"logo": "/assets/partscape/images/partscape-logo.svg",
		"title": app_title,
		"route": app_home,

	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "partscape.bundle.css"
# app_include_js = "partscape.bundle.js"

# include js, css files in header of web template
# web_include_css = "/assets/partscape/css/partscape.css"
# web_include_js = "/assets/partscape/js/partscape.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "partscape/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"Doctype": "public/js/doctype.js"}
# webform_include_css = {"Doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Purchase Order": "public/js/purchase_order.js",
    "Purchase Receipt": "public/js/purchase_receipt.js",
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Sales Order": "public/js/sales_order.js",
    "Delivery Note": "public/js/delivery_note.js",
    "Sales Invoice": "public/js/sales_invoice.js",
    "Item": "public/js/item.js",
    "Stock Entry": "public/js/stock_entry.js",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Vehicle": {
        "validate": "partscape.partscape.doctype.vehicle.vehicle.validate_vehicle",
        "after_insert": "partscape.partscape.doctype.vehicle.vehicle.after_insert_vehicle",
    },
    "Purchase Order": {
        "validate": "partscape.utils.po_hooks.validate_purchase_order",
    },
    "Stock Entry": {
        "validate": "partscape.utils.stock_hooks.validate_stock_entry",
    },
    "Customer": {
        "validate": "partscape.utils.customer_hooks.validate_customer",
        "after_insert": "partscape.utils.customer_hooks.after_insert_customer",
        "on_update": "partscape.utils.customer_hooks.on_update_customer",
    },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": [
        "partscape.api.data_pipeline.run_daily_sync"
    ],
    "hourly": [
        "partscape.api.vin_decoder.process_pending_vin_decodes"
    ],
}

# Testing
# -------

# before_tests = "partscape.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "partscape.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "partscape.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting data
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["partscape.utils.before_request"]
# after_request = ["partscape.utils.after_request"]

# Job Events
# ----------
# before_job = ["partscape.utils.before_job"]
# after_job = ["partscape.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field1}", "{field2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype}",
# 		"filter_by": "{filter_by}",
# 	},
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"partscape.auth.validate"
# ]

# Fixtures
# --------
fixtures = [
    {"dt": "Custom Field", "filters": [
        ["module", "=", "PartScape"]
    ]},
    {"dt": "Property Setter", "filters": [
        ["module", "=", "PartScape"]
    ]},
    {"dt": "Role", "filters": [
        ["name", "in", ["Fleet Manager", "Parts Clerk", "Workshop Technician"]]
    ]},
]
