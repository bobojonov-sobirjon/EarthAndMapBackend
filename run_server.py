#!/usr/bin/env python
"""Django serverni 8009-portda ishga tushirish."""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8009'])
