# Copyright (C) 2016-present the ayncpg authors and contributors
# <see AUTHORS file>
#
# This module is part of asyncpg and is released under
# the Apache 2.0 License: http://www.apache.org/licenses/LICENSE-2.0


import re


def _quote_ident(ident):
    return f""""{ident.replace('"', '""')}\""""


def _quote_literal(string):
    return f"""'{string.replace("'", "''")}'"""


async def _mogrify(conn, query, args):
    """Safely inline arguments to query text."""
    # Introspect the target query for argument types and
    # build a list of safely-quoted fully-qualified type names.
    ps = await conn.prepare(query)
    paramtypes = []
    for t in ps.get_parameters():
        pname = f'_{t.name[:-2]}' if t.name.endswith('[]') else t.name
        paramtypes.append(f'{_quote_ident(t.schema)}.{_quote_ident(pname)}')
    del ps

    # Use Postgres to convert arguments to text representation
    # by casting each value to text.
    cols = [
        f'quote_literal(${i}::{t}::text)'
        for i, t in enumerate(paramtypes, start=1)
    ]

    textified = await conn.fetchrow(
        'SELECT {cols}'.format(cols=', '.join(cols)), *args)

    # Finally, replace $n references with text values.
    return re.sub(
        r'\$(\d+)\b', lambda m: textified[int(m.group(1)) - 1], query)
