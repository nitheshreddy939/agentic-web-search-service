"""Built-in demo site — realistic, markup-heavy form pages.

These pages deliberately carry the chrome of a real site (nav, nested
layout divs, inline styles, analytics script) because that is exactly the
bloat the accessibility tree strips out. The 15 eval scenarios in
``evals/scenarios.py`` are defined against these pages.
"""
from __future__ import annotations

_CHROME_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{title}</title><style>body{{font-family:system-ui}} .wrap{{max-width:720px;margin:auto}}
.card{{border:1px solid #ddd;padding:24px;border-radius:12px}} label{{display:block;margin:12px 0 4px}}
input,select,textarea{{width:100%;padding:8px}} button{{margin-top:16px;padding:10px 22px}}</style>
<script>window.analytics={{track:function(){{}},id:'UA-DEMO-123456'}};</script></head>
<body><div class="outer"><div class="layout"><header class="site-header"><nav class="main-nav">
<a href="/demo/contact">Home</a> <a href="/demo/contact">Products</a> <a href="/demo/contact">Pricing</a>
<a href="/demo/contact">Docs</a> <a href="/demo/contact">Support</a></nav></header>
<main><div class="wrap"><div class="breadcrumb">Home / Forms / {title}</div>
<div class="card"><h1>{title}</h1>"""

_CHROME_TAIL = """</div><aside class="promo"><div class="promo-card"><h2>Why us</h2>
<p>Trusted by teams everywhere. Fast, reliable, secure.</p></div></aside></div></main>
<footer class="site-footer"><div>About Careers Privacy Terms Contact Sitemap</div>
<div>Copyright 2026 Demo Corp. All rights reserved.</div></footer></div></div>
<script>console.log('pageview');</script></body></html>"""


def page(title: str, form_html: str, success: str) -> str:
    form = (
        f'<form method="get" action="/demo/success">'
        f'<input type="hidden" name="msg" value="{success}">{form_html}'
        f"</form>"
    )
    return _CHROME_HEAD.format(title=title) + form + _CHROME_TAIL


def field(label: str, fid: str, ftype: str = "text", extra: str = "") -> str:
    return (f'<div class="field-row"><div class="field-inner">'
            f'<label for="{fid}">{label}</label>'
            f'<input id="{fid}" name="{fid}" type="{ftype}" {extra}></div></div>')


def select(label: str, fid: str, options: list[str]) -> str:
    opts = "".join(f'<option>{o}</option>' for o in options)
    return (f'<div class="field-row"><label for="{fid}">{label}</label>'
            f'<select id="{fid}" name="{fid}">{opts}</select></div>')


def textarea(label: str, fid: str) -> str:
    return (f'<div class="field-row"><label for="{fid}">{label}</label>'
            f'<textarea id="{fid}" name="{fid}" rows="4"></textarea></div>')


def button(label: str = "Submit") -> str:
    return f'<button type="submit">{label}</button>'


# slug -> (title, html, goal fields, success text, submit label)
SCENARIOS: dict[str, dict] = {
    "contact": dict(
        title="Contact Us", success="Contact received",
        html=field("Full Name", "name") + field("Email", "email", "email")
        + textarea("Message", "message") + button("Send Message"),
        fields={"Full Name": "Nithesh Reddy", "Email": "nithesh@example.com", "Message": "Hello, I need help with my account."},
        submit="Send Message"),
    "job-application": dict(
        title="Job Application", success="Application submitted",
        html=field("Full Name", "name") + field("Email", "email", "email") + field("Phone", "phone", "tel")
        + select("Role", "role", ["Backend Engineer", "Frontend Engineer", "Full Stack Engineer"]) + button("Submit Application"),
        fields={"Full Name": "Nithesh Reddy", "Email": "nithesh@example.com", "Phone": "4085551234", "Role": "Backend Engineer"},
        submit="Submit Application"),
    "newsletter": dict(
        title="Newsletter Signup", success="Subscribed successfully",
        html=field("Email", "email", "email") + button("Subscribe"),
        fields={"Email": "nithesh@example.com"}, submit="Subscribe"),
    "login": dict(
        title="Sign In", success="Welcome back",
        html=field("Email", "email", "email") + field("Password", "password", "password") + button("Sign In"),
        fields={"Email": "nithesh@example.com", "Password": "demo-password-123"}, submit="Sign In"),
    "registration": dict(
        title="Create Account", success="Account created",
        html=field("Full Name", "name") + field("Email", "email", "email")
        + field("Password", "password", "password") + field("Phone", "phone", "tel") + button("Register"),
        fields={"Full Name": "Nithesh Reddy", "Email": "nithesh@example.com", "Password": "demo-password-123", "Phone": "4085551234"},
        submit="Register"),
    "checkout": dict(
        title="Checkout", success="Order placed",
        html=field("Full Name", "name") + field("Street Address", "address")
        + field("City", "city") + field("ZIP Code", "zip") + button("Place Order"),
        fields={"Full Name": "Nithesh Reddy", "Street Address": "1920 NE Terre View Dr", "City": "Pullman", "ZIP Code": "99163"},
        submit="Place Order"),
    "appointment": dict(
        title="Book Appointment", success="Appointment booked",
        html=field("Full Name", "name") + field("Email", "email", "email")
        + field("Date", "date", "date") + select("Time Slot", "slot", ["9:00 AM", "11:00 AM", "2:00 PM"]) + button("Book"),
        fields={"Full Name": "Nithesh Reddy", "Email": "nithesh@example.com", "Date": "2026-11-02", "Time Slot": "11:00 AM"},
        submit="Book"),
    "survey": dict(
        title="Quick Survey", success="Survey completed",
        html=field("Full Name", "name")
        + '<div><label><input type="radio" name="rating" value="yes"> Satisfied</label></div>'
        + textarea("Comments", "comments") + button("Submit Survey"),
        fields={"Full Name": "Nithesh Reddy", "Comments": "Great service, fast support."},
        submit="Submit Survey"),
    "search": dict(
        title="Search", success="Search results",
        html=field("Search", "q", "search") + button("Search"),
        fields={"Search": "browser agents"}, submit="Search"),
    "rsvp": dict(
        title="Event RSVP", success="RSVP confirmed",
        html=field("Full Name", "name") + field("Email", "email", "email")
        + select("Guests", "guests", ["1", "2", "3"]) + button("Confirm RSVP"),
        fields={"Full Name": "Nithesh Reddy", "Email": "nithesh@example.com", "Guests": "2"},
        submit="Confirm RSVP"),
    "feedback": dict(
        title="Feedback", success="Feedback received",
        html=field("Email", "email", "email") + select("Rating", "rating", ["5 - Excellent", "4 - Good", "3 - Okay"])
        + textarea("Feedback", "feedback") + button("Send Feedback"),
        fields={"Email": "nithesh@example.com", "Rating": "5 - Excellent", "Feedback": "The agent filled this form in seconds."},
        submit="Send Feedback"),
    "address-update": dict(
        title="Update Address", success="Address updated",
        html=field("Street Address", "address") + field("City", "city")
        + field("State", "state") + field("ZIP Code", "zip") + button("Save Changes"),
        fields={"Street Address": "500 College Ave", "City": "Pullman", "State": "WA", "ZIP Code": "99163"},
        submit="Save Changes"),
    "password-reset": dict(
        title="Reset Password", success="Reset link sent",
        html=field("Email", "email", "email") + button("Send Reset Link"),
        fields={"Email": "nithesh@example.com"}, submit="Send Reset Link"),
    "travel-search": dict(
        title="Flight Search", success="Flights found",
        html=field("From City", "from") + field("To City", "to")
        + field("Departure Date", "date", "date") + button("Search Flights"),
        fields={"From City": "Seattle", "To City": "San Francisco", "Departure Date": "2026-12-10"},
        submit="Search Flights"),
    "support-ticket": dict(
        title="Support Ticket", success="Ticket created",
        html=field("Full Name", "name") + field("Email", "email", "email")
        + select("Priority", "priority", ["Low", "Medium", "High"])
        + textarea("Issue Description", "issue") + button("Create Ticket"),
        fields={"Full Name": "Nithesh Reddy", "Email": "nithesh@example.com", "Priority": "High",
                "Issue Description": "Login page returns a 500 error."},
        submit="Create Ticket"),
}
