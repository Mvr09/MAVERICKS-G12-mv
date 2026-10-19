"""Credential-aware packaging check; never prints values.

Short administrator passwords can coincide with ports, dates or gazetteer data.
Those natural occurrences are not credential assignments. Opaque credentials
remain checked everywhere; even short passwords are rejected in assignments.
"""
import re


def credential_match(content: bytes, values: dict):
    text=content.decode('utf-8',errors='ignore')
    for name in ('TYPESAFE_API_KEY','ADMIN_PASSWORD','SESSION_SECRET'):
        value=values.get(name)
        if not value:continue
        if name!='ADMIN_PASSWORD' or len(value)>=12:
            if value.encode() in content:return name
        else:
            prefix=r'''(?i)(?:admin[_-]?password|password|contraseña)["']?\s*[:=]\s*["']?'''
            if re.search(prefix+re.escape(value)+r'''(?=["'\s,;}]|$)''',text):return name
    return None
