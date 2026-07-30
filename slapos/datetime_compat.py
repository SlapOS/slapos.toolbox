import datetime

# datetime's UTC alias needs Python 3.11+; package supports 3.8+.
UTC_compat = getattr(datetime, 'UTC', datetime.timezone.utc)
