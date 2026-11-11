from django.dispatch import Signal

# Sent after the transaction that created the ticket commits.
# Arguments: sender, ticket, request_url (absolute URL of the ticket, may be "").
ticket_created = Signal()
