#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testapp.settings")

    from django.core.management import execute_from_command_line

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    execute_from_command_line(sys.argv)
