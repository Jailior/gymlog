import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def error(message, code=400):
    def escape(s):

        # special characters
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s

    return render_template("error.html", top=code, bottom=escape(message)), code

def kg(value):
    """Format value as kg."""
    return f"{value:,.1f} kg"